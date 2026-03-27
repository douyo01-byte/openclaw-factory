#!/usr/bin/env python3
import json

def format_reply(payload: dict) -> str:
    domain = payload.get("domain", "")
    context = payload.get("context", {})
    steps = payload.get("steps", [])
    lines = []
    lines.append("依頼を受理しました。")
    lines.append(f"領域: {domain}")
    if context.get("target_object"):
        lines.append(f"対象: {context['target_object']}")
    if context.get("urls"):
        lines.append("参照URL:")
        lines.extend([f"- {u}" for u in context["urls"]])
    lines.append("内部実行ステップ:")
    lines.extend([f"{s['step_order']}. {s['step_type']}" for s in steps])
    lines.append("次アクション: 実処理へ進行")
    return "\n".join(lines)

def main() -> None:
    import sys
    payload = json.loads(sys.stdin.read())
    print(format_reply(payload))

if __name__ == "__main__":
    main()
