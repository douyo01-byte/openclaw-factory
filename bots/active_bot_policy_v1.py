from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT / "config" / "active_bot_policy_20260313.json"

def load_policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))

def core_keep() -> list[str]:
    return list(load_policy().get("core_keep", []))

def parked() -> list[str]:
    return list(load_policy().get("parked", []))

def archived_keywords() -> list[str]:
    return [str(x).lower() for x in load_policy().get("archived_keywords", [])]

def parked_keywords() -> list[str]:
    return [str(x).lower() for x in load_policy().get("parked_keywords", [])]

def classify_text(text: str) -> str:
    s = (text or "").lower()
    for k in archived_keywords():
        if k in s:
            return "archived_or_parked"
    for k in parked_keywords():
        if k in s:
            return "parked"
    return ""

def is_archived_or_parked_text(text: str) -> bool:
    return classify_text(text) == "archived_or_parked"
