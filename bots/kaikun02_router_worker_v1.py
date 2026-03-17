from __future__ import annotations
import os
import time
import sqlite3
import requests
from pathlib import Path

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

def quick_ai_employee_ranking(c):
    rows = c.execute("""
        select
          rank_no,
          coalesce(source_ai,'') as source_ai,
          coalesce(total_count,0) as total_count,
          coalesce(merged_count,0) as merged_count,
          coalesce(merge_rate,0) as merge_rate,
          coalesce(score,0) as score
        from ai_employee_rankings
        order by rank_no asc
        limit 10
    """).fetchall()
    out = ["📊 OpenClaw AI社員ランキング", ""]
    if not rows:
        out.append("ランキングデータはまだありません。")
        return "\n".join(out)
    for r in rows:
        out.append(
            f"{r['rank_no']}. {r['source_ai']} proposals={r['total_count']} merged={r['merged_count']} merge_rate={float(r['merge_rate']):.4f} score={float(r['score']):.4f}"
        )
    return "\n".join(out)

def quick_runtime_classification():
    p = Path("/Users/doyopc/AI/openclaw-factory-daemon/reports/audit_20260317/runtime_classification_merged.md")
    try:
        return p.read_text(encoding="utf-8")[:3500]
    except Exception as e:
        return f"Runtime classification 読 み 込 み 失 敗 : {e}"


def quick_flow_bottleneck(c):
    total = c.execute("select count(*) from dev_proposals").fetchone()[0]
    merged = c.execute("""
        select count(*) from dev_proposals
        where coalesce(status,'')='merged'
          and coalesce(dev_stage,'')='merged'
          and coalesce(pr_status,'')='merged'
    """).fetchone()[0]
    open_pr = c.execute("""
        select count(*) from dev_proposals
        where coalesce(pr_status,'')='open'
          and coalesce(pr_url,'')<>''
    """).fetchone()[0]
    waiting_inbox = c.execute("""
        select count(*) from inbox_commands
        where coalesce(processed,0)=0
    """).fetchone()[0]
    router_new = c.execute("""
        select count(*) from router_tasks
        where coalesce(status,'')='new'
    """).fetchone()[0]
    router_started = c.execute("""
        select count(*) from router_tasks
        where coalesce(status,'')='started'
    """).fetchone()[0]
    router_timeout = c.execute("""
        select count(*) from router_tasks
        where coalesce(status,'')='timeout'
    """).fetchone()[0]
    refined_wait = c.execute("""
        select count(*) from dev_proposals
        where coalesce(status,'') in ('promoted','refining','refined')
    """).fetchone()[0]
    executor_wait = c.execute("""
        select count(*) from dev_proposals
        where coalesce(status,'') in ('decomposed','executor_ready','execute_now','approved','pr_created')
          and coalesce(pr_status,'')<>'merged'
    """).fetchone()[0]

    stages = [
        ("task_router_v1", waiting_inbox + router_new),
        ("kaikun02_router_worker_v1", router_started),
        ("dev_pr_watcher_v1", open_pr),
        ("spec_refiner_v2", refined_wait),
        ("dev_pr_creator_v1", executor_wait),
    ]
    stages.sort(key=lambda x: x[1], reverse=True)
    top_name, top_count = stages[0]

    out = []
    out.append("🚦 OpenClaw 本流ボトルネック")
    out.append("")
    out.append(f"total={total}")
    out.append(f"merged={merged}")
    out.append(f"open_pr={open_pr}")
    out.append(f"inbox_waiting={waiting_inbox}")
    out.append(f"router_new={router_new}")
    out.append(f"router_started={router_started}")
    out.append(f"router_timeout={router_timeout}")
    out.append(f"refined_wait={refined_wait}")
    out.append(f"executor_wait={executor_wait}")
    out.append("")
    out.append(f"top_bottleneck={top_name} ({top_count})")

    if top_name == "task_router_v1":
        out.append("reason=inbox/router 側の未処理が最も多い")
    elif top_name == "kaikun02_router_worker_v1":
        out.append("reason=kaikun02 started タスク滞留")
    elif top_name == "dev_pr_watcher_v1":
        out.append("reason=open PR の監視・同期帯が残っている")
    elif top_name == "spec_refiner_v2":
        out.append("reason=promoted/refined 帯が滞留")
    elif top_name == "dev_pr_creator_v1":
        out.append("reason=executor_ready〜PR作成帯が滞留")
    else:
        out.append("reason=単一点ボトルネックは弱い")

    return "\n".join(out)

