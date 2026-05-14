from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DB = (
    os.environ.get("OCLAW_DB_PATH")
    or os.environ.get("FACTORY_DB_PATH")
    or os.environ.get("DB_PATH")
    or str(Path.home() / "AI/openclaw-factory/data/openclaw.db")
)

SEVERITY_SCORE = {
    "LOW": 25,
    "MEDIUM": 50,
    "HIGH": 75,
    "CRITICAL": 95,
}

EFFECTIVENESS_SCORE = {
    "INEFFECTIVE": 15,
    "PARTIALLY_EFFECTIVE": 55,
    "EFFECTIVE": 82,
    "HIGHLY_EFFECTIVE": 95,
}

MIGRATION_SQL = """
CREATE TABLE IF NOT EXISTS dev_autopilot_operational_patterns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pattern_key TEXT NOT NULL UNIQUE,
  pattern_name TEXT NOT NULL DEFAULT '',
  occurrence_count INTEGER NOT NULL DEFAULT 0,
  avg_severity REAL NOT NULL DEFAULT 0,
  avg_improvement_score REAL NOT NULL DEFAULT 0,
  last_seen_at TEXT NOT NULL DEFAULT '',
  associated_bottlenecks_json TEXT NOT NULL DEFAULT '[]',
  forecast_outcomes_json TEXT NOT NULL DEFAULT '{}',
  remediation_history_json TEXT NOT NULL DEFAULT '[]',
  effectiveness_history_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dev_autopilot_patterns_last_seen
ON dev_autopilot_operational_patterns(last_seen_at);

CREATE TABLE IF NOT EXISTS dev_autopilot_incident_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  incident_key TEXT NOT NULL UNIQUE,
  pattern_key TEXT NOT NULL DEFAULT '',
  detected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  severity TEXT NOT NULL DEFAULT 'MEDIUM',
  signals_json TEXT NOT NULL DEFAULT '{}',
  diagnosis_json TEXT NOT NULL DEFAULT '{}',
  remediation_json TEXT NOT NULL DEFAULT '{}',
  outcome_json TEXT NOT NULL DEFAULT '{}',
  bottlenecks_json TEXT NOT NULL DEFAULT '[]',
  forecast_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dev_autopilot_incidents_pattern
ON dev_autopilot_incident_history(pattern_key, detected_at);
"""


PATTERN_CATALOG: dict[str, dict[str, Any]] = {
    "deferred_queue_runaway": {
        "name": "Deferred queue runaway",
        "signals": {"deferred backlog", "queue growth", "worker starvation", "retry amplification"},
        "bottlenecks": ["worker starvation", "retry amplification"],
        "remediation": "simulate cleanup thresholds",
        "forecast": "deferred backlog likely to recur under sustained intake",
    },
    "retry_amplification": {
        "name": "Retry amplification",
        "signals": {"retry amplification", "retry_count growth", "executor churn", "queue growth"},
        "bottlenecks": ["executor churn", "duplicate retry loops"],
        "remediation": "cap retries and require explicit failure classification",
        "forecast": "retry pressure can mask root-cause failures",
    },
    "worker_starvation": {
        "name": "Worker starvation",
        "signals": {"worker starvation", "new task backlog", "oldest task age", "low completion"},
        "bottlenecks": ["insufficient active workers", "blocked execution lane"],
        "remediation": "rebalance worker targets and reduce stale backlog",
        "forecast": "latency grows until intake slows or workers recover",
    },
    "approval_stagnation": {
        "name": "Approval stagnation",
        "signals": {"approval stagnation", "pending approvals", "waiting_answer", "review delay"},
        "bottlenecks": ["human approval gate", "stale review queue"],
        "remediation": "batch approvals by risk and age",
        "forecast": "delivery slows despite healthy execution capacity",
    },
    "planner_overload": {
        "name": "Planner overload",
        "signals": {"planner overload", "proposal backlog", "open PR backlog", "decision fanout"},
        "bottlenecks": ["too many active planning fronts", "low merge throughput"],
        "remediation": "limit active planning fronts and prioritize by risk",
        "forecast": "planning output outpaces review and merge capacity",
    },
}

