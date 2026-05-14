from typing import Any, Optional
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
try:
    from fastapi import FastAPI, Query
    from pydantic import BaseModel
    from fastapi.responses import JSONResponse, FileResponse, Response
    from fastapi.staticfiles import StaticFiles
except ModuleNotFoundError:
    def Query(default=None, **_kwargs):
        return default

    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    class Response:
        def __init__(self, content="", media_type=None):
            self.content = content
            self.media_type = media_type

    class JSONResponse(dict):
        pass

    class FileResponse:
        def __init__(self, path):
            self.path = path

    class StaticFiles:
        def __init__(self, directory):
            self.directory = directory

    class FastAPI:
        def __init__(self, title=""):
            self.title = title

        def get(self, *_args, **_kwargs):
            return lambda fn: fn

        def post(self, *_args, **_kwargs):
            return lambda fn: fn

        def mount(self, *_args, **_kwargs):
            return None

        async def __call__(self, scope, receive, send):
            body = b"fastapi dependency missing"
            await send({
                "type": "http.response.start",
                "status": 503,
                "headers": [(b"content-type", b"text/plain")],
            })
            await send({"type": "http.response.body", "body": body})
import datetime
import os
import sqlite3
import sys

DB_PATH = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
BOT_DIR = Path(__file__).resolve().parent
if str(BOT_DIR) not in sys.path:
    sys.path.insert(0, str(BOT_DIR))

app = FastAPI(title="OpenClaw UI API")


def connect_db() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    return c


def table_exists(c: sqlite3.Connection, table: str) -> bool:
    row = c.execute(
        "select 1 from sqlite_master where type='table' and name=?",
        (table,),
    ).fetchone()
    return row is not None


def table_columns(c: sqlite3.Connection, table: str) -> set[str]:
    if not table_exists(c, table):
        return set()
    return {str(r["name"]) for r in c.execute(f"pragma table_info({table})").fetchall()}


def rows(c: sqlite3.Connection, sql: str, args=()):
    return [dict(r) for r in c.execute(sql, args).fetchall()]


class LocalOpenClawDBAdapter:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_router_tasks(self):
        with connect_db() as c:
            if not table_exists(c, "router_tasks"):
                return []
            order = "id desc" if "id" in table_columns(c, "router_tasks") else "rowid desc"
            return rows(c, f"select * from router_tasks order by {order} limit 1000")

    def get_parent_child_relations(self):
        with connect_db() as c:
            if not table_exists(c, "router_tasks"):
                return []
            cols = table_columns(c, "router_tasks")
            if not {"id", "parent_task_id"}.issubset(cols):
                return []
            return rows(
                c,
                """
                select parent_task_id as parent_id, id as child_id
                from router_tasks
                where parent_task_id is not null
                order by parent_task_id desc, id desc
                limit 1000
                """,
            )

    def get_execs(self):
        with connect_db() as c:
            if not table_exists(c, "router_tasks"):
                return []
            cols = table_columns(c, "router_tasks")
            if "mode" not in cols:
                return []
            return rows(
                c,
                """
                select *
                from router_tasks
                where coalesce(mode,'')='EXEC'
                   or coalesce(target_bot,'')='ops_exec'
                order by id desc
                limit 1000
                """,
            )

    def get_logs(self, task_id: Optional[int] = None, limit: int = 100):
        with connect_db() as c:
            for table in ("router_task_logs", "task_logs", "logs"):
                if not table_exists(c, table):
                    continue
                cols = table_columns(c, table)
                where = ""
                args: list[object] = []
                if task_id is not None:
                    if "task_id" in cols:
                        where = "where task_id=?"
                        args.append(task_id)
                    elif "router_task_id" in cols:
                        where = "where router_task_id=?"
                        args.append(task_id)
                order = "id desc" if "id" in cols else "rowid desc"
                args.append(limit)
                return rows(c, f"select * from {table} {where} order by {order} limit ?", args)
            return []

    def get_artifacts(self, task_id: Optional[int] = None):
        with connect_db() as c:
            for table in ("router_task_artifacts", "task_artifacts", "artifacts"):
                if not table_exists(c, table):
                    continue
                cols = table_columns(c, table)
                where = ""
                args: list[object] = []
                if task_id is not None:
                    if "task_id" in cols:
                        where = "where task_id=?"
                        args.append(task_id)
                    elif "router_task_id" in cols:
                        where = "where router_task_id=?"
                        args.append(task_id)
                order = "id desc" if "id" in cols else "rowid desc"
                return rows(c, f"select * from {table} {where} order by {order} limit 1000", args)
            return []

    def get_capabilities(self):
        with connect_db() as c:
            for table in ("capability_registry", "capabilities"):
                if not table_exists(c, table):
                    continue
                cols = table_columns(c, table)
                order = "id desc" if "id" in cols else "rowid desc"
                return rows(c, f"select * from {table} order by {order} limit 1000")
            return []


