#!/usr/bin/env python3
import os
import sqlite3
import sys

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))

def connect():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    return con

def find_artifact(arts, artifact_type):
    for a in arts:
        if a["artifact_type"] == artifact_type:
            return a
    return None

def build_reply(job_id: int) -> str:
    con = connect()
    c = con.cursor()
    job = c.execute("select * from conversation_jobs where id=?", (job_id,)).fetchone()
    arts = c.execute(
        """
        select artifact_type, artifact_title, artifact_body, artifact_path, version
        from conversation_artifacts
        where job_id=?
        order by id asc
        """,
        (job_id,),
    ).fetchall()
    con.close()

    best = find_artifact(arts, "lp_best_markdown")
    improved = find_artifact(arts, "lp_improved_markdown")
    fv = find_artifact(arts, "fv_copy_final_markdown")
    cta = find_artifact(arts, "cta_compare_markdown")
    lp_final = find_artifact(arts, "lp_final_markdown")
    preview = find_artifact(arts, "public_preview_url")
    html_export = find_artifact(arts, "lp_html_export")

    lines = []
    lines.append(f"案件 {job_id} の処理が完了しました。")
    lines.append(f"領域: {job['domain']}")
    if job["target_object"]:
        lines.append(f"対象: {job['target_object']}")
    lines.append("")

    if best:
        lines.append("【本命LP】")
        lines.append(best["artifact_body"][:220])
        lines.append("")

    if improved:
        lines.append("【改善版LP】")
        lines.append(improved["artifact_body"][:260])
        lines.append("")

    if fv:
        lines.append("【FV完成稿コピー】")
        lines.append(fv["artifact_body"][:260])
        lines.append("")

    if cta:
        lines.append("【CTA比較案】")
        lines.append(cta["artifact_body"][:260])
        lines.append("")

    if lp_final:
        lines.append("【LP完成稿】")
        lines.append(lp_final["artifact_body"][:420])
        lines.append("")

    if preview:
        lines.append("【お客様確認用URL】")
        lines.append(preview["artifact_body"])
        lines.append("")

    elif html_export:
        lines.append("【HTML出力】")
        lines.append(html_export["artifact_body"])
        if html_export["artifact_path"]:
            lines.append(html_export["artifact_path"])
        lines.append("")

    lines.append("次アクション候補:")
    lines.append("1. お客様に確認URLを送る")
    lines.append("2. CTA最終案を決める")
    lines.append("3. 公開前チェックを行う")
    return "\n".join(lines).strip()

def main() -> None:
    job_id = int(sys.argv[1])
    print(build_reply(job_id))

if __name__ == "__main__":
    main()
