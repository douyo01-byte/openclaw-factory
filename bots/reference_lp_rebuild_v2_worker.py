from __future__ import annotations
import os
import re
import sys
import html
import sqlite3
from pathlib import Path

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
HTML_DIR = Path("/Users/doyopc/AI/openclaw-factory-daemon/data/telegram_os_html")
HTML_DIR.mkdir(parents=True, exist_ok=True)

def conn():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def fetch_latest(c, job_id: int, artifact_type: str):
    return c.execute("""
        select *
        from conversation_artifacts
        where job_id=?
          and artifact_type=?
        order by id desc
        limit 1
    """, (job_id, artifact_type)).fetchone()

def fetch_all(c, job_id: int, artifact_type: str):
    return c.execute("""
        select *
        from conversation_artifacts
        where job_id=?
          and artifact_type=?
        order by id asc
    """, (job_id, artifact_type)).fetchall()

def extract_image_urls(text: str) -> list[str]:
    if not text:
        return []
    urls = re.findall(r'https?://[^\s<>"\'\]]+', text)
    out = []
    seen = set()
    for u in urls:
        u = u.strip().rstrip(".,)")
        if not re.search(r'\.(avif|webp|png|jpe?g)(\?|$)', u, re.I):
            continue
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out

def lines_after_heading(md: str, heading: str) -> list[str]:
    if not md:
        return []
    s = md.splitlines()
    out = []
    hit = False
    for line in s:
        t = line.strip()
        if t == heading:
            hit = True
            continue
        if hit and t.startswith("## "):
            break
        if hit:
            if t:
                out.append(t)
    return out

def bullet_lines(md: str, heading: str) -> list[str]:
    vals = []
    for line in lines_after_heading(md, heading):
        t = line.strip()
        if t.startswith("- "):
            vals.append(t[2:].strip())
    return vals

def prose_after_heading(md: str, heading: str) -> str:
    vals = []
    for line in lines_after_heading(md, heading):
        t = line.strip()
        if t.startswith("- "):
            continue
        vals.append(t)
    return " ".join(vals).strip()

def render_cards(items: list[str]) -> str:
    if not items:
        return ""
    return "".join(
        f'<div class="benefit-card">{html.escape(x)}</div>'
        for x in items
    )

def render_bullets(items: list[str]) -> str:
    if not items:
        return ""
    return "<ul>" + "".join(f"<li>{html.escape(x)}</li>" for x in items) + "</ul>"

def pick_images(c, job_id: int):
    a = fetch_latest(c, job_id, "product_image_urls_markdown")
    urls = extract_image_urls(a["artifact_body"] if a else "")
    hero = urls[0] if len(urls) >= 1 else ""
    sub1 = urls[1] if len(urls) >= 2 else hero
    sub2 = urls[2] if len(urls) >= 3 else hero
    return hero, sub1, sub2, urls

