#!/usr/bin/env python3
import html
import os
import re
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))
OUT_DIR = Path(os.environ.get("TELEGRAM_OS_HTML_DIR", os.path.expanduser("~/AI/openclaw-factory-daemon/data/telegram_os_html")))

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
        where coalesce(current_phase,'') in ('lp_final_done','public_preview_done')
          and coalesce(status,'')='done'
        order by id asc
        limit ?
        """,
        (limit,),
    ).fetchall()

def get_artifact(c, job_id, artifact_type):
    return c.execute(
        """
        select *
        from conversation_artifacts
        where job_id=? and artifact_type=?
        order by id desc
        limit 1
        """,
        (job_id, artifact_type),
    ).fetchone()

def upsert_artifact(c, job_id, artifact_type, artifact_title, artifact_body, artifact_path, version=1):
    old = c.execute(
        """
        select id from conversation_artifacts
        where job_id=? and artifact_type=?
        order by id desc
        limit 1
        """,
        (job_id, artifact_type),
    ).fetchone()
    if old:
        c.execute(
            """
            update conversation_artifacts
            set artifact_title=?, artifact_body=?, artifact_path=?, version=?
            where id=?
            """,
            (artifact_title, artifact_body, artifact_path, version, old["id"]),
        )
    else:
        c.execute(
            """
            insert into conversation_artifacts(
              job_id, artifact_type, artifact_title, artifact_body, artifact_path, version, created_at
            ) values(?,?,?,?,?,?,datetime('now'))
            """,
            (job_id, artifact_type, artifact_title, artifact_body, artifact_path, version),
        )

def extract_value(text, heading):
    m = re.search(rf'##\s*{re.escape(heading)}\s*\n(.+?)(?:\n## |\Z)', text, re.S)
    return m.group(1).strip() if m else ""

def extract_lines(text, heading):
    block = extract_value(text, heading)
    rows = []
    for line in block.splitlines():
        s = line.strip()
        if not s:
            continue
        s = re.sub(r'^[-・]\s*', '', s)
        rows.append(s)
    return rows

def first_image_url(text):
    if not text:
        return ""
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("http://") or s.startswith("https://"):
            return s
        m = re.search(r'https?://\S+', s)
        if m:
            return m.group(0)
    return ""

def build_html(job, fv_text, body_text, cta_text, image_url):
    main_copy = extract_value(fv_text, "メインコピー案") or "隠すより、整えて魅せる。"
    sub_copy = extract_value(fv_text, "サブコピー案")
    benefits = extract_lines(fv_text, "ベネフィット表示")
    cta_lines = extract_lines(cta_text, "CTA案 2")
    cta_label = cta_lines[0] if cta_lines else "educate B の魅力を確認する"

    sec1 = extract_value(body_text, "1. ファーストビュー本文")
    sec2 = extract_value(body_text, "2. こんな方へ")
    sec3 = extract_value(body_text, "3. educate B の価値")
    sec4 = extract_value(body_text, "4. 成分訴求本文")
    sec5 = extract_value(body_text, "5. 使用シーン本文")
    sec6 = extract_value(body_text, "6. CTA前本文")

    benefits_html = "".join(f"<li>{html.escape(x)}</li>" for x in benefits[:3])

    image_block = f'<img src="{html.escape(image_url)}" alt="educate B" class="hero-image">' if image_url else '<div class="hero-image placeholder">商品画像</div>'

    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>educate B</title>
  <style>
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", "Yu Gothic", sans-serif;
      background: #f3f1ee;
      color: #2d2a28;
      line-height: 1.8;
    }}
    .wrap {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 24px;
    }}
    .card {{
      background: #fcfbf9;
      border-radius: 28px;
      padding: 28px;
      box-shadow: 0 8px 30px rgba(0,0,0,0.04);
      margin-bottom: 24px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 24px;
      align-items: center;
    }}
    .eyebrow {{
      color: #8b7d71;
      font-size: 14px;
      letter-spacing: 0.08em;
      margin-bottom: 10px;
    }}
    h1 {{
      font-size: 54px;
      line-height: 1.12;
      margin: 0 0 14px 0;
    }}
    .sub {{
      font-size: 20px;
      color: #5c534c;
      margin-bottom: 18px;
    }}
    .benefits {{
      padding-left: 20px;
      margin: 0 0 22px 0;
    }}
    .btn {{
      display: inline-block;
      background: #c9a977;
      color: #fff;
      text-decoration: none;
      padding: 16px 30px;
      border-radius: 999px;
      font-weight: 700;
      font-size: 20px;
    }}
    .hero-image {{
      width: 100%;
      max-width: 420px;
      display: block;
      margin: 0 auto;
      border-radius: 24px;
      background: #fff;
    }}
    .placeholder {{
      min-height: 420px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #8b7d71;
      background: #efe8df;
    }}
    h2 {{
      font-size: 34px;
      line-height: 1.3;
      margin: 0 0 14px 0;
    }}
    p {{
      font-size: 20px;
      margin: 0;
    }}
    .cta-final {{
      text-align: center;
    }}
    .cta-final p {{
      margin-bottom: 18px;
    }}
    @media (max-width: 800px) {{
      .hero {{
        grid-template-columns: 1fr;
      }}
      h1 {{
        font-size: 40px;
      }}
      p {{
        font-size: 18px;
      }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="card hero">
      <div>
        <div class="eyebrow">educate B</div>
        <h1>{html.escape(main_copy)}</h1>
        <div class="sub">{html.escape(sub_copy)}</div>
        <ul class="benefits">{benefits_html}</ul>
        <a class="btn" href="https://kuu-medic.com/products/educate-b">{html.escape(cta_label)}</a>
      </div>
      <div>{image_block}</div>
    </section>

    <section class="card">
      <h2>毎日のベースメイクを、もっと心地よく。</h2>
      <p>{html.escape(sec1)}</p>
    </section>

    <section class="card">
      <h2>こんな方へ</h2>
      <p>{html.escape(sec2)}</p>
    </section>

    <section class="card">
      <h2>educate B の価値</h2>
      <p>{html.escape(sec3)}</p>
    </section>

    <section class="card">
      <h2>着眼成分と発想</h2>
      <p>{html.escape(sec4)}</p>
    </section>

    <section class="card">
      <h2>使いやすさを意識した設計</h2>
      <p>{html.escape(sec5)}</p>
    </section>

    <section class="card cta-final">
      <h2>まずは商品詳細を確認し、自分に合う使い方を検討してください。</h2>
      <p>{html.escape(sec6)}</p>
      <a class="btn" href="https://kuu-medic.com/products/educate-b">{html.escape(cta_label)}</a>
    </section>
  </div>
</body>
</html>
"""

def run_once():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    con = connect()
    c = con.cursor()
    rows = fetch_jobs(c, 20)
    done = 0

    for job in rows:
        try:
            fv = get_artifact(c, job["id"], "fv_copy_final_markdown")
            body = get_artifact(c, job["id"], "section_body_markdown")
            cta = get_artifact(c, job["id"], "cta_compare_markdown")
            imgs = get_artifact(c, job["id"], "product_image_urls_markdown")

            if not fv or not body or not cta:
                continue

            image_url = first_image_url(imgs["artifact_body"] if imgs else "")
            html_text = build_html(
                job,
                fv["artifact_body"],
                body["artifact_body"],
                cta["artifact_body"],
                image_url,
            )

            out_path = OUT_DIR / f"job_{job['id']}_lp.html"
            out_path.write_text(html_text, encoding="utf-8")

            upsert_artifact(
                c,
                job["id"],
                "lp_html_export",
                "lp_html_export",
                f"HTMLを書き出しました: {out_path}",
                str(out_path),
                1,
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
