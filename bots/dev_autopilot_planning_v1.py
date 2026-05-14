from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any

from dev_autopilot_arbitration_v1 import arbitrate, top_forecast_risk
from dev_autopilot_causal_graph_v1 import clamp
from dev_autopilot_loop_v1 import build_loop
from dev_autopilot_policy_v1 import select_policy
from dev_autopilot_memory_v1 import DB


HORIZON_FACTORS = {
    "24h": {
        "risk_growth": 1.0,
        "operator_load": 0.7,
        "maintenance": 0.8,
        "policy_penalty": 0.6,
    },
    "7d": {
        "risk_growth": 1.35,
        "operator_load": 1.0,
        "maintenance": 1.0,
        "policy_penalty": 1.0,
    },
    "30d": {
        "risk_growth": 1.85,
        "operator_load": 1.4,
        "maintenance": 1.5,
        "policy_penalty": 1.45,
    },
}

PLANNING_MODES = [
    "STABILITY_SUSTAINMENT",
    "RECOVERY_ACCELERATION",
    "LOW_OPERATOR_LOAD",
    "SAFE_OPTIMIZATION",
    "RISK_CONTAINMENT",
]

FUTURE_PLACEHOLDERS = [
    "capacity forecasting",
    "operator burnout estimation",
    "infrastructure scaling plans",
    "adaptive maintenance windows",
]


@dataclass(frozen=True)
class LongHorizonPlan:
    horizon: str
    planning_mode: str
    sustainability_score: int
    recurrence_risk: str
    recurrence_risk_score: int
    maintenance_pressure: str
    maintenance_pressure_score: int
    operator_load: str
    operator_load_score: int
    stability_projection: str
    stability_projection_score: int
    dominant_long_term_risk: str
    recommended_long_horizon_focus: str
    anti_patterns: list[str]
    supporting_signals: list[str]
    scoring_examples: dict[str, int]


def label(value: int, high_label: str = "HIGH") -> str:
    if value >= 75:
        return high_label
    if value >= 45:
        return "MEDIUM"
    return "LOW"


def stability_label(value: int) -> str:
    if value >= 70:
        return "IMPROVING"
    if value >= 45:
        return "FRAGILE"
    return "DEGRADING"


def policy_instability_score(policy_result: dict[str, Any]) -> int:
    transitions = policy_result["transitions"]
    score = int(transitions["switch_count"]) * 12 + int(transitions["recent_switch_count"]) * 9
    if transitions["policy_flapping_detected"]:
        score += 22
    if transitions["unstable_policy_switching"]:
        score += 18
    score += sum(int(v) * 14 for v in transitions["repeated_failed_policy_modes"].values())
    return clamp(score)


def remediation_churn_score(loop: dict[str, Any], arbitration_result: dict[str, Any]) -> int:
    ranked = arbitration_result.get("ranked", [])
    near_ties = 0
    if ranked:
        top = int(ranked[0]["score"])
        near_ties = sum(1 for item in ranked[1:] if top - int(item["score"]) <= 5)
    partial_effective = 0
    for pattern in loop.get("patterns", []):
        if str(pattern.get("historical_effectiveness", "")).upper() == "PARTIALLY_EFFECTIVE":
            partial_effective += 1
    return clamp(near_ties * 16 + partial_effective * 11)


def approval_backlog_pressure(loop: dict[str, Any], horizon: str) -> int:
    health = loop.get("health", {})
    pending = int(health.get("pending_approvals", 0))
    proposals = int(health.get("proposal_backlog", 0))
    factor = HORIZON_FACTORS[horizon]["operator_load"]
    return clamp((pending * 5 + proposals * 4) * factor)


def recurrence_score(loop: dict[str, Any], horizon: str) -> int:
    risk = top_forecast_risk(loop.get("patterns", []))
    instability = int(loop.get("health", {}).get("instability_score", 0))
    hotspot_pressure = int(loop.get("hotspot", {}).get("downstream_instability", 0))
    factor = HORIZON_FACTORS[horizon]["risk_growth"]
    return clamp((risk * 0.42 + instability * 0.31 + hotspot_pressure * 0.27) * factor)


