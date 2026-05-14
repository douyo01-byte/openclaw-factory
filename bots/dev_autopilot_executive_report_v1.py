from __future__ import annotations

import argparse

from dev_autopilot_arbitration_v1 import arbitrate
from dev_autopilot_loop_v1 import build_loop
from dev_autopilot_memory_v1 import DB
from dev_autopilot_planning_v1 import build_plan
from dev_autopilot_policy_v1 import select_policy


DO_NOT_DO = [
    "no launchctl",
    "no deploy",
    "no git push",
    "no executable router_tasks",
    "no auto Codex",
    "no Telegram",
    "no subprocesses",
    "no external API spend",
]

SAFETY_CONSTRAINTS = [
    "read-only only",
    "dry-run posture",
    "human approval required",
    "no automatic execution",
    "no router_tasks creation",
]


def chain_text(chain: list[str]) -> str:
    return " -> ".join(x for x in chain if x) or "unknown"


def best_action(loop: dict, arbitration_result: dict) -> str:
    selected = arbitration_result.get("selected")
    action = ""
    if selected is not None:
        action = str(getattr(selected, "recommended_action", "")).strip()
    if not action:
        actions = loop.get("actions", [])
        if actions:
            action = str(actions[0].get("action", "")).strip()
    if "simulate cleanup thresholds" in action:
        return "approve dry-run cleanup simulation review"
    if action:
        return f"approve dry-run {action} review" if not action.startswith("approve") else action
    return "approve dry-run operational review"


def build_report(db_path: str) -> dict:
    loop = build_loop(db_path)
    policy = select_policy(db_path)
    selected_policy = policy["selected"].policy_name
    arbitration = arbitrate(db_path, selected_policy)
    plan_7d = build_plan(db_path, "7d")
    return {
        "loop": loop,
        "policy": policy,
        "arbitration": arbitration,
        "plan": plan_7d,
        "status": loop["current_mode"],
        "overall_health": loop["health"],
        "top_risk": loop["top_risk"],
        "root_cause": chain_text(loop["root_chain"]),
        "selected_policy": selected_policy,
        "best_safe_next_action": best_action(loop, arbitration),
        "long_horizon_warning": (
            f"{plan_7d.dominant_long_term_risk}; "
            f"{plan_7d.planning_mode}; "
            f"sustainability_score={plan_7d.sustainability_score}"
        ),
    }


def print_list(items: list[str]) -> None:
    for item in items:
        print(f"- {item}")


def print_report(report: dict) -> None:
    loop = report["loop"]
    plan = report["plan"]
    policy = report["policy"]["selected"]
    arbitration = report["arbitration"]
    selected = arbitration["selected"]
    health = report["overall_health"]

    print("OPENCLAW EXECUTIVE OPERATIONAL REPORT")
    print("")
    print("status:")
    print(report["status"])
    print("")
    print("current_mode:")
    print(report["status"])
    print("")
    print("overall_health:")
    print(f"- health_score: {health['health_score']}")
    print(f"- instability_score: {health['instability_score']}")
    print(f"- deferred_backlog: {health['deferred_backlog']}")
    print(f"- retry_pressure: {health['retry_pressure']}")
    print("")
    print("top_risk:")
    print(report["top_risk"])
    print("")
    print("root_cause:")
    print(report["root_cause"])
    print("")
    print("selected_policy:")
    print(report["selected_policy"])
    print("")
    print("policy_reason:")
    print(policy.selection_reason)
    print("")
    print("best_safe_remediation:")
    print(loop["best_safe_remediation"])
    print("")
    print("best_safe_next_action:")
    print(report["best_safe_next_action"])
    print("")
    print("arbitration_summary:")
    print(f"- strategy: {selected.recommended_action}")
    print(f"- priority_class: {selected.priority_class}")
    print(f"- safety_alignment: {selected.safety_alignment}")
    print("")
    print("long_horizon_warning:")
    print(report["long_horizon_warning"])
    print("")
    print("long_horizon_detail:")
    print(f"- horizon: {plan.horizon}")
    print(f"- recurrence_risk: {plan.recurrence_risk}")
    print(f"- operator_load: {plan.operator_load}")
    print(f"- focus: {plan.recommended_long_horizon_focus}")
    print("")
    print("recommended_human_action:")
    print(report["best_safe_next_action"])
    print("")
    print("safety_constraints_active:")
    print_list(SAFETY_CONSTRAINTS)
    print("")
    print("do_not_do:")
    print_list(DO_NOT_DO)


def print_compact(report: dict) -> None:
    print("OPENCLAW EXECUTIVE COMPACT")
    print("")
    print(f"status: {report['status']}")
    print(f"health: {report['overall_health']['health_score']} / instability {report['overall_health']['instability_score']}")
    print(f"top_risk: {report['top_risk']}")
    print(f"root_cause: {report['root_cause']}")
    print(f"selected_policy: {report['selected_policy']}")
    print(f"best_safe_next_action: {report['best_safe_next_action']}")
    print(f"long_horizon_warning: {report['long_horizon_warning']}")
    print("do_not_do: no launchctl; no deploy; no git push; no executable router_tasks; no auto Codex")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Read-only executive operational report for OpenClaw autopilot state.")
    ap.add_argument("--db", default=DB, help="SQLite database path. Default: DB_PATH/OCLAW_DB_PATH/FACTORY_DB_PATH or factory DB.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("report", help="Print full executive operational report.")
    sub.add_parser("compact", help="Print compact executive operational report.")
    return ap


def main() -> None:
    args = build_parser().parse_args()
    report = build_report(args.db)
    if args.cmd == "report":
        print_report(report)
        return
    if args.cmd == "compact":
        print_compact(report)
        return
    raise SystemExit(f"unknown command: {args.cmd}")


if __name__ == "__main__":
    main()
