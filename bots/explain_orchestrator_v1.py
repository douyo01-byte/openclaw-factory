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
    return bool(c.execute("select 1 from explain_sent where k=?",(k,)).fetchone())

def mark(c,k):
    c.execute("insert or replace into explain_sent(k,sent_at) values(?,?)",(k,now()))

def status_label(status,spec_stage,dev_stage):
    if status=="merged" or dev_stage=="merged":
        return "統合完了"
    if status in ("pr_created","open") or dev_stage in ("executed","pr_created","open"):
        return "開発進行中"
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

    done=[]
    if spec_stage=="refined":
        done.append("仕様を整理し、次の実装に渡せる状態にしました。")
    if dev_stage in ("executed","pr_created","open","merged"):
        done.append("実装作業を進め、開発パイプラインを前進させました。")
    if pr_number:
        done.append(f"関連するPRは #{pr_number} として追跡できます。")
    if status=="merged" or dev_stage=="merged":
        done.append("変更は main への統合まで完了しています。")
    if not done:
        done.append("状態変化を記録し、経営側が追いやすいよう整理しました。")

    impact=[]
    if spec_stage=="refined":
        impact.append("仕様確認の手戻りが減ります。")
    if dev_stage in ("executed","pr_created","open","merged"):
        impact.append("開発の前進状況が明確になります。")
    if pr_number:
        impact.append("GitHub上で追跡可能です。")
    if status=="merged" or dev_stage=="merged":
        impact.append("以後の処理はこの変更を前提に進められます。")
    if not impact:
        impact.append("現時点では進行状況の可視化が主な効果です。")

    if status=="merged" or dev_stage=="merged":
        next_action="次は効果確認と、続きの改善候補の整理です。"
    elif status in ("pr_created","open"):
        next_action="次はPR確認と統合完了の監視です。"
    elif dev_stage=="executed":
        next_action="次はPR作成またはレビュー待ちの確認です。"
    elif spec_stage=="refined":
        next_action="次は実装着手の確認です。"
    elif status=="approved":
        next_action="次は仕様整理に進みます。"
    else:
        next_action="次は状態変化の監視を続けます。"

    lines=[
        "【案件名】",
        title,
        "",
        "【提案ID】",
        str(pid),
        "",
        "【現在の状態】",
        status_label(status,spec_stage,dev_stage),
        "",
        "【今回実施したこと】",
    ]
    lines.extend([f"- {x}" for x in done])
    lines.extend([
        "",
        "【変更した理由】",
        "OpenClawの自動開発ループを前に進め、社長が今の状態を判断しやすくするためです。",
        "",
        "【影響範囲】",
    ])
    lines.extend([f"- {x}" for x in impact])
    lines.extend([
        "",
        "【次にやること】",
        next_action,
    ])
    if pr_url:
        lines.extend([
            "",
            "【参照先】",
            pr_url,
        ])
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
            d.execute(
                "insert or ignore into ceo_hub_events(source,source_key,title,body,level,created_at) values(?,?,?,?,?,?)",
                ("explain_orchestrator_v1", key, f"詳しい解説 #{pid}", build_text(r), "info", now())
            )
            mark(d,key)
            d.commit()
            done+=1
    print(f"explain_done={done}", flush=True)

if __name__=="__main__":
    run_once()
