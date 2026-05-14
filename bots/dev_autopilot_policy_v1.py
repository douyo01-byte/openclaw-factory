from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any

from dev_autopilot_arbitration_v1 import (
    ARBITRATION_MODES,
    candidate_set,
    score_candidate,
    top_forecast_risk,
)
from dev_autopilot_causal_graph_v1 import clamp
from dev_autopilot_loop_v1 import build_loop
from dev_autopilot_memory_v1 import DB, connect, safe_json, table_exists


POLICIES = [
    "RECOVERY_FIRST",
    "STABILITY_FIRST",
    "THROUGHPUT_FIRST",
    "LOW_RISK_FIRST",
    "HUMAN_REVIEW_FIRST",
]

EXPECTED_BEHAVIOR = {
    "RECOVERY_FIRST": [
        "prefer highest projected health recovery",
        "accept moderate review complexity when safety alignment passes",
        "prioritize runaway containment proposals",
    ],
    "STABILITY_FIRST": [
        "prefer low-risk containment strategies",
        "reduce unstable remediation proposals",
        "increase explainability weighting",
    ],
    "THROUGHPUT_FIRST": [
        "prefer queue-drain and bottleneck relief proposals",
        "accept lower stability margin only under low health risk",
        "increase throughput weighting",
    ],
    "LOW_RISK_FIRST": [
        "prefer observation and reversible review steps",
        "minimize side effect risk",
        "defer aggressive recovery proposals",
    ],
    "HUMAN_REVIEW_FIRST": [
        "prioritize explicit operator review gates",
        "increase explanation requirements",
        "avoid policy actions with ambiguous safety posture",
    ],
}

FUTURE_PLACEHOLDERS = [
    "adaptive weighting",
    "operator preference learning",
    "long-horizon policy planning",
    "policy rollback heuristics",
]


@dataclass(frozen=True)
class PolicyScore:
    policy_name: str
    score: int
    selection_confidence: int
    selection_reason: str
    supporting_signals: list[str]
    expected_behavior: list[str]


def top_arbitration_by_mode(loop: dict[str, Any]) -> dict[str, dict[str, Any]]:
    candidates = candidate_set(loop)
    by_mode: dict[str, dict[str, Any]] = {}
    for mode in POLICIES:
        ranked = sorted(
            [{"candidate": c, "score": score_candidate(c, mode)} for c in candidates],
            key=lambda x: (-int(x["score"]), x["candidate"].strategy_key),
        )
        by_mode[mode] = ranked[0]
    return by_mode


def trend_escalation_score(loop: dict[str, Any]) -> int:
    health = loop.get("health", {})
    retry_pressure = int(health.get("retry_pressure", 0))
    deferred = int(health.get("deferred_backlog", 0))
    age = int(health.get("oldest_task_age_seconds", 0))
    return clamp(min(35, retry_pressure / 80) + min(35, deferred / 500) + min(30, age / 3600))


def remediation_harm_score(loop: dict[str, Any]) -> int:
    patterns = loop.get("patterns", [])
    if not patterns:
        return 25
    top = patterns[0]
    effectiveness = str(top.get("historical_effectiveness", "")).upper()
    improvement = int(float(top.get("avg_improvement_score", 0)))
    if "INEFFECTIVE" in effectiveness:
        return clamp(70 + (50 - improvement))
    if "PARTIALLY_EFFECTIVE" in effectiveness:
        return clamp(42 + max(0, 55 - improvement))
    return clamp(20 + max(0, 45 - improvement))


