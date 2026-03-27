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
        where coalesce(current_phase,'')='cta_compare_done'
          and coalesce(status,'')='done'
          and coalesce(final_reply_status,'') in ('', 'ready', 'queued')
          and id not in (
            select job_id
            from conversation_artifacts
            where artifact_type='section_body_markdown'
          )
        order by id asc
        limit ?
        """,
        (limit,),
    ).fetchall()

def build_body(job):
    target = job["target_object"] or "対象商品"
    lines = []
    lines.append(f"# {target} セクション本文案")
    lines.append("")
    lines.append("## 1. ファーストビュー本文")
    lines.append("自然なツヤ、均一なトーン、しっとり感を意識しながら、毎日のベースメイクを心地よく整えるBB下地。")
    lines.append("")
    lines.append("## 2. こんな方へ")
    lines.append("厚塗り感は出したくないけれど、肌印象はきれいに整えたい。そんな方に向けた、毎日使いやすいベースメイク発想です。")
    lines.append("")
    lines.append("## 3. educate B の価値")
    lines.append("隠すことを目的にするのではなく、肌そのものが整って見える印象へ。自然なツヤと均一なトーンを意識し、重さを抑えながら使いやすさを目指します。")
    lines.append("")
    lines.append("## 4. 成分訴求本文")
    lines.append("EGF、ビタミンE、セラミド群、植物オイルなどの着眼成分をもとに、仕上がりだけでなく毎日手に取りやすい使用感にも目を向けた設計です。")
    lines.append("")
    lines.append("## 5. 使用イメージ本文")
    lines.append("忙しい朝でも取り入れやすく、肌になじませたときの重たさを抑えながら、自然な印象に整えていくイメージで使える1本です。")
    lines.append("")
    lines.append("## 6. 画像ギャラリー前本文")
    lines.append("商品の印象や質感が伝わるよう、メイン画像、寄り画像、補助画像を組み合わせて視覚的にもわかりやすく整理します。")
    lines.append("")
    lines.append("## 7. CTA前補強本文")
    lines.append("自然なツヤ、均一なトーン、しっとり感。この3点を軸に、毎日のベースメイクを見直したい方へ。")
    lines.append("")
    lines.append("## 8. 最終CTA前本文")
    lines.append("まずは商品詳細を確認し、自分の肌印象に合うかを確かめながら取り入れ方を検討してください。")
    lines.append("")
    lines.append("## 次アクション")
    lines.append("- LP完成稿へ統合")
    lines.append("- CTA採用案を確定")
    lines.append("- 必要ならトーンをさらに上質寄りに調整")
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
                (job["id"], "section_body_markdown", "section_body", body, "", 1)
            )
            c.execute(
                """
                update conversation_jobs
                set current_phase='section_body_done',
                    updated_at=datetime('now')
                where id=?
                """,
                (job["id"],)
            )
            print(f"section_body_done job_id={job['id']}", flush=True)
            done += 1
        except Exception as e:
            print(f"section_body_error job_id={job['id']} err={e}", flush=True)
    con.commit()
    con.close()
    print(f"section_body_total={done}", flush=True)

if __name__ == "__main__":
    run_once()
