import os,sqlite3,datetime,requests

DB=os.environ.get("DB_PATH") or "data/openclaw.db"
FACTORY_DB=os.environ.get("FACTORY_DB_PATH") or os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db")
TOKEN=(os.environ.get("TELEGRAM_REPORT_BOT_TOKEN") or "").strip()
CEO_CHAT_ID=(os.environ.get("CEO_CHAT_ID") or "").strip()

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

def ensure(c):
    c.execute("""CREATE TABLE IF NOT EXISTS report_sent(
        k TEXT PRIMARY KEY,
        sent_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")

def already_sent(c,k):
    r=c.execute("select 1 from report_sent where k=?",(k,)).fetchone()
    return bool(r)

def mark_sent(c,k):
    c.execute("insert or replace into report_sent(k,sent_at) values(?,?)",(k,now()))

def tg_send(text):
    if not TOKEN:
        raise RuntimeError("TELEGRAM_REPORT_BOT_TOKEN empty")
    if not CEO_CHAT_ID:
        raise RuntimeError("CEO_CHAT_ID empty")
    r=requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id":CEO_CHAT_ID,"text":text},
        timeout=20,
    )
    r.raise_for_status()

def stage_text(status,spec_stage,dev_stage):
    if status=="merged" or dev_stage=="merged":
        return "統合完了"
    if status in ("pr_created","open") or dev_stage in ("pr_created","open","executed"):
        return "実装進行"
    if spec_stage=="refined":
        return "仕様整理完了"
    if status=="approved":
        return "承認済み"
    return "進行中"

def build_text(r):
    pid=int(r["id"])
    title=(r["title"] or "").strip()
    status=(r["status"] or "").strip()
    spec_stage=(r["spec_stage"] or "").strip()
    dev_stage=(r["dev_stage"] or "").strip()
    pr_number=r["pr_number"] or ""
    pr_url=(r["pr_url"] or "").strip()
    spec_len=r["spec_len"] or 0

    lines=[
        "報告係（しらせるん）",
        "",
        f"案件名: {title}",
        f"提案ID: {pid}",
        f"現在地: {stage_text(status,spec_stage,dev_stage)}",
        "",
        f"設計士（きめたろう）: 仕様段階 = {spec_stage or '未着手'}",
        f"エンジニア（つくるぞう）: 開発段階 = {dev_stage or '未着手'}",
    ]

    if spec_len:
        lines.append(f"設計士（きめたろう）: 仕様書文字数 = {spec_len}")

    if status in ("pr_created","open","merged") or dev_stage in ("pr_created","open","merged","executed"):
        lines.append("監査係（みはるん）: 実装結果を確認対象に入れました")

    if pr_number:
        lines.append(f"監査係（みはるん）: PR番号 = {pr_number}")
    if pr_url:
        lines.append(f"監査係（みはるん）: {pr_url}")

    if status=="merged" or dev_stage=="merged":
        lines.append("統合係（くっつけ丸）: main への統合まで完了しました")
    elif status in ("pr_created","open") or dev_stage in ("pr_created","open","executed"):
        lines.append("統合係（くっつけ丸）: 統合待ちです")

    lines.append("")
    lines.append(f"報告係（しらせるん）: ステータス = {status or '未設定'}")
    return "\n".join(lines)

def run_once():
    done=0
    with dconn() as d, fconn() as f:
        ensure(d)
        rows=f.execute("""
            select id,title,
                   coalesce(status,'') as status,
                   coalesce(spec_stage,'') as spec_stage,
                   coalesce(dev_stage,'') as dev_stage,
                   pr_number,
                   coalesce(pr_url,'') as pr_url,
                   length(coalesce(spec,'')) as spec_len
            from dev_proposals
            where coalesce(status,'') in ('approved','pr_created','open','merged')
               or coalesce(dev_stage,'') in ('executed','pr_created','open','merged')
               or coalesce(spec_stage,'')='refined'
            order by id desc
            limit 30
        """).fetchall()

        for r in rows:
            pid=int(r["id"])
            key="proposal:{id}:status:{status}:spec:{spec}:dev:{dev}:pr:{pr}".format(
                id=pid,
                status=r["status"] or "",
                spec=r["spec_stage"] or "",
                dev=r["dev_stage"] or "",
                pr=r["pr_number"] or "",
            )
            if already_sent(d,key):
                continue
            tg_send(build_text(r))
            mark_sent(d,key)
            d.commit()
            done+=1
    print(f"report_done={done}", flush=True)

if __name__=="__main__":
    run_once()
