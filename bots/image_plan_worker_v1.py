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
        where coalesce(current_phase,'')='lp_improved_done'
          and coalesce(status,'')='done'
          and id not in (
            select job_id from conversation_artifacts where artifact_type='image_plan_markdown'
          )
        order by id asc
        limit ?
        """,
        (limit,),
    ).fetchall()

def get_analysis(c, job_id):
    return c.execute(
        """
        select artifact_body
        from conversation_artifacts
        where job_id=?
          and artifact_type='analysis_markdown'
        order by id desc
        limit 1
        """,
        (job_id,),
    ).fetchone()

def get_improved_lp(c, job_id):
    return c.execute(
        """
        select artifact_body
        from conversation_artifacts
        where job_id=?
          and artifact_type='lp_improved_markdown'
        order by id desc
        limit 1
        """,
        (job_id,),
    ).fetchone()

def build_plan(job, analysis_text, lp_text):
    target = job["target_object"] or "対象商品"
    lines = []
    lines.append(f"# {target} 画像構成案")
    lines.append("")
    lines.append("## 目的")
    lines.append("- LPの第一印象を上げる")
    lines.append("- 商品の高級感と使う理由を視覚で伝える")
    lines.append("- 既存商品画像を活かして制作コストを抑える")
    lines.append("")
    lines.append("## 必要画像")
    lines.append("1. 商品単体メイン")
    lines.append("   - 白背景 or 淡色背景")
    lines.append("   - ボトル/パッケージを正面で見せる")
    lines.append("2. 使用感イメージ")
    lines.append("   - 肌の質感が伝わる近接カット")
    lines.append("   - 厚塗り感ではなく自然な印象")
    lines.append("3. 成分訴求イメージ")
    lines.append("   - ザクロ種子油")
    lines.append("   - セラミド群")
    lines.append("   - ビタミンE / EGF")
    lines.append("4. ベネフィット説明図")
    lines.append("   - 自然なツヤ")
    lines.append("   - 均一なトーン")
    lines.append("   - しっとり感")
    lines.append("5. CTA付近の補強画像")
    lines.append("   - 商品を手に取るイメージ")
    lines.append("   - 商品とテキストを一緒に見せる")
    lines.append("")
    lines.append("## FV画像案")
    lines.append("- 商品画像を中央")
    lines.append("- 背景は白〜ベージュ系")
    lines.append("- 余白を広めに取り、高級感寄り")
    lines.append("")
    lines.append("## 既存素材の活用方針")
    lines.append("- 現サイトの既存商品画像を優先利用")
    lines.append("- Shopify配信画像URLを候補として収集")
    lines.append("- 公開前は権利・契約範囲だけ確認")
    lines.append("")
    lines.append("## デザイン指示")
    lines.append("- 色数は少なめ")
    lines.append("- テキストは短く")
    lines.append("- 美容感より清潔感と上質感を優先")
    lines.append("")
    lines.append("## 次アクション")
    lines.append("- 商品画像URL抽出")
    lines.append("- FVラフ構成作成")
    lines.append("- CTA周辺の画像配置案作成")
    return "\n".join(lines)

def run_once():
    con = connect()
    c = con.cursor()
    rows = fetch_jobs(c, 10)
    done = 0
    for job in rows:
        try:
            analysis = get_analysis(c, job["id"])
            lp = get_improved_lp(c, job["id"])
            body = build_plan(
                job,
                analysis["artifact_body"] if analysis else "",
                lp["artifact_body"] if lp else "",
            )
            c.execute(
                """
                insert into conversation_artifacts(
                  job_id, artifact_type, artifact_title, artifact_body, artifact_path, version, created_at
                ) values(?,?,?,?,?,?,datetime('now'))
                """,
                (job["id"], "image_plan_markdown", "image_plan", body, "", 1)
            )
            c.execute(
                """
                update conversation_jobs
                set current_phase='image_plan_done',
                    updated_at=datetime('now')
                where id=?
                """,
                (job["id"],)
            )
            print(f"image_plan_done job_id={job['id']}", flush=True)
            done += 1
        except Exception as e:
            print(f"image_plan_error job_id={job['id']} err={e}", flush=True)
    con.commit()
    con.close()
    print(f"image_plan_total={done}", flush=True)

if __name__ == "__main__":
    run_once()
