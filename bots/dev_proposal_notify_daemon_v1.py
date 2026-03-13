from __future__ import annotations
import os
import time
import sqlite3
import requests

DB_PATH = os.environ.get("DB_PATH", "data/openclaw.db")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def _conn():
    c = sqlite3.connect(DB_PATH, timeout=20, isolation_level=None)
    try:
        c.execute("PRAGMA busy_timeout=20000")
    except Exception:
        pass
    try:
        c.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    try:
        c.execute("PRAGMA synchronous=NORMAL")
    except Exception:
        pass
    c.row_factory = sqlite3.Row
    return c


def tg_send(text: str) -> str:
    if not BOT_TOKEN or not CHAT_ID:
        return ""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=20)
    if r.status_code != 200:
        return ""
    j = r.json()
    if not j.get("ok"):
        return ""
    m = j.get("result", {}).get("message_id", "")
    return str(m) if m is not None else ""


def build_text(row) -> str:
    pid = row["id"]
    title = (row["title"] if "title" in row.keys() else "") or ""
    body = (row["proposal"] if "proposal" in row.keys() else "") or ""
    status = row["status"]
    s = []
    s.append(f"🧠 新しい開発提案 #{pid}")
    if title:
        s.append("")
        s.append("タイトル:")
        s.append(title.strip())
    if body:
        s.append("")
        s.append("概要:")
        s.append(body.strip()[:1200])
    s.append("")
    s.append(f"状態: {status}")
    s.append("")
    s.append("返信で操作:")
    s.append(f"承認 #{pid}")
    s.append(f"保留 #{pid}")
    s.append(f"質問 #{pid} 内容")
    return "\n".join(s)


def tick():
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT * FROM dev_proposals WHERE status='proposed' AND ((notified_at IS NULL OR notified_at='') OR (notified_msg_id IS NULL OR notified_msg_id='')) ORDER BY id ASC LIMIT 20"
        ).fetchall()
        for r in rows:
            text = build_text(r)
            try:
                mid = tg_send(text)
            except Exception:
                mid = ""
            conn.execute(
                "UPDATE dev_proposals SET notified_at=datetime('now'), notified_msg_id=? WHERE id=?",
                (mid, r["id"]),
            )
        if rows:
            conn.commit()
    finally:
        conn.close()


def human_explain(row):
    title = str(row["title"] or "").strip()
    target = str(row["target_system"] or "").strip()
    kind = str(row["improvement_type"] or "").strip()
    status = str(row["status"] or "").strip()
    pr = str(row["pr_number"] or "").strip()
    source_ai = str(row["source_ai"] or "").strip()

    what = "自動開発"
    if status == "approved":
        what = "開発候補を生成"
    elif status == "pr_created":
        what = "PRを自動作成"
    elif status == "merged":
        what = "本流へ反映"

    lines = []
    lines.append(f"🛠 BOT開発通知")
    lines.append(f"状態: {what}")
    lines.append(f"対象: {target or '-'}")
    lines.append(f"内容: {title or '-'}")
    lines.append(f"種別: {kind or '-'}")
    lines.append(f"実行AI: {source_ai or '-'}")

    explain = []
    t = (title or "").lower()
    if "guard" in t:
        explain.append("異常系で落ちにくくする修正です。")
    elif "bugfix" in t:
        explain.append("不具合や取りこぼしを減らす修正です。")
    elif "refactor" in t:
        explain.append("構造整理で保守しやすくする修正です。")
    elif "logging" in t:
        explain.append("原因追跡をしやすくする修正です。")
    elif "optimization" in t or "performance" in t:
        explain.append("速度や負荷を改善する修正です。")
    else:
        explain.append("安定性または運用性を上げる修正です。")

    lines.append("解説: " + " ".join(explain))

    if pr:
        lines.append(f"PR: #{pr}")

    return "\n".join(lines)

def main():
    interval = int(os.environ.get("PROPOSAL_NOTIFY_INTERVAL", "5"))
    while True:
        try:
            tick()
        except Exception as e:
            print('[notify] err', repr(e), flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()
