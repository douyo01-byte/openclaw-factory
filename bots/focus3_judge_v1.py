from __future__ import annotations
import os
import sqlite3

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

def score(theme: str):
    t = theme or ""
    s = 0
    reasons = []

    if "今ある商品の売上改善" in t or "売上改善" in t:
        s += 30
        reasons.append("既存資産活用")
    if "競合差別化" in t:
        s += 18
        reasons.append("比較優位を作りやすい")
    if "海外で売れる日本商品" in t:
        s += 12
        reasons.append("市場余地あり")

    if "1件" in t:
        s += 10
        reasons.append("絞り込み済み")
    if "最初の検証" in t:
        s += 12
        reasons.append("検証が速い")
    if "実行" in t:
        s += 8
        reasons.append("行動に落ちやすい")

    if "売上" in t:
        s += 15
        reasons.append("収益直結")
    if "継続" in t or "リピート" in t or "定期" in t:
        s += 10
        reasons.append("継続利益余地")

    return s, " / ".join(reasons[:5])

def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    cur.execute("""
    create table if not exists focus3_score_log (
      id integer primary key,
      project_id integer,
      theme text,
      score integer,
      reasons text,
      created_at text default (datetime('now'))
    )
    """)

    rows = cur.execute("""
    select id, theme
    from active_projects
    where status in ('active','winner','paused')
    order by id asc
    """).fetchall()

    if not rows:
        print("no_projects", flush=True)
        con.close()
        return

    cur.execute("delete from focus3_score_log")

    ranked = []
    for r in rows:
        s, reasons = score(r["theme"])
        ranked.append((r["id"], r["theme"], s, reasons))
        cur.execute("""
        insert into focus3_score_log(project_id, theme, score, reasons, created_at)
        values(?,?,?,?,datetime('now'))
        """, (r["id"], r["theme"], s, reasons))

    ranked.sort(key=lambda x: (-x[2], x[0]))
    winner_id, winner_theme, winner_score, winner_reasons = ranked[0]

    cur.execute("update active_projects set status='paused'")
    cur.execute("update active_projects set status='winner' where id=?", (winner_id,))

    cur.execute("""
    create table if not exists focus3_winner_log (
      id integer primary key,
      project_id integer,
      theme text,
      score integer,
      reasons text,
      created_at text default (datetime('now'))
    )
    """)
    cur.execute("""
    insert into focus3_winner_log(project_id, theme, score, reasons, created_at)
    values(?,?,?,?,datetime('now'))
    """, (winner_id, winner_theme, winner_score, winner_reasons))

    cur.execute("""
    insert into router_tasks
    (task_role,target_bot,mode,status,task_text,created_at,updated_at)
    values
    ('AI','kaikun04','THINK','new',?,datetime('now'),datetime('now'))
    """, (f"[WINNER_ONLY] 勝ち案件だけ進める。理由: {winner_reasons}。テーマ: {winner_theme}",))

    con.commit()
    con.close()
    print(f"winner={winner_id} score={winner_score}", flush=True)

if __name__ == "__main__":
    main()
