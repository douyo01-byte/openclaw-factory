from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any

from dev_autopilot_causal_graph_v1 import clamp
from dev_autopilot_loop_v1 import build_loop
from dev_autopilot_memory_v1 import DB


ARBITRATION_MODES = {
    "RECOVERY_FIRST": {
        "projected_health_gain": 0.26,
        "operational_stability": 0.18,
        "forecasted_risk_reduction": 0.20,
        "historical_effectiveness": 0.16,
        "side_effect_safety": 0.08,
        "human_review_simplicity": 0.05,
        "causal_propagation_reduction": 0.07,
    },
    "STABILITY_FIRST": {
        "projected_health_gain": 0.14,
        "operational_stability": 0.28,
        "forecasted_risk_reduction": 0.18,
        "historical_effectiveness": 0.13,
        "side_effect_safety": 0.14,
        "human_review_simplicity": 0.06,
        "causal_propagation_reduction": 0.07,
    },
    "THROUGHPUT_FIRST": {
        "projected_health_gain": 0.22,
        "operational_stability": 0.12,
        "forecasted_risk_reduction": 0.15,
        "historical_effectiveness": 0.13,
        "side_effect_safety": 0.08,
        "human_review_simplicity": 0.08,
        "causal_propagation_reduction": 0.22,
    },
    "LOW_RISK_FIRST": {
        "projected_health_gain": 0.10,
        "operational_stability": 0.22,
        "forecasted_risk_reduction": 0.13,
        "historical_effectiveness": 0.12,
        "side_effect_safety": 0.25,
        "human_review_simplicity": 0.13,
        "causal_propagation_reduction": 0.05,
    },
    "HUMAN_REVIEW_FIRST": {
        "projected_health_gain": 0.11,
        "operational_stability": 0.17,
        "forecasted_risk_reduction": 0.12,
        "historical_effectiveness": 0.11,
        "side_effect_safety": 0.17,
        "human_review_simplicity": 0.25,
        "causal_propagation_reduction": 0.07,
    },
}

DEFAULT_MODE_BY_LOOP_MODE = {
    "CRITICAL_RECOVERY_MODE": "RECOVERY_FIRST",
    "STABILIZATION_MODE": "STABILITY_FIRST",
    "NORMAL_OPTIMIZATION_MODE": "LOW_RISK_FIRST",
}

FUTURE_PLACEHOLDERS = [
    "dynamic priority balancing",
    "adaptive arbitration weighting",
    "operator preference arbitration",
    "cost-aware operational tradeoffs",
]


@dataclass(frozen=True)
class ArbitrationCandidate:
    strategy_key: str
    recommended_action: str
    priority_class: str
    conflict_left: str
    conflict_right: str
    tradeoff_reason: str
    expected_benefits: list[str]
    expected_costs: list[str]
    metrics: dict[str, int]
    safety_alignment: str


def effectiveness_score(patterns: list[dict[str, Any]], action: str) -> int:
    if not patterns:
        return 45
    top = patterns[0]
    base = int(float(top.get("avg_improvement_score", 45)))
    effect = str(top.get("historical_effectiveness", "")).upper()
    if "EFFECTIVE" == effect:
        base += 12
    elif "PARTIALLY_EFFECTIVE" == effect:
        base += 4
    if str(top.get("most_effective_remediation", "")).strip().lower() in action.lower():
        base += 12
    return clamp(base)


def top_forecast_risk(patterns: list[dict[str, Any]]) -> int:
    if not patterns:
        return 50
    return max(int(p.get("recurrence_risk", p.get("forecast_recurring_risk", 0))) for p in patterns)


def side_effect_safety(strategy_key: str, loop: dict[str, Any]) -> int:
    if strategy_key in {"observe_only", "human_review_gate"}:
        return 95
    if strategy_key == "stability_guardrails":
        return 88
    if strategy_key == "cleanup_threshold_simulation":
        return 78
    if strategy_key == "throughput_rebalance_review":
        return 62
    return 70


def human_review_simplicity(strategy_key: str) -> int:
    return {
        "observe_only": 96,
        "human_review_gate": 92,
        "cleanup_threshold_simulation": 76,
        "stability_guardrails": 72,
        "throughput_rebalance_review": 58,
    }.get(strategy_key, 65)


