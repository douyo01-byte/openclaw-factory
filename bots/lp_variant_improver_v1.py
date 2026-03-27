#!/usr/bin/env python3
import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))

def connect():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def fetch_jobs(c, limit=10):
    return c.execute(
        """
        select *
        from conversation_jobs
        where coalesce(current_phase,'')='lp_review_done'
          and coalesce(status,'')='done'
          and id not in (
            select job_id from conversation_artifacts where artifact_type='lp_improved_markdown'
          )
        order by id asc
        limit ?
        """,
        (limit,),
    ).fetchall()

def get_best(c, job_id):
    return c.execute(
        """
        select *
        from conversation_artifacts
        where job_id=?
          and artifact_type='lp_best_markdown'
        order by id desc
        limit 1
        """,
        (job_id,),
    ).fetchone()

def improve_text(text: str):
    base = text.strip()
    extra = """

## 改善版ファーストビュー
軽やかに整えて、素肌そのものがきれいに見える印象へ。

### 改善版サブコピー
自然なツヤ、均一なトーン、しっとり感を意識しながら、
毎日のベースメイクを心地よく仕上げるBBクリーム下地。

## 改善版CTA
まずは educate B の魅力を商品ページで確認する
"""
    return base + "\n" + extra.strip() + "\n"

def run_once():
    con = connect()
    c = con.cursor()
    rows = fetch_jobs(c, 10)
    done = 0
    for job in rows:
        try:
            best = get_best(c, job["id"])
            if not best:
                continue
            improved = improve_text(best["artifact_body"])
            c.execute(
                """
                insert into conversation_artifacts(
                  job_id, artifact_type, artifact_title, artifact_body, artifact_path, version, created_at
                ) values(?,?,?,?,?,?,datetime('now'))
                """,
                (job["id"], "lp_improved_markdown", "lp_improved", improved, "", 1)
            )
            c.execute(
                """
                update conversation_jobs
                set current_phase='lp_improved_done',
                    updated_at=datetime('now')
                where id=?
                """,
                (job["id"],)
            )
            print(f"improved job_id={job['id']}", flush=True)
            done += 1
        except Exception as e:
            print(f"error job_id={job['id']} err={e}", flush=True)
    con.commit()
    con.close()
    print(f"improve_done={done}", flush=True)

if __name__ == "__main__":
    run_once()
