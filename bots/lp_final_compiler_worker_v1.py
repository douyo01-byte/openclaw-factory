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
        where coalesce(current_phase,'')='section_body_done'
          and coalesce(status,'')='done'
          and coalesce(final_reply_status,'') in ('', 'ready', 'queued')
          and id not in (
            select job_id
            from conversation_artifacts
            where artifact_type='lp_final_markdown'
          )
        order by id asc
        limit ?
        """,
        (limit,),
    ).fetchall()

def get_artifact(c, job_id, artifact_type):
    return c.execute(
        """
        select artifact_body
        from conversation_artifacts
        where job_id=?
          and artifact_type=?
        order by id desc
        limit 1
        """,
        (job_id, artifact_type),
    ).fetchone()

def build_final(job, fv_copy, cta_compare, section_body, image_urls):
    target = job["target_object"] or "対象商品"
    fv = fv_copy["artifact_body"] if fv_copy else ""
    cta = cta_compare["artifact_body"] if cta_compare else ""
    body = section_body["artifact_body"] if section_body else ""
    imgs = image_urls["artifact_body"] if image_urls else ""

    lines = []
    lines.append(f"# {target} LP完成稿")
    lines.append("")
    lines.append("## ファーストビュー")
    lines.append(fv.strip() if fv else "FV完成稿コピー未生成")
    lines.append("")
    lines.append("## セクション本文")
    lines.append(body.strip() if body else "セクション本文未生成")
    lines.append("")
    lines.append("## CTA比較")
    lines.append(cta.strip() if cta else "CTA比較未生成")
    lines.append("")
    lines.append("## 商品画像URL候補")
    lines.append(imgs.strip() if imgs else "商品画像URL候補未生成")
    lines.append("")
    lines.append("## 公開前チェック")
    lines.append("- 薬機法表現の再確認")
    lines.append("- CTA採用案の最終決定")
    lines.append("- 使用画像の権利範囲確認")
    lines.append("- 見出しと本文の重複圧縮")
    lines.append("")
    lines.append("## 次アクション")
    lines.append("- LP完成稿を HTML へ落とす")
    lines.append("- FV画像採用案を確定")
    lines.append("- CTA最終案を 1つに絞る")
    return "\n".join(lines)

def run_once():
    con = connect()
    c = con.cursor()
    rows = fetch_jobs(c, 10)
    done = 0
    for job in rows:
        try:
            fv_copy = get_artifact(c, job["id"], "fv_copy_final_markdown")
            cta_compare = get_artifact(c, job["id"], "cta_compare_markdown")
            section_body = get_artifact(c, job["id"], "section_body_markdown")
            image_urls = get_artifact(c, job["id"], "product_image_urls_markdown")

            body = build_final(job, fv_copy, cta_compare, section_body, image_urls)

            c.execute(
                """
                insert into conversation_artifacts(
                  job_id, artifact_type, artifact_title, artifact_body, artifact_path, version, created_at
                ) values(?,?,?,?,?,?,datetime('now'))
                """,
                (job["id"], "lp_final_markdown", "lp_final", body, "", 1)
            )
            c.execute(
                """
                update conversation_jobs
                set current_phase='lp_final_done',
                    updated_at=datetime('now')
                where id=?
                """,
                (job["id"],)
            )
            print(f"lp_final_done job_id={job['id']}", flush=True)
            done += 1
        except Exception as e:
            print(f"lp_final_error job_id={job['id']} err={e}", flush=True)
    con.commit()
    con.close()
    print(f"lp_final_total={done}", flush=True)

if __name__ == "__main__":
    run_once()