def maintenance_pressure_score(loop: dict[str, Any], arbitration_result: dict[str, Any], policy_result: dict[str, Any], horizon: str) -> int:
    churn = remediation_churn_score(loop, arbitration_result)
    policy_instability = policy_instability_score(policy_result)
    instability = int(loop.get("health", {}).get("instability_score", 0))
    factor = HORIZON_FACTORS[horizon]["maintenance"]
    return clamp((churn * 0.28 + policy_instability * 0.28 + instability * 0.44) * factor)


def operator_load_score(loop: dict[str, Any], policy_result: dict[str, Any], horizon: str) -> int:
    approval = approval_backlog_pressure(loop, horizon)
    policy_instability = policy_instability_score(policy_result)
    action_count = len(loop.get("actions", []))
    factor = HORIZON_FACTORS[horizon]["operator_load"]
    return clamp(approval * 0.45 + policy_instability * 0.35 + action_count * 7 * factor)


def stability_projection_score(loop: dict[str, Any], recurrence: int, maintenance: int, policy_result: dict[str, Any], horizon: str) -> int:
    health_score = int(loop.get("health", {}).get("health_score", 50))
    policy_score = int(policy_result["selected"].score)
    policy_penalty = policy_instability_score(policy_result) * HORIZON_FACTORS[horizon]["policy_penalty"] * 0.18
    return clamp(health_score * 0.30 + policy_score * 0.32 + (100 - recurrence) * 0.22 + (100 - maintenance) * 0.16 - policy_penalty)


def detect_anti_patterns(loop: dict[str, Any], policy_result: dict[str, Any], arbitration_result: dict[str, Any]) -> list[str]:
    anti: list[str] = []
    patterns = loop.get("patterns", [])
    names = [str(p.get("pattern_name", "")).lower() for p in patterns]
    if any("retry" in x for x in names) and remediation_churn_score(loop, arbitration_result) >= 30:
        anti.append("endless retry tuning loop")
    if any("deferred queue runaway" in x for x in names) and int(loop.get("health", {}).get("deferred_backlog", 0)) > 0:
        anti.append("recurring backlog runaway")
    if policy_result["transitions"]["policy_flapping_detected"]:
        anti.append("unstable policy oscillation")
    if any("approval stagnation" in x for x in names) or int(loop.get("health", {}).get("pending_approvals", 0)) >= 8:
        anti.append("chronic approval stagnation")
    return anti or ["no dominant long-term anti-pattern detected"]


def select_planning_mode(loop: dict[str, Any], policy_result: dict[str, Any], recurrence: int, operator_load: int, stability: int) -> str:
    selected_policy = policy_result["selected"].policy_name
    if operator_load >= 75:
        return "LOW_OPERATOR_LOAD"
    if recurrence >= 80:
        return "RISK_CONTAINMENT"
    if selected_policy == "RECOVERY_FIRST" and stability < 45:
        return "RECOVERY_ACCELERATION"
    if selected_policy in {"STABILITY_FIRST", "HUMAN_REVIEW_FIRST"} or int(loop.get("health", {}).get("instability_score", 0)) >= 60:
        return "STABILITY_SUSTAINMENT"
    return "SAFE_OPTIMIZATION"


def dominant_risk(loop: dict[str, Any], anti_patterns: list[str]) -> str:
    if any("retry" in x for x in anti_patterns):
        return "retry amplification recurrence"
    if any("backlog" in x for x in anti_patterns):
        return "deferred backlog runaway recurrence"
    if any("approval" in x for x in anti_patterns):
        return "approval stagnation accumulation"
    root = str(loop.get("root", {}).get("label", "operational instability"))
    return f"{root} recurrence"


def focus_for_mode(mode: str, dominant: str) -> str:
    if mode == "LOW_OPERATOR_LOAD":
        return "reduce manual review pressure before expanding remediation scope"
    if mode == "RISK_CONTAINMENT":
        return "contain recurring instability before throughput optimization"
    if mode == "RECOVERY_ACCELERATION":
        return "accelerate safe recovery while preserving human approval gates"
    if mode == "STABILITY_SUSTAINMENT":
        return "reduce causal amplification before throughput optimization"
    return f"optimize safely while monitoring {dominant}"


