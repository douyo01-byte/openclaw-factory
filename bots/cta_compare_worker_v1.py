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
        where coalesce(current_phase,'')='fv_copy_final_done'
          and coalesce(status,'')='done'
          and coalesce(final_reply_status,'') in ('', 'ready', 'queued')
          and id not in (
            select job_id
            from conversation_artifacts
            where artifact_type='cta_compare_markdown'
          )
        order by id asc
        limit ?
        """,
        (limit,),
    ).fetchall()

def build_body(job):
    target = job["target_object"] or "対象商品"
    lines = []
    lines.append(f"# {target} CTA比較案")
    lines.append("")
    lines.append("## CTA案 1")
    lines.append("まずは商品詳細を見る")
    lines.append("- 最も無難")
    lines.append("- 押し売り感が弱い")
    lines.append("- 初回導線向け")
    lines.append("")
    lines.append("## CTA案 2")
    lines.append("educate B の魅力を確認する")
    lines.append("- 商品名を入れて印象固定")
    lines.append("- 比較的やわらかい")
    lines.append("- LP中盤〜終盤向け")
    lines.append("")
    lines.append("## CTA案 3")
    lines.append("自分の肌印象を整える一歩を始める")
    lines.append("- ベネフィット訴求寄り")
    lines.append("- 感情訴求が入る")
    lines.append("- 強めのコピー寄り")
    lines.append("")
    lines.append("## 推奨")
    lines.append("- FV直下: CTA案 1")
    lines.append("- 最終CTA: CTA案 2")
    lines.append("- テスト比較用: CTA案 3")
    lines.append("")
    lines.append("## 次アクション")
    lines.append("- セクション本文作成")
    lines.append("- CTA配置位置の最終調整")
    return "\n".join(lines)

def run_once():
    con = connect()
    c = con.cursor()
    rows = fetch_jobs(c, 10)
    done = 0
    for job in rows:
        try:
            body = build_body(job)
            c.execute(
                """
                insert into conversation_artifacts(
                  job_id, artifact_type, artifact_title, artifact_body, artifact_path, version, created_at
                ) values(?,?,?,?,?,?,datetime('now'))
                """,
                (job["id"], "cta_compare_markdown", "cta_compare", body, "", 1)
            )
            c.execute(
                """
                update conversation_jobs
                set current_phase='cta_compare_done',
                    updated_at=datetime('now')
                where id=?
                """,
                (job["id"],)
            )
            print(f"cta_compare_done job_id={job['id']}", flush=True)
            done += 1
        except Exception as e:
            print(f"cta_compare_error job_id={job['id']} err={e}", flush=True)
    con.commit()
    con.close()
    print(f"cta_compare_total={done}", flush=True)

if __name__ == "__main__":
    run_once()
