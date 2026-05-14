#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GOAL_DOC = ROOT / "docs" / "OPENCLAW_LONG_HORIZON_GOAL.md"


def _read_goal_doc(path: Path = GOAL_DOC) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _section(text: str, heading: str) -> str:
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    return match.group("body").strip() if match else ""


def _clean_scalar(value: str) -> str:
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    if not lines:
        return ""
    first = lines[0]
    return first[2:].strip() if first.startswith("- ") else first


def _bullets(value: str) -> list[str]:
    items = []
    for line in value.splitlines():
        line = line.strip()
        if line.startswith("- "):
            items.append(line[2:].strip())
    return items


def _roadmap(text: str) -> list[dict[str, Any]]:
    body = _section(text, "Staged Roadmap")
    phases: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw in body.splitlines():
        line = raw.strip()
        if line.startswith("### "):
            if current:
                phases.append(current)
            title = line[4:].strip()
            current = {"phase": title, "items": []}
        elif line.startswith("- ") and current is not None:
            current["items"].append(line[2:].strip())
    if current:
        phases.append(current)
    return phases


def read_active_goal(path: Path = GOAL_DOC) -> dict[str, Any]:
    text = _read_goal_doc(path)
    if not text:
        return {
            "ok": False,
            "active_goal": "",
            "current_phase": "",
            "current_focus": "",
            "next_best_step": "",
            "blocked_by": ["goal document not found"],
            "safety_status": "read-only; goal document unavailable",
            "expected_value": "",
            "source_docs": [],
            "roadmap": [],
            "doc_path": str(path),
        }

    blocked = _bullets(_section(text, "Blocked By"))
    return {
        "ok": True,
        "active_goal": _clean_scalar(_section(text, "Active Goal")),
        "current_phase": _clean_scalar(_section(text, "Current Phase")),
        "current_focus": _clean_scalar(_section(text, "Current Focus")),
        "next_best_step": _clean_scalar(_section(text, "Next Best Step")),
        "blocked_by": blocked,
        "safety_status": _clean_scalar(_section(text, "Safety Status")),
        "expected_value": _clean_scalar(_section(text, "Expected Value")),
        "source_docs": _bullets(_section(text, "Source Of Truth Docs")),
        "roadmap": _roadmap(text),
        "doc_path": str(path),
    }


def main() -> None:
    import json

    print(json.dumps(read_active_goal(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
