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

def allowed_targets() -> list[str]:
    return core_keep() + parked()

def is_allowed_target(path: str) -> bool:
    p = (path or "").replace("\\", "/")
    return p in set(allowed_targets())
