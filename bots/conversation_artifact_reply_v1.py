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
        select artifact_type, artifact_title, artifact_body, artifact_path, version
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
            lines.append(a["artifact_body"][:140])
            lines.append("")
        elif a["artifact_type"] == "lp_review_markdown":
            lines.append("【LPレビュー】")
            lines.append(a["artifact_body"][:140])
            lines.append("")
        elif a["artifact_type"] == "lp_improved_markdown":
            lines.append("【改善版LP】")
            lines.append(a["artifact_body"][:160])
            lines.append("")
        elif a["artifact_type"] == "image_plan_markdown":
            lines.append("【画像構成案】")
            lines.append(a["artifact_body"][:140])
            lines.append("")
        elif a["artifact_type"] == "product_image_urls_markdown":
            lines.append("【商品画像URL候補】")
            lines.append(a["artifact_body"][:140])
            lines.append("")
        elif a["artifact_type"] == "fv_wireframe_markdown":
            lines.append("【FVラフ構成】")
            lines.append(a["artifact_body"][:150])
            lines.append("")
        elif a["artifact_type"] == "section_outline_markdown":
            lines.append("【セクション構成】")
            lines.append(a["artifact_body"][:150])
            lines.append("")
        elif a["artifact_type"] == "fv_copy_final_markdown":
            lines.append("【FV完成稿コピー】")
            lines.append(a["artifact_body"][:160])
            lines.append("")
        elif a["artifact_type"] == "cta_compare_markdown":
            lines.append("【CTA比較案】")
            lines.append(a["artifact_body"][:160])
            lines.append("")
        elif a["artifact_type"] == "section_body_markdown":
            lines.append("【セクション本文案】")
            lines.append(a["artifact_body"][:180])
            lines.append("")
        elif a["artifact_type"] == "lp_final_markdown":
            lines.append("【LP完成稿】")
            lines.append(a["artifact_body"][:260])
            lines.append("")
        elif a["artifact_type"] == "lp_html_export":
            lines.append("【HTML出力】")
            lines.append(a["artifact_body"])
            if a["artifact_path"]:
                lines.append(a["artifact_path"])
            lines.append("")
        elif a["artifact_type"] == "lp_markdown":
            lines.append(f"【LP案 v{a['version']}】")
            lines.append(a["artifact_body"][:70])
            lines.append("")

    lines.append("次アクション候補:")
    lines.append("1. HTMLを確認する")
    lines.append("2. CTA最終案を決める")
    lines.append("3. 公開前チェックを行う")
    return "\n".join(lines).strip()

def main() -> None:
    job_id = int(sys.argv[1])
    print(build_reply(job_id))

if __name__ == "__main__":
    main()
