import os
import re
import sqlite3
import subprocess
from datetime import datetime, timedelta

DB = (
    os.environ.get("OCLAW_DB_PATH")
    or os.environ.get("DB_PATH")
    or os.path.expanduser("~/AI/openclaw-factory-daemon/data/openclaw_real.db")
)

BOT_LABELS = {
    "supervisor": "jp.openclaw.supervisor",
    "self_healing_v2": "jp.openclaw.self_healing_v2",
    "ceo_dashboard": "jp.openclaw.ceo_dashboard",
    "spec_refiner_v2": "jp.openclaw.spec_refiner_v2",
    "dev_pr_watcher_v1": "jp.openclaw.dev_pr_watcher_v1",
    "dev_command_executor_v1": "jp.openclaw.dev_command_executor_v1",
    "dev_pr_automerge_v1": "jp.openclaw.dev_pr_automerge_v1",
    "innovation_engine": "jp.openclaw.innovation_engine",
    "code_review_engine": "jp.openclaw.code_review_engine",
    "business_engine": "jp.openclaw.business_engine",
    "revenue_engine": "jp.openclaw.revenue_engine",
    "ai_employee_factory": "jp.openclaw.ai_employee_factory",
    "ai_meeting_engine": "jp.openclaw.ai_meeting_engine",
    "ai_ceo_engine": "jp.openclaw.ai_ceo_engine",
    "spec_reply_v1": "jp.openclaw.spec_reply_v1",
    "tg_poll_loop": "jp.openclaw.tg_poll_loop",
    "update_pr_created": "jp.openclaw.update_pr_created",
}

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    try:
        c.execute("PRAGMA busy_timeout=30000")
    except Exception:
        pass
    return c

def one(c, sql, args=()):
    r = c.execute(sql, args).fetchone()
    if r is None:
        return None
    if isinstance(r, sqlite3.Row):
        return list(r)[0]
    return r[0]

def rows(c, sql, args=()):
    return c.execute(sql, args).fetchall()

def label_state(label):
    uid = os.getuid()
    try:
        out = subprocess.check_output(
            ["launchctl", "print", f"gui/{uid}/{label}"],
            stderr=subprocess.STDOUT,
            text=True,
        )
    except Exception:
        return "停止"
    state = ""
    pid = ""
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("state ="):
            state = s.split("=", 1)[1].strip()
        elif s.startswith("pid ="):
            pid = s.split("=", 1)[1].strip()
    if state in ("running", "active"):
        return "稼働中"
    if state == "not running":
        return "停止"
    return "不明" if not state else state

def count_status(c, status):
    return one(c, "select count(*) from dev_proposals where coalesce(status,'')=?", (status,)) or 0

def waiting_answer_count(c):
    try:
        return one(c, "select count(*) from proposal_state where coalesce(stage,'')='waiting_answer'") or 0
    except Exception:
        return 0

def executable_queue(c):
    return one(c, """
    select count(*)
    from dev_proposals
    where status='approved'
      and coalesce(project_decision,'')='execute_now'
      and coalesce(guard_status,'')='safe'
      and coalesce(spec,'')!=''
      and coalesce(dev_stage,'') in ('','approved')
    """) or 0

def latest_merge(c):
    r = c.execute("""
    select proposal_id, title
    from ceo_hub_events
    where coalesce(event_type,'')='merged'
    order by id desc
    limit 1
    """).fetchone()
    if not r:
        return None
    pid = r["proposal_id"] if "proposal_id" in r.keys() else None
    title = r["title"] if "title" in r.keys() else ""
    if pid:
        return f"#{pid} {title}"
    return title or "なし"

def latest_proposal(c):
    r = c.execute("""
    select
      id,
      title,
      coalesce(source_ai,'') as source_ai,
      coalesce(brain_type,'') as brain_type
    from dev_proposals
    order by id desc
    limit 1
    """).fetchone()
    if not r:
        return None, None, None
    source = (r["source_ai"] or r["brain_type"] or "不明").strip()
    return r["id"], r["title"], source

def today_summary(c):
    r = c.execute("""
    select coalesce(event_type,'') as event_type, count(*) as n
    from ceo_hub_events
    where datetime(created_at) >= datetime('now','localtime','start of day')
    group by coalesce(event_type,'')
    order by n desc, event_type asc
    """).fetchall()
    if not r:
        return "イベント 0件"
    return " / ".join([f"{x['event_type']} {x['n']}件" for x in r[:5]])

