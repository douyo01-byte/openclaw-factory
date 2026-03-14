from __future__ import annotations
import os, time, sqlite3, requests

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = float(os.environ.get("KAIKUN02_ROUTER_WORKER_SLEEP", "8"))
BOT_TOKEN = (os.environ.get("KAIKUN02_ROUTER_BOT_TOKEN") or os.environ.get("TELEGRAM_CEO_BOT_TOKEN") or "").strip()
CHAT_ID = (os.environ.get("KAIKUN02_ROUTER_CHAT_ID") or os.environ.get("TELEGRAM_CEO_CHAT_ID") or "").strip()

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    try:
        c.execute("pragma journal_mode=WAL")
    except Exception:
        pass
    return c

def ensure_schema(c):
    cols = {r["name"] for r in c.execute("pragma table_info(router_tasks)").fetchall()}
    if "started_at" not in cols:
        c.execute("alter table router_tasks add column started_at text default ''")
    if "finished_at" not in cols:
        c.execute("alter table router_tasks add column finished_at text default ''")
    if "result_text" not in cols:
        c.execute("alter table router_tasks add column result_text text default ''")
    if "sent_message_id" not in cols:
        c.execute("alter table router_tasks add column sent_message_id text default ''")

def tg_send(text: str):
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError("kaikun02 telegram env missing")
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text},
        timeout=20,
    )
    r.raise_for_status()
    j = r.json()
    return str(((j.get("result") or {}).get("message_id") or ""))

def quick_dashboard(c):
    total = c.execute("select count(*) from dev_proposals").fetchone()[0]
    merged = c.execute("select count(*) from dev_proposals where coalesce(status,'')='merged'").fetchone()[0]
    pending = c.execute("""
        select count(*) from dev_proposals
        where coalesce(status,'') in ('pending','approved','new','open','execute_now','pr_created')
    """).fetchone()[0]
    started = c.execute("select count(*) from router_tasks where coalesce(status,'')='started'").fetchone()[0]
    timeout = c.execute("select count(*) from router_tasks where coalesce(status,'')='timeout'").fetchone()[0]
    return "\n".join([
        "📊 OpenClaw 進捗",
        "",
        f"提案総数: {total}",
        f"マージ済: {merged}",
        f"保留系: {pending}",
        f"進行中タスク: {started}",
        f"timeout: {timeout}",
    ])

def quick_next_tasks(c):
    rows = c.execute("""
        select id, coalesce(title,'') as title
        from dev_proposals
        where coalesce(status,'') <> 'merged'
        order by id desc
        limit 5
    """).fetchall()
    out = ["🔧 次の作業候補", ""]
    if not rows:
        out.append("未マージ候補は見当たりません。")
        return "\n".join(out)
    for r in rows:
        out.append(f"- {r['id']} {r['title']}")
    return "\n".join(out)

def quick_weak_points(c):
    stalled = c.execute("select count(*) from router_tasks where coalesce(status,'')='timeout'").fetchone()[0]
    nostart = c.execute("select count(*) from router_tasks where coalesce(status,'')='new'").fetchone()[0]
    return "\n".join([
        "⚠️ 弱点チェック",
        "",
        f"timeoutタスク: {stalled}",
        f"未処理タスク: {nostart}",
        "大きな異常はありません。" if stalled == 0 and nostart < 20 else "処理滞留を確認してください。"
    ])

def normalize_text(s: str) -> str:
    return "".join((s or "").lower().split())

def tick():
    c = conn()
    try:
        ensure_schema(c)
        rows = c.execute("""
            select id, task_text
            from router_tasks
            where coalesce(status,'new')='new'
              and coalesce(target_bot,'')='kaikun02'
            order by id asc
            limit 5
        """).fetchall()
        done = 0
        for r in rows:
            txt_raw = r["task_text"] or ""
            txt = normalize_text(txt_raw)

            if "進捗" in txt or "status" in txt:
                body = quick_dashboard(c)
                sent_message_id = tg_send(body)
                result = f"quick_dashboard_sent: {body[:120]}"
            elif "次の作業" in txt or "next" in txt:
                body = quick_next_tasks(c)
                sent_message_id = tg_send(body)
                result = f"quick_next_sent: {body[:120]}"
            elif "弱点" in txt or "problem" in txt:
                body = quick_weak_points(c)
                sent_message_id = tg_send(body)
                result = f"quick_weak_sent: {body[:120]}"
            else:
                routed_text = f"[TASK_ID:{r['id']}]\n{txt_raw}\n\n返信の先頭に [TASK_ID:{r['id']}] を付けてください。"
                sent_message_id = tg_send(routed_text)
                result = f"sent_to_kaikun02: {routed_text[:120]}"

            c.execute("""
                update router_tasks
                set status='started',
                    started_at=datetime('now'),
                    updated_at=datetime('now'),
                    result_text=?,
                    sent_message_id=?
                where id=?
            """, (result, sent_message_id, r["id"]))
            done += 1

        if done:
            c.commit()
        print(f"[kaikun02_router_worker_v1] done={done}", flush=True)
    finally:
        c.close()

def main():
    while True:
        try:
            tick()
        except Exception as e:
            print(f"[kaikun02_router_worker_v1] err={e!r}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
