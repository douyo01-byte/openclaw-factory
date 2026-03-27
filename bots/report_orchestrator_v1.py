import os,sqlite3,datetime,json

DB=os.environ.get("DB_PATH") or "data/openclaw.db"
FACTORY_DB=os.environ.get("FACTORY_DB_PATH") or os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db")
FEEDBACK_JSON=os.environ.get("SELF_IMPROVEMENT_FEEDBACK_JSON") or os.path.expanduser("~/AI/openclaw-factory-daemon/obs/self_improvement_feedback.json")

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
    c.execute("""CREATE TABLE IF NOT EXISTS ceo_hub_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        source_key TEXT,
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        level TEXT NOT NULL DEFAULT 'info',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        sent_at TEXT
    )""")
    cols={r["name"] for r in c.execute("pragma table_info(ceo_hub_events)").fetchall()}
    if "source" not in cols:
        c.execute("alter table ceo_hub_events add column source text")
    if "source_key" not in cols:
        c.execute("alter table ceo_hub_events add column source_key text")
    if "level" not in cols:
        c.execute("alter table ceo_hub_events add column level text default 'info'")
    if "sent_at" not in cols:
        c.execute("alter table ceo_hub_events add column sent_at text")
    c.execute("update ceo_hub_events set source='legacy_ceo_hub' where coalesce(source,'')=''")
    c.execute("update ceo_hub_events set source_key='legacy:' || id where coalesce(source_key,'')=''")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_ceo_hub_source_key ON ceo_hub_events(source,source_key)")

def already_sent(c,k):
    return bool(c.execute("select 1 from report_sent where k=?",(k,)).fetchone())

def mark_sent(c,k):
    c.execute("insert or replace into report_sent(k,sent_at) values(?,?)",(k,now()))

def stage_text(status,spec_stage,dev_stage):
    if status=="merged" or dev_stage=="merged":
        return "統 合 完 了 "
    if status in ("pr_created","open") or dev_stage in ("pr_created","open","executed"):
        return "開 発 進 行 中 "
    if spec_stage=="refined":
        return "仕 様 整 理 完 了 "
    if status=="approved":
        return "承 認 済 み "
    return "進 行 中 "

def change_summary(status,spec_stage,dev_stage,pr_number):
    xs=[]
    if spec_stage=="refined":
        xs.append("仕 様 整 理 完 了 ")
    if dev_stage in ("executed","pr_created","open","merged"):
        xs.append("実 装 前 進 ")
    if pr_number:
        xs.append(f"PR #{pr_number}")
    if status=="merged" or dev_stage=="merged":
        xs.append("main統 合 完 了 ")
    if not xs:
        xs.append("状 態 更 新 ")
    return " / ".join(xs)

def next_action(status,spec_stage,dev_stage):
    if status=="merged" or dev_stage=="merged":
        return "次 の 改 善 候 補 へ 進 み ま す 。 "
    if status in ("pr_created","open"):
        return "PR確 認 と 統 合 待 ち で す 。 "
    if dev_stage=="executed":
        return "PR作 成 ま た は レ ビ ュ ー 待 ち で す 。 "
    if spec_stage=="refined":
        return "開 発 着 手 待 ち で す 。 "
    if status=="approved":
        return "仕 様 整 理 へ 進 み ま す 。 "
    return "継 続 監 視 し ま す 。 "

def load_feedback_lines():
    try:
        data=json.loads(open(FEEDBACK_JSON,encoding="utf-8").read())
    except Exception:
        return []
    top=data.get("top_exec_patterns") or []
    best="-"
    neg="-"
    for r in top:
        key=str(r.get("pattern_key") or "").strip()
        if best=="-" and key.startswith("script=") and float(r.get("weight") or 0)>0:
            best=key
        if neg=="-" and key=="no_exec_block":
            neg=f"no_exec_block x{int(r.get('sample_count') or 0)}"
    positive=int(data.get("positive_learning_rows") or 0)
    negative=int(data.get("negative_learning_rows") or 0)
    private_pending=int(data.get("tg_private_pending") or 0)
    ops_new=int(data.get("ops_exec_new_remaining") or 0)
    kaikun_new=int(data.get("kaikun04_new_remaining") or 0)
    return [
        f"【 自 己 改 善 】 正 {positive} / 負 {negative}",
        f"【 EXEC 学 習 】 成 功 {best} / 抑 制 {neg}",
        f"【 ル ー プ 健 康 】 private={private_pending} ops_exec={ops_new} kaikun04={kaikun_new}",
    ]

def build_text(r):
    pid=int(r["id"])
    title=(r["title"] or "").strip()
    status=(r["status"] or "").strip()
    spec_stage=(r["spec_stage"] or "").strip()
    dev_stage=(r["dev_stage"] or "").strip()
    pr_number=r["pr_number"] or ""
    lines=[
        "【 案 件 】 ",
        f"{title} / #{pid}",
        "",
        "【 現 在 地 】 ",
        stage_text(status,spec_stage,dev_stage),
        "",
        "【 今 回 の 変 化 】 ",
        change_summary(status,spec_stage,dev_stage,pr_number),
        "",
        "【 次 ア ク シ ョ ン 】 ",
        next_action(status,spec_stage,dev_stage),
    ]
    fb=load_feedback_lines()
    if fb:
        lines += ["", *fb]
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
                   pr_number
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
            d.execute(
                "insert or ignore into ceo_hub_events(source,source_key,title,body,level,created_at) values(?,?,?,?,?,?)",
                ("report_orchestrator_v1", key, f"案 件 報 告  #{pid}", build_text(r), "info", now())
            )
            mark_sent(d,key)
            d.commit()
            done+=1
    print(f"report_done={done}", flush=True)

if __name__=="__main__":
    run_once()
