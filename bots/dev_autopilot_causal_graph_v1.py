from __future__ import annotations

import argparse
import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dev_autopilot_memory_v1 import (
    DB,
    Incident,
    columns,
    connect,
    load_incidents,
    safe_json,
    score_severity,
    severity_label,
    signal_terms,
    table_exists,
)


SIGNAL_LABELS = {
    "planner_overload": "planner overload",
    "task_fanout_increase": "task fanout increase",
    "retry_amplification": "retry amplification",
    "worker_starvation": "worker starvation",
    "deferred_queue_runaway": "deferred queue runaway",
    "approval_stagnation": "approval stagnation",
}

SIGNAL_TERMS = {
    "planner_overload": {"planner overload", "proposal backlog", "open PR backlog", "decision fanout"},
    "task_fanout_increase": {"task fanout increase", "fanout", "new task backlog", "queue growth"},
    "retry_amplification": {"retry amplification", "retry_count growth", "executor churn", "duplicate retry loops"},
    "worker_starvation": {"worker starvation", "oldest task age", "low completion", "blocked execution lane"},
    "deferred_queue_runaway": {"deferred queue runaway", "deferred backlog", "queue growth", "stalled"},
    "approval_stagnation": {"approval stagnation", "pending approvals", "waiting_answer", "review delay"},
}

BASE_EDGES = [
    ("planner_overload", "task_fanout_increase", 74, 1.6),
    ("task_fanout_increase", "retry_amplification", 72, 1.8),
    ("retry_amplification", "worker_starvation", 82, 2.4),
    ("worker_starvation", "deferred_queue_runaway", 86, 2.2),
    ("deferred_queue_runaway", "approval_stagnation", 69, 1.5),
    ("planner_overload", "approval_stagnation", 61, 1.3),
    ("retry_amplification", "deferred_queue_runaway", 78, 2.0),
]

OPTIONAL_CONTEXT_TABLES = {
    "operational_memory": [
        "dev_autopilot_operational_patterns",
        "dev_autopilot_incident_history",
    ],
    "trend_history": [
        "dev_autopilot_trend_history",
        "dev_autopilot_runtime_trends",
        "runtime_trend_history",
    ],
    "diagnosis_outputs": [
        "dev_autopilot_diagnosis_outputs",
        "dev_autopilot_diagnoses",
        "diagnosis_outputs",
    ],
    "forecast_outputs": [
        "dev_autopilot_forecast_outputs",
        "dev_autopilot_forecasts",
        "forecast_outputs",
    ],
    "optimizer_outputs": [
        "dev_autopilot_optimizer_outputs",
        "dev_autopilot_optimization_outputs",
        "optimizer_outputs",
    ],
    "remediation_outcomes": [
        "dev_autopilot_remediation_outcomes",
        "remediation_outcomes",
    ],
}

FUTURE_PLACEHOLDERS = [
    "weighted causal graphs",
    "dynamic propagation simulation",
    "instability diffusion modeling",
    "cascading failure prediction",
]


@dataclass(frozen=True)
class CausalEdge:
    cause: str
    effect: str
    confidence: int
    historical_recurrence: int
    severity_propagation: int
    operational_impact_multiplier: float


def clamp(value: float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(round(value))))


def signal_name(key: str) -> str:
    return SIGNAL_LABELS.get(key, key.replace("_", " "))


def incident_has_signal(incident: Incident, signal_key: str) -> bool:
    terms = signal_terms(incident.signals)
    terms.add(incident.pattern_key.replace("_", " "))
    terms.add(incident.pattern_key)
    terms.update(str(x).strip().lower() for x in incident.bottlenecks if str(x).strip())
    diagnosis = json.dumps(incident.diagnosis, ensure_ascii=False).lower()
    forecast = json.dumps(incident.forecast, ensure_ascii=False).lower()
    haystack = terms | {diagnosis, forecast}
    for term in SIGNAL_TERMS.get(signal_key, {signal_name(signal_key)}):
        needle = term.lower()
        if needle in haystack or any(needle in item for item in haystack):
            return True
    return False


def severity_for_incidents(incidents: list[Incident]) -> int:
    return clamp(score_severity([i.severity for i in incidents]))


