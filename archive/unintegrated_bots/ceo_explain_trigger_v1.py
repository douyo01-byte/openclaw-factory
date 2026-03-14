import os
import sqlite3
import datetime
import requests

DB = os.environ.get("DB_PATH") or "data/openclaw.db"
TOKEN = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA busy_timeout=30000")
    try:
        c.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    return c

def tg_send(chat_id, text):
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": str(chat_id), "text": text},
        timeout=20,
    )
    r.raise_for_status()

def norm(text):
    t = (text or "").lower()
    for x in [" ", "　", "?", "？", "。", "!", "！", "\n", "\r", "\t"]:
        t = t.replace(x, "")
    return t

def detect_mode(text):
    t = norm(text)
    if not t:
        return None
    if any(k in t for k in ["技術詳細", "技術", "実装詳細"]):
        return "tech"
    if any(k in t for k in ["なぜai", "なぜ", "理由", "どうして"]):
        return "reason"
    if any(k in t for k in ["実装コスト", "コスト", "工数", "負荷"]):
        return "cost"
    if any(k in t for k in ["詳しく", "詳細", "詳報", "その件詳しく", "もっと詳しく", "この案件を詳しく"]):
        return "summary"
    return None

def latest_target(c):
    return c.execute("""
        select
          id,
          coalesce(title,'不明') as title,
          coalesce(nullif(source_ai,''), nullif(brain_type,''), nullif(decided_by,''), '不明') as ai_name,
          coalesce(nullif(project_decision,''), '未判定') as decision,
          coalesce(priority, 0) as priority,
          coalesce(nullif(result_type,''), 'pending') as result_type,
          coalesce(result_score, 0) as result_score,
          coalesce(nullif(description,''), '') as description,
          coalesce(nullif(spec,''), '') as spec
        from dev_proposals
        order by priority desc, id desc
        limit 1
    """).fetchone()

def decision_label(v):
    m = {
        "execute_now": "今すぐ実行",
        "backlog": "保留 / バックログ",
        "pending": "未判定",
        "approved": "承認済み",
    }
    return m.get((v or "").strip(), v or "未判定")

def purpose_text(r):
    src = f"{r['title']}\n{r['description']}\n{r['spec']}".lower()
    if "safety" in src or "guard" in src or "security" in src:
        return "開発や運用で危険な変更を防ぎ、安全性を上げることが目的です。"
    if "logging" in src or "log" in src:
        return "状況把握と障害解析をしやすくし、運用効率を上げることが目的です。"
    if "dashboard" in src or "board" in src:
        return "社長や運用側が全体状況を短時間で把握できるようにすることが目的です。"
    if (r["description"] or "").strip():
        return "提案内容を前進させ、開発と運用の質を高めることが目的です。"
    return "OpenClaw全体の安定性と運用効率を高めるための提案です。"

def why_now_text(r):
    p = float(r["priority"] or 0)
    d = (r["decision"] or "").strip()
    if d == "execute_now":
        return "優先度が高く、今動かす価値があると判断されています。"
    if p >= 5:
        return "他案件より優先して確認する価値がある状態です。"
    if p > 0:
        return "緊急ではありませんが、候補として継続監視する段階です。"
    return "現時点では低優先度で、必要性を見極める段階です。"

def risk_text(r):
    title = (r["title"] or "").lower()
    if "safety" in title or "guard" in title or "security" in title:
        return "今すぐ大きな事故に直結しなくても、将来の変更規模が大きくなるほど未整備の影響が出やすくなります。"
    if "logging" in title or "log" in title:
        return "放置すると原因調査や障害切り分けに時間がかかる可能性があります。"
    return "短期リスクは大きくありませんが、将来の拡張時に重要度が上がる可能性があります。"

def next_action_text(r):
    d = (r["decision"] or "").strip()
    if d == "execute_now":
        return "・実装範囲の確定\n・影響箇所の確認\n・着手判断"
    if d == "backlog":
        return "・必要性の再評価\n・技術影響の確認\n・着手条件の整理"
    return "・案件意図の整理\n・優先度の再確認\n・次回判定材料の準備"

def tech_detail_text(r):
    desc = (r["description"] or "").strip()
    spec = (r["spec"] or "").strip()
    body = []
    body.append(f"案件 #{r['id']} の技術詳細です")
    body.append("")
    body.append("■ 技術的に見るポイント")
    title = (r["title"] or "").lower()
    if "dashboard" in title or "board" in title:
        body.append("・集計元DBの整理")
        body.append("・表示項目の優先順位設計")
        body.append("・Telegramで崩れない本文生成")
        body.append("・重複送信や無反応防止")
    elif "logging" in title or "log" in title:
        body.append("・ログ出力粒度の統一")
        body.append("・障害時に追いやすい形式化")
        body.append("・不要ログ削減と可読性向上")
    elif "safety" in title or "guard" in title or "security" in title:
        body.append("・危険操作の遮断条件")
        body.append("・誤実行を防ぐガード分岐")
        body.append("・既存運用を壊さない導入順")
    else:
        body.append("・既存処理への影響確認")
        body.append("・追加ロジックの責務分離")
        body.append("・運用ループでの安定動作確認")
    if desc:
        body.append("")
        body.append("■ 説明文")
        body.append(desc[:700])
    if spec:
        body.append("")
        body.append("■ 仕様メモ")
        body.append(spec[:700])
    body.append("")
    body.append("必要なら次に")
    body.append("・なぜAIがこの提案を出したか")
    body.append("・実装コスト感")
    body.append("まで続けて説明できます。")
    return "\n".join(body)

