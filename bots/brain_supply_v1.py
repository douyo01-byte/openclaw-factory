import os, sqlite3, random, time, traceback, re

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

TEMPLATES = [
    "ECで売れる海外トレンド商品を3つ提案",
    "日本未上陸でヒットしそうなガジェットを提案",
    "美容・健康分野で利益率の高い商品案を出す",
    "サブスク型で収益化できるサービス案を出す",
    "小資本で始められる輸入ビジネス案を提案",
    "競合が弱いニッチ市場を1つ見つけて提案",
]

def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "brain-supply"

def get_cols(c):
    return c.execute("pragma table_info(dev_proposals)").fetchall()

def once():
    conn = sqlite3.connect(DB, timeout=30)
    c = conn.cursor()
    c.execute("pragma busy_timeout=30000")

    text = random.choice(TEMPLATES)
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
