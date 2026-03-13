from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLICY = ROOT / "config" / "active_bot_policy_20260313.json"

def load_policy() -> dict:
    return json.loads(POLICY.read_text(encoding="utf-8"))

def core_keep() -> list[str]:
    return list(load_policy().get("core_keep", []))

def parked() -> list[str]:
    return list(load_policy().get("parked", []))

def archived() -> list[str]:
    return list(load_policy().get("archived", []))

def allowed_targets() -> set[str]:
    return set(core_keep())

def parked_targets() -> set[str]:
    return set(parked())

def archived_targets() -> set[str]:
    return set(archived())

def normalize(path: str) -> str:
    return (path or "").replace("\\", "/").strip()

def is_allowed_target(path: str) -> bool:
    return normalize(path) in allowed_targets()

def is_parked_target(path: str) -> bool:
    return normalize(path) in parked_targets()

def is_archived_target(path: str) -> bool:
    return normalize(path) in archived_targets()

def classify_text(text: str) -> str:
    t = (text or "").lower()
    for x in sorted(archived_targets()):
        name = x.split("/")[-1].lower()
        if name and name in t:
            return "archived_or_parked"
    for x in sorted(parked_targets()):
        name = x.split("/")[-1].lower()
        if name and name in t:
            return "parked"
    return ""
