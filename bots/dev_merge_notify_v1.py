from __future__ import annotations
import os
import time
import json
import sqlite3
import requests

DB_PATH = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
STATE_PATH = os.path.expanduser("~/AI/openclaw-factory-daemon/data/dev_merge_notify_v1.state")
SLEEP = int(os.environ.get("DEV_MERGE_NOTIFY_SLEEP", "10"))
TG_TOKEN = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
TG_CHAT = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()

def tg_send(text: str):
    if not TG_TOKEN or not TG_CHAT:
        print("[merge_notify] telegram env missing", flush=True)
        return
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data={"chat_id": TG_CHAT, "text": text},
        timeout=(3, 20),
    ).raise_for_status()

def load_last_id() -> int:
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return int((f.read() or "0").strip() or "0")
    except Exception:
        return 0

def save_last_id(v: int):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        f.write(str(v))

def explain_type(v: str) -> str:
    t = (v or "").strip().lower()
    if t in ("bugfix", "bug_fix", "fix"):
        return "不具合を潰して、止まりにくくする修正です。"
    if t in ("guard", "safety"):
        return "異常系を吸収して、落ちにくくする修正です。"
    if t in ("refactor",):
        return "構造整理で、今後の保守と追加開発をしやすくする修正です。"
    if t in ("logging", "observability", "diagnostics"):
        return "原因追跡をしやすくする、運用向けの修正です。"
    if t in ("optimization", "performance"):
        return "速度や負荷を改善する修正です。"
    if t in ("automation",):
        return "自動化を進めて、手作業を減らす修正です。"
    return "安定性または運用性を上げる修正です。"

def shorten(s: str, n: int) -> str:
    s = (s or "").strip().replace("\n", " ")
    return s if len(s) <= n else s[:n].rstrip() + "..."

def build_msg(ev: sqlite3.Row, dp: sqlite3.Row | None) -> str:
    pid = ev["proposal_id"]
    title = shorten((ev["title"] or "").replace("統   合   完   了   : ", "").replace("統  合  完  了  : ", "").strip(), 140)
    pr_url = (ev["pr_url"] or "").strip()

    target_system = ""
    improvement_type = ""
    source_ai = ""
    result_note = ""
    result_type = ""

    if dp is not None:
        target_system = dp["target_system"] or ""
        improvement_type = dp["improvement_type"] or ""
        source_ai = dp["source_ai"] or ""
        result_note = dp["result_note"] or ""
        result_type = dp["result_type"] or ""

    lines = []
    lines.append("🚀 Kaikun01 開発完了")
    lines.append(f"案件ID: {pid}")
    lines.append(f"内容: {title}")

    if target_system:
        lines.append(f"対象: {target_system}")

    if improvement_type:
        lines.append(f"種類: {improvement_type}")
        lines.append(f"解説: {explain_type(improvement_type)}")
    else:
        lines.append("解説: 安定性または運用性を上げる修正です。")

    if source_ai:
        lines.append(f"実行者: {source_ai}")

    if result_type:
        lines.append(f"学習結果: {result_type}")

    if result_note:
        lines.append(f"補足: {shorten(result_note, 120)}")

    lines.append("結果: main への統合完了")

    if pr_url:
        lines.append(f"PR: {pr_url}")

    return "\n".join(lines)

def main():
    while True:
        try:
            last_id = load_last_id()
            conn = sqlite3.connect(DB_PATH, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("pragma busy_timeout=30000")

            rows = conn.execute("""
                select
                  e.id,
                  e.event_type,
                  e.proposal_id,
                  e.title,
                  coalesce(e.pr_url,'') as pr_url
                from ceo_hub_events e
                where e.event_type='merged'
                  and e.id > ?
                order by e.id asc
            """, (last_id,)).fetchall()

            new_last = last_id

            for r in rows:
                dp = conn.execute("""
                    select
                      id,
                      target_system,
                      improvement_type,
                      source_ai,
                      result_type,
                      result_note
                    from dev_proposals
                    where id=?
                    limit 1
                """, (r["proposal_id"],)).fetchone()

                msg = build_msg(r, dp)
                tg_send(msg)
                new_last = int(r["id"])
                print(f"[merge_notify] sent event_id={new_last} proposal_id={r['proposal_id']}", flush=True)

            conn.close()

            if new_last != last_id:
                save_last_id(new_last)

        except Exception as e:
            print(f"[merge_notify] error {e!r}", flush=True)

        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