def reason_detail_text(r):
    src = f"{r['title']}\n{r['description']}\n{r['spec']}".lower()
    lines = []
    lines.append(f"案件 #{r['id']} をAIが提案した理由です")
    lines.append("")
    lines.append("■ 提案理由")
    if "dashboard" in src or "board" in src:
        lines.append("社長や運用側の把握速度を上げる効果が大きく、経営判断の入口として価値が高いためです。")
    elif "logging" in src or "log" in src:
        lines.append("障害解析や日常運用の効率改善につながり、地味ですが継続効果が高いためです。")
    elif "safety" in src or "guard" in src or "security" in src:
        lines.append("将来の事故や誤操作を未然に減らせる可能性があり、守りの価値があるためです。")
    else:
        lines.append("既存業務の改善余地があり、安定性または効率向上に寄与すると判断されたためです。")
    lines.append("")
    lines.append("■ AI視点の判断材料")
    lines.append(f"・現在の判断: {decision_label(r['decision'])}")
    lines.append(f"・優先度: {r['priority']}")
    lines.append(f"・評価: {r['result_type']} / score={r['result_score']}")
    lines.append("")
    lines.append("■ 補足")
    lines.append("この提案は、即実装だけでなく“後で効く改善候補”として保持されている可能性もあります。")
    lines.append("")
    lines.append("必要なら次に")
    lines.append("・技術詳細")
    lines.append("・実装コスト感")
    lines.append("まで続けて説明できます。")
    return "\n".join(lines)

def cost_detail_text(r):
    title = (r["title"] or "").lower()
    lines = []
    lines.append(f"案件 #{r['id']} の実装コスト感です")
    lines.append("")
    lines.append("■ ざっくり見積り")
    if "dashboard" in title or "board" in title:
        lines.append("中程度です。")
        lines.append("集計SQL、本文整形、会話分岐、送信確認まで入るため、点ではなく面の調整になります。")
    elif "logging" in title or "log" in title:
        lines.append("低〜中程度です。")
        lines.append("既存構造が崩れていなければ比較的入れやすいですが、運用確認に時間がかかる可能性があります。")
    elif "safety" in title or "guard" in title or "security" in title:
        lines.append("中程度です。")
        lines.append("事故防止系は条件漏れ確認が必要なので、実装自体より検証コストが乗りやすいです。")
    else:
        lines.append("小〜中程度です。")
        lines.append("既存コードへの影響範囲次第で上下します。")
    lines.append("")
    lines.append("■ コストが増える要因")
    lines.append("・既存本線を壊さない制約")
    lines.append("・Telegram会話の自然さ調整")
    lines.append("・運用ループ上での再起動確認")
    lines.append("")
    lines.append("■ 次の判断")
    lines.append("先に小さく通してから、本文や分岐を段階的に厚くする進め方が安全です。")
    return "\n".join(lines)

def build_explain_text(r):
    return "\n".join([
        f"案件 #{r['id']} の詳報です",
        "",
        "■ 件名",
        f"{r['title']}",
        "",
        "■ 発案AI",
        f"{r['ai_name']}",
        "",
        "■ 現在の判断",
        f"{decision_label(r['decision'])}",
        "",
        "■ 優先度",
        f"{r['priority']}",
        "",
        "■ 評価",
        f"{r['result_type']}",
        "",
        "■ スコア",
        f"{r['result_score']}",
        "",
        "■ この案件の目的",
        f"{purpose_text(r)}",
        "",
        "■ なぜ今見るべきか",
        f"{why_now_text(r)}",
        "",
        "■ 放置リスク",
        f"{risk_text(r)}",
        "",
        "■ 次にやること",
        f"{next_action_text(r)}",
        "",
        "必要なら次に",
        "・技術詳細",
        "・なぜAIがこの提案を出したか",
        "・実装コスト感",
        "まで続けて説明できます。"
    ])

def build_reply(mode, r):
    if mode == "tech":
        return tech_detail_text(r)
    if mode == "reason":
        return reason_detail_text(r)
    if mode == "cost":
        return cost_detail_text(r)
    return build_explain_text(r)

def run_once():
    if not TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN empty")
    done = 0
    with conn() as c:
        rows = c.execute("""
            select id, chat_id, text
            from inbox_commands
            where coalesce(processed,0)=0
            order by id asc
            limit 20
        """).fetchall()
        for row in rows:
            mode = detect_mode(row["text"] or "")
            if not mode:
                continue
            tgt = latest_target(c)
            if tgt:
                tg_send(row["chat_id"], build_reply(mode, tgt))
            else:
                tg_send(row["chat_id"], "詳報対象の案件がまだありません。")
            c.execute(
                "update inbox_commands set processed=1,status='explain_trigger_done',applied_at=? where id=?",
                (now(), int(row["id"]))
            )
            done += 1
        c.commit()
    print(f"explain_trigger_done={done}", flush=True)

if __name__ == "__main__":
    run_once()
