def format_dev_reply(proposal_id: int, decision: str, extra: str | None = None) -> str:
    decision = (decision or "").strip().lower()
    if decision.startswith("ok"):
        return f"""✅ 開発提案 #{proposal_id} を承認しました

・自動でPRを作成
・自動でマージ
・開発パイプラインに反映

Factoryは次のフェーズへ進みます。"""
    if decision.startswith("hold"):
        return f"""⏸ 開発提案 #{proposal_id} は保留になりました

追加判断が行われるまで実行は停止しています。"""
    if decision.startswith("req"):
        reason = extra or "追加情報が必要です"
        return f"""❓ 開発提案 #{proposal_id} は追加確認が必要です

理由：
{reason}

Telegramで返信してください。"""
    return f"🤖 不明な状態: {decision}"
