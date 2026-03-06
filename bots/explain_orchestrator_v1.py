import os,sqlite3,datetime

DB=os.environ.get("DB_PATH") or "data/openclaw.db"
FACTORY_DB=os.environ.get("FACTORY_DB_PATH") or os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db")

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
    c.execute("""CREATE TABLE IF NOT EXISTS explain_sent(
        k TEXT PRIMARY KEY,
        sent_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS ceo_hub_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        source_key TEXT NOT NULL,
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        level TEXT NOT NULL DEFAULT 'info',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        sent_at TEXT
    )""")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_ceo_hub_source_key ON ceo_hub_events(source,source_key)")

def done_key(c,k):
    r=c.execute("select 1 from explain_sent where k=?",(k,)).fetchone()
    return bool(r)

def mark(c,k):
    c.execute("insert or replace into explain_sent(k,sent_at) values(?,?)",(k,now()))

def build_text(r):
    pid=int(r["id"])
    title=(r["title"] or "").strip()
    status=(r["status"] or "").strip()
    spec_stage=(r["spec_stage"] or "").strip()
    dev_stage=(r["dev_stage"] or "").strip()
    pr_number=r["pr_number"] or ""
    pr_url=(r["pr_url"] or "").strip()

    lines=[
        "自動解説",
        "",
        f"案件: {title}",
        f"提案ID: {pid}",
        "",
        "今回やったこと:",
    ]

    if spec_stage=="refined":
        lines.append("- 設計士（きめたろう）が仕様を整理しました")
    if dev_stage in ("executed","pr_created","open","merged"):
        lines.append("- エンジニア（つくるぞう）が実装を進めました")
    if pr_number:
        lines.append(f"- 監査係（みはるん）が PR #{pr_number} を追跡しています")
    if status=="merged" or dev_stage=="merged":
        lines.append("- 統合係（くっつけ丸）が main へ統合しました")

    lines.extend([
        "",
        "なぜやったか:",
        "- OpenClawの自動開発ループを前進させるため",
        "",
        "次に見るべき点:",
    ])

    if status=="merged" or dev_stage=="merged":
        lines.append("- 次の改善候補を出す段階です")
    elif status in ("pr_created","open"):
        lines.append("- PR確認と統合完了を待ちます")
    elif spec_stage=="refined":
        lines.append("- 開発着手へ進むか確認します")
    else:
        lines.append("- 状態変化を監視します")

    if pr_url:
        lines.extend(["", f"参照: {pr_url}"])

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
                   coalesce(pr_url,'') as pr_url
            from dev_proposals
            where coalesce(status,'') in ('pr_created','open','merged')
               or coalesce(dev_stage,'') in ('executed','pr_created','open','merged')
               or coalesce(spec_stage,'')='refined'
            order by id desc
            limit 20
        """).fetchall()

        for r in rows:
            pid=int(r["id"])
            key="explain:{id}:{status}:{spec}:{dev}:{pr}".format(
                id=pid,
                status=r["status"] or "",
                spec=r["spec_stage"] or "",
                dev=r["dev_stage"] or "",
                pr=r["pr_number"] or "",
            )
            if done_key(d,key):
                continue
            text=build_text(r)
            d.execute(
                "insert or ignore into ceo_hub_events(source,source_key,title,body,level,created_at) values(?,?,?,?,?,?)",
                ("explain_orchestrator_v1", key, f"自動解説 #{pid}", text, "info", now())
            )
            mark(d,key)
            d.commit()
            done+=1
    print(f"explain_done={done}", flush=True)

if __name__=="__main__":
    run_once()