def recurrence_for_edge(cause: str, effect: str, incidents: list[Incident]) -> tuple[int, list[Incident]]:
    supporting = [i for i in incidents if incident_has_signal(i, cause) and incident_has_signal(i, effect)]
    cause_only = [i for i in incidents if incident_has_signal(i, cause)]
    effect_only = [i for i in incidents if incident_has_signal(i, effect)]
    recurrence = len(supporting) * 18 + min(len(cause_only), len(effect_only)) * 7
    return clamp(recurrence), supporting or effect_only or cause_only


def load_context_snapshot(db_path: str) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "db": db_path,
        "source_tables": {},
        "signals": {},
    }
    con = connect(db_path)
    if con is None:
        snapshot["source_tables"] = {k: "example" for k in OPTIONAL_CONTEXT_TABLES}
        snapshot["signals"] = {
            "planner overload": 2,
            "task fanout increase": 3,
            "retry amplification": 5,
            "worker starvation": 4,
            "deferred queue runaway": 4,
            "approval stagnation": 1,
        }
        return snapshot

    try:
        for role, candidates in OPTIONAL_CONTEXT_TABLES.items():
            found = ""
            row_count = 0
            for table in candidates:
                if table_exists(con, table):
                    found = table
                    row_count = int(con.execute(f"select count(*) from {table}").fetchone()[0])
                    break
            snapshot["source_tables"][role] = {"table": found or "not_found", "rows": row_count}

        text_parts: list[str] = []
        for candidates in OPTIONAL_CONTEXT_TABLES.values():
            for table in candidates:
                if not table_exists(con, table):
                    continue
                cols = columns(con, table)
                usable_cols = [c for c in cols if c.endswith("_json") or c in {"pattern_key", "incident_key", "severity", "status"}]
                if not usable_cols:
                    continue
                selected = ", ".join(usable_cols[:8])
                rows = con.execute(f"select {selected} from {table} order by rowid desc limit 25").fetchall()
                for row in rows:
                    text_parts.append(" ".join(str(row[c]) for c in row.keys() if row[c] is not None))
        blob = "\n".join(text_parts).lower()
        for key, terms in SIGNAL_TERMS.items():
            snapshot["signals"][signal_name(key)] = sum(blob.count(term.lower()) for term in terms)
    finally:
        con.close()
    return snapshot


def build_edges(incidents: list[Incident], context: dict[str, Any]) -> list[CausalEdge]:
    context_counts = {str(k).lower(): int(v) for k, v in safe_json(context.get("signals"), {}).items() if str(v).isdigit() or isinstance(v, int)}
    edges: list[CausalEdge] = []
    for cause, effect, base_confidence, base_multiplier in BASE_EDGES:
        recurrence, supporting = recurrence_for_edge(cause, effect, incidents)
        severity = severity_for_incidents(supporting)
        context_boost = min(
            10,
            int(context_counts.get(signal_name(cause), 0)) + int(context_counts.get(signal_name(effect), 0)),
        )
        confidence = clamp(base_confidence * 0.58 + recurrence * 0.27 + severity * 0.15 + context_boost)
        multiplier = round(base_multiplier + (severity / 100.0) * 0.45 + (recurrence / 100.0) * 0.35, 2)
        edges.append(
            CausalEdge(
                cause=cause,
                effect=effect,
                confidence=confidence,
                historical_recurrence=recurrence,
                severity_propagation=severity,
                operational_impact_multiplier=multiplier,
            )
        )
    return sorted(edges, key=lambda e: (-e.confidence, -e.operational_impact_multiplier, e.cause, e.effect))


def outgoing(edges: list[CausalEdge]) -> dict[str, list[CausalEdge]]:
    graph: dict[str, list[CausalEdge]] = {}
    for edge in edges:
        graph.setdefault(edge.cause, []).append(edge)
    for key in graph:
        graph[key].sort(key=lambda e: (-e.confidence, -e.operational_impact_multiplier, e.effect))
    return graph


def incoming(edges: list[CausalEdge]) -> dict[str, list[CausalEdge]]:
    graph: dict[str, list[CausalEdge]] = {}
    for edge in edges:
        graph.setdefault(edge.effect, []).append(edge)
    return graph


def path_score(path: list[CausalEdge]) -> float:
    if not path:
        return 0.0
    confidence = sum(e.confidence for e in path) / len(path)
    recurrence = sum(e.historical_recurrence for e in path) / len(path)
    impact = 1.0
    for edge in path:
        impact *= min(3.0, edge.operational_impact_multiplier)
    return confidence * 0.48 + recurrence * 0.22 + min(100, impact * 12) * 0.30


