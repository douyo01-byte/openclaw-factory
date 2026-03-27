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
        where coalesce(current_phase,'')='section_outline_done'
          and coalesce(status,'')='done'
          and coalesce(final_reply_status,'') in ('', 'ready', 'queued')
          and id not in (
            select job_id
            from conversation_artifacts
            where artifact_type='fv_copy_final_markdown'
          )
        order by id asc
        limit ?
        """,
        (limit,),
    ).fetchall()

def build_copy(job):
    target = job["target_object"] or "対象商品"
    lines = []
    lines.append(f"# {target} FV完成稿コピー")
    lines.append("")
    lines.append("## メインコピー案")
    lines.append("隠すより、整えて魅せる。")
    lines.append("")
    lines.append("## サブコピー案")
    lines.append("自然なツヤ、均一なトーン、しっとり感を意識した、毎日使いやすいBB下地。")
    lines.append("")
    lines.append("## ベネフィット表示")
    lines.append("- 自然なツヤ")
    lines.append("- 均一なトーン")
    lines.append("- しっとり感")
    lines.append("")
    lines.append("## CTA案")
    lines.append("まずは商品詳細を見る")
    lines.append("")
    lines.append("## 補助コピー")
    lines.append("美容成分発想で、ベースメイク時間を心地よいケア時間へ。")
    lines.append("")
    lines.append("## トーン指示")
    lines.append("- 短く")
    lines.append("- 上質感優先")
    lines.append("- 誇張しすぎない")
    lines.append("")
    lines.append("## 次アクション")
    lines.append("- CTA比較案を3つ出す")
    lines.append("- セクション本文へ展開")
    return "\n".join(lines)

def run_once():
    con = connect()
    c = con.cursor()
    rows = fetch_jobs(c, 10)
    done = 0
    for job in rows:
        try:
            body = build_copy(job)
            c.execute(
                """
                insert into conversation_artifacts(
                  job_id, artifact_type, artifact_title, artifact_body, artifact_path, version, created_at
                ) values(?,?,?,?,?,?,datetime('now'))
                """,
                (job["id"], "fv_copy_final_markdown", "fv_copy_final", body, "", 1)
            )
            c.execute(
                """
                update conversation_jobs
                set current_phase='fv_copy_final_done',
                    updated_at=datetime('now')
                where id=?
                """,
                (job["id"],)
            )
            print(f"fv_copy_final_done job_id={job['id']}", flush=True)
            done += 1
        except Exception as e:
            print(f"fv_copy_final_error job_id={job['id']} err={e}", flush=True)
    con.commit()
    con.close()
    print(f"fv_copy_final_total={done}", flush=True)

if __name__ == "__main__":
    run_once()