def quick_top_watchpoints(c):
    open_pr = c.execute("""
        select count(*) from dev_proposals
        where coalesce(pr_status,'')='open'
          and coalesce(pr_url,'')<>''
    """).fetchone()[0]
    router_new = c.execute("""
        select count(*) from router_tasks
        where coalesce(status,'')='new'
    """).fetchone()[0]
    router_started = c.execute("""
        select count(*) from router_tasks
        where coalesce(status,'')='started'
    """).fetchone()[0]
    router_timeout = c.execute("""
        select count(*) from router_tasks
        where coalesce(status,'')='timeout'
    """).fetchone()[0]
    inbox_waiting = c.execute("""
        select count(*) from inbox_commands
        where coalesce(processed,0)=0
    """).fetchone()[0]
    executor_wait = c.execute("""
        select count(*) from dev_proposals
        where coalesce(status,'') in ('decomposed','executor_ready','execute_now','approved','pr_created')
          and coalesce(pr_status,'')<>'merged'
    """).fetchone()[0]
    refined_wait = c.execute("""
        select count(*) from dev_proposals
        where coalesce(status,'') in ('promoted','refining','refined')
    """).fetchone()[0]

    rows = [
        ("router_queue", router_new + router_started + router_timeout),
        ("executor_band", executor_wait),
        ("refiner_band", refined_wait),
        ("open_pr_band", open_pr),
        ("inbox_waiting", inbox_waiting),
    ]
    rows.sort(key=lambda x: x[1], reverse=True)

    out = []
    out.append("👀 OpenClaw 上位3監視ポイント")
    out.append("")
    for i, (name, val) in enumerate(rows[:3], start=1):
        out.append(f"{i}. {name} = {val}")
    out.append("")
    out.append(f"open_pr={open_pr}")
    out.append(f"router_new={router_new}")
    out.append(f"router_started={router_started}")
    out.append(f"router_timeout={router_timeout}")
    out.append(f"inbox_waiting={inbox_waiting}")
    out.append(f"executor_wait={executor_wait}")
    out.append(f"refined_wait={refined_wait}")
    return "\n".join(out)

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
            quick_done = False

            if "進捗" in txt or "status" in txt:
                body = quick_dashboard(c)
                sent_message_id = tg_send(body)
                result = f"quick_dashboard_sent: {body[:120]}"
                quick_done = True

            elif "次の作業" in txt or "next" in txt:
                body = quick_next_tasks(c)
                sent_message_id = tg_send(body)
                result = f"quick_next_sent: {body[:120]}"
                quick_done = True

            elif "弱点" in txt or "problem" in txt:
                body = quick_weak_points(c)
                sent_message_id = tg_send(body)
                result = f"quick_weak_sent: {body[:120]}"
                quick_done = True

            elif (
                "社員ランキング" in txt
                or "ai社員ランキング" in txt
                or ("ランキング" in txt and "社員" in txt)
                or "source_ai" in txt
                or "誰が一番強い" in txt
                or "誰が強い" in txt
            ):
                body = quick_ai_employee_ranking(c)
                sent_message_id = tg_send(body)
                result = f"quick_ai_employee_ranking_sent: {body[:120]}"
                quick_done = True

            elif (
                "本流ボトルネック" in txt
                or "ボトルネック" in txt
                or "どこで詰まってる" in txt
                or "どこが詰まってる" in txt
                or "詰まり" in txt
                or "bottleneck" in txt
                or "flow" in txt
            ):
                body = quick_flow_bottleneck(c)
                sent_message_id = tg_send(body)
                result = f"quick_flow_bottleneck_sent: {body[:120]}"
                quick_done = True

            elif (
                "上位3監視ポイント" in txt
                or "監視ポイント" in txt
                or "今見るべき" in txt
                or "どこを見ればいい" in txt
                or "watchpoint" in txt
            ):
                body = quick_top_watchpoints(c)
                sent_message_id = tg_send(body)
                result = f"quick_top_watchpoints_sent: {body[:120]}"
                quick_done = True

            elif (
                "active本流" in txt
                or "runtime分類" in txt
                or "reserve_implemented" in txt
                or "keep_not_active" in txt
                or "reserve" in txt
                or "未接続" in txt
                or "使えてないプログラム" in txt
                or "現役と予備" in txt
                or "activeとreserve" in txt
            ):
                body = quick_runtime_classification()
                sent_message_id = tg_send(body)
                result = f"quick_runtime_classification_sent: {body[:120]}"
                quick_done = True

            else:
                routed_text = f"[TASK_ID:{r['id']}]
{txt_raw}

返 信 の 先 頭 に [TASK_ID:{r['id']}] を 付 け て く だ さ い 。"
                sent_message_id = tg_send(routed_text)
                result = f"sent_to_kaikun02: {routed_text[:120]}"

            if quick_done:
                c.execute("""
                    update router_tasks
                    set status='done',
                        started_at=coalesce(nullif(started_at,''), datetime('now')),
                        finished_at=datetime('now'),
                        updated_at=datetime('now'),
                        result_text=?,
                        sent_message_id=?
                    where id=?
                """, (result, sent_message_id, r["id"]))
            else:
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