def adapter() -> LocalOpenClawDBAdapter:
    return LocalOpenClawDBAdapter(DB_PATH)

@app.get("/")
def root():
    html = open("ui/index.html", encoding="utf-8").read()
    return Response(content=html, media_type="text/html")

app.mount("/ui", StaticFiles(directory="ui"), name="ui")

@app.get("/health")
def health():
    return {"ok": True, "db_path": DB_PATH}


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def render_text(fn, *args) -> str:
    buf = StringIO()
    with redirect_stdout(buf):
        fn(*args)
    return buf.getvalue().strip()


def report_response(report: str, **extra):
    data = {
        "ok": True,
        "report": report,
        "generated_at": now_iso(),
    }
    data.update(extra)
    return data


def dataclass_like(value: Any) -> dict[str, Any]:
    if hasattr(value, "__dataclass_fields__"):
        return {key: getattr(value, key) for key in value.__dataclass_fields__}
    if isinstance(value, dict):
        return value
    return {}


def incident_like(value: Any) -> dict[str, Any]:
    return {
        "incident_key": getattr(value, "incident_key", ""),
        "pattern_key": getattr(value, "pattern_key", ""),
        "detected_at": getattr(value, "detected_at", ""),
        "severity": getattr(value, "severity", ""),
        "signals": getattr(value, "signals", {}),
        "diagnosis": getattr(value, "diagnosis", {}),
        "remediation": getattr(value, "remediation", {}),
        "outcome": getattr(value, "outcome", {}),
        "bottlenecks": getattr(value, "bottlenecks", []),
        "forecast": getattr(value, "forecast", {}),
    }