def build_plan(db_path: str, horizon: str) -> LongHorizonPlan:
    loop = build_loop(db_path)
    policy_result = select_policy(db_path)
    arbitration_result = arbitrate(db_path, policy_result["selected"].policy_name)
    recurrence = recurrence_score(loop, horizon)
    maintenance = maintenance_pressure_score(loop, arbitration_result, policy_result, horizon)
    operator = operator_load_score(loop, policy_result, horizon)
    stability = stability_projection_score(loop, recurrence, maintenance, policy_result, horizon)
    sustainability = clamp(
        stability * 0.38
        + (100 - recurrence) * 0.26
        + (100 - maintenance) * 0.20
        + (100 - operator) * 0.16
    )
    anti_patterns = detect_anti_patterns(loop, policy_result, arbitration_result)
    mode = select_planning_mode(loop, policy_result, recurrence, operator, stability)
    dominant = dominant_risk(loop, anti_patterns)
    focus = focus_for_mode(mode, dominant)
    selected_policy = policy_result["selected"].policy_name
    return LongHorizonPlan(
        horizon=horizon,
        planning_mode=mode,
        sustainability_score=sustainability,
        recurrence_risk=label(recurrence),
        recurrence_risk_score=recurrence,
        maintenance_pressure=label(maintenance),
        maintenance_pressure_score=maintenance,
        operator_load=label(operator),
        operator_load_score=operator,
        stability_projection=stability_label(stability),
        stability_projection_score=stability,
        dominant_long_term_risk=dominant,
        recommended_long_horizon_focus=focus,
        anti_patterns=anti_patterns,
        supporting_signals=[
            f"selected_policy={selected_policy}",
            f"loop_state={loop['loop_state']}",
            f"current_mode={loop['current_mode']}",
            f"top_risk={loop['top_risk']}",
            f"policy_flapping={str(policy_result['transitions']['policy_flapping_detected']).lower()}",
            f"arbitration_strategy={arbitration_result['selected'].recommended_action}",
        ],
        scoring_examples={
            "recurrence_risk": recurrence,
            "maintenance_pressure": maintenance,
            "operator_load": operator,
            "stability_projection": stability,
            "sustainability_score": sustainability,
        },
    )


def print_list(items: list[str]) -> None:
    for item in items:
        print(f"- {item}")


def print_plan(plan: LongHorizonPlan) -> None:
    print("OPENCLAW LONG-HORIZON PLAN")
    print("")
    print("planning_horizon:")
    print(plan.horizon)
    print("")
    print("planning_mode:")
    print(plan.planning_mode)
    print("")
    print("sustainability_score:")
    print(plan.sustainability_score)
    print("")
    print("recurrence_risk:")
    print(plan.recurrence_risk)
    print("")
    print("maintenance_pressure:")
    print(plan.maintenance_pressure)
    print("")
    print("operator_load:")
    print(plan.operator_load)
    print("")
    print("stability_projection:")
    print(plan.stability_projection)
    print("")
    print("dominant_long_term_risk:")
    print(plan.dominant_long_term_risk)
    print("")
    print("recommended_long_horizon_focus:")
    print(plan.recommended_long_horizon_focus)
    print("")
    print("supporting_signals:")
    print_list(plan.supporting_signals)
    print("")
    print("long_term_anti_patterns:")
    print_list(plan.anti_patterns)
    print("")
    print("sustainability_scoring:")
    for key, value in plan.scoring_examples.items():
        print(f"- {key}: {value}")
    print("")
    print("planning_mode_examples:")
    print_list(PLANNING_MODES)
    print("")
    print("future_extension_placeholders:")
    print_list(FUTURE_PLACEHOLDERS)
    print("")
    print("execution_policy:")
    print("- dry_run_default: true")
    print("- human_approval_required: true")
    print("- automatic_execution: false")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Deterministic long-horizon operational sustainability planning.")
    ap.add_argument("--db", default=DB, help="SQLite database path. Default: DB_PATH/OCLAW_DB_PATH/FACTORY_DB_PATH or factory DB.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    plan = sub.add_parser("plan", help="Produce long-horizon operational plan.")
    plan.add_argument("--horizon", choices=sorted(HORIZON_FACTORS), default="7d")
    return ap


def main() -> None:
    args = build_parser().parse_args()
    if args.cmd == "plan":
        print_plan(build_plan(args.db, args.horizon))
        return
    raise SystemExit(f"unknown command: {args.cmd}")


if __name__ == "__main__":
    main()