def policy_scores(loop: dict[str, Any]) -> list[PolicyScore]:
    health = loop.get("health", {})
    health_score = int(health.get("health_score", 50))
    instability = int(health.get("instability_score", 50))
    forecast_risk = top_forecast_risk(loop.get("patterns", []))
    root_confidence = int(loop.get("root", {}).get("confidence", 0))
    hotspot = loop.get("hotspot", {})
    hotspot_label = str(hotspot.get("label", "unknown"))
    hotspot_pressure = int(hotspot.get("downstream_instability", 0))
    arbitration = top_arbitration_by_mode(loop)
    trend = trend_escalation_score(loop)
    harm = remediation_harm_score(loop)
    pending_approvals = int(health.get("pending_approvals", 0))
    proposal_backlog = int(health.get("proposal_backlog", 0))

    raw_scores = {
        "RECOVERY_FIRST": (
            (100 - health_score) * 0.30
            + forecast_risk * 0.24
            + hotspot_pressure * 0.18
            + root_confidence * 0.15
            + trend * 0.08
            + int(arbitration["RECOVERY_FIRST"]["score"]) * 0.05
            - harm * 0.10
        ),
        "STABILITY_FIRST": (
            instability * 0.25
            + hotspot_pressure * 0.24
            + trend * 0.18
            + harm * 0.16
            + forecast_risk * 0.10
            + int(arbitration["STABILITY_FIRST"]["score"]) * 0.07
        ),
        "THROUGHPUT_FIRST": (
            max(0, pending_approvals * 3) * 0.18
            + max(0, proposal_backlog * 5) * 0.16
            + int(arbitration["THROUGHPUT_FIRST"]["score"]) * 0.20
            + health_score * 0.20
            - instability * 0.18
            - forecast_risk * 0.08
        ),
        "LOW_RISK_FIRST": (
            health_score * 0.18
            + (100 - forecast_risk) * 0.22
            + (100 - instability) * 0.22
            + int(arbitration["LOW_RISK_FIRST"]["score"]) * 0.18
            + (100 - harm) * 0.20
        ),
        "HUMAN_REVIEW_FIRST": (
            harm * 0.20
            + root_confidence * 0.15
            + hotspot_pressure * 0.13
            + int(arbitration["HUMAN_REVIEW_FIRST"]["score"]) * 0.18
            + max(0, pending_approvals * 4) * 0.12
            + forecast_risk * 0.12
            + trend * 0.10
        ),
    }

    reasons = {
        "RECOVERY_FIRST": "critical health and runaway forecast favor recovery containment",
        "STABILITY_FIRST": "retry amplification and worker starvation instability outweigh throughput recovery benefits",
        "THROUGHPUT_FIRST": "low health risk and backlog pressure favor throughput recovery",
        "LOW_RISK_FIRST": "low instability and low forecast pressure favor reversible low-risk review",
        "HUMAN_REVIEW_FIRST": "high ambiguity or harmful history requires explicit operator review first",
    }

    supporting = {
        "RECOVERY_FIRST": [
            f"health_score={health_score}",
            f"forecast_risk={forecast_risk}",
            f"causal_hotspot={hotspot_label}",
            f"trend_escalation={trend}",
        ],
        "STABILITY_FIRST": [
            "high causal amplification",
            f"hotspot={hotspot_label}",
            f"instability_score={instability}",
            f"historical_harm_pressure={harm}",
        ],
        "THROUGHPUT_FIRST": [
            f"pending_approvals={pending_approvals}",
            f"proposal_backlog={proposal_backlog}",
            f"health_score={health_score}",
        ],
        "LOW_RISK_FIRST": [
            f"health_score={health_score}",
            f"forecast_risk={forecast_risk}",
            f"instability_score={instability}",
        ],
        "HUMAN_REVIEW_FIRST": [
            f"root_confidence={root_confidence}",
            f"historical_harm_pressure={harm}",
            "human approval required",
        ],
    }

    ordered: list[PolicyScore] = []
    for policy in POLICIES:
        score = clamp(raw_scores[policy])
        ordered.append(
            PolicyScore(
                policy_name=policy,
                score=score,
                selection_confidence=score,
                selection_reason=reasons[policy],
                supporting_signals=supporting[policy],
                expected_behavior=EXPECTED_BEHAVIOR[policy],
            )
        )
    return sorted(ordered, key=lambda x: (-x.score, x.policy_name))


def load_policy_history(db_path: str) -> tuple[list[dict[str, Any]], str]:
    con = connect(db_path)
    if con is None:
        return example_policy_history(), "example"
    try:
        candidates = [
            "dev_autopilot_policy_history",
            "dev_autopilot_policy_transitions",
            "operational_policy_history",
        ]
        for table in candidates:
            if not table_exists(con, table):
                continue
            cols = {str(r["name"]) for r in con.execute(f"pragma table_info({table})").fetchall()}
            policy_col = "policy_name" if "policy_name" in cols else "selected_policy" if "selected_policy" in cols else ""
            time_col = "selected_at" if "selected_at" in cols else "created_at" if "created_at" in cols else "detected_at" if "detected_at" in cols else ""
            if not policy_col:
                continue
            select_cols = [policy_col]
            if time_col:
                select_cols.append(time_col)
            if "outcome_json" in cols:
                select_cols.append("outcome_json")
            if "status" in cols:
                select_cols.append("status")
            rows = con.execute(
                f"select {', '.join(select_cols)} from {table} order by rowid desc limit 12"
            ).fetchall()
            history = []
            for idx, row in enumerate(reversed(rows)):
                outcome = safe_json(row["outcome_json"], {}) if "outcome_json" in row.keys() else {}
                history.append(
                    {
                        "policy_name": str(row[policy_col]),
                        "selected_at": str(row[time_col]) if time_col else f"history-{idx}",
                        "status": str(row["status"]) if "status" in row.keys() else str(outcome.get("status", "unknown")),
                        "effective": bool(outcome.get("effective", str(outcome.get("status", "")).lower() == "effective")),
                    }
                )
            if history:
                return history, table
    finally:
        con.close()
    return example_policy_history(), "example"


def example_policy_history() -> list[dict[str, Any]]:
    return [
        {"policy_name": "RECOVERY_FIRST", "selected_at": "2026-05-11 09:00:00", "status": "partial", "effective": True},
        {"policy_name": "STABILITY_FIRST", "selected_at": "2026-05-11 14:00:00", "status": "partial", "effective": True},
        {"policy_name": "RECOVERY_FIRST", "selected_at": "2026-05-12 09:00:00", "status": "failed", "effective": False},
        {"policy_name": "STABILITY_FIRST", "selected_at": "2026-05-12 16:00:00", "status": "partial", "effective": True},
        {"policy_name": "HUMAN_REVIEW_FIRST", "selected_at": "2026-05-13 08:00:00", "status": "safe", "effective": True},
    ]


