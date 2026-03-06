import os,sqlite3,datetime,requests

DB=os.environ.get("DB_PATH") or "data/openclaw.db"
FACTORY_DB=os.environ.get("FACTORY_DB_PATH") or os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db")
TOKEN=(os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def dconn():
    c=sqlite3.connect(DB,timeout=30)
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA busy_timeout=30000")
    try:
        c.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    return c

def fconn():
    c=sqlite3.connect(FACTORY_DB,timeout=30)
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA busy_timeout=30000")
    try:
        c.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    return c

def tg_send(chat_id,text):
    r=requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id":str(chat_id),"text":text},
        timeout=20,
    )
    r.raise_for_status()

def one(c,q,a=()):
    r=c.execute(q,a).fetchone()
    return r[0] if r else 0

def build_text():
    with dconn() as d, fconn() as f:
        emp_rows=d.execute("""
            select display_name, role_name
            from ai_employees
            where is_enabled=1
            order by id asc
        """).fetchall()

        total_props=one(f,"select count(*) from dev_proposals")
        approved=one(f,"select count(*) from dev_proposals where coalesce(status,'')='approved'")
        refined=one(f,"select count(*) from dev_proposals where coalesce(spec_stage,'')='refined'")
        executing=one(f,"select count(*) from dev_proposals where coalesce(dev_stage,'') in ('executed','pr_created','open')")
        merged=one(f,"select count(*) from dev_proposals where coalesce(status,'')='merged' or coalesce(dev_stage,'')='merged'")
        waiting_answer=one(f,"select count(*) from proposal_state where coalesce(stage,'')='waiting_answer'")
        answer_received=one(f,"select count(*) from proposal_state where coalesce(stage,'')='answer_received'")
        pr_open=one(f,"select count(*) from dev_proposals where coalesce(pr_status,'')='open'")
        pr_merged=one(f,"select count(*) from dev_proposals where coalesce(pr_status,'')='merged'")

        recent=f.execute("""
            select id,title,coalesce(status,''),coalesce(spec_stage,''),coalesce(dev_stage,'')
            from dev_proposals
            order by id desc
            limit 5
        """).fetchall()

    lines=[
        "OpenClaw Company Status",
        "",
        f"時刻: {now()}",
        "",
        "社員一覧:",
    ]

    for r in emp_rows:
        lines.append(f"- {r['display_name']} / {r['role_name']}")

    lines.extend([
        "",
        "案件状況:",
        f"- 全案件: {total_props}",
        f"- 承認済み: {approved}",
        f"- 仕様整理済み: {refined}",
        f"- 開発進行中: {executing}",
        f"- 統合完了: {merged}",
        "",
        "仕様応答:",
        f"- 回答待ち: {waiting_answer}",
        f"- 回答受領: {answer_received}",
        "",
        "PR状況:",
        f"- Open: {pr_open}",
        f"- Merged: {pr_merged}",
        "",
        "最新案件:",
    ])

    for r in recent:
        lines.append(
            f"- #{r['id']} {r['title']} | status={r[2] or '-'} | spec={r[3] or '-'} | dev={r[4] or '-'}"
        )

    lines.extend([
        "",
        "使えるCEOコマンド:",
        "/company",
        "/meeting <議題>",
    ])
    return "\n".join(lines)

def run_once():
    if not TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN empty")

    done=0
    with dconn() as d:
        rows=d.execute("""
            select id,chat_id,text
            from inbox_commands
            where coalesce(processed,0)=0
              and trim(coalesce(text,''))='/company'
            order by id asc
            limit 5
        """).fetchall()

        for r in rows:
            try:
                tg_send(r["chat_id"], build_text())
                d.execute(
                    "update inbox_commands set processed=1,status='company_done',applied_at=? where id=?",
                    (now(), int(r["id"]))
                )
            except Exception as e:
                d.execute(
                    "update inbox_commands set status='company_error', error=?, applied_at=? where id=?",
                    (repr(e), now(), int(r["id"]))
                )
            d.commit()
            done+=1

    print(f"company_done={done}", flush=True)

if __name__=="__main__":
    run_once()
