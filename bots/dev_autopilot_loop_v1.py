from __future__ import annotations

import argparse
from typing import Any

from dev_autopilot_causal_graph_v1 import (
    build_edges,
    clamp,
    find_paths,
    format_chain,
    hotspot_candidates,
    load_context_snapshot,
    path_score,
    report_path,
    root_candidates,
)
from dev_autopilot_memory_v1 import (
    DB,
    current_state_signals,
    group_patterns,
    load_incidents,
)


FUTURE_PLACEHOLDERS = [
    "adaptive operational policies",
    "self-tuning remediation ranking",
    "operator preference memory",
    "long-horizon operational planning",
]


def numeric_signal(signals: dict[str, Any], key: str) -> int:
    value = signals.get(key, 0)
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value)
    except Exception:
        return 0


def current_health(signals: dict[str, Any]) -> dict[str, int]:
    deferred = numeric_signal(signals, "deferred backlog")
    new_backlog = numeric_signal(signals, "new task backlog")
    retries = numeric_signal(signals, "retry_count growth")
    oldest_age = numeric_signal(signals, "oldest task age")
    approvals = numeric_signal(signals, "pending approvals")
    proposals = numeric_signal(signals, "proposal backlog")

    instability = clamp(
        min(35, deferred / 400)
        + min(24, new_backlog / 450)
        + min(18, retries / 120)
        + min(15, oldest_age / 3600)
        + min(8, approvals / 3)
        + min(8, proposals / 8)
    )
    return {
        "instability_score": instability,
        "health_score": max(0, 100 - instability),
        "deferred_backlog": deferred,
        "new_task_backlog": new_backlog,
        "retry_pressure": retries,
        "oldest_task_age_seconds": oldest_age,
        "pending_approvals": approvals,
        "proposal_backlog": proposals,
    }


def classify_mode(health: dict[str, int], patterns: list[dict[str, Any]], root_confidence: int) -> str:
    top_risk = int(patterns[0]["forecast_recurring_risk"]) if patterns else 0
    instability = health["instability_score"]
    if instability >= 80 or root_confidence >= 92 or top_risk >= 80:
        return "CRITICAL_RECOVERY_MODE"
    if instability >= 55 or top_risk >= 65:
        return "STABILIZATION_MODE"
    return "NORMAL_OPTIMIZATION_MODE"


def classify_loop_state(mode: str, health: dict[str, int], root_confidence: int) -> str:
    instability = health["instability_score"]
    if mode == "CRITICAL_RECOVERY_MODE":
        return "STABILIZE"
    if instability >= 65:
        return "RECOVER"
    if root_confidence >= 70:
        return "INVESTIGATE"
    if instability <= 25:
        return "OPTIMIZE"
    return "WATCHLIST"


def best_remediation(patterns: list[dict[str, Any]]) -> str:
    for pattern in patterns:
        remediation = str(pattern.get("most_effective_remediation", "")).strip()
        if remediation:
            return remediation
    return "run dry-run causal investigation review"


def projected_gain(patterns: list[dict[str, Any]], health: dict[str, int], root_confidence: int) -> int:
    improvement = float(patterns[0].get("avg_improvement_score", 0)) if patterns else 40.0
    instability = health["instability_score"]
    return clamp(8 + improvement * 0.22 + root_confidence * 0.05 + instability * 0.04, 0, 35)


def historical_note(patterns: list[dict[str, Any]]) -> str:
    if not patterns:
        return "no persisted operational memory available; deterministic examples used"
    top = patterns[0]
    remediation = str(top.get("most_effective_remediation", "remediation")).strip()
    effectiveness = str(top.get("historical_effectiveness", "UNKNOWN")).lower()
    if remediation:
        return f"{remediation} previously {effectiveness.replace('_', ' ')}"
    return f"historical effectiveness: {effectiveness}"


def simulation_outcomes(patterns: list[dict[str, Any]], gain: int) -> list[str]:
    outcomes = []
    if patterns:
        top = patterns[0]
        outcomes.append(f"dry-run containment could improve health by +{gain}")
        outcomes.append(f"recurrence risk remains {top.get('forecast_recurring_risk', 0)} without containment")
        outcomes.append(f"expected bottleneck relief: {', '.join(top.get('associated_signals', [])[:2]) or 'unknown'}")
    else:
        outcomes.append(f"dry-run investigation could improve health by +{gain}")
        outcomes.append("recurrence risk unknown until memory tables are populated")
    return outcomes


