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
        where coalesce(current_phase,'')='fv_wireframe_done'
          and coalesce(status,'')='done'
          and coalesce(final_reply_status,'') in ('', 'ready', 'queued')
          and id not in (
            select job_id
            from conversation_artifacts
            where artifact_type='section_outline_markdown'
          )
        order by id asc
        limit ?
        """,
        (limit,),
    ).fetchall()

def build_outline(job):
    target = job["target_object"] or "対象商品"

    lines = []
    lines.append(f"# {target} LPセクション構成")
    lines.append("")
    lines.append("## 1. ファーストビュー")
    lines.append("- メインコピー")
    lines.append("- サブコピー")
    lines.append("- 商品画像")
    lines.append("- CTA")
    lines.append("")
    lines.append("## 2. こんな悩みを持つ方へ")
    lines.append("- 厚塗り感を出したくない")
    lines.append("- 肌印象を自然に整えたい")
    lines.append("- 乾燥感を避けたい")
    lines.append("")
    lines.append("## 3. educate B の価値")
    lines.append("- 自然なツヤ")
    lines.append("- 均一なトーン")
    lines.append("- しっとり感")
    lines.append("- 毎日使いやすいBB下地")
    lines.append("")
    lines.append("## 4. 成分訴求")
    lines.append("- EGF")
    lines.append("- ビタミンE")
    lines.append("- セラミド群")
    lines.append("- 植物オイル")
    lines.append("")
    lines.append("## 5. 使用イメージ")
    lines.append("- 肌へのなじみ")
    lines.append("- 重すぎない印象")
    lines.append("- 日常使いのしやすさ")
    lines.append("")
    lines.append("## 6. 商品画像ギャラリー")
    lines.append("- メイン商品画像")
    lines.append("- 寄り画像")
    lines.append("- 補助画像")
    lines.append("")
    lines.append("## 7. CTA前補強")
    lines.append("- ベネフィット再提示")
    lines.append("- 短い安心材料")
    lines.append("- ボタン直前コピー")
    lines.append("")
    lines.append("## 8. 最終CTA")
    lines.append("- 商品詳細を見る")
    lines.append("- 購入導線へ進む")
    lines.append("")
    lines.append("## 次アクション")
    lines.append("- 各セクション本文案作成")
    lines.append("- FV完成稿コピー作成")
    lines.append("- CTA文言比較")
    return "\n".join(lines)

def run_once():
    con = connect()
    c = con.cursor()
    rows = fetch_jobs(c, 10)
    done = 0
    for job in rows:
        try:
            body = build_outline(job)
            c.execute(
                """
                insert into conversation_artifacts(
                  job_id, artifact_type, artifact_title, artifact_body, artifact_path, version, created_at
                ) values(?,?,?,?,?,?,datetime('now'))
                """,
                (job["id"], "section_outline_markdown", "section_outline", body, "", 1)
            )
            c.execute(
                """
                update conversation_jobs
                set current_phase='section_outline_done',
                    updated_at=datetime('now')
                where id=?
                """,
                (job["id"],)
            )
            print(f"section_outline_done job_id={job['id']}", flush=True)
            done += 1
        except Exception as e:
            print(f"section_outline_error job_id={job['id']} err={e}", flush=True)
    con.commit()
    con.close()
    print(f"section_outline_total={done}", flush=True)

if __name__ == "__main__":
    run_once()