def find_paths(edges: list[CausalEdge], max_depth: int = 4) -> list[list[CausalEdge]]:
    graph = outgoing(edges)
    all_paths: list[list[CausalEdge]] = []

    def walk(node: str, path: list[CausalEdge], seen: set[str]) -> None:
        if path:
            all_paths.append(path)
        if len(path) >= max_depth:
            return
        for edge in graph.get(node, []):
            if edge.effect in seen:
                continue
            walk(edge.effect, path + [edge], seen | {edge.effect})

    for start in sorted(graph):
        walk(start, [], {start})
    return sorted(all_paths, key=path_score, reverse=True)


def node_scores(edges: list[CausalEdge]) -> dict[str, dict[str, float]]:
    scores: dict[str, dict[str, float]] = {}
    for edge in edges:
        cause = scores.setdefault(edge.cause, {"outgoing": 0.0, "incoming": 0.0, "impact": 0.0, "confidence": 0.0})
        effect = scores.setdefault(edge.effect, {"outgoing": 0.0, "incoming": 0.0, "impact": 0.0, "confidence": 0.0})
        weighted = edge.confidence * edge.operational_impact_multiplier
        cause["outgoing"] += weighted
        cause["impact"] += edge.operational_impact_multiplier
        cause["confidence"] = max(cause["confidence"], edge.confidence)
        effect["incoming"] += weighted
        effect["confidence"] = max(effect["confidence"], edge.confidence)
    return scores


def root_candidates(edges: list[CausalEdge]) -> list[dict[str, Any]]:
    scores = node_scores(edges)
    inc = incoming(edges)
    candidates: list[dict[str, Any]] = []
    for node, stats in scores.items():
        root_score = stats["outgoing"] - stats["incoming"] * 0.42 + stats["impact"] * 8
        if not inc.get(node):
            root_score += 18
        candidates.append(
            {
                "signal": node,
                "label": signal_name(node),
                "confidence": clamp(stats["confidence"] + min(18, root_score / 18)),
                "root_score": round(root_score, 1),
            }
        )
    return sorted(candidates, key=lambda x: (-float(x["root_score"]), str(x["signal"])))


def hotspot_candidates(edges: list[CausalEdge]) -> list[dict[str, Any]]:
    scores = node_scores(edges)
    inc = incoming(edges)
    out = outgoing(edges)
    hot: list[dict[str, Any]] = []
    for node, stats in scores.items():
        outgoing_count = len(out.get(node, []))
        incoming_count = len(inc.get(node, []))
        max_in = max((e.operational_impact_multiplier for e in inc.get(node, [])), default=1.0)
        max_out = max((e.operational_impact_multiplier for e in out.get(node, [])), default=0.0)
        bridge_bonus = 1.2 if incoming_count and outgoing_count else 0.0
        amplification = max_in * max_out + outgoing_count * 0.35 + bridge_bonus
        if amplification <= 0:
            continue
        hot.append(
            {
                "signal": node,
                "label": signal_name(node),
                "impact_multiplier": round(amplification, 2),
                "downstream_instability": clamp(stats["outgoing"] / 4),
                "incoming_pressure": clamp(stats["incoming"] / 5),
                "recommended_containment": signal_name(node),
            }
        )
    return sorted(hot, key=lambda x: (-float(x["impact_multiplier"]), -int(x["downstream_instability"]), str(x["signal"])))


def report_path(edges: list[CausalEdge], root_signal: str) -> list[CausalEdge]:
    paths = find_paths(edges)
    root_paths = [path for path in paths if path and path[0].cause == root_signal]
    terminal_paths = [path for path in root_paths if path[-1].effect == "approval_stagnation"]
    if terminal_paths:
        return sorted(terminal_paths, key=lambda p: (len(p), path_score(p)), reverse=True)[0]
    if root_paths:
        return root_paths[0]
    return paths[0] if paths else []


def format_chain(path: list[CausalEdge]) -> list[str]:
    if not path:
        return []
    chain = [signal_name(path[0].cause)]
    chain.extend(signal_name(edge.effect) for edge in path)
    return chain