def remediation_comparison(arbitration: dict[str, Any], plan: Any) -> list[dict[str, Any]]:
    base_sustainability = int(getattr(plan, "sustainability_score", 0))
    items = []
    for row in arbitration.get("ranked", [])[:5]:
        candidate = row.get("candidate")
        data = dataclass_like(candidate)
        metrics = data.get("metrics", {})
        projected_gain = int(metrics.get("projected_health_gain", 0))
        stability = int(metrics.get("operational_stability", 0))
        items.append(
            {
                "strategy_key": data.get("strategy_key", ""),
                "recommended_action": data.get("recommended_action", ""),
                "priority_class": data.get("priority_class", ""),
                "tradeoff_reason": data.get("tradeoff_reason", ""),
                "expected_benefits": data.get("expected_benefits", []),
                "expected_costs": data.get("expected_costs", []),
                "projected_health_gain": projected_gain,
                "projected_instability_reduction": max(0, stability - (100 - projected_gain)),
                "projected_sustainability_delta": max(-30, min(30, projected_gain // 2 + stability // 8 - base_sustainability // 10)),
                "confidence_score": int(row.get("score", 0)),
                "safety_alignment": data.get("safety_alignment", ""),
                "metrics": metrics,
            }
        )
    return items


def build_timeline(incidents: list[Any], policy_history: list[dict[str, Any]], loop: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for incident in incidents[-8:]:
        item = incident_like(incident)
        signals = item["signals"] or {}
        events.append(
            {
                "kind": "incident",
                "at": item["detected_at"],
                "title": item["pattern_key"].replace("_", " ") or item["incident_key"],
                "detail": item["diagnosis"].get("summary", item["severity"]),
                "severity": item["severity"],
                "value": int(signals.get("retry_count growth", signals.get("deferred backlog", 0)) or 0),
            }
        )
        attempt = str((item["remediation"] or {}).get("attempt", "")).strip()
        if attempt:
            events.append(
                {
                    "kind": "remediation",
                    "at": item["detected_at"],
                    "title": attempt,
                    "detail": f"effectiveness={item['outcome'].get('effectiveness', 'unknown')}",
                    "severity": item["severity"],
                    "value": int((item["forecast"] or {}).get("recurring_risk", 0) or 0),
                }
            )
    for row in policy_history[-8:]:
        events.append(
            {
                "kind": "policy",
                "at": str(row.get("selected_at", "")),
                "title": str(row.get("policy_name", "")),
                "detail": f"status={row.get('status', 'unknown')} effective={str(row.get('effective', 'unknown')).lower()}",
                "severity": "MEDIUM" if not row.get("effective", True) else "LOW",
                "value": 1,
            }
        )
    health = loop.get("health", {})
    events.append(
        {
            "kind": "instability",
            "at": now_iso(),
            "title": "current instability spike",
            "detail": f"instability={health.get('instability_score', 0)} retry={health.get('retry_pressure', 0)} deferred={health.get('deferred_backlog', 0)}",
            "severity": "HIGH" if int(health.get("instability_score", 0)) >= 55 else "LOW",
            "value": int(health.get("instability_score", 0)),
        }
    )
    return sorted(events, key=lambda x: str(x.get("at", "")), reverse=True)[:16]


def drift_summary(loop: dict[str, Any], policy_result: dict[str, Any], plan: Any) -> dict[str, Any]:
    health = loop.get("health", {})
    transitions = policy_result.get("transitions", {})
    retry = int(health.get("retry_pressure", 0))
    deferred = int(health.get("deferred_backlog", 0))
    operator = int(getattr(plan, "operator_load_score", 0))
    flapping = int(transitions.get("recent_switch_count", 0))
    return {
        "retry_amplification_trend": {
            "label": "critical" if retry >= 120 else "warning" if retry >= 20 else "stable",
            "value": retry,
            "series": [max(0, retry - 160), max(0, retry - 90), max(0, retry - 45), retry],
        },
        "deferred_queue_growth_trend": {
            "label": "critical" if deferred >= 1000 else "warning" if deferred >= 50 else "stable",
            "value": deferred,
            "series": [max(0, deferred - 900), max(0, deferred - 460), max(0, deferred - 120), deferred],
        },
        "operator_load_trend": {
            "label": "critical" if operator >= 80 else "warning" if operator >= 55 else "stable",
            "value": operator,
            "series": [max(0, operator - 22), max(0, operator - 12), max(0, operator - 5), operator],
        },
        "policy_flapping_frequency": {
            "label": "critical" if transitions.get("policy_flapping_detected") else "warning" if flapping else "stable",
            "value": flapping,
            "series": [0, max(0, flapping - 2), max(0, flapping - 1), flapping],
        },
    }


def compact_loop_summary(loop: dict[str, Any]) -> dict[str, Any]:
    health = loop.get("health", {})
    root = loop.get("root", {})
    hotspot = loop.get("hotspot", {})
    return {
        "status": loop.get("current_mode", "unknown"),
        "loop_state": loop.get("loop_state", "unknown"),
        "health_score": health.get("health_score", 0),
        "instability_score": health.get("instability_score", 0),
        "deferred_backlog": health.get("deferred_backlog", 0),
        "retry_pressure": health.get("retry_pressure", 0),
        "top_risk": loop.get("top_risk", "unknown"),
        "root_cause": root.get("label", "unknown"),
        "root_confidence": root.get("confidence", 0),
        "root_chain": loop.get("root_chain", []),
        "root_chain_score": loop.get("root_chain_score", 0),
        "hotspot": hotspot.get("label", "unknown"),
        "best_safe_remediation": loop.get("best_safe_remediation", ""),
        "projected_health_gain": loop.get("projected_health_gain", 0),
        "actions": loop.get("actions", []),
        "watchlist": loop.get("watchlist", []),
        "simulation_outcomes": loop.get("simulation_outcomes", []),
        "historical_note": loop.get("historical_note", ""),
        "decision_trace": loop.get("decision_trace", []),
        "memory_source": loop.get("memory_source", "unknown"),
        "operational_memory_update_plan": loop.get("operational_memory_update_plan", {}),
    }


def compact_plan_summary(plan: Any) -> dict[str, Any]:
    return {
        "planning_horizon": plan.horizon,
        "planning_mode": plan.planning_mode,
        "sustainability_score": plan.sustainability_score,
        "recurrence_risk": plan.recurrence_risk,
        "recurrence_risk_score": plan.recurrence_risk_score,
        "maintenance_pressure": plan.maintenance_pressure,
        "maintenance_pressure_score": plan.maintenance_pressure_score,
        "operator_load": plan.operator_load,
        "operator_load_score": plan.operator_load_score,
        "stability_projection": plan.stability_projection,
        "stability_projection_score": plan.stability_projection_score,
        "dominant_long_term_risk": plan.dominant_long_term_risk,
        "recommended_long_horizon_focus": plan.recommended_long_horizon_focus,
        "anti_patterns": plan.anti_patterns,
        "supporting_signals": plan.supporting_signals,
        "scoring_examples": plan.scoring_examples,
    }


APPROVAL_STATES = ["proposed", "reviewing", "approved_dry_run", "rejected", "archived"]


def clamp_int(value: Any, minimum: int = 0, maximum: int = 100) -> int:
    try:
        return max(minimum, min(maximum, int(float(value))))
    except (TypeError, ValueError):
        return minimum


def parse_time(value: str) -> datetime.datetime | None:
    if not value:
        return None
    try:
        clean = value.replace("Z", "+00:00")
        parsed = datetime.datetime.fromisoformat(clean)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
        return parsed
    except ValueError:
        return None


def recommendation_age(first_seen: str, last_updated: str) -> dict[str, Any]:
    now = datetime.datetime.now(datetime.timezone.utc)
    first = parse_time(first_seen)
    updated = parse_time(last_updated)
    age_hours = int((now - first).total_seconds() // 3600) if first else 0
    updated_hours = int((now - updated).total_seconds() // 3600) if updated else 0
    if age_hours >= 168:
        stale = "high"
    elif age_hours >= 24 or updated_hours >= 12:
        stale = "medium"
    else:
        stale = "low"
    return {
        "first_seen": first_seen,
        "last_updated": last_updated,
        "recommendation_age_hours": age_hours,
        "recommendation_age": f"{age_hours}h",
        "stale_risk": stale,
    }


def text_score(text: str, keywords: list[str], base: int, bonus: int = 20) -> int:
    low = text.lower()
    score = base
    for keyword in keywords:
        if keyword.lower() in low:
            score += bonus
    return clamp_int(score)


def alignment_scores(candidate: dict[str, Any], plan: dict[str, Any]) -> dict[str, int]:
    text = " ".join(
        str(candidate.get(key, ""))
        for key in ("recommended_action", "strategy_key", "tradeoff_reason")
    )
    benefits = " ".join(str(x) for x in candidate.get("expected_benefits", []))
    costs = " ".join(str(x) for x in candidate.get("expected_costs", []))
    all_text = " ".join([text, benefits, costs, plan.get("recommended_long_horizon_focus", "")])
    stability = clamp_int(candidate.get("metrics", {}).get("operational_stability", 50))
    projected_gain = clamp_int(candidate.get("projected_health_gain", 0))
    return {
        "revenue_impact": text_score(all_text, ["revenue", "money", "earn", "sales", "稼ぐ", "売上", "収益"], 35),
        "infrastructure_impact": text_score(all_text, ["runtime", "db", "queue", "service", "health", "cleanup", "infra"], 35),
        "autonomy_progression_impact": text_score(all_text, ["approval", "dry-run", "autonomy", "policy", "governance", "自律"], 30),
        "operational_stability_impact": clamp_int(stability + projected_gain // 3),
    }


def risk_level_for(candidate: dict[str, Any], plan: dict[str, Any], operator_load_score: int) -> str:
    safety = str(candidate.get("safety_alignment", "")).lower()
    confidence = clamp_int(candidate.get("confidence_score", 0))
    recurrence = clamp_int(plan.get("recurrence_risk_score", 0))
    if safety and safety != "pass":
        return "critical"
    if recurrence >= 80 or operator_load_score >= 80:
        return "critical"
    if confidence < 55 or recurrence >= 60 or operator_load_score >= 55:
        return "high"
    return "medium"


def approval_state_for(risk_level: str) -> str:
    if risk_level in {"critical", "high"}:
        return "reviewing"
    return "proposed"


def build_governance_recommendations() -> dict[str, Any]:
    generated_at = now_iso()
    try:
        from dev_autopilot_executive_report_v1 import build_report

        report = build_report(DB_PATH)
        plan = compact_plan_summary(report["plan"])
        comparison = remediation_comparison(report["arbitration"], report["plan"])
        explanation = report.get("policy", {}).get("selected")
        policy_reason = getattr(explanation, "selection_reason", "")
        history = report.get("policy", {}).get("history", [])
        first_seen = str((history[0] if history else {}).get("selected_at", generated_at))
        last_updated = str((history[-1] if history else {}).get("selected_at", generated_at))
        operator_load_score = clamp_int(plan.get("operator_load_score", 0))
        operator_overload = operator_load_score >= 70
        max_items = 2 if operator_overload else 5
        rejected = [
            {
                "recommendation": item.get("recommended_action", ""),
                "reason": item.get("tradeoff_reason", ""),
                "confidence": item.get("confidence_score", 0),
            }
            for item in comparison[1:5]
        ]
        seen: set[str] = set()
        items = []
        for idx, candidate in enumerate(comparison):
            recommendation = str(candidate.get("recommended_action") or candidate.get("strategy_key") or "Review recommendation")
            duplicate_key = " ".join(recommendation.lower().split())[:120]
            if duplicate_key in seen:
                continue
            seen.add(duplicate_key)
            risk_level = risk_level_for(candidate, plan, operator_load_score)
            age = recommendation_age(first_seen, last_updated)
            projected_gain = clamp_int(candidate.get("projected_health_gain", 0))
            confidence = clamp_int(candidate.get("confidence_score", 0))
            item_rejected = rejected if idx == 0 else [
                {
                    "recommendation": comparison[0].get("recommended_action", ""),
                    "reason": "Selected item has stronger expected value under current risk.",
                    "confidence": comparison[0].get("confidence_score", 0),
                }
            ]
            items.append(
                {
                    "id": f"governance-{idx + 1}",
                    "state": approval_state_for(risk_level),
                    "recommendation": recommendation,
                    "expected_value": "; ".join(candidate.get("expected_benefits", [])[:3]) or "Expected to improve operational reliability.",
                    "risk": candidate.get("tradeoff_reason") or plan.get("dominant_long_term_risk", "unknown"),
                    "risk_level": risk_level,
                    "projected_gain": projected_gain,
                    "rollback_difficulty": "medium" if risk_level == "medium" else "high",
                    "confidence": confidence,
                    "why_selected": candidate.get("tradeoff_reason") or policy_reason or "Highest ranked safe recommendation.",
                    "rejected_alternatives": item_rejected,
                    "governance_reasoning": {
                        "why_now": f"{plan.get('dominant_long_term_risk', 'current risk')} with operator_load={operator_load_score}.",
                        "why_safe": "Recommendation only. Execution is disabled; dry-run review is the maximum allowed next step.",
                        "why_not_alternatives": "Lower-ranked alternatives have weaker expected value, confidence, or safety alignment.",
                        "expected_downside": "; ".join(candidate.get("expected_costs", [])[:3]) or "May consume operator review attention.",
                        "unknowns": [
                            "Actual production impact requires dry-run evidence.",
                            "Human approval is required before any execution-capable change.",
                        ],
                    },
                    "human_review_required": risk_level in {"critical", "high"},
                    "banner": {
                        "requires_human_approval": risk_level in {"critical", "high"},
                        "execution_disabled": True,
                        "dry_run_only": True,
                    },
                    "aging": age,
                    "strategic_alignment": alignment_scores(candidate, plan),
                    "safety_contract": [
                        "No POST",
                        "No DB writes",
                        "No launchctl",
                        "No deploy",
                        "No router_task creation",
                        "Recommendation only",
                    ],
                }
            )
            if len(items) >= max_items:
                break
        return {
            "ok": True,
            "generated_at": generated_at,
            "mode": "recommendation_only",
            "allowed_states": APPROVAL_STATES,
            "operator_load": {
                "score": operator_load_score,
                "level": "overload" if operator_overload else "normal",
                "recommendation_limit": max_items,
                "duplicate_noise_suppressed": True,
                "policy": "show only highest expected value items" if operator_overload else "show top recommendations",
            },
            "count": len(items),
            "items": items,
        }
    except Exception as e:
        return {
            "ok": False,
            "generated_at": generated_at,
            "mode": "recommendation_only",
            "allowed_states": APPROVAL_STATES,
            "operator_load": {
                "score": 0,
                "level": "unknown",
                "recommendation_limit": 0,
                "duplicate_noise_suppressed": True,
                "policy": "no recommendations while governance source is unavailable",
            },
            "count": 0,
            "items": [],
            "error": f"governance_source_unavailable:{e!r}",
            "safety_contract": [
                "No POST",
                "No DB writes",
                "No launchctl",
                "No deploy",
                "No router_task creation",
                "Recommendation only",
            ],
        }


@app.get("/api/dev-autopilot/compact")
def dev_autopilot_compact():
    from dev_autopilot_executive_report_v1 import build_report, print_compact
    from dev_autopilot_memory_v1 import load_incidents

    report = build_report(DB_PATH)
    plan = compact_plan_summary(report["plan"])
    policy = report["policy"]
    arbitration = report["arbitration"]
    incidents, memory_source = load_incidents(DB_PATH)
    return report_response(
        render_text(print_compact, report),
        summary={
            "status": report["status"],
            "health": report["overall_health"],
            "top_risk": report["top_risk"],
            "root_cause": report["root_cause"],
            "root_chain": report["loop"].get("root_chain", []),
            "selected_policy": report["selected_policy"],
            "best_safe_next_action": report["best_safe_next_action"],
            "sustainability_score": plan["sustainability_score"],
            "do_not_do": [
                "no launchctl",
                "no deploy",
                "no git push",
                "no executable router_tasks",
                "no auto Codex",
            ],
        },
        loop=compact_loop_summary(report["loop"]),
        plan=plan,
        timeline=build_timeline(incidents, policy["history"], report["loop"]),
        comparison=remediation_comparison(arbitration, report["plan"]),
        policy_explanation={
            "selected_policy": report["selected_policy"],
            "arbitration_mode": arbitration["mode"],
            "reason": policy["selected"].selection_reason,
            "supporting_signals": policy["selected"].supporting_signals,
            "selected_strategy": arbitration["selected"].recommended_action,
            "selected_tradeoff": arbitration["selected"].tradeoff_reason,
            "rejected_alternatives": [
                {
                    "recommended_action": dataclass_like(row["candidate"]).get("recommended_action", ""),
                    "score": row.get("score", 0),
                    "reason": dataclass_like(row["candidate"]).get("tradeoff_reason", ""),
                }
                for row in arbitration.get("ranked", [])[1:5]
            ],
        },
        drift=drift_summary(report["loop"], policy, report["plan"]),
        memory_source=memory_source,
    )


@app.get("/api/dev-autopilot/report")
def dev_autopilot_report():
    from dev_autopilot_executive_report_v1 import build_report, print_report

    report = build_report(DB_PATH)
    return report_response(
        render_text(print_report, report),
        summary={
            "status": report["status"],
            "health": report["overall_health"],
            "top_risk": report["top_risk"],
            "root_cause": report["root_cause"],
            "root_chain": report["loop"].get("root_chain", []),
            "selected_policy": report["selected_policy"],
            "best_safe_next_action": report["best_safe_next_action"],
            "sustainability_score": report["plan"].sustainability_score,
            "do_not_do": [
                "no launchctl",
                "no deploy",
                "no git push",
                "no executable router_tasks",
                "no auto Codex",
            ],
        },
    )


@app.get("/api/dev-autopilot/policy")
def dev_autopilot_policy():
    from dev_autopilot_arbitration_v1 import arbitrate
    from dev_autopilot_policy_v1 import print_policy, select_policy

    policy = select_policy(DB_PATH)
    selected = policy["selected"]
    arbitration = arbitrate(DB_PATH, selected.policy_name)
    return report_response(
        render_text(print_policy, policy),
        selected_policy=selected.policy_name,
        selection_confidence=selected.selection_confidence,
        summary={
            "selected_policy": selected.policy_name,
            "selection_confidence": selected.selection_confidence,
            "selection_reason": selected.selection_reason,
            "supporting_signals": selected.supporting_signals,
            "expected_behavior": selected.expected_behavior,
            "policy_scores": [dataclass_like(score) for score in policy["scores"]],
            "transitions": policy["transitions"],
            "history_source": policy["history_source"],
            "history": policy["history"][-12:],
            "arbitration_mode": arbitration["mode"],
            "selected_strategy": arbitration["selected"].recommended_action,
            "selected_tradeoff": arbitration["selected"].tradeoff_reason,
            "rejected_alternatives": [
                {
                    "recommended_action": dataclass_like(row["candidate"]).get("recommended_action", ""),
                    "score": row.get("score", 0),
                    "reason": dataclass_like(row["candidate"]).get("tradeoff_reason", ""),
                }
                for row in arbitration.get("ranked", [])[1:5]
            ],
        },
    )


@app.get("/api/dev-autopilot/loop")
def dev_autopilot_loop():
    from dev_autopilot_loop_v1 import build_loop, print_summary

    loop = build_loop(DB_PATH)
    return report_response(
        render_text(print_summary, loop),
        current_mode=loop["current_mode"],
        loop_state=loop["loop_state"],
        top_risk=loop["top_risk"],
        summary=compact_loop_summary(loop),
    )


@app.get("/api/dev-autopilot/risks")
def dev_autopilot_risks():
    from dev_autopilot_arbitration_v1 import arbitrate
    from dev_autopilot_policy_v1 import select_policy
    from dev_autopilot_planning_v1 import build_plan, print_plan

    plan = build_plan(DB_PATH, "7d")
    policy = select_policy(DB_PATH)
    arbitration = arbitrate(DB_PATH, policy["selected"].policy_name)
    return report_response(
        render_text(print_plan, plan),
        planning_horizon=plan.horizon,
        sustainability_score=plan.sustainability_score,
        recurrence_risk=plan.recurrence_risk,
        dominant_long_term_risk=plan.dominant_long_term_risk,
        summary=compact_plan_summary(plan),
        comparison=remediation_comparison(arbitration, plan),
    )


@app.get("/api/dev-autopilot/memory")
def dev_autopilot_memory():
    from dev_autopilot_memory_v1 import group_patterns, load_incidents, print_patterns

    incidents, source = load_incidents(DB_PATH)
    patterns = group_patterns(incidents)
    return report_response(
        render_text(print_patterns, patterns, source),
        summary={
            "source": source,
            "incident_count": len(incidents),
            "incidents": [incident_like(x) for x in incidents[-12:]],
            "patterns": patterns[:8],
        },
    )


@app.get("/api/goals/active")
def active_goal():
    from openclaw_goal_reader_v1 import read_active_goal

    goal = read_active_goal()
    return JSONResponse(goal)


@app.get("/api/governance/approval-queue")
def governance_approval_queue():
    return JSONResponse(build_governance_recommendations())


@app.get("/api/governance/summary")
def governance_summary():
    data = build_governance_recommendations()
    items = data.get("items", [])
    return JSONResponse(
        {
            "ok": data.get("ok", False),
            "generated_at": data.get("generated_at", now_iso()),
            "mode": data.get("mode", "recommendation_only"),
            "allowed_states": data.get("allowed_states", APPROVAL_STATES),
            "operator_load": data.get("operator_load", {}),
            "count": len(items),
            "states": {
                state: len([item for item in items if item.get("state") == state])
                for state in APPROVAL_STATES
            },
            "human_review_required": len([item for item in items if item.get("human_review_required")]),
            "execution_disabled": True,
            "dry_run_only": True,
        }
    )


class TaskCreate(BaseModel):
    target_bot: str = "kaikun04"
    mode: str = "THINK"
    task_role: str = ""
    parent_task_id: int | None = None
    task_text: str



class TaskAction(BaseModel):
    action: str
    target_bot: str = "kaikun04"
    mode: str = "THINK"

@app.post("/api/tasks")
def create_task(payload: TaskCreate):
    import sqlite3
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    c.execute("""
        insert into router_tasks(
          source_command_id, parent_task_id, task_role, mode, target_bot, task_text, status, created_at, updated_at
        ) values(
          0, ?, ?, ?, ?, ?, 'new', datetime('now'), datetime('now')
        )
    """, (
        payload.parent_task_id,
        payload.task_role or "",
        payload.mode,
        payload.target_bot,
        payload.task_text
    ))
    new_id = c.execute("select last_insert_rowid()").fetchone()[0]
    c.commit()
    c.close()
    return {"ok": True, "id": new_id}


class ExecCreate(BaseModel):
    script: str
    args: str = ""

@app.post("/api/exec")
def create_exec(payload: ExecCreate):
    import sqlite3
    allowed = {
        "db_health.sh",
        "git_status.sh",
        "status_core.sh",
        "kick_service.sh",
        "route_smoke.sh",
        "gh_pr_create.sh",
        "gh_pr_merge.sh",
        "git_commit_push.sh",
        "restart_service.sh",
        "fix_db.sh",
        "deploy_safe.sh",
        "run_python.sh",
        "log_check.sh"
    }
    script = (payload.script or "").strip()
    args = (payload.args or "").strip()
    if script not in allowed:
        return {"ok": False, "error": "script_not_allowed"}
    task_text = f"[EXEC]\nscript={script}"
    if args:
        task_text += f"\narg={args}"
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.execute("pragma busy_timeout=30000")
    c.execute("""
        insert into router_tasks(
          source_command_id, parent_task_id, task_role, mode, target_bot, task_text, status, created_at, updated_at
        ) values(
          0, null, '', 'EXEC', 'ops_exec', ?, 'new', datetime('now'), datetime('now')
        )
    """, (task_text,))
    new_id = c.execute("select last_insert_rowid()").fetchone()[0]
    c.commit()
    c.close()
    return {"ok": True, "id": new_id, "task_text": task_text}

@app.get("/api/tasks")
def tasks(limit: int = Query(100, ge=1, le=1000)):
    rows = adapter().get_router_tasks()
    rows = sorted(rows, key=lambda x: x.get("id", 0), reverse=True)[:limit]
    return {"count": len(rows), "items": rows}

@app.get("/api/relations")
def relations():
    rows = adapter().get_parent_child_relations()
    return {"count": len(rows), "items": rows}

@app.get("/api/execs")
def execs(limit: int = Query(100, ge=1, le=1000)):
    rows = adapter().get_execs()[:limit]
    return {"count": len(rows), "items": rows}

@app.get("/api/logs")
def logs(task_id: Optional[int] = None, limit: int = Query(100, ge=1, le=1000)):
    rows = adapter().get_logs(task_id=task_id, limit=limit)
    return {"count": len(rows), "items": rows}

@app.get("/api/artifacts")
def artifacts(task_id: Optional[int] = None):
    rows = adapter().get_artifacts(task_id=task_id)
    return {"count": len(rows), "items": rows}

@app.get("/api/capabilities")
def capabilities():
    rows = adapter().get_capabilities()
    return {"count": len(rows), "items": rows}



@app.get("/api/tmp_exec")
def tmp_exec(limit: int = Query(50, ge=1, le=200)):
    root = Path("/Users/doyopc/AI/openclaw-factory-daemon/tmp_exec")
    items = []
    if root.exists():
        for f in sorted(root.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
            try:
                items.append({
                    "name": f.name,
                    "size": f.stat().st_size,
                    "mtime": int(f.stat().st_mtime),
                    "content": f.read_text(encoding="utf-8", errors="ignore")[:2000]
                })
            except Exception as e:
                items.append({
                    "name": f.name,
                    "size": 0,
                    "mtime": 0,
                    "content": f"read_error:{e!r}"
                })
    return {"count": len(items), "items": items}

@app.get("/api/summary")
def summary():
    a = adapter()
    data = {
        "router_tasks": len(a.get_router_tasks()),
        "relations": len(a.get_parent_child_relations()),
        "execs": len(a.get_execs()),
        "artifacts": len(a.get_artifacts()),
        "capabilities": len(a.get_capabilities()),
    }
    return JSONResponse(data)


@app.post("/api/tasks/{task_id}/exec")
def force_exec(task_id: int):
    import sqlite3
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.execute("pragma busy_timeout=30000")

    c.execute("""
        update router_tasks
        set status='new',
            updated_at=datetime('now')
        where id=?
    """, (task_id,))

    c.commit()
    c.close()
    return {"ok": True, "task_id": task_id}


@app.post("/api/tasks/{task_id}/action")
def task_action(task_id: int, payload: TaskAction):
    import sqlite3
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")

    row = c.execute("""
        select *
        from router_tasks
        where id=?
    """, (task_id,)).fetchone()

    if not row:
        c.close()
        return {"ok": False, "error": "not_found", "task_id": task_id}

    action = (payload.action or "").strip().lower()

    if action == "cancel":
        c.execute("""
            update router_tasks
            set status='cancelled',
                updated_at=datetime('now')
            where id=?
        """, (task_id,))
        c.commit()
        c.close()
        return {"ok": True, "action": action, "task_id": task_id}

    if action == "rerun":
        c.execute("""
            update router_tasks
            set status='new',
                updated_at=datetime('now')
            where id=?
        """, (task_id,))
        c.commit()
        c.close()
        return {"ok": True, "action": action, "task_id": task_id}

    if action == "duplicate":
        c.execute("""
            insert into router_tasks(
              source_command_id, parent_task_id, task_role, mode, target_bot, task_text, status, created_at, updated_at
            ) values(
              ?, ?, ?, ?, ?, ?, 'new', datetime('now'), datetime('now')
            )
        """, (
            row["source_command_id"] or 0,
            row["parent_task_id"],
            row["task_role"] or "",
            payload.mode or row["mode"] or "THINK",
            payload.target_bot or row["target_bot"] or "kaikun04",
            row["task_text"] or ""
        ))
        new_id = c.execute("select last_insert_rowid()").fetchone()[0]
        c.commit()
        c.close()
        return {"ok": True, "action": action, "task_id": task_id, "new_id": new_id}

    c.close()
    return {"ok": False, "error": "invalid_action", "task_id": task_id, "action": action}



@app.get("/api/tmp_exec_html")
def tmp_exec_html(limit: int = Query(30, ge=1, le=100)):
    root = Path("/Users/doyopc/AI/openclaw-factory-daemon/public_preview/tmp_exec_lp")
    items = []
    if root.exists():
        for f in sorted(root.glob("*.html"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
            items.append({
                "name": f.name,
                "path": str(f),
                "mtime": int(f.stat().st_mtime),
                "size": f.stat().st_size
            })
    return {"count": len(items), "items": items}


@app.get("/api/tmp_exec_html_file")
def tmp_exec_html_file(name: str):
    from fastapi.responses import FileResponse
    path = Path("/Users/doyopc/AI/openclaw-factory-daemon/public_preview/tmp_exec_lp") / name
    if path.exists():
        return FileResponse(path)
    return {"error":"not found"}
