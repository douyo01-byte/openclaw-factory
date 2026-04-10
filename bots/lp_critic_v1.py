import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))

def score_row(hook, problem, promise, cta, price_hint):
    s = 0
    t = " ".join([hook or "", problem or "", promise or "", cta or "", price_hint or ""])
    if "無料" in t:
        s += 20
    if "760円" in t or "円" in t:
        s += 15
    if "終わる" in t or "不安" in t or "離れる" in t:
        s += 20
    if "確認" in t or "整理" in t:
        s += 15
    if "続き" in t or "解放" in t:
        s += 15
    if len(hook or "") < 12:
        s -= 10
    return s

def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    rows = cur.execute("""
    select id, hook, problem, promise, cta, price_hint
    from lp_patterns
    order by id asc
    """).fetchall()

    for row in rows:
        pid, hook, problem, promise, cta, price_hint = row
        s = score_row(hook, problem, promise, cta, price_hint)
        cur.execute("update lp_patterns set score=? where id=?", (s, pid))

    con.commit()
    con.close()
    print("lp_critic_scored", flush=True)

if __name__ == "__main__":
    main()
