#!/usr/bin/env python3
import html
import os
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))
ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "telegram_os_html"

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
        where coalesce(current_phase,'')='lp_final_done'
          and coalesce(status,'')='done'
          and coalesce(final_reply_status,'') in ('', 'ready', 'queued', 'sent')
          and id not in (
            select job_id
            from conversation_artifacts
            where artifact_type='lp_html_export'
          )
        order by id asc
        limit ?
        """,
        (limit,),
    ).fetchall()

def get_body(c, job_id, artifact_type):
    row = c.execute(
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
    return row["artifact_body"] if row else ""

def esc(s: str) -> str:
    return html.escape(s or "")

def nl2br(s: str) -> str:
    return "<br>\n".join(esc(s).splitlines())

def build_html(job, fv_copy, section_body, cta_compare, image_urls):
    title = f"{job['target_object'] or 'LP'} LP Draft"
    fv = nl2br(fv_copy)
    body = nl2br(section_body)
    cta = nl2br(cta_compare)
    imgs = nl2br(image_urls)

    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<style>
body {{
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Yu Gothic", sans-serif;
  color: #222;
  background: #faf8f5;
}}
.wrap {{
  max-width: 1100px;
  margin: 0 auto;
  padding: 32px 20px 80px;
}}
.hero {{
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 32px;
  align-items: center;
  padding: 48px 0 24px;
}}
.card {{
  background: #fff;
  border-radius: 18px;
  padding: 24px;
  box-shadow: 0 10px 30px rgba(0,0,0,.06);
}}
.eyebrow {{
  font-size: 12px;
  letter-spacing: .08em;
  color: #8b7d6b;
  margin-bottom: 10px;
}}
h1 {{
  font-size: 40px;
  line-height: 1.25;
  margin: 0 0 16px;
}}
.sub {{
  font-size: 16px;
  line-height: 1.9;
  color: #555;
}}
.cta {{
  display: inline-block;
  margin-top: 18px;
  padding: 14px 22px;
  border-radius: 999px;
  background: #c8a97e;
  color: #fff;
  text-decoration: none;
  font-weight: 700;
}}
.image-box {{
  min-height: 420px;
  border-radius: 22px;
  background: linear-gradient(180deg, #f6f1ea, #efe6da);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8b7d6b;
  text-align: center;
  padding: 24px;
}}
section {{
  margin-top: 28px;
}}
h2 {{
  font-size: 24px;
  margin: 0 0 14px;
}}
.block {{
  white-space: normal;
  line-height: 1.95;
  color: #444;
}}
@media (max-width: 860px) {{
  .hero {{
    grid-template-columns: 1fr;
  }}
  h1 {{
    font-size: 30px;
  }}
}}
</style>
</head>
<body>
<div class="wrap">
  <section class="hero">
    <div class="card">
      <div class="eyebrow">{esc(job["target_object"] or "Product")}</div>
      <h1>隠すより、整えて魅せる。</h1>
      <div class="sub">{fv}</div>
      <a class="cta" href="#cta">まずは商品詳細を見る</a>
    </div>
    <div class="image-box card">
      <div>
        <strong>商品画像配置エリア</strong><br>
        正面商品画像 / 白〜ベージュ背景 / 補助成分ビジュアル
      </div>
    </div>
  </section>

  <section class="card">
    <h2>セクション本文</h2>
    <div class="block">{body}</div>
  </section>

  <section class="card">
    <h2>CTA比較</h2>
    <div class="block">{cta}</div>
  </section>

  <section class="card">
    <h2>商品画像URL候補</h2>
    <div class="block">{imgs}</div>
  </section>

  <section id="cta" class="card">
    <h2>最終CTA</h2>
    <div class="block">まずは商品詳細を確認し、自分に合う使い方を検討してください。</div>
    <a class="cta" href="#">educate B の魅力を確認する</a>
  </section>
</div>
</body>
</html>
"""

def run_once():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    con = connect()
    c = con.cursor()
    rows = fetch_jobs(c, 10)
    done = 0
    for job in rows:
        try:
            fv_copy = get_body(c, job["id"], "fv_copy_final_markdown")
            section_body = get_body(c, job["id"], "section_body_markdown")
            cta_compare = get_body(c, job["id"], "cta_compare_markdown")
            image_urls = get_body(c, job["id"], "product_image_urls_markdown")

            html_text = build_html(job, fv_copy, section_body, cta_compare, image_urls)
            out_path = OUT_DIR / f"job_{job['id']}_lp.html"
            out_path.write_text(html_text, encoding="utf-8")

            c.execute(
                """
                insert into conversation_artifacts(
                  job_id, artifact_type, artifact_title, artifact_body, artifact_path, version, created_at
                ) values(?,?,?,?,?,?,datetime('now'))
                """,
                (
                    job["id"],
                    "lp_html_export",
                    "lp_html_export",
                    f"HTMLを書き出しました: {out_path}",
                    str(out_path),
                    1
                )
            )
            c.execute(
                """
                update conversation_jobs
                set current_phase='lp_html_export_done',
                    updated_at=datetime('now')
                where id=?
                """,
                (job["id"],)
            )
            print(f"lp_html_export_done job_id={job['id']} path={out_path}", flush=True)
            done += 1
        except Exception as e:
            print(f"lp_html_export_error job_id={job['id']} err={e}", flush=True)
    con.commit()
    con.close()
    print(f"lp_html_export_total={done}", flush=True)

if __name__ == "__main__":
    run_once()