def priority_items(c):
    return c.execute("""
    select
      id,
      title,
      coalesce(priority,0) as priority,
      coalesce(project_decision,'') as project_decision,
      coalesce(guard_status,'') as guard_status,
      coalesce(source_ai,'') as source_ai,
      coalesce(brain_type,'') as brain_type
    from dev_proposals
    where coalesce(status,'')='approved'
    order by
      case
        when coalesce(project_decision,'')='execute_now' and coalesce(guard_status,'')='safe' then 0
        when coalesce(project_decision,'')='execute_now' then 1
        when coalesce(project_decision,'')='backlog' then 2
        when coalesce(project_decision,'')='archive' then 3
        else 4
      end,
      coalesce(priority,0) desc,
      id desc
    limit 3
    """).fetchall()

def decision_jp(v):
    if v == "execute_now":
        return "execute_now"
    if v == "backlog":
        return "保留 / バックログ"
    if v == "archive":
        return "archive"
    if v == "duplicate":
        return "duplicate"
    return v or "未判定"

def source_jp(row):
    s = (row["source_ai"] or row["brain_type"] or "").strip()
    return s if s else "不明"

def consult_lines(c):
    lines = []
    approved = count_status(c, "approved")
    queue = executable_queue(c)
    if approved > 0:
        lines.append(f"- 承認済み案件が {approved}件あり、優先順位の監視が必要です")
    if queue > 0:
        lines.append(f"- executable 条件を満たす案件が {queue}件あり、executor 消化フェーズです")
    return lines or ["- 特記事項なし"]

def recent_learning(c):
    rs = c.execute("""
    select proposal_id, title, body
    from ceo_hub_events
    where coalesce(event_type,'')='learning_result'
    order by id desc
    limit 4
    """).fetchall()
    out = []
    for r in rs:
        body = r["body"] or ""
        m1 = re.search(r"result=([a-zA-Z_]+)", body)
        m2 = re.search(r"score=([0-9.]+)", body)
        result = m1.group(1) if m1 else "unknown"
        score = m2.group(1) if m2 else "?"
        out.append((r["proposal_id"], result, score))
    return out

def total_proposals(c):
    return one(c, "select count(*) from dev_proposals") or 0

def open_prs(c):
    return one(c, """
    select count(*)
    from dev_proposals
    where coalesce(pr_status,'')='open'
       or coalesce(status,'')='open'
       or coalesce(dev_stage,'')='open'
    """) or 0

def pending_unapproved(c):
    return one(c, """
    select count(*)
    from dev_proposals
    where coalesce(status,'') in ('pending','proposed','req','needs_info')
    """) or 0