def candidate_metrics(strategy_key: str, loop: dict[str, Any]) -> dict[str, int]:
    health_gain = int(loop.get("projected_health_gain", 0))
    instability = int(loop.get("health", {}).get("instability_score", 0))
    root_confidence = int(loop.get("root", {}).get("confidence", 0))
    hotspot_pressure = int(loop.get("hotspot", {}).get("downstream_instability", 60))
    risk = top_forecast_risk(loop.get("patterns", []))

    if strategy_key == "cleanup_threshold_simulation":
        projected_gain = clamp(health_gain + 4)
        stability = clamp(100 - instability + 22)
        propagation = clamp(root_confidence * 0.45 + hotspot_pressure * 0.45 + 10)
    elif strategy_key == "stability_guardrails":
        projected_gain = clamp(health_gain - 3)
        stability = clamp(100 - instability + 34)
        propagation = clamp(root_confidence * 0.34 + hotspot_pressure * 0.38 + 8)
    elif strategy_key == "throughput_rebalance_review":
        projected_gain = clamp(health_gain + 9)
        stability = clamp(100 - instability + 8)
        propagation = clamp(root_confidence * 0.25 + hotspot_pressure * 0.54)
    elif strategy_key == "human_review_gate":
        projected_gain = clamp(health_gain - 7)
        stability = clamp(100 - instability + 26)
        propagation = clamp(root_confidence * 0.22 + hotspot_pressure * 0.20)
    else:
        projected_gain = clamp(health_gain - 14)
        stability = clamp(100 - instability + 18)
        propagation = clamp(root_confidence * 0.12 + hotspot_pressure * 0.10)

    side_safety = side_effect_safety(strategy_key, loop)
    review = human_review_simplicity(strategy_key)
    historical = effectiveness_score(loop.get("patterns", []), strategy_key.replace("_", " "))
    forecast_reduction = clamp(risk * 0.45 + projected_gain * 0.55)

    return {
        "projected_health_gain": projected_gain,
        "operational_stability": stability,
        "forecasted_risk_reduction": forecast_reduction,
        "historical_effectiveness": historical,
        "side_effect_safety": side_safety,
        "human_review_simplicity": review,
        "causal_propagation_reduction": propagation,
    }


def candidate_set(loop: dict[str, Any]) -> list[ArbitrationCandidate]:
    best = str(loop.get("best_safe_remediation", "simulate cleanup thresholds"))
    root = str(loop.get("root", {}).get("label", "retry amplification"))
    hotspot = str(loop.get("hotspot", {}).get("label", "worker starvation"))
    return [
        ArbitrationCandidate(
            strategy_key="cleanup_threshold_simulation",
            recommended_action=best,
            priority_class="P0_RECOVERY_REVIEW",
            conflict_left="reduce deferred queue",
            conflict_right="avoid worker starvation",
            tradeoff_reason="best projected recovery with acceptable starvation risk",
            expected_benefits=[
                "deferred queue reduction",
                "improved health score",
                "lower forecasted runaway probability",
            ],
            expected_costs=[
                "temporary retry delays",
                "moderate operational risk",
            ],
            metrics=candidate_metrics("cleanup_threshold_simulation", loop),
            safety_alignment="PASS",
        ),
        ArbitrationCandidate(
            strategy_key="stability_guardrails",
            recommended_action=f"tighten dry-run guardrails around {hotspot}",
            priority_class="P1_STABILITY_REVIEW",
            conflict_left="increase throughput",
            conflict_right="maintain stability",
            tradeoff_reason="best stability preservation while reducing propagation pressure",
            expected_benefits=[
                "lower instability propagation",
                "reduced worker starvation pressure",
                "clearer bounded review scope",
            ],
            expected_costs=[
                "slower queue drain",
                "possible throughput delay",
            ],
            metrics=candidate_metrics("stability_guardrails", loop),
            safety_alignment="PASS",
        ),
        ArbitrationCandidate(
            strategy_key="throughput_rebalance_review",
            recommended_action=f"review throughput rebalance options for {root}",
            priority_class="P1_THROUGHPUT_REVIEW",
            conflict_left="increase throughput",
            conflict_right="avoid retry starvation",
            tradeoff_reason="higher queue relief but weaker stability protection",
            expected_benefits=[
                "faster backlog drain if approved",
                "reduced task fanout pressure",
            ],
            expected_costs=[
                "higher side effect risk",
                "more complex human review",
                "possible retry amplification if mis-scoped",
            ],
            metrics=candidate_metrics("throughput_rebalance_review", loop),
            safety_alignment="PASS",
        ),
        ArbitrationCandidate(
            strategy_key="human_review_gate",
            recommended_action="require explicit human review before any remediation write",
            priority_class="P0_SAFETY_GATE",
            conflict_left="reduce approval friction",
            conflict_right="preserve explainability quality",
            tradeoff_reason="lowest ambiguity and strongest safety alignment",
            expected_benefits=[
                "preserves explainable decision trace",
                "prevents accidental execution",
                "keeps remediation reversible",
            ],
            expected_costs=[
                "slower recovery",
                "approval queue may remain elevated",
            ],
            metrics=candidate_metrics("human_review_gate", loop),
            safety_alignment="PASS",
        ),
        ArbitrationCandidate(
            strategy_key="observe_only",
            recommended_action="continue observation and defer remediation proposal",
            priority_class="P2_WATCHLIST",
            conflict_left="maintain safety",
            conflict_right="recover quickly",
            tradeoff_reason="lowest intervention risk but insufficient recovery pressure",
            expected_benefits=[
                "minimal side effects",
                "simple human review",
            ],
            expected_costs=[
                "deferred queue may continue growing",
                "runaway probability remains elevated",
            ],
            metrics=candidate_metrics("observe_only", loop),
            safety_alignment="PASS",
        ),
    ]