def print_chain(chain: list[str]) -> None:
    for idx, item in enumerate(chain):
        if idx:
            print("  ->")
        print(item)


def print_graph(edges: list[CausalEdge], context: dict[str, Any], source: str) -> None:
    roots = root_candidates(edges)
    hotspots = hotspot_candidates(edges)
    best_root = roots[0] if roots else {"label": "unknown", "confidence": 0}
    best_path = report_path(edges, str(best_root.get("signal", "")))
    best_hotspot = hotspots[0] if hotspots else {"label": "unknown", "impact_multiplier": 0}

    print("OPENCLAW CAUSAL GRAPH REPORT")
    print("")
    print(f"memory_source: {source}")
    print("")
    print("Most likely root cause:")
    print(best_root["label"])
    print("")
    print("confidence:")
    print(best_root["confidence"])
    print("")
    print("propagation chain:")
    print_chain(format_chain(best_path))
    print("")
    print("highest amplification hotspot:")
    print(best_hotspot["label"])
    print("")
    print("impact_multiplier:")
    print(best_hotspot["impact_multiplier"])
    print("")
    print("recommended containment target:")
    print(best_root["label"])
    print("")
    print("reason:")
    print("highest downstream instability propagation")
    print("")
    print("causal_edges:")
    for edge in edges:
        print(f"- {signal_name(edge.cause)} -> {signal_name(edge.effect)}")
        print(f"  confidence: {edge.confidence}")
        print(f"  historical_recurrence: {edge.historical_recurrence}")
        print(f"  severity_propagation: {edge.severity_propagation}")
        print(f"  operational_impact_multiplier: {edge.operational_impact_multiplier}")
    print("")
    print("source_context:")
    for role, meta in safe_json(context.get("source_tables"), {}).items():
        print(f"- {role}: {meta}")


def print_roots(edges: list[CausalEdge]) -> None:
    print("OPENCLAW ROOT CAUSE CHAINS")
    print("")
    paths = find_paths(edges)
    for idx, path in enumerate(paths[:5], start=1):
        chain = format_chain(path)
        print(f"ROOT CAUSE CHAIN {idx}")
        print("")
        print_chain(chain)
        print("")
        print(f"chain_confidence: {clamp(sum(e.confidence for e in path) / len(path)) if path else 0}")
        print(f"severity_propagation: {clamp(sum(e.severity_propagation for e in path) / len(path)) if path else 0}")
        print(f"instability_path_score: {round(path_score(path), 1)}")
        if idx < min(5, len(paths)):
            print("")


def print_hotspots(edges: list[CausalEdge]) -> None:
    print("OPENCLAW BOTTLENECK PROPAGATION HOTSPOTS")
    print("")
    graph = outgoing(edges)
    for item in hotspot_candidates(edges)[:6]:
        node = str(item["signal"])
        print(f"- {item['label']}")
        print(f"  impact_multiplier: {item['impact_multiplier']}")
        print(f"  downstream_instability: {item['downstream_instability']}")
        print(f"  incoming_pressure: {item['incoming_pressure']}")
        downstream = [signal_name(edge.effect) for edge in graph.get(node, [])]
        print(f"  propagation_paths: {', '.join(downstream) if downstream else 'none'}")
        print(f"  recommended_containment_target: {item['recommended_containment']}")
    print("")
    print("future_extension_placeholders:")
    for item in FUTURE_PLACEHOLDERS:
        print(f"- {item}")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Deterministic causal graph analysis for operational degradation signals.")
    ap.add_argument("--db", default=DB, help="SQLite database path. Default: DB_PATH/OCLAW_DB_PATH/FACTORY_DB_PATH or factory DB.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("graph", help="Show causal graph report with edge scores.")
    sub.add_parser("roots", help="Show likely root-cause chains.")
    sub.add_parser("hotspots", help="Show bottleneck propagation hotspots.")
    return ap


def main() -> None:
    args = build_parser().parse_args()
    incidents, source = load_incidents(args.db)
    context = load_context_snapshot(args.db)
    edges = build_edges(incidents, context)

    if args.cmd == "graph":
        print_graph(edges, context, source)
        return
    if args.cmd == "roots":
        print_roots(edges)
        return
    if args.cmd == "hotspots":
        print_hotspots(edges)
        return
    raise SystemExit(f"unknown command: {args.cmd}")


if __name__ == "__main__":
    main()
