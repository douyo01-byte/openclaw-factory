#!/usr/bin/env python3
import json
from typing import Any

def decompose(domain: str, text: str, context: dict[str, Any]) -> dict[str, Any]:
    if domain == "creative":
        steps = [
            "analyze_source",
            "extract_claims",
            "extract_ingredients_or_features",
            "generate_angles",
            "generate_variants",
            "self_review",
            "format_reply",
        ]
    elif domain == "development":
        steps = [
            "analyze_requirement",
            "inspect_existing_code",
            "define_change_scope",
            "implement",
            "test",
            "summarize_result",
            "format_reply",
        ]
    else:
        steps = [
            "analyze_source",
            "extract_key_points",
            "summarize_findings",
            "format_reply",
        ]
    return {
        "domain": domain,
        "request_text": text,
        "context": context,
        "steps": [{"step_order": i + 1, "step_type": s} for i, s in enumerate(steps)],
    }

def main() -> None:
    import sys
    payload = json.loads(sys.stdin.read())
    print(json.dumps(decompose(payload["domain"], payload["text"], payload["context"]), ensure_ascii=False))

if __name__ == "__main__":
    main()