def transition_analysis(history: list[dict[str, Any]], selected_policy: str) -> dict[str, Any]:
    names = [str(x.get("policy_name", "")) for x in history if str(x.get("policy_name", ""))]
    switches = sum(1 for a, b in zip(names, names[1:]) if a != b)
    recent = names[-5:]
    recent_switches = sum(1 for a, b in zip(recent, recent[1:]) if a != b)
    failed_counts: dict[str, int] = {}
    for row in history:
        if not bool(row.get("effective", False)):
            name = str(row.get("policy_name", ""))
            failed_counts[name] = failed_counts.get(name, 0) + 1
    flapping = recent_switches >= 3
    repeated_failed = {k: v for k, v in failed_counts.items() if v >= 2}
    unstable_switching = switches >= max(3, len(names) // 2)
    return {
        "selected_policy": selected_policy,
        "history_count": len(history),
        "switch_count": switches,
        "recent_switch_count": recent_switches,
        "policy_flapping_detected": flapping,
        "unstable_policy_switching": unstable_switching,
        "repeated_failed_policy_modes": repeated_failed,
        "transition_recommendation": (
            "hold selected policy for next human review window"
            if flapping or unstable_switching
            else "transition risk acceptable"
        ),
    }


def select_policy(db_path: str) -> dict[str, Any]:
    loop = build_loop(db_path)
    scores = policy_scores(loop)
    selected = scores[0]
    history, history_source = load_policy_history(db_path)
    transitions = transition_analysis(history, selected.policy_name)
    return {
        "loop": loop,
        "scores": scores,
        "selected": selected,
        "history": history,
        "history_source": history_source,
        "transitions": transitions,
    }


def print_list(items: list[str]) -> None:
    for item in items:
        print(f"- {item}")


def print_policy(result: dict[str, Any]) -> None:
    selected: PolicyScore = result["selected"]
    print("OPENCLAW OPERATIONAL POLICY")
    print("")
    print("selected_policy:")
    print(selected.policy_name)
    print("")
    print("selection_confidence:")
    print(selected.selection_confidence)
    print("")
    print("reason:")
    print(selected.selection_reason)
    print("")
    print("supporting_signals:")
    print_list(selected.supporting_signals)
    print("")
    print("expected_behavior:")
    print_list(selected.expected_behavior)
    print("")
    print("policy_scores:")
    for score in result["scores"]:
        print(f"- {score.policy_name}: {score.score}")
    print("")
    print("loop_context:")
    loop = result["loop"]
    print(f"- current_mode: {loop['current_mode']}")
    print(f"- loop_state: {loop['loop_state']}")
    print(f"- top_risk: {loop['top_risk']}")
    print(f"- root_cause: {loop['root'].get('label', 'unknown')}")
    print("")
    print("safety_policy:")
    print("- dry_run_default: true")
    print("- human_approval_required: true")
    print("- automatic_execution: false")


def print_transitions(result: dict[str, Any]) -> None:
    transitions = result["transitions"]
    print("OPENCLAW POLICY TRANSITION AWARENESS")
    print("")
    print(f"history_source: {result['history_source']}")
    print("")
    print("recent_policy_history:")
    for row in result["history"][-8:]:
        print(f"- {row['selected_at']}: {row['policy_name']} status={row['status']} effective={str(row['effective']).lower()}")
    print("")
    print("policy_flapping:")
    print(str(transitions["policy_flapping_detected"]).lower())
    print("")
    print("unstable_policy_switching:")
    print(str(transitions["unstable_policy_switching"]).lower())
    print("")
    print("repeated_failed_policy_modes:")
    failed = transitions["repeated_failed_policy_modes"]
    if failed:
        for name, count in failed.items():
            print(f"- {name}: {count}")
    else:
        print("- none")
    print("")
    print("transition_recommendation:")
    print(transitions["transition_recommendation"])
    print("")
    print("policy_flapping_examples:")
    print("- RECOVERY_FIRST -> STABILITY_FIRST -> RECOVERY_FIRST -> STABILITY_FIRST")
    print("- THROUGHPUT_FIRST -> LOW_RISK_FIRST -> THROUGHPUT_FIRST within short review windows")
    print("")
    print("future_extension_placeholders:")
    print_list(FUTURE_PLACEHOLDERS)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Deterministic adaptive operational policy selection.")
    ap.add_argument("--db", default=DB, help="SQLite database path. Default: DB_PATH/OCLAW_DB_PATH/FACTORY_DB_PATH or factory DB.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("policy", help="Select and explain the adaptive operational policy.")
    sub.add_parser("transitions", help="Show policy transition and flapping awareness.")
    return ap


def main() -> None:
    args = build_parser().parse_args()
    result = select_policy(args.db)
    if args.cmd == "policy":
        print_policy(result)
        return
    if args.cmd == "transitions":
        print_transitions(result)
        return
    raise SystemExit(f"unknown command: {args.cmd}")


if __name__ == "__main__":
    main()