EXAMPLE_INCIDENTS = [
    {
        "incident_key": "deferred-runaway-001",
        "pattern_key": "deferred_queue_runaway",
        "detected_at": "2026-05-10 09:00:00",
        "severity": "HIGH",
        "signals": {"deferred backlog": 44, "worker starvation": True, "retry amplification": True},
        "diagnosis": {"summary": "deferred queue grew faster than worker drain rate"},
        "remediation": {"attempt": "simulate cleanup thresholds"},
        "outcome": {"effectiveness": "PARTIALLY_EFFECTIVE", "improvement_score": 56},
        "bottlenecks": ["worker starvation", "retry amplification"],
        "forecast": {"recurring_risk": 74, "outcome": "queue remains unstable without threshold tuning"},
    },
    {
        "incident_key": "deferred-runaway-002",
        "pattern_key": "deferred_queue_runaway",
        "detected_at": "2026-05-11 10:30:00",
        "severity": "HIGH",
        "signals": {"deferred backlog": 57, "worker starvation": True, "queue growth": True},
        "diagnosis": {"summary": "deferred tasks recurred after intake spike"},
        "remediation": {"attempt": "raise cleanup priority"},
        "outcome": {"effectiveness": "PARTIALLY_EFFECTIVE", "improvement_score": 49},
        "bottlenecks": ["worker starvation"],
        "forecast": {"recurring_risk": 77, "outcome": "backlog likely returns during next spike"},
    },
    {
        "incident_key": "deferred-runaway-003",
        "pattern_key": "deferred_queue_runaway",
        "detected_at": "2026-05-12 08:45:00",
        "severity": "CRITICAL",
        "signals": {"deferred backlog": 81, "retry amplification": True, "oldest task age": 7200},
        "diagnosis": {"summary": "retry pressure amplified deferred queue"},
        "remediation": {"attempt": "simulate cleanup thresholds"},
        "outcome": {"effectiveness": "PARTIALLY_EFFECTIVE", "improvement_score": 61},
        "bottlenecks": ["retry amplification", "old task age"],
        "forecast": {"recurring_risk": 82, "outcome": "critical recurrence possible"},
    },
    {
        "incident_key": "deferred-runaway-004",
        "pattern_key": "deferred_queue_runaway",
        "detected_at": "2026-05-13 07:20:00",
        "severity": "HIGH",
        "signals": {"deferred backlog": 63, "worker starvation": True, "retry amplification": True},
        "diagnosis": {"summary": "same signature as deferred runaway incident #3"},
        "remediation": {"attempt": "simulate cleanup thresholds"},
        "outcome": {"effectiveness": "PARTIALLY_EFFECTIVE", "improvement_score": 59},
        "bottlenecks": ["worker starvation", "retry amplification"],
        "forecast": {"recurring_risk": 78, "outcome": "recurrence likely without cleanup threshold adoption"},
    },
    {
        "incident_key": "retry-amplification-002",
        "pattern_key": "retry_amplification",
        "detected_at": "2026-05-12 11:00:00",
        "severity": "HIGH",
        "signals": {"retry amplification": True, "retry_count growth": 31, "executor churn": True},
        "diagnosis": {"summary": "failed tasks re-entered the active lane repeatedly"},
        "remediation": {"attempt": "cap retries and classify terminal failures"},
        "outcome": {"effectiveness": "EFFECTIVE", "improvement_score": 79},
        "bottlenecks": ["duplicate retry loops"],
        "forecast": {"recurring_risk": 66, "outcome": "risk falls if retry caps remain active"},
    },
    {
        "incident_key": "approval-stagnation-001",
        "pattern_key": "approval_stagnation",
        "detected_at": "2026-05-13 13:00:00",
        "severity": "MEDIUM",
        "signals": {"pending approvals": 18, "waiting_answer": True, "review delay": True},
        "diagnosis": {"summary": "approval queue aged while execution capacity stayed idle"},
        "remediation": {"attempt": "batch approvals by risk and age"},
        "outcome": {"effectiveness": "PARTIALLY_EFFECTIVE", "improvement_score": 52},
        "bottlenecks": ["human approval gate"],
        "forecast": {"recurring_risk": 58, "outcome": "moderate recurrence risk"},
    },
]