def render():
    with conn() as c:
        latest_id, latest_title, latest_source = latest_proposal(c)
        lines = []
        lines.append("OpenClaw CEOダッシュボード")
        lines.append("（AI経営管理システム）")
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.append("【今日の主な動き】")
        lines.append("")
        lines.append(f"概要: {today_summary(c)}")
        lines.append(f"最新提案: #{latest_id} {latest_title}" if latest_id else "最新提案: なし")
        lines.append(f"発案AI: {latest_source}")
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.append("【社長の返答待ち項目】")
        lines.append("")
        wa = waiting_answer_count(c)
        lines.append(f"現在 {wa}件")
        lines.append("")
        lines.append("※ 社長判断が必要な案件がここに表示されます")
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.append("【直近の案件（優先順）】")
        lines.append("")
        for r in priority_items(c):
            lines.append(f"#{r['id']} {r['title']}")
            lines.append(f"優先度: {r['priority']}")
            lines.append(f"判断: {decision_jp(r['project_decision'])}")
            lines.append(f"監査: {r['guard_status'] or 'pending'}")
            lines.append(f"発案AI: {source_jp(r)}")
            lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.append("【専務・幹部から社長への相談 / 共有】")
        lines.append("")
        for x in consult_lines(c):
            lines.append(x)
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.append("【会社状態】")
        lines.append("")
        lines.append(f"総提案件数: {total_proposals(c)}")
        lines.append(f"マージ済み: {count_status(c,'merged')}")
        lines.append(f"Open PR: {open_prs(c)}")
        lines.append(f"実行待ち案件: {executable_queue(c)}")
        lines.append(f"未承認案件: {pending_unapproved(c)}")
        lines.append(f"Executor状態: {'消化フェーズ' if executable_queue(c) > 0 else '稼働待ちあり'}")
        lines.append(f"Executor Queue: {executable_queue(c)}")
        lines.append(f"最新マージ: {latest_merge(c) or 'なし'}")
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.append("【最近の意思決定】")
        lines.append("")
        for pid, result, score in recent_learning(c):
            lines.append(f"#{pid} 評価: {result}")
            lines.append(f"スコア: {score}")
        if not recent_learning(c):
            lines.append("記録なし")
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.append("【AI社員構成】")
        lines.append("")
        lines.append("■ 海外事業")
        lines.append("SekawakuClaw_bot")
        lines.append("・さがすけ（探索）")
        lines.append("・しらべえ（調査）")
        lines.append("・かんがえもん（企画）")
        lines.append("")
        lines.append("■ 開発")
        lines.append("Kaikun01_bot")
        lines.append("・きめたろう（設計）")
        lines.append("・つくるぞう（実装）")
        lines.append("・みはるん（監査）")
        lines.append("・くっつけ丸（統合）")
        lines.append("")
        lines.append("■ 経営共有")
        lines.append("Kaikun02_bot")
        lines.append("・ひしょりん（秘書）")
        lines.append("・しらせるん（報告）")
        lines.append("")
        lines.append("■ 自動実行")
        lines.append("Kaikun03_bot")
        lines.append("・とどけるん（通知）")
        lines.append("・まわすけ（実行管理）")
        lines.append("・なおし丸（自己修復）")
        lines.append("・みはりん（監視）")
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.append("【BOT状態】")
        lines.append("")
        lines.append("Core")
        lines.append(f"supervisor: {label_state(BOT_LABELS['supervisor'])}")
        lines.append(f"self_healing_v2: {label_state(BOT_LABELS['self_healing_v2'])}")
        lines.append(f"ceo_dashboard: {label_state(BOT_LABELS['ceo_dashboard'])}")
        lines.append("")
        lines.append("開発")
        lines.append(f"spec_refiner_v2: {label_state(BOT_LABELS['spec_refiner_v2'])}")
        lines.append(f"dev_pr_watcher_v1: {label_state(BOT_LABELS['dev_pr_watcher_v1'])}")
        lines.append(f"dev_command_executor_v1: {label_state(BOT_LABELS['dev_command_executor_v1'])}")
        lines.append(f"dev_pr_automerge_v1: {label_state(BOT_LABELS['dev_pr_automerge_v1'])}")
        lines.append("")
        lines.append("提案生成")
        lines.append(f"innovation_engine: {label_state(BOT_LABELS['innovation_engine'])}")
        lines.append(f"code_review_engine: {label_state(BOT_LABELS['code_review_engine'])}")
        lines.append(f"business_engine: {label_state(BOT_LABELS['business_engine'])}")
        lines.append(f"revenue_engine: {label_state(BOT_LABELS['revenue_engine'])}")
        lines.append("")
        lines.append("経営補助")
        lines.append(f"ai_employee_factory: {label_state(BOT_LABELS['ai_employee_factory'])}")
        lines.append(f"ai_meeting_engine: {label_state(BOT_LABELS['ai_meeting_engine'])}")
        lines.append(f"ai_ceo_engine: {label_state(BOT_LABELS['ai_ceo_engine'])}")
        lines.append("")
        lines.append("補助")
        lines.append(f"spec_reply_v1: {label_state(BOT_LABELS['spec_reply_v1'])}")
        lines.append(f"tg_poll_loop: {label_state(BOT_LABELS['tg_poll_loop'])}")
        lines.append(f"update_pr_created: {label_state(BOT_LABELS['update_pr_created'])}")
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.append("【次の一手】")
        lines.append("")
        q = executable_queue(c)
        if q > 0:
            lines.append(f"・Executor Queue {q}件の消化監視")
        latest = priority_items(c)
        ids = [str(r["id"]) for r in latest if r["project_decision"] == "execute_now"][:3]
        if ids:
            lines.append(f"・#{' / #'.join(ids)} のPR化確認")
        lines.append("・Kaikun02要約が ceo_hub_events の merged / pr_created / learning_result を確実に拾っているか監視")
        return "\n".join(lines)

if __name__ == "__main__":
    print(render())