def recommended_actions(
    mode: str,
    loop_state: str,
    root_label: str,
    hotspot_label: str,
    remediation: str,
    patterns: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    actions = [
        {
            "priority": "P0" if mode == "CRITICAL_RECOVERY_MODE" else "P1",
            "type": "manual_review",
            "action": f"approve dry-run {remediation} review",
            "reason": f"{root_label} is the highest-confidence upstream cause",
        },
        {
            "priority": "P1",
            "type": "investigation",
            "action": f"inspect {hotspot_label} propagation path",
            "reason": "highest amplification hotspot in causal graph",
        },
    ]
    if patterns:
        watch = str(patterns[min(1, len(patterns) - 1)].get("pattern_name", "")).lower()
        actions.append(
            {
                "priority": "P2",
                "type": "watchlist",
                "action": f"review recurrence guardrails for {watch}",
                "reason": "recurring operational pattern remains active in memory",
            }
        )
    if loop_state in {"STABILIZE", "RECOVER"}:
        actions.append(
            {
                "priority": "P1",
                "type": "safe_proposal",
                "action": "compare cleanup thresholds in dry-run only",
                "reason": "human approval required before any operational change",
            }
        )
    return actions


def build_loop(db_path: str) -> dict[str, Any]:
    incidents, memory_source = load_incidents(db_path)
    patterns = group_patterns(incidents)
    context = load_context_snapshot(db_path)
    edges = build_edges(incidents, context)
    roots = root_candidates(edges)
    hotspots = hotspot_candidates(edges)
    root = roots[0] if roots else {"signal": "", "label": "unknown", "confidence": 0}
    root_signal = str(root.get("signal", ""))
    path = report_path(edges, root_signal)
    if not path:
        paths = find_paths(edges)
        path = paths[0] if paths else []
    chain = format_chain(path)
    hotspot = hotspots[0] if hotspots else {"label": "unknown", "impact_multiplier": 0}
    signals = current_state_signals(db_path)
    health = current_health(signals)
    root_confidence = int(root.get("confidence", 0))
    mode = classify_mode(health, patterns, root_confidence)
    loop_state = classify_loop_state(mode, health, root_confidence)
    remediation = best_remediation(patterns)
    gain = projected_gain(patterns, health, root_confidence)
    actions = recommended_actions(
        mode=mode,
        loop_state=loop_state,
        root_label=str(root.get("label", "unknown")),
        hotspot_label=str(hotspot.get("label", "unknown")),
        remediation=remediation,
        patterns=patterns,
    )
    watchlist = [str(p.get("pattern_name", "")).lower() for p in patterns[1:3]]
    if str(root.get("label", "")).lower() not in watchlist:
        watchlist.append(str(root.get("label", "")).lower())

    return {
        "db": db_path,
        "memory_source": memory_source,
        "current_signals": signals,
        "health": health,
        "patterns": patterns,
        "edges": edges,
        "root": root,
        "root_chain": chain,
        "root_chain_score": round(path_score(path), 1) if path else 0,
        "hotspot": hotspot,
        "current_mode": mode,
        "loop_state": loop_state,
        "top_risk": str(hotspot.get("label", root.get("label", "unknown"))),
        "best_safe_remediation": remediation,
        "optimizer_recommendation": f"prefer human-reviewed dry-run containment for {root.get('label', 'unknown')}",
        "projected_health_gain": gain,
        "simulation_outcomes": simulation_outcomes(patterns, gain),
        "historical_note": historical_note(patterns),
        "watchlist": [x for x in watchlist if x and x != "unknown"][:4],
        "actions": actions,
        "decision_trace": [
            "telemetry/trend reads loaded current runtime counters",
            f"diagnosis selected {root.get('label', 'unknown')} as upstream cause",
            f"forecast ranked {patterns[0]['pattern_name'] if patterns else 'unknown'} as top recurrence risk",
            f"simulation estimated +{gain} projected health gain",
            f"optimizer selected {remediation} as safest constrained recommendation",
            "operational memory update remains a human-approved future write",
            "causal graph analysis selected propagation chain and hotspot",
        ],
        "operational_memory_update_plan": {
            "dry_run": True,
            "write_performed": False,
            "proposed_incident_note": f"{root.get('label', 'unknown')} -> {hotspot.get('label', 'unknown')}",
        },
        "source_context": context.get("source_tables", {}),
    }


def print_chain(chain: list[str]) -> None:
    for idx, item in enumerate(chain):
        if idx:
            print("  ->")
        print(item)


def print_loop_report(loop: dict[str, Any]) -> None:
    print("OPENCLAW OPERATIONAL LOOP REPORT")
    print("")
    print("current_mode:")
    print(loop["current_mode"])
    print("")
    print("loop_state:")
    print(loop["loop_state"])
    print("")
    print("current_operational_state:")
    health = loop["health"]
    print(f"- health_score: {health['health_score']}")
    print(f"- instability_score: {health['instability_score']}")
    print(f"- deferred_backlog: {health['deferred_backlog']}")
    print(f"- retry_pressure: {health['retry_pressure']}")
    print("")
    print("top_risk:")
    print(loop["top_risk"])
    print("")
    print("root_cause_chain:")
    print_chain(loop["root_chain"])
    print("")
    print("best_constrained_remediation:")
    print(loop["best_safe_remediation"])
    print("")
    print("best_safe_remediation:")
    print(loop["best_safe_remediation"])
    print("")
    print("optimizer_recommendation:")
    print(loop["optimizer_recommendation"])
    print("")
    print("projected_health_gain:")
    print(f"+{loop['projected_health_gain']}")
    print("")
    print("expected_future_risks:")
    for pattern in loop["patterns"][:3]:
        print(f"- {pattern['pattern_name']}: recurrence_risk={pattern['recurrence_risk']}")
    print("")
    print("simulation_outcomes:")
    for outcome in loop["simulation_outcomes"]:
        print(f"- {outcome}")
    print("")
    print("historical_effectiveness:")
    print(loop["historical_note"])
    print("")
    print("recommended_human_action:")
    print(loop["actions"][0]["action"])
    print("")
    print("decision_trace:")
    for step in loop["decision_trace"]:
        print(f"- {step}")
    print("")
    print("operational_memory_update_plan:")
    plan = loop["operational_memory_update_plan"]
    print(f"- dry_run: {str(plan['dry_run']).lower()}")
    print(f"- write_performed: {str(plan['write_performed']).lower()}")
    print(f"- proposed_incident_note: {plan['proposed_incident_note']}")
    print("")
    print("watchlist:")
    for item in loop["watchlist"]:
        print(f"- {item}")
    print("")
    print("historical_note:")
    print(loop["historical_note"])
    print("")
    print("human_approval_required:")
    print("true")


def print_summary(loop: dict[str, Any]) -> None:
    print("OPENCLAW LOOP SUMMARY")
    print("")
    print(f"current_mode: {loop['current_mode']}")
    print(f"loop_state: {loop['loop_state']}")
    print(f"top_risk: {loop['top_risk']}")
    print(f"root_cause: {loop['root'].get('label', 'unknown')}")
    print(f"root_confidence: {loop['root'].get('confidence', 0)}")
    print(f"hotspot: {loop['hotspot'].get('label', 'unknown')}")
    print(f"projected_health_gain: +{loop['projected_health_gain']}")
    print(f"best_safe_remediation: {loop['best_safe_remediation']}")


def print_next_actions(loop: dict[str, Any]) -> None:
    print("OPENCLAW HUMAN ACTION QUEUE")
    print("")
    print("execution_policy:")
    print("- dry_run_default: true")
    print("- human_approval_required: true")
    print("- executable_router_tasks_created: false")
    print("")
    print("highest_priority_manual_reviews:")
    for action in loop["actions"]:
        print(f"- {action['priority']} {action['type']}: {action['action']}")
        print(f"  reason: {action['reason']}")
    print("")
    print("safest_remediation_proposals:")
    print(f"- {loop['best_safe_remediation']}")
    print("- compare cleanup thresholds in dry-run only")
    print("- record outcome in operational memory after human review")
    print("")
    print("highest_confidence_investigations:")
    print(f"- inspect root chain score {loop['root_chain_score']}: {' -> '.join(loop['root_chain'])}")
    print(f"- inspect hotspot: {loop['hotspot'].get('label', 'unknown')}")
    print("")
    print("future_extension_placeholders:")
    for item in FUTURE_PLACEHOLDERS:
        print(f"- {item}")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Deterministic closed-loop operational learning coordinator.")
    ap.add_argument("--db", default=DB, help="SQLite database path. Default: DB_PATH/OCLAW_DB_PATH/FACTORY_DB_PATH or factory DB.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run", help="Produce the full operational loop report.")
    sub.add_parser("summary", help="Produce a compact loop summary.")
    sub.add_parser("next-actions", help="Produce human-review action queue.")
    return ap


def main() -> None:
    args = build_parser().parse_args()
    loop = build_loop(args.db)
    if args.cmd == "run":
        print_loop_report(loop)
        return
    if args.cmd == "summary":
        print_summary(loop)
        return
    if args.cmd == "next-actions":
        print_next_actions(loop)
        return
    raise SystemExit(f"unknown command: {args.cmd}")


if __name__ == "__main__":
    main()
