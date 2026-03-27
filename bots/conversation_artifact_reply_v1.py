#!/usr/bin/env python3
import os
import sqlite3
import sys

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))

def connect():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    return con

def build_reply(job_id: int) -> str:
    con = connect()
    c = con.cursor()
    job = c.execute("select * from conversation_jobs where id=?", (job_id,)).fetchone()
    arts = c.execute(
        """
        select artifact_type, artifact_title, artifact_body, version
        from conversation_artifacts
        where job_id=?
        order by id asc
        """,
        (job_id,),
    ).fetchall()
    con.close()

    lines = []
    lines.append(f"案件 {job_id} の処理が完了しました。")
    lines.append(f"領域: {job['domain']}")
    if job["target_object"]:
        lines.append(f"対象: {job['target_object']}")
    lines.append("")
    for a in arts:
        if a["artifact_type"] == "analysis_markdown":
            lines.append("【分析】")
            lines.append(a["artifact_body"][:700])
            lines.append("")
        elif a["artifact_type"] == "lp_markdown":
            lines.append(f"【LP案 v{a['version']}】")
            lines.append(a["artifact_body"][:700])
            lines.append("")
    lines.append("次アクション候補:")
    lines.append("1. 3案を比較して本命1案を選ぶ")
    lines.append("2. FVを強化する")
    lines.append("3. CTAを改善する")
    return "\n".join(lines).strip()

def main() -> None:
    job_id = int(sys.argv[1])
    print(build_reply(job_id))

if __name__ == "__main__":
    main()
