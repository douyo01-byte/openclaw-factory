#!/usr/bin/env python3
import json
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
        where coalesce(domain,'') in ('analysis','creative')
          and coalesce(status,'')='new'
        order by id asc
        limit ?
        """,
        (limit,),
    ).fetchall()

def load_context(c, job_id):
    row = c.execute(
        """
        select input_json
        from conversation_job_steps
        where job_id=?
        order by step_order asc
        limit 1
        """,
        (job_id,),
    ).fetchone()
    if not row or not row["input_json"]:
        return {}
    try:
        return json.loads(row["input_json"])
    except:
        return {}

def build_analysis(job, ctx):
    target = job["target_object"] or "対象商品"
    request_text = job["request_text"] or ""
    urls = []
    if isinstance(ctx, dict):
        context = ctx.get("context", {})
        if isinstance(context, dict):
            urls = context.get("urls", []) or []

    body = []
    body.append(f"# {target} 初期分析")
    body.append("")
    body.append("## 依頼")
    body.append(request_text)
    body.append("")
    if urls:
        body.append("## 参照URL")
        for u in urls:
            body.append(f"- {u}")
        body.append("")
    body.append("## 仮説整理")
    body.append("- 現サイトの主訴求を抽出して勝ち軸を整理する案件")
    body.append("- Telegram完結の制作フローへつなぐ前提")
    body.append("- 次段階では商品情報抽出とLP3案生成へ進める")
    body.append("")
    body.append("## 勝ち軸案")
    body.append("1. 素肌印象を整えるベース訴求")
    body.append("2. 乾燥対策・しっとり感訴求")
    body.append("3. 成分発想・美容下地訴求")
    body.append("")
    body.append("## 次アクション")
    body.append("- 商品情報抽出")
    body.append("- 現サイト訴求の整理")
    body.append("- LP3案生成")
    return "\n".join(body)

def mark_done(c, job_id, artifact_body):
    c.execute(
        """
        insert into conversation_artifacts(
          job_id, artifact_type, artifact_title, artifact_body, artifact_path, version, created_at
        ) values(?,?,?,?,?,?,datetime('now'))
        """,
        (
            job_id,
            "analysis_markdown",
            "initial_analysis",
            artifact_body,
            "",
            1,
        )
    )
    c.execute(
        """
        update conversation_job_steps
        set status='done', output_json=?, updated_at=datetime('now')
        where job_id=?
        """,
        (json.dumps({"result": "done"}, ensure_ascii=False), job_id)
    )
    c.execute(
        """
        update conversation_jobs
        set current_phase='analysis_done',
            status='done',
            updated_at=datetime('now')
        where id=?
        """,
        (job_id,)
    )

def run_once():
    con = connect()
    c = con.cursor()
    rows = fetch_jobs(c, 10)
    done = 0
    for job in rows:
        try:
            ctx = load_context(c, job["id"])
            artifact_body = build_analysis(job, ctx)
            mark_done(c, job["id"], artifact_body)
            print(f"done job_id={job['id']}", flush=True)
            done += 1
        except Exception as e:
            c.execute(
                """
                update conversation_jobs
                set current_phase='analysis_error',
                    status='error',
                    updated_at=datetime('now')
                where id=?
                """,
                (job["id"],)
            )
            print(f"error job_id={job['id']} err={e}", flush=True)
    con.commit()
    con.close()
    print(f"worker_done={done}", flush=True)

if __name__ == "__main__":
    run_once()
