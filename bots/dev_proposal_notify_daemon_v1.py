from __future__ import annotations
import os, time, sqlite3, re
import requests

DB_PATH=os.environ.get("DB_PATH","data/openclaw.db")
BOT_TOKEN=os.environ.get("TELEGRAM_BOT_TOKEN","")
CHAT_ID=os.environ.get("TELEGRAM_CHAT_ID","")

def _conn():
    c=sqlite3.connect(DB_PATH)
    c.row_factory=sqlite3.Row
    return c

def tg_send(text: str) -> str:
    if not BOT_TOKEN or not CHAT_ID:
        return ""
    url=f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r=requests.post(url, json={"chat_id":CHAT_ID,"text":text}, timeout=20)
    if r.status_code!=200:
        return ""
    j=r.json()
    if not j.get("ok"):
        return ""
    m=j.get("result",{}).get("message_id","")
    return str(m) if m is not None else ""

def build_text(row) -> str:
    pid=row["id"]
    title=(row["title"] if "title" in row.keys() else "") or ""
    body=(row["proposal"] if "proposal" in row.keys() else "") or ""
    status=(row["status"] or "")

    head={
        "proposed":"🧠 開発提案が届きました",
        "needs_info":"❓ 追加情報が必要です",
        "req":"❓ 詳細が必要です",
        "approved":"✅ 採用しました",
        "hold":"⏸ 保留中です",
        "merged":"🏁 完了しました",
    }.get(status,"🧠 開発提案")

    act={
        "proposed":"次のどれかを返信してください（迷ったら質問）。",
        "needs_info":"質問に答えるか、追加で質問してください。",
        "req":"詳細を返信してください（ログ/症状/期待動作）。",
        "approved":"採用済みです。実行側の進行を待ちます。",
        "hold":"保留中です。再開するなら採用/質問。",
        "merged":"完了済みです。",
    }.get(status,"返信で操作できます。")

    x=[]
    x.append(f"{head} (#{pid})")
    x.append(f"状態: {status}")
    x.append("")
    x.append(act)

    if title:
        x.append("")
        x.append("要点:")
        x.append(title.strip()[:140])

    if body:
        t=[y.strip() for y in body.strip().splitlines() if y.strip()]
        if t:
            x.append("")
            x.append("概要（先頭のみ）:")
            x.append(("- " + "\n- ".join(t[:3]))[:600])

    x.append("")
    x.append("返信テンプレ（そのまま送ってOK）:")
    x.append(f"承認 #{pid}")
    x.append(f"保留 #{pid}")
    x.append(f"質問 #{pid} どのファイルを触りますか？")
    return "\n".join(x)

def tick():

    conn=_conn()
    rows=conn.execute(
        "SELECT * FROM dev_proposals WHERE status='proposed' AND ((notified_at IS NULL OR notified_at='') OR (notified_msg_id IS NULL OR notified_msg_id='')) ORDER BY id ASC LIMIT 20"
    ).fetchall()
    for r in rows:
        text=build_text(r)
        mid=tg_send(text)
        conn.execute(
            "UPDATE dev_proposals SET notified_at=datetime('now','localtime'), notified_msg_id=? WHERE id=?",
            (mid, r["id"]),
        )
        conn.commit()
    conn.close()

def main():
    interval=int(os.environ.get("PROPOSAL_NOTIFY_INTERVAL","5"))
    while True:
        try:
            tick()
        except Exception:
            pass
        time.sleep(interval)

if __name__=="__main__":
    main()