@dataclass(frozen=True)
class Incident:
    incident_key: str
    pattern_key: str
    detected_at: str
    severity: str
    signals: dict[str, Any]
    diagnosis: dict[str, Any]
    remediation: dict[str, Any]
    outcome: dict[str, Any]
    bottlenecks: list[str]
    forecast: dict[str, Any]


def connect(db_path: str) -> sqlite3.Connection | None:
    if not db_path or not Path(db_path).exists():
        return None
    con = sqlite3.connect(db_path, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con


def table_exists(con: sqlite3.Connection, table: str) -> bool:
    row = con.execute(
        "select 1 from sqlite_master where type='table' and name=?",
        (table,),
    ).fetchone()
    return row is not None


def columns(con: sqlite3.Connection, table: str) -> set[str]:
    if not table_exists(con, table):
        return set()
    return {str(r["name"]) for r in con.execute(f"pragma table_info({table})").fetchall()}


def safe_json(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except Exception:
        return fallback


def rows_to_incidents(rows: list[sqlite3.Row]) -> list[Incident]:
    incidents: list[Incident] = []
    for r in rows:
        incidents.append(
            Incident(
                incident_key=str(r["incident_key"]),
                pattern_key=str(r["pattern_key"] or ""),
                detected_at=str(r["detected_at"] or ""),
                severity=str(r["severity"] or "MEDIUM").upper(),
                signals=safe_json(r["signals_json"], {}),
                diagnosis=safe_json(r["diagnosis_json"], {}),
                remediation=safe_json(r["remediation_json"], {}),
                outcome=safe_json(r["outcome_json"], {}),
                bottlenecks=safe_json(r["bottlenecks_json"], []),
                forecast=safe_json(r["forecast_json"], {}),
            )
        )
    return incidents


def example_incidents() -> list[Incident]:
    return [
        Incident(
            incident_key=str(x["incident_key"]),
            pattern_key=str(x["pattern_key"]),
            detected_at=str(x["detected_at"]),
            severity=str(x["severity"]),
            signals=dict(x["signals"]),
            diagnosis=dict(x["diagnosis"]),
            remediation=dict(x["remediation"]),
            outcome=dict(x["outcome"]),
            bottlenecks=list(x["bottlenecks"]),
            forecast=dict(x["forecast"]),
        )
        for x in EXAMPLE_INCIDENTS
    ]


def load_incidents(db_path: str) -> tuple[list[Incident], str]:
    con = connect(db_path)
    if con is None:
        return example_incidents(), "example"
    try:
        if not table_exists(con, "dev_autopilot_incident_history"):
            return example_incidents(), "example"
        need = {
            "incident_key",
            "pattern_key",
            "detected_at",
            "severity",
            "signals_json",
            "diagnosis_json",
            "remediation_json",
            "outcome_json",
            "bottlenecks_json",
            "forecast_json",
        }
        if not need.issubset(columns(con, "dev_autopilot_incident_history")):
            return example_incidents(), "example"
        rows = con.execute(
            """
            select incident_key, pattern_key, detected_at, severity, signals_json,
                   diagnosis_json, remediation_json, outcome_json, bottlenecks_json,
                   forecast_json
            from dev_autopilot_incident_history
            order by detected_at asc, id asc
            """
        ).fetchall()
        if not rows:
            return example_incidents(), "example"
        return rows_to_incidents(rows), "database"
    finally:
        con.close()


def score_severity(values: list[str]) -> float:
    if not values:
        return 0.0
    return sum(SEVERITY_SCORE.get(v.upper(), 50) for v in values) / len(values)


def severity_label(score: float) -> str:
    if score >= 90:
        return "CRITICAL"
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"


def parse_time(value: str) -> dt.datetime | None:
    formats = (
        ("%Y-%m-%d %H:%M:%S", 19),
        ("%Y-%m-%dT%H:%M:%S", 19),
        ("%Y-%m-%d", 10),
    )
    for fmt, width in formats:
        try:
            return dt.datetime.strptime(value[:width], fmt)
        except ValueError:
            pass
    return None


def recurrence_intervals(incidents: list[Incident]) -> list[int]:
    times = [t for t in (parse_time(i.detected_at) for i in incidents) if t is not None]
    times.sort()
    return [max(0, int((b - a).total_seconds() // 3600)) for a, b in zip(times, times[1:])]


def signal_terms(signals: dict[str, Any]) -> set[str]:
    terms: set[str] = set()
    for k, v in signals.items():
        key = str(k).strip().lower()
        if key:
            terms.add(key)
        if isinstance(v, str) and v.strip():
            terms.add(v.strip().lower())
        if isinstance(v, bool) and v and key:
            terms.add(key)
        if isinstance(v, (int, float)) and v > 0 and key:
            terms.add(key)
    return terms


def average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def group_patterns(incidents: list[Incident]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Incident]] = {}
    for incident in incidents:
        grouped.setdefault(incident.pattern_key, []).append(incident)

    patterns: list[dict[str, Any]] = []
    for key, rows in grouped.items():
        catalog = PATTERN_CATALOG.get(key, {"name": key.replace("_", " ").title(), "signals": set()})
        severity_avg = score_severity([r.severity for r in rows])
        improvements = [
            float(r.outcome.get("improvement_score", EFFECTIVENESS_SCORE.get(str(r.outcome.get("effectiveness", "")).upper(), 0)))
            for r in rows
        ]
        risk = average([float(r.forecast.get("recurring_risk", 0)) for r in rows])
        intervals = recurrence_intervals(rows)
        remediation_counts: dict[str, int] = {}
        effectiveness_counts: dict[str, int] = {}
        bottlenecks: set[str] = set()
        forecasts: list[str] = []
        for r in rows:
            attempt = str(r.remediation.get("attempt", "")).strip()
            if attempt:
                remediation_counts[attempt] = remediation_counts.get(attempt, 0) + 1
            eff = str(r.outcome.get("effectiveness", "")).strip().upper()
            if eff:
                effectiveness_counts[eff] = effectiveness_counts.get(eff, 0) + 1
            bottlenecks.update(str(x) for x in r.bottlenecks if str(x).strip())
            outcome = str(r.forecast.get("outcome", "")).strip()
            if outcome:
                forecasts.append(outcome)
        best_remediation = max(remediation_counts.items(), key=lambda x: (x[1], x[0]))[0] if remediation_counts else ""
        best_effectiveness = max(effectiveness_counts.items(), key=lambda x: (x[1], x[0]))[0] if effectiveness_counts else ""
        last_seen = max((r.detected_at for r in rows), default="")
        confidence = min(98, 35 + len(rows) * 12 + int(len(bottlenecks) * 2))
        instability = min(100, int(severity_avg * 0.45 + risk * 0.35 + max(0, 70 - average(intervals or [70])) * 0.2))
        patterns.append(
            {
                "pattern_key": key,
                "pattern_name": str(catalog.get("name", key)),
                "occurrences": len(rows),
                "historical_severity": severity_label(severity_avg),
                "historical_severity_score": round(severity_avg, 1),
                "most_effective_remediation": best_remediation or str(catalog.get("remediation", "")),
                "historical_effectiveness": best_effectiveness or "UNKNOWN",
                "avg_improvement_score": round(average(improvements), 1),
                "recurrence_intervals_hours": intervals,
                "associated_signals": sorted(bottlenecks),
                "forecast_recurring_risk": int(round(risk)),
                "forecast_outcomes": forecasts[:3],
                "pattern_confidence": confidence,
                "recurrence_risk": int(round(risk)),
                "operational_instability_score": instability,
                "last_seen_at": last_seen,
            }
        )
    return sorted(patterns, key=lambda p: (-int(p["operational_instability_score"]), str(p["pattern_key"])))


def current_state_signals(db_path: str) -> dict[str, Any]:
    signals: dict[str, Any] = {
        "deferred backlog": 0,
        "new task backlog": 0,
        "retry_count growth": 0,
        "pending approvals": 0,
        "proposal backlog": 0,
        "open PR backlog": 0,
    }
    con = connect(db_path)
    if con is None:
        signals.update(
            {
                "deferred backlog": 62,
                "worker starvation": True,
                "retry amplification": True,
                "oldest task age": 5400,
            }
        )
        return signals
    try:
        if table_exists(con, "router_tasks"):
            cols = columns(con, "router_tasks")
            if "status" in cols:
                signals["deferred backlog"] = int(
                    con.execute(
                        "select count(*) from router_tasks where coalesce(status,'') in ('deferred','stalled')"
                    ).fetchone()[0]
                )
                signals["new task backlog"] = int(
                    con.execute(
                        "select count(*) from router_tasks where coalesce(status,'') in ('new','pending')"
                    ).fetchone()[0]
                )
            if "retry_count" in cols:
                signals["retry_count growth"] = int(
                    con.execute("select coalesce(sum(retry_count),0) from router_tasks").fetchone()[0]
                )
            if {"created_at", "status"}.issubset(cols):
                row = con.execute(
                    """
                    select max(strftime('%s','now') - strftime('%s', created_at))
                    from router_tasks
                    where coalesce(status,'') in ('new','pending','deferred','stalled')
                    """
                ).fetchone()
                signals["oldest task age"] = int(row[0] or 0)
        if table_exists(con, "dev_proposals"):
            cols = columns(con, "dev_proposals")
            if "status" in cols:
                signals["pending approvals"] = int(
                    con.execute(
                        "select count(*) from dev_proposals where coalesce(status,'') in ('pending','approved')"
                    ).fetchone()[0]
                )
                signals["proposal backlog"] = int(
                    con.execute(
                        "select count(*) from dev_proposals where coalesce(status,'') not in ('merged','closed','done')"
                    ).fetchone()[0]
                )
            if "pr_status" in cols:
                signals["open PR backlog"] = int(
                    con.execute("select count(*) from dev_proposals where coalesce(pr_status,'')='open'").fetchone()[0]
                )
        signals["worker starvation"] = int(signals.get("new task backlog", 0)) >= 20 or int(signals.get("oldest task age", 0)) >= 3600
        signals["retry amplification"] = int(signals.get("retry_count growth", 0)) >= 10
        signals["approval stagnation"] = int(signals.get("pending approvals", 0)) >= 10
        signals["planner overload"] = int(signals.get("proposal backlog", 0)) >= 30 or int(signals.get("open PR backlog", 0)) >= 10
        return signals
    finally:
        con.close()


def similarity(current: dict[str, Any], incidents: list[Incident]) -> list[dict[str, Any]]:
    current_terms = signal_terms(current)
    scored: list[dict[str, Any]] = []
    for incident in incidents:
        incident_terms = signal_terms(incident.signals)
        catalog_terms = set(PATTERN_CATALOG.get(incident.pattern_key, {}).get("signals", set()))
        terms = incident_terms | {str(x).lower() for x in catalog_terms}
        overlap = current_terms & terms
        union = current_terms | terms
        score = int(round((len(overlap) / len(union)) * 100)) if union else 0
        if score > 0:
            scored.append(
                {
                    "incident_key": incident.incident_key,
                    "pattern_key": incident.pattern_key,
                    "pattern_name": PATTERN_CATALOG.get(incident.pattern_key, {}).get("name", incident.pattern_key),
                    "similarity_score": score,
                    "matched_signals": sorted(overlap),
                    "historical_severity": incident.severity,
                    "historical_effectiveness": str(incident.outcome.get("effectiveness", "UNKNOWN")).upper(),
                }
            )
    return sorted(scored, key=lambda x: (-int(x["similarity_score"]), str(x["incident_key"])))[:8]


def print_patterns(patterns: list[dict[str, Any]], source: str) -> None:
    print("OPENCLAW OPERATIONAL MEMORY")
    print("")
    print(f"source: {source}")
    print("")
    for idx, p in enumerate(patterns, start=1):
        if idx > 1:
            print("")
        print(f"Recurring pattern: {p['pattern_name']}")
        print("")
        print("occurrences:")
        print(p["occurrences"])
        print("")
        print("historical_severity:")
        print(p["historical_severity"])
        print("")
        print("most_effective_remediation:")
        print(p["most_effective_remediation"])
        print("")
        print("historical_effectiveness:")
        print(p["historical_effectiveness"])
        print("")
        print("associated_signals:")
        for signal in p["associated_signals"]:
            print(f"- {signal}")
        print("")
        print("forecast_recurring_risk:")
        print(p["forecast_recurring_risk"])
        print("")
        print("memory_scoring:")
        print(f"- pattern_confidence: {p['pattern_confidence']}")
        print(f"- recurrence_risk: {p['recurrence_risk']}")
        print(f"- historical_severity: {p['historical_severity_score']}")
        print(f"- operational_instability_score: {p['operational_instability_score']}")
        print("")
        print("recurrence_intervals_hours:")
        print(", ".join(str(x) for x in p["recurrence_intervals_hours"]) or "none")


def print_incidents(incidents: list[Incident], source: str) -> None:
    print("OPENCLAW INCIDENT HISTORY")
    print("")
    print(f"source: {source}")
    for incident in sorted(incidents, key=lambda x: x.detected_at, reverse=True):
        print("")
        print(f"- {incident.incident_key}")
        print(f"  pattern: {PATTERN_CATALOG.get(incident.pattern_key, {}).get('name', incident.pattern_key)}")
        print(f"  detected_at: {incident.detected_at}")
        print(f"  severity: {incident.severity}")
        print(f"  signals: {', '.join(sorted(signal_terms(incident.signals)))}")
        print(f"  remediation_attempt: {incident.remediation.get('attempt', '')}")
        print(f"  historical_effectiveness: {incident.outcome.get('effectiveness', 'UNKNOWN')}")
        print(f"  forecast_recurring_risk: {incident.forecast.get('recurring_risk', 0)}")


def print_compare(db_path: str, incidents: list[Incident], source: str) -> None:
    current = current_state_signals(db_path)
    matches = similarity(current, incidents)
    print("OPENCLAW MEMORY COMPARISON")
    print("")
    print(f"memory_source: {source}")
    print("")
    print("current_signals:")
    for key in sorted(current):
        value = current[key]
        if value:
            print(f"- {key}: {value}")
    print("")
    print("similarity_examples:")
    if not matches:
        print("- no historical similarity detected")
    for match in matches:
        print(
            f"- Current state resembles {match['pattern_name']} incident "
            f"{match['incident_key']} ({match['similarity_score']}%)"
        )
        print(f"  matched_signals: {', '.join(match['matched_signals'])}")
        print(f"  historical_severity: {match['historical_severity']}")
        print(f"  historical_effectiveness: {match['historical_effectiveness']}")


def print_migration() -> None:
    print("-- Suggested safe migration only. Not applied by this script.")
    print(MIGRATION_SQL.strip())
    print("")
    print("-- Future extension placeholders:")
    print("-- - causal pattern graphs")
    print("-- - operational anomaly clustering")
    print("-- - adaptive remediation weighting")
    print("-- - predictive instability modeling")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Deterministic operational memory reports for dev autopilot runtime.")
    ap.add_argument("--db", default=DB, help="SQLite database path. Default: DB_PATH/OCLAW_DB_PATH/FACTORY_DB_PATH or factory DB.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("patterns", help="Show recurring operational patterns and memory scores.")
    sub.add_parser("incidents", help="Show historical incident examples and effectiveness.")
    sub.add_parser("compare", help="Compare current safe telemetry shape to historical patterns.")
    sub.add_parser("migration", help="Print suggested migration SQL without applying it.")
    return ap


def main() -> None:
    args = build_parser().parse_args()
    if args.cmd == "migration":
        print_migration()
        return

    incidents, source = load_incidents(args.db)
    if args.cmd == "patterns":
        print_patterns(group_patterns(incidents), source)
        return
    if args.cmd == "incidents":
        print_incidents(incidents, source)
        return
    if args.cmd == "compare":
        print_compare(args.db, incidents, source)
        return
    raise SystemExit(f"unknown command: {args.cmd}")


if __name__ == "__main__":
    main()