def score_candidate(candidate: ArbitrationCandidate, mode: str) -> int:
    weights = ARBITRATION_MODES[mode]
    score = 0.0
    for key, weight in weights.items():
        score += candidate.metrics.get(key, 0) * weight
    if candidate.safety_alignment != "PASS":
        score -= 100
    return clamp(score)


def auto_mode(loop: dict[str, Any]) -> str:
    return DEFAULT_MODE_BY_LOOP_MODE.get(str(loop.get("current_mode", "")), "LOW_RISK_FIRST")


def arbitrate(db_path: str, mode: str | None) -> dict[str, Any]:
    loop = build_loop(db_path)
    selected_mode = mode or auto_mode(loop)
    if selected_mode not in ARBITRATION_MODES:
        allowed = ", ".join(sorted(ARBITRATION_MODES))
        raise SystemExit(f"unknown arbitration mode: {selected_mode}; allowed: {allowed}")

    candidates = candidate_set(loop)
    ranked = sorted(
        [
            {
                "candidate": candidate,
                "score": score_candidate(candidate, selected_mode),
            }
            for candidate in candidates
        ],
        key=lambda x: (-int(x["score"]), x["candidate"].strategy_key),
    )
    selected = ranked[0]["candidate"]
    return {
        "mode": selected_mode,
        "loop": loop,
        "ranked": ranked,
        "selected": selected,
        "selected_score": ranked[0]["score"],
    }


def print_list(items: list[str]) -> None:
    for item in items:
        print(f"- {item}")


def print_report(result: dict[str, Any]) -> None:
    selected: ArbitrationCandidate = result["selected"]
    loop = result["loop"]
    print("OPENCLAW OPERATIONAL ARBITRATION")
    print("")
    print("arbitration_mode:")
    print(result["mode"])
    print("")
    print("priority_conflict:")
    print(selected.conflict_left)
    print("vs")
    print(selected.conflict_right)
    print("")
    print("selected_strategy:")
    print(selected.recommended_action)
    print("")
    print("priority_class:")
    print(selected.priority_class)
    print("")
    print("arbitration_score:")
    print(result["selected_score"])
    print("")
    print("tradeoff_reason:")
    print(selected.tradeoff_reason)
    print("")
    print("expected_benefits:")
    print_list(selected.expected_benefits)
    print("")
    print("expected_costs:")
    print_list(selected.expected_costs)
    print("")
    print("safety_alignment:")
    print(selected.safety_alignment)
    print("")
    print("balanced_metrics:")
    for key, value in selected.metrics.items():
        print(f"- {key}: {value}")
    print("")
    print("competing_objectives_detected:")
    conflicts = []
    for item in result["ranked"]:
        c: ArbitrationCandidate = item["candidate"]
        pair = f"{c.conflict_left} vs {c.conflict_right}"
        if pair not in conflicts:
            conflicts.append(pair)
    print_list(conflicts)
    print("")
    print("loop_context:")
    print(f"- current_mode: {loop['current_mode']}")
    print(f"- loop_state: {loop['loop_state']}")
    print(f"- top_risk: {loop['top_risk']}")
    print(f"- root_cause: {loop['root'].get('label', 'unknown')}")
    print(f"- projected_health_gain: +{loop['projected_health_gain']}")
    print("")
    print("ranked_alternatives:")
    for item in result["ranked"][1:]:
        c = item["candidate"]
        print(f"- {c.recommended_action}: score={item['score']} safety={c.safety_alignment}")
    print("")
    print("human_approval_required:")
    print("true")
    print("")
    print("future_extension_placeholders:")
    print_list(FUTURE_PLACEHOLDERS)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Deterministic multi-objective operational arbitration.")
    ap.add_argument("--db", default=DB, help="SQLite database path. Default: DB_PATH/OCLAW_DB_PATH/FACTORY_DB_PATH or factory DB.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    arb = sub.add_parser("arbitrate", help="Rank remediation strategies under safety constraints.")
    arb.add_argument("--mode", choices=sorted(ARBITRATION_MODES), default=None)
    return ap


def main() -> None:
    args = build_parser().parse_args()
    if args.cmd == "arbitrate":
        print_report(arbitrate(args.db, args.mode))
        return
    raise SystemExit(f"unknown command: {args.cmd}")


if __name__ == "__main__":
    main()
