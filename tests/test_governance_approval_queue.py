from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BOT_DIR = ROOT / "bots"
if str(BOT_DIR) not in sys.path:
    sys.path.insert(0, str(BOT_DIR))

from bots import openclaw_ui_api


def json_payload(value):
    if isinstance(value, dict):
        return value
    body = getattr(value, "body", b"{}")
    if isinstance(body, bytes):
        body = body.decode("utf-8")
    return json.loads(body)


def fake_plan(**overrides):
    base = {
        "horizon": "7d",
        "planning_mode": "governance",
        "sustainability_score": 64,
        "recurrence_risk": "retry amplification recurrence",
        "recurrence_risk_score": 84,
        "maintenance_pressure": "medium",
        "maintenance_pressure_score": 57,
        "operator_load": "high",
        "operator_load_score": 68,
        "stability_projection": "watch",
        "stability_projection_score": 52,
        "dominant_long_term_risk": "retry amplification recurrence",
        "recommended_long_horizon_focus": "approval queue stabilization before autonomy",
        "anti_patterns": [],
        "supporting_signals": ["retry pressure", "operator load"],
        "scoring_examples": [],
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def candidate(
    action: str,
    score: int,
    projected_gain: int,
    safety_alignment: str = "pass",
    tradeoff: str = "best expected value under current risk",
):
    return {
        "strategy_key": action.replace(" ", "_"),
        "recommended_action": action,
        "priority_class": "high",
        "tradeoff_reason": tradeoff,
        "expected_benefits": ["improved governance", "reduced duplicate noise"],
        "expected_costs": ["operator review time"],
        "safety_alignment": safety_alignment,
        "metrics": {
            "projected_health_gain": projected_gain,
            "operational_stability": 62,
        },
    }, score


def fake_report(operator_load_score: int = 68):
    ranked = []
    for action, score, gain in (
        ("simulate cleanup thresholds", 91, 34),
        ("require explicit human review before writes", 81, 22),
        ("continue observation", 64, 8),
    ):
        cand, cand_score = candidate(action, score, gain)
        ranked.append({"candidate": cand, "score": cand_score})
    return {
        "plan": fake_plan(operator_load_score=operator_load_score),
        "arbitration": {"ranked": ranked},
        "policy": {
            "selected": SimpleNamespace(selection_reason="highest expected value with bounded safety"),
            "history": [
                {"selected_at": "2026-05-12T00:00:00+00:00"},
                {"selected_at": "2026-05-14T00:00:00+00:00"},
            ],
        },
    }


class GovernanceApprovalQueueTests(unittest.TestCase):
    def test_build_governance_recommendations_success_shape_and_safety(self) -> None:
        with mock.patch("dev_autopilot_executive_report_v1.build_report", return_value=fake_report()):
            data = openclaw_ui_api.build_governance_recommendations()

        self.assertTrue(data["ok"])
        self.assertEqual(data["mode"], "recommendation_only")
        self.assertGreater(data["count"], 0)
        self.assertTrue(data["items"])

        allowed = set(data["allowed_states"])
        required_fields = {
            "recommendation",
            "expected_value",
            "risk",
            "projected_gain",
            "rollback_difficulty",
            "confidence",
            "why_selected",
            "rejected_alternatives",
            "governance_reasoning",
            "aging",
            "strategic_alignment",
        }
        for item in data["items"]:
            self.assertIn(item["state"], allowed)
            self.assertTrue(required_fields.issubset(item.keys()))
            self.assertIn("No POST", item["safety_contract"])
            self.assertIn("No DB writes", item["safety_contract"])
            self.assertTrue(item["banner"]["execution_disabled"])
            self.assertTrue(item["banner"]["dry_run_only"])
            if item["risk_level"] in {"critical", "high"}:
                self.assertTrue(item["human_review_required"])
            for key in (
                "revenue_impact",
                "infrastructure_impact",
                "autonomy_progression_impact",
                "operational_stability_impact",
            ):
                self.assertIn(key, item["strategic_alignment"])

    def test_governance_summary_reports_safety_and_state_counts(self) -> None:
        with mock.patch("dev_autopilot_executive_report_v1.build_report", return_value=fake_report()):
            summary = json_payload(openclaw_ui_api.governance_summary())

        self.assertTrue(summary["execution_disabled"])
        self.assertTrue(summary["dry_run_only"])
        self.assertIn("states", summary)
        for state in openclaw_ui_api.APPROVAL_STATES:
            self.assertIn(state, summary["states"])
        self.assertGreaterEqual(summary["human_review_required"], 1)

    def test_build_governance_recommendations_failure_is_safe(self) -> None:
        with mock.patch("dev_autopilot_executive_report_v1.build_report", side_effect=RuntimeError("boom")):
            data = openclaw_ui_api.build_governance_recommendations()

        self.assertFalse(data["ok"])
        self.assertEqual(data["mode"], "recommendation_only")
        self.assertEqual(data["count"], 0)
        for item in (
            "No POST",
            "No DB writes",
            "No launchctl",
            "No deploy",
            "No router_task creation",
            "Recommendation only",
        ):
            self.assertIn(item, data["safety_contract"])

    def test_approval_queue_ui_is_read_only_and_visible(self) -> None:
        html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")

        for marker in (
            "Approval Queue",
            "/api/governance/approval-queue",
            "Human Review Required",
            "execution disabled",
            "dry-run only",
        ):
            self.assertIn(marker, html)
        self.assertIsNone(
            re.search(
                r"fetch\([^)]*/api/governance/approval-queue[^)]*(method|POST)",
                html,
                flags=re.IGNORECASE | re.DOTALL,
            )
        )


if __name__ == "__main__":
    unittest.main()
