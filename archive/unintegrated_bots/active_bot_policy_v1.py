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

def allowed_targets() -> list[str]:
    return core_keep() + parked()

def blocked_targets() -> list[str]:
    return archived() + parked()

def normalize(path: str) -> str:
    return (path or "").replace("\\", "/").strip()

def is_allowed_target(path: str) -> bool:
    p = normalize(path)
    return p in set(map(normalize, allowed_targets()))

def is_blocked_target(path: str) -> bool:
    p = normalize(path)
    return p in set(map(normalize, blocked_targets()))

def classify_target(path: str) -> str:
    p = normalize(path)
    if not p:
        return ""
    if p in set(map(normalize, archived())):
        return "archived_or_parked"
    if p in set(map(normalize, parked())):
        return "parked"
    if p in set(map(normalize, core_keep())):
        return "core_keep"
    return ""