def build_v2(job_id: int):
    c = conn()

    job = c.execute("select * from conversation_jobs where id=?", (job_id,)).fetchone()
    if not job:
        raise RuntimeError("job_not_found")

    fv = fetch_latest(c, job_id, "fv_copy_final_v2_markdown")
    outline = fetch_latest(c, job_id, "section_outline_v2_markdown")
    body = fetch_latest(c, job_id, "section_body_v2_markdown")
    final_lp = fetch_latest(c, job_id, "lp_final_v2_markdown")

    if not fv or not body or not final_lp:
        raise RuntimeError("v2_artifact_missing")

    hero_img, sub_img1, sub_img2, all_imgs = pick_images(c, job_id)

    main_copy = prose_after_heading(fv["artifact_body"], "## メ イ ン コ ピ ー") or prose_after_heading(fv["artifact_body"], "## メインコピー")
    sub_copy = prose_after_heading(fv["artifact_body"], "## サ ブ コ ピ ー") or prose_after_heading(fv["artifact_body"], "## サブコピー")
    benefits = bullet_lines(fv["artifact_body"], "## ベ ネ フ ィ ッ ト 表 示") or bullet_lines(fv["artifact_body"], "## ベネフィット表示")
    cta = prose_after_heading(fv["artifact_body"], "## CTA案") or "商品詳細を見る"
    subline = prose_after_heading(fv["artifact_body"], "## 補 助 コ ピ ー") or prose_after_heading(fv["artifact_body"], "## 補助コピー")

    concern_title = "こんな方へ"
    concern_body = prose_after_heading(body["artifact_body"], "## 2. こ ん な 方 へ") or prose_after_heading(body["artifact_body"], "## 2. こんな方へ")
    value_title = "educate B の価値"
    value_body = prose_after_heading(body["artifact_body"], "## 3. 仕 上 が り 価 値") or prose_after_heading(body["artifact_body"], "## 3. 仕上がり価値")
    ingredient_title = "成分発想"
    ingredient_body = prose_after_heading(body["artifact_body"], "## 4. 成 分 発 想") or prose_after_heading(body["artifact_body"], "## 4. 成分発想")
    usage_title = "使用イメージ"
    usage_body = prose_after_heading(body["artifact_body"], "## 5. 使 用 イ メ ー ジ") or prose_after_heading(body["artifact_body"], "## 5. 使用イメージ")
    summary_title = "商品要約"
    summary_body = prose_after_heading(body["artifact_body"], "## 6. 商 品 要 約") or prose_after_heading(body["artifact_body"], "## 6. 商品要約")
    closing_title = "クロージング"
    closing_body = prose_after_heading(body["artifact_body"], "## 7. ク ロ ー ジ ン グ CTA") or prose_after_heading(body["artifact_body"], "## 7. クロージングCTA")

    target_items = [
        "厚塗り感は出したくない",
        "肌印象を自然に整えたい",
        "乾燥感を避けたい",
    ]
    if outline:
        tmp = bullet_lines(outline["artifact_body"], "## 2. こ ん な 悩 み を 持 つ 方 へ") or bullet_lines(outline["artifact_body"], "## 2. こんな悩みを持つ方へ")
        if tmp:
            target_items = tmp[:3]

    product_name = html.escape((job["target_object"] or "educate B").strip() or "educate B")

    hero_image_html = ""
    if hero_img:
        hero_image_html = f'''
        <div class="hero-image-wrap">
          <img class="hero-image" src="{html.escape(hero_img)}" alt="{product_name}">
        </div>
        '''
    else:
        hero_image_html = f'''
        <div class="hero-image-wrap placeholder">
          <div class="placeholder-inner">
            <div class="placeholder-over">PRODUCT VISUAL AREA</div>
            <div class="placeholder-name">{product_name}</div>
            <div class="placeholder-sub">商品画像を大きく配置</div>
          </div>
        </div>
        '''

    gallery_html = ""
    gallery_imgs = [x for x in [sub_img1, sub_img2] if x]
    if gallery_imgs:
        gallery_html = '<div class="image-grid">' + "".join(
            f'<img class="sub-image" src="{html.escape(u)}" alt="{product_name}">' for u in gallery_imgs[:2]
        ) + '</div>'

    page = f'''<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{product_name} LP v2</title>
<style>
:root {{
  --bg:#f6f2ee;
  --paper:#fffdfb;
  --ink:#1f1f22;
  --sub:#6d625c;
  --line:#e8ddd4;
  --accent:#1f1f22;
  --accent2:#b99872;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0;
  font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Yu Gothic","Noto Sans JP",sans-serif;
  background:var(--bg);
  color:var(--ink);
  line-height:1.7;
}}
img {{ display:block; max-width:100%; }}
.wrap {{
  width:min(100%, 1120px);
  margin:0 auto;
  padding:28px 18px 80px;
}}
.hero {{
  padding:28px 0 18px;
}}
.hero-grid {{
  display:grid;
  grid-template-columns:1.05fr .95fr;
  gap:28px;
  align-items:center;
}}
.eyebrow {{
  font-size:14px;
  letter-spacing:.12em;
  color:#8e756b;
  margin-bottom:18px;
}}
h1 {{
  margin:0 0 18px;
  font-size:clamp(42px, 7vw, 76px);
  line-height:1.08;
  letter-spacing:-0.03em;
}}
.lead {{
  margin:0 0 24px;
  font-size:clamp(18px, 2.7vw, 30px);
  color:var(--sub);
}}
.subline {{
  margin-top:18px;
  color:#7f726b;
  font-size:16px;
}}
.hero-image-wrap {{
  background:linear-gradient(180deg,#f7eee7 0%,#f4ece6 100%);
  border:1px solid var(--line);
  border-radius:32px;
  padding:20px;
  min-height:420px;
  display:flex;
  align-items:center;
  justify-content:center;
  overflow:hidden;
  box-shadow:0 10px 30px rgba(41,28,17,.05);
}}
.hero-image {{
  width:100%;
  height:auto;
  object-fit:contain;
  border-radius:18px;
}}
.placeholder-inner {{
  text-align:center;
  color:#9b7f75;
}}
.placeholder-over {{
  font-size:16px;
  letter-spacing:.12em;
  margin-bottom:16px;
}}
.placeholder-name {{
  font-size:48px;
  font-weight:700;
  line-height:1.1;
}}
.placeholder-sub {{
  margin-top:14px;
  font-size:16px;
}}
.benefit-row {{
  display:grid;
  grid-template-columns:repeat(3,1fr);
  gap:16px;
  margin:28px 0 22px;
}}
.benefit-card {{
  background:var(--paper);
  border:1px solid var(--line);
  border-radius:22px;
  padding:22px 18px;
  font-size:15px;
  min-height:106px;
  display:flex;
  align-items:center;
}}
.cta {{
  display:inline-flex;
  align-items:center;
  justify-content:center;
  text-decoration:none;
  min-height:66px;
  padding:0 28px;
  background:var(--accent);
  color:#fff;
  border-radius:999px;
  font-size:18px;
  font-weight:700;
  margin-top:8px;
}}
.section {{
  padding:56px 0;
  border-top:1px solid #ebe3dc;
}}
.section-grid {{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:28px;
  align-items:start;
}}
.card {{
  background:var(--paper);
  border:1px solid var(--line);
  border-radius:28px;
  padding:28px;
}}
.card h2, .card h3 {{
  margin:0 0 14px;
  font-size:clamp(28px,4vw,48px);
  line-height:1.14;
}}
.card p {{
  margin:0;
  font-size:18px;
}}
.card ul {{
  margin:0;
  padding-left:1.2em;
  font-size:18px;
}}
.image-grid {{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:18px;
  margin-top:18px;
}}
.sub-image {{
  width:100%;
  border-radius:22px;
  border:1px solid var(--line);
  background:#fff;
}}
.product-summary {{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:28px;
  align-items:center;
}}
.product-shot {{
  background:#fff;
  border:1px solid var(--line);
  border-radius:28px;
  padding:18px;
}}
footer {{
  padding:56px 0 20px;
}}
@media (max-width: 860px) {{
  .hero-grid,
  .section-grid,
  .product-summary,
  .benefit-row {{
    grid-template-columns:1fr;
  }}
  .wrap {{
    padding:20px 16px 64px;
  }}
  h1 {{
    font-size:clamp(40px, 12vw, 64px);
  }}
  .hero-image-wrap {{
    min-height:320px;
  }}
  .card {{
    padding:24px;
  }}
}}
</style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="hero-grid">
        <div>
          <div class="eyebrow">BB BASE MAKE / {product_name.upper()}</div>
          <h1>{html.escape(main_copy)}</h1>
          <p class="lead">{html.escape(sub_copy)}</p>
          <div class="benefit-row">{render_cards(benefits)}</div>
          <a class="cta" href="https://kuu-medic.com/products/educate-b" target="_blank" rel="noopener noreferrer">{html.escape(cta)}</a>
          <div class="subline">{html.escape(subline)}</div>
        </div>
        <div>
          {hero_image_html}
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-grid">
        <div class="card">
          <h2>{html.escape(concern_title)}</h2>
          <p>{html.escape(concern_body)}</p>
          <div style="height:18px"></div>
          {render_bullets(target_items)}
        </div>
        <div class="card">
          <h2>{html.escape(value_title)}</h2>
          <p>{html.escape(value_body)}</p>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-grid">
        <div class="card">
          <h2>{html.escape(ingredient_title)}</h2>
          <p>{html.escape(ingredient_body)}</p>
        </div>
        <div class="card">
          <h2>{html.escape(usage_title)}</h2>
          <p>{html.escape(usage_body)}</p>
          {gallery_html}
        </div>
      </div>
    </section>

    <section class="section">
      <div class="product-summary">
        <div class="product-shot">
          {f'<img class="hero-image" src="{html.escape(hero_img)}" alt="{product_name}">' if hero_img else hero_image_html}
        </div>
        <div class="card">
          <h2>{html.escape(summary_title)}</h2>
          <p>{html.escape(summary_body)}</p>
          <div style="height:22px"></div>
          <a class="cta" href="https://kuu-medic.com/products/educate-b" target="_blank" rel="noopener noreferrer">{html.escape(cta)}</a>
        </div>
      </div>
    </section>

    <footer>
      <div class="card">
        <h2>{html.escape(closing_title)}</h2>
        <p>{html.escape(closing_body)}</p>
      </div>
    </footer>
  </div>
</body>
</html>'''

    out_path = HTML_DIR / f"job_{job_id}_lp_v2.html"
    out_path.write_text(page, encoding="utf-8")

    c.execute("""
        insert into conversation_artifacts(
          job_id, artifact_type, artifact_title, artifact_body, artifact_path, version, created_at
        ) values(?,?,?,?,?,?,datetime('now'))
    """, (
        job_id,
        "lp_html_export_v2",
        "lp_html_export_v2",
        f"HTMLを 書 き 出 し ま し た : {out_path}",
        str(out_path),
        2,
    ))
    c.execute("""
        update conversation_jobs
        set current_phase='lp_v2_rebuilt_done',
            updated_at=datetime('now')
        where id=?
    """, (job_id,))
    c.commit()
    c.close()
    print(f"reference_rebuild_v2_done job_id={job_id} path={out_path}", flush=True)

def main():
    job_id = int(sys.argv[1]) if len(sys.argv) > 1 else 19
    build_v2(job_id)

if __name__ == "__main__":
    main()
