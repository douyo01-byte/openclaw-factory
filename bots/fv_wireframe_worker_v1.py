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
        where coalesce(current_phase,'')='product_image_urls_done'
          and coalesce(status,'')='done'
          and coalesce(final_reply_status,'') in ('', 'ready', 'queued')
          and id not in (
            select job_id
            from conversation_artifacts
            where artifact_type='fv_wireframe_markdown'
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

def build_wireframe(job, lp_text, image_plan_text, image_urls_text):
    target = job["target_object"] or "対象商品"

    lines = []
    lines.append(f"# {target} FVラフ構成")
    lines.append("")
    lines.append("## FV目的")
    lines.append("- 3秒で商品ジャンルと価値を伝える")
    lines.append("- 高級感よりも上質感と清潔感を優先")
    lines.append("- 商品画像を主役にしつつコピーを短く見せる")
    lines.append("")
    lines.append("## ワイヤー構成")
    lines.append("[上部余白]")
    lines.append("  ↓")
    lines.append("[左: コピー領域] [右: 商品画像領域]")
    lines.append("  ↓")
    lines.append("[ベネフィット3点]")
    lines.append("  ↓")
    lines.append("[CTAボタン]")
    lines.append("")
    lines.append("## 左側コピー案")
    lines.append("### メインコピー")
    lines.append("隠すより、整えて魅せる。")
    lines.append("")
    lines.append("### サブコピー")
    lines.append("自然なツヤ、均一なトーン、しっとり感を意識したBB下地。")
    lines.append("")
    lines.append("### ベネフィット3点")
    lines.append("- 自然なツヤ")
    lines.append("- 均一なトーン")
    lines.append("- しっとり感")
    lines.append("")
    lines.append("## 右側画像配置")
    lines.append("- 正面の商品画像を中央配置")
    lines.append("- 背景は白〜ベージュの淡色")
    lines.append("- 商品の周囲に余白を広く取る")
    lines.append("- 成分イメージを入れるなら下部に小さく補助配置")
    lines.append("")
    lines.append("## CTA案")
    lines.append("- まずは商品詳細を見る")
    lines.append("- educate B の魅力を確認する")
    lines.append("")
    lines.append("## 補助テキスト")
    lines.append("- 美容成分発想")
    lines.append("- 毎日使いやすいベースメイク")
    lines.append("")
    lines.append("## デザインメモ")
    lines.append("- フォントは細め寄り")
    lines.append("- 黒ベタよりグレー文字")
    lines.append("- 要素を詰めすぎない")
    lines.append("- 商品画像の影は弱め")
    lines.append("")
    lines.append("## 画像URL利用方針")
    lines.append("- og:image候補を最優先")
    lines.append("- 正方形画像なら中央トリミング前提")
    lines.append("- CTA直前に寄り画像を置く場合は別ブロック化")
    lines.append("")
    lines.append("## 次アクション")
    lines.append("- FV完成稿テキスト作成")
    lines.append("- セクション構成へ展開")
    lines.append("- 画像採用案を1つに絞る")

    return "\n".join(lines)

def run_once():
    con = connect()
    c = con.cursor()
    rows = fetch_jobs(c, 10)
    done = 0
    for job in rows:
        try:
            lp = get_artifact(c, job["id"], "lp_improved_markdown")
            image_plan = get_artifact(c, job["id"], "image_plan_markdown")
            image_urls = get_artifact(c, job["id"], "product_image_urls_markdown")

            body = build_wireframe(
                job,
                lp["artifact_body"] if lp else "",
                image_plan["artifact_body"] if image_plan else "",
                image_urls["artifact_body"] if image_urls else "",
            )

            c.execute(
                """
                insert into conversation_artifacts(
                  job_id, artifact_type, artifact_title, artifact_body, artifact_path, version, created_at
                ) values(?,?,?,?,?,?,datetime('now'))
                """,
                (job["id"], "fv_wireframe_markdown", "fv_wireframe", body, "", 1)
            )

            c.execute(
                """
                update conversation_jobs
                set current_phase='fv_wireframe_done',
                    updated_at=datetime('now')
                where id=?
                """,
                (job["id"],)
            )

            print(f"fv_wireframe_done job_id={job['id']}", flush=True)
            done += 1
        except Exception as e:
            print(f"fv_wireframe_error job_id={job['id']} err={e}", flush=True)

    con.commit()
    con.close()
    print(f"fv_wireframe_total={done}", flush=True)

if __name__ == "__main__":
    run_once()
