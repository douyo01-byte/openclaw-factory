import os, sqlite3, random, time, traceback, re

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

TEMPLATES = [
    "ECで 売 れ る 海 外 ト レ ン ド 商 品 を 3つ 提 案 ",
    "日 本 未 上 陸 で ヒ ッ ト し そ う な ガ ジ ェ ッ ト を 提 案 ",
    "美 容 ・ 健 康 分 野 で 利 益 率 の 高 い 商 品 案 を 出 す ",
    "サ ブ ス ク 型 で 収 益 化 で き る サ ー ビ ス 案 を 出 す ",
    "小 資 本 で 始 め ら れ る 輸 入 ビ ジ ネ ス 案 を 提 案 ",
    "競 合 が 弱 い ニ ッ チ 市 場 を 1つ 見 つ け て 提 案 ",
    "法 人 向 け に 横 展 開 し や す い 海 外 商 品 案 を 出 す ",
    "リ ピ ー ト 購 入 が 狙 え る 消 耗 型 商 品 を 提 案 ",
    "サ ロ ン 向 け に 卸 し や す い 商 品 案 を 提 案 ",
    "単 価 と 利 益 率 の バ ラ ン ス が 良 い 商 品 案 を 提 案 ",
    "日 本 で 競 争 が 緩 い 海 外 D2C商 品 を 提 案 ",
    "少 人 数 運 用 で 売 り や す い 商 品 案 を 提 案 ",
]

def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "brain-supply"

def get_cols(c):
    return c.execute("pragma table_info(dev_proposals)").fetchall()

def recent_titles(c, limit=20):
    rows = c.execute(
        """
        select coalesce(title,'')
        from dev_proposals
        where coalesce(source_ai,'')='brain_supply'
        order by id desc
        limit ?
        """,
        (limit,)
    ).fetchall()
    return {r[0] for r in rows if r[0]}

def choose_text(c):
    recent = recent_titles(c, 20)
    candidates = [x for x in TEMPLATES if x not in recent]
    if not candidates:
        candidates = TEMPLATES[:]
    return random.choice(candidates)

def once():
    conn = sqlite3.connect(DB, timeout=30)
    c = conn.cursor()
    c.execute("pragma busy_timeout=30000")

    text = choose_text(c)

    exists = c.execute(
        """
        select 1
        from dev_proposals
        where coalesce(source_ai,'')='brain_supply'
          and coalesce(title,'')=?
          and id >= coalesce((select max(id) - 20 from dev_proposals), 0)
        limit 1
        """,
        (text,)
    ).fetchone()
    if exists:
        conn.close()
        print("skip duplicate:", text, flush=True)
        return

    ts = c.execute("select strftime('%Y%m%d%H%M%S','now')").fetchone()[0]
    branch = f"brain-supply/{slugify(text)[:40]}-{ts}"

    col_rows = get_cols(c)
    names = {r[1] for r in col_rows}

    values = {}

    if "title" in names:
        values["title"] = text
    if "description" in names:
        values["description"] = text
    if "source_ai" in names:
        values["source_ai"] = "brain_supply"
    if "status" in names:
        values["status"] = "new"
    if "branch_name" in names:
        values["branch_name"] = branch
    if "branch_status" in names:
        values["branch_status"] = "pending"
    if "dev_stage" in names:
        values["dev_stage"] = "new"
    if "pr_status" in names:
        values["pr_status"] = ""
    if "result_type" in names:
        values["result_type"] = "proposal"
    if "priority" in names:
        values["priority"] = "normal"
    if "category" in names:
        values["category"] = "idea_generation"
    if "target_system" in names:
        values["target_system"] = "idea_pool"

    cols = []
    exprs = []
    params = []

    for name, val in values.items():
        cols.append(name)
        exprs.append("?")
        params.append(val)

    if "created_at" in names:
        cols.append("created_at")
        exprs.append("datetime('now')")
    if "updated_at" in names:
        cols.append("updated_at")
        exprs.append("datetime('now')")

    sql = f"insert into dev_proposals ({', '.join(cols)}) values ({', '.join(exprs)})"
    c.execute(sql, tuple(params))
    conn.commit()
    conn.close()
    print("inserted:", text, "| branch:", branch, flush=True)

def main():
    while True:
        try:
            once()
        except Exception:
            traceback.print_exc()
        time.sleep(600)

if __name__ == "__main__":
    main()
