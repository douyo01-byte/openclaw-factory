from __future__ import annotations
import os
import re
import sys
import html
import sqlite3
import urllib.request
from pathlib import Path

DB = os.environ.get("DB_PATH") or f"{Path.home()}/AI/openclaw-factory/data/openclaw.db"
ROOT = Path.home() / "AI" / "openclaw-factory-daemon"
HTML_DIR = ROOT / "data" / "telegram_os_html"
HTML_DIR.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0"

def db():
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

def fetch_url(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
    for enc in ("utf-8", "utf-8-sig", "cp932", "shift_jis", "latin-1"):
        try:
            return raw.decode(enc)
        except Exception:
            pass
    return raw.decode("utf-8", errors="ignore")

def uniq(xs):
    out = []
    seen = set()
    for x in xs:
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out

def normalize_url_text(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\r", "\n")
    s = re.sub(r'https?:\s*/\s*/', lambda m: m.group(0).replace(" ", ""), s)
    s = re.sub(r'\s+', ' ', s)
    s = s.replace('https:// ', 'https://').replace('http:// ', 'http://')
    s = s.replace('/ ', '/').replace(' ?', '?').replace('? ', '?')
    s = s.replace(' &', '&').replace('& ', '&').replace(' =', '=').replace('= ', '=')
    s = s.replace(' :', ':').replace(': ', ':')
    return s


def pick_working_image_urls(urls: list[str]) -> list[str]:
    import requests
    out = []
    seen = set()
    for u in urls:
        if not u:
            continue
        u = u.strip().replace("http://", "https://", 1)
        if u in seen:
            continue
        seen.add(u)
        try:
            r = requests.get(u, timeout=15, stream=True, headers={"User-Agent":"Mozilla/5.0"})
            ctype = (r.headers.get("content-type") or "").lower()
            if r.status_code == 200 and ("image/" in ctype or u.lower().endswith((".png",".jpg",".jpeg",".webp",".avif"))):
                out.append(u)
        except Exception:
            pass
    return out
def image_urls_from_artifact(text: str) -> list[str]:
    s = normalize_url_text(text or "")
    urls = re.findall(r'https?://[A-Za-z0-9_\-./?&=%#:~]+', s)
    out = []
    for u in urls:
        lu = u.lower().rstrip('.,)')
        if any(k in lu for k in [".jpg", ".jpeg", ".png", ".webp", ".avif", "cdn/shop/files", "cdn/shop/t/files"]):
            out.append(lu)
    return uniq(out)

def product_url(job) -> str:
    s = (job["request_text"] or "") + "\n" + (job["target_object"] or "")
    m = re.search(r'https?://[^\s]+', s)
    if m:
        return m.group(0).rstrip('.,)')
    return "https://kuu-medic.com/products/educate-b"

def image_urls_from_product_page(url: str) -> list[str]:
    page = fetch_url(url)
    vals = []
    for pat in [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'https://[^"\']+cdn/shop/files/[^"\']+',
        r'https://[^"\']+cdn/shop/t/files/[^"\']+',
    ]:
        vals += re.findall(pat, page, re.I)
    cleaned = []
    for u in vals:
        u = u.replace("\\/", "/").strip()
        if u.startswith("//"):
            u = "https:" + u
        cleaned.append(u)
    cleaned = uniq(cleaned)
    preferred = []
    rest = []
    for u in cleaned:
        lu = u.lower()
        if "fit_cover" in lu or "educate" in lu or "bb" in lu:
            preferred.append(u)
        else:
            rest.append(u)
    return uniq(preferred + rest)

def lines_after_heading(md: str, heading: str) -> list[str]:
    if not md:
        return []
    out = []
    hit = False
    for line in md.splitlines():
        t = line.strip()
        if t == heading:
            hit = True
            continue
        if hit and t.startswith("## "):
            break
        if hit and t:
            out.append(t)
    return out

def prose(md: str, heading_a: str, heading_b: str = "") -> str:
    for h in [heading_a, heading_b]:
        if not h:
            continue
        vals = []
        for line in lines_after_heading(md, h):
            if line.strip().startswith("- "):
                continue
            vals.append(line.strip())
        if vals:
            return " ".join(vals).strip()
    return ""

def bullets(md: str, heading_a: str, heading_b: str = "") -> list[str]:
    for h in [heading_a, heading_b]:
        if not h:
            continue
        vals = []
        for line in lines_after_heading(md, h):
            t = line.strip()
            if t.startswith("- "):
                vals.append(t[2:].strip())
        if vals:
            return vals
    return []

def render_cards(items: list[str]) -> str:
    return "".join(f'<div class="benefit-card">{html.escape(x)}</div>' for x in items if x)

def render_list(items: list[str]) -> str:
    if not items:
        return ""
    return "<ul>" + "".join(f"<li>{html.escape(x)}</li>" for x in items) + "</ul>"

def svg_bg_data(label: str, c1="#efe4da", c2="#fbf7f2", c3="#d7bfae") -> str:
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1400" viewBox="0 0 1200 1400">
<defs><linearGradient id="g" x1="0" x2="1" y1="0" y2="1">
<stop offset="0%" stop-color="{c1}"/><stop offset="100%" stop-color="{c2}"/>
</linearGradient></defs>
<rect width="1200" height="1400" fill="url(#g)"/>
<circle cx="180" cy="240" r="180" fill="{c3}" opacity="0.12"/>
<circle cx="1000" cy="260" r="200" fill="{c3}" opacity="0.10"/>
<circle cx="900" cy="1100" r="260" fill="{c3}" opacity="0.10"/>
</svg>"""
    return "data:image/svg+xml;utf8," + urllib.request.quote(svg)

def hero_html(name: str, img_url: str) -> str:
    bg = svg_bg_data(name)
    if img_url:
        return f'''
<div class="hero-visual" style="background-image:url('{bg}')">
  <img class="hero-product" src="{html.escape(img_url)}" alt="{html.escape(name)}">
</div>'''
    return f'''
<div class="hero-visual placeholder" style="background-image:url('{bg}')">
  <div class="placeholder-over">PRODUCT VISUAL AREA</div>
  <div class="placeholder-name">{html.escape(name)}</div>
</div>'''

def gallery_html(name: str, img_url: str, tone: str) -> str:
    bg = svg_bg_data(name, "#f5eadf" if tone == "warm" else "#f3eee9", "#fcf8f4", "#ceb6a2")
    if img_url:
        return f'''
<div class="gallery-item" style="background-image:url('{bg}')">
  <img class="gallery-product" src="{html.escape(img_url)}" alt="{html.escape(name)}">
</div>'''
    return f'''
<div class="gallery-item placeholder-small" style="background-image:url('{bg}')">
  <div>{html.escape(name)}</div>
</div>'''


def faq_html() -> str:
    items = [
        ("厚塗り感は出やすい？", "重たさを出しすぎず、肌印象を自然に整える方向で見せる構成です。"),
        ("どんな日のベースメイクに向いている？", "忙しい朝や、軽やかに整えたい日に取り入れやすい見せ方です。"),
        ("使用量の目安は？", "顔全体に少量ずつのばしながら調整する使い方を前提に案内します。"),
        ("スキンケア後すぐ使える？", "スキンケア後、肌になじんだタイミングで使う流れを想定しています。"),
        ("乾燥が気になる時でも使いやすい？", "しっとり感と心地よさを意識したベースメイク発想として訴求します。"),
    ]
    out = ['<section class="section"><div class="card"><h2>よくある質問</h2><div class="faq-list">']
    for q, a in items:
        out.append(f'<div class="faq-item"><div class="faq-q">{html.escape(q)}</div><div class="faq-a">{html.escape(a)}</div></div>')
    out.append('</div></div></section>')
    return "".join(out)

def spec_html(name: str) -> str:
    rows = [
        ("カテゴリ", "BB下地 / ベースメイク"),
        ("訴求軸", "自然なツヤ / 均一なトーン / しっとり感"),
        ("使用シーン", "朝の時短メイク / 毎日使い / 軽く整えたい日"),
        ("仕上がり方針", "厚塗り感を抑えて肌印象を整える"),
        ("見せ方", f"{name} の商品画像を主役にしたLP構成"),
    ]
    out = ['<section class="section"><div class="card"><h2>商品スペック</h2><div class="spec-list">']
    for k, v in rows:
        out.append(f'<div class="spec-row"><div class="spec-key">{html.escape(k)}</div><div class="spec-val">{html.escape(v)}</div></div>')
    out.append('</div></div></section>')
    return "".join(out)

def pre_cta_html() -> str:
    return """
<section class="section">
  <div class="card pre-cta">
    <h2>整えるだけで、印象は変わる。</h2>
    <p>厚塗りで隠すのではなく、自然に整って見えることを大切にしたい方へ。educate B は、毎日のベースメイクを重たくしすぎず、心地よく続けやすい方向へ寄せた提案です。</p>
    <p>まずは商品詳細を確認して、自分の肌印象に合う使い方を見つけてください。</p>
  </div>
</section>
"""

def long_benefit_html() -> str:
    blocks = [
        ("自然なツヤ", "つくり込みすぎず、素肌が整って見える印象へ寄せる。"),
        ("均一なトーン", "重ねすぎないまま、ばらつきを感じさせにくい見え方を目指す。"),
        ("しっとり感", "乾燥が気になる日でも使いやすい心地よさを意識する。"),
    ]
    out = ['<section class="section"><div class="section-grid">']
    for t, d in blocks:
        out.append(f'<div class="card"><h2>{html.escape(t)}</h2><p>{html.escape(d)}</p></div>')
    out.append('</div></section>')
    return "".join(out)

def usage_scene_html() -> str:
    scenes = [
        ("朝の時短メイク", "短い時間でも肌印象を整えたい朝に。"),
        ("軽く仕上げたい日", "重たさを出したくない日でも、きちんと感は保ちたい時に。"),
        ("乾燥感を避けたい日", "心地よさを意識しながらベースメイクを整えたい場面に。"),
    ]
    out = ['<section class="section"><div class="section-grid">']
    for t, d in scenes:
        out.append(f'<div class="card"><h2>{html.escape(t)}</h2><p>{html.escape(d)}</p></div>')
    out.append('</div></section>')
    return "".join(out)

def build(job_id: int):
    c = db()
    job = c.execute("select * from conversation_jobs where id=?", (job_id,)).fetchone()
    if not job:
        raise RuntimeError("job_not_found")
    fv = fetch_latest(c, job_id, "fv_copy_final_v3_markdown") or fetch_latest(c, job_id, "fv_copy_final_v2_markdown")
    outline = fetch_latest(c, job_id, "section_outline_v3_markdown") or fetch_latest(c, job_id, "section_outline_v2_markdown")
    body = fetch_latest(c, job_id, "section_body_v3_markdown") or fetch_latest(c, job_id, "section_body_v2_markdown")
    final_lp = fetch_latest(c, job_id, "lp_final_v3_markdown") or fetch_latest(c, job_id, "lp_final_v2_markdown")
    img_art = fetch_latest(c, job_id, "product_image_urls_markdown")

    if not fv or not body or not final_lp:
        missing = []
        if not fv:
            missing.append("fv_copy_final_v3_markdown_or_v2")
        if not outline:
            missing.append("section_outline_v3_markdown_or_v2")
        if not body:
            missing.append("section_body_v3_markdown_or_v2")
        if not final_lp:
            missing.append("lp_final_v3_markdown_or_v2")
        raise RuntimeError("required_artifact_missing:" + ",".join(missing))

    name = (job["target_object"] or "educate B").strip() or "educate B"
    prod_url = product_url(job)

    art_urls = image_urls_from_artifact(img_art["artifact_body"] if img_art else "")
    art_urls = pick_working_image_urls(art_urls)
    if art_urls:
        art_urls = [art_urls[0], art_urls[0], art_urls[0], art_urls[0]]
    if art_urls:
        art_urls = [art_urls[0], art_urls[0], art_urls[0], art_urls[0]]

    page_urls = image_urls_from_product_page(prod_url)
    urls = uniq(art_urls + page_urls)

    hero = urls[0] if len(urls) > 0 else ""
    sub1 = urls[1] if len(urls) > 1 else hero
    sub2 = urls[2] if len(urls) > 2 else hero

    main_copy = prose(fv["artifact_body"], "## メ イ ン コ ピ ー", "## メインコピー")
    sub_copy = prose(fv["artifact_body"], "## サ ブ コ ピ ー", "## サブコピー")
    benefits = bullets(fv["artifact_body"], "## ベ ネ フ ィ ッ ト 表 示", "## ベネフィット表示")
    cta = prose(fv["artifact_body"], "## CTA案") or "商品詳細を見る"
    subline = prose(fv["artifact_body"], "## 補 助 コ ピ ー", "## 補助コピー")

    concern = prose(body["artifact_body"], "## 2. こ ん な 方 へ", "## 2. こんな方へ")
    value = prose(body["artifact_body"], "## 3. 仕 上 が り 価 値", "## 3. 仕上がり価値")
    ingredient = prose(body["artifact_body"], "## 4. 成 分 発 想", "## 4. 成分発想")
    usage = prose(body["artifact_body"], "## 5. 使 用 イ メ ー ジ", "## 5. 使用イメージ")
    summary = prose(body["artifact_body"], "## 6. 商 品 要 約", "## 6. 商品要約")
    closing = prose(body["artifact_body"], "## 7. ク ロ ー ジ ン グ CTA", "## 7. クロージングCTA")

    target_items = [
        "厚塗り感は出したくない",
        "肌印象を自然に整えたい",
        "乾燥感を避けたい",
    ]
    if outline:
        tmp = bullets(outline["artifact_body"], "## 2. こ ん な 悩 み を 持 つ 方 へ", "## 2. こんな悩みを持つ方へ")
        if tmp:
            target_items = tmp[:3]

    html_text = f'''<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(name)} LP v3</title>
<style>
:root {{
  --bg:#f7f2ed;
  --paper:#fffdfa;
  --ink:#1f1f22;
  --sub:#6f6660;
  --line:#eadfd6;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0;
  font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Yu Gothic","Noto Sans JP",sans-serif;
  background:var(--bg);
  color:var(--ink);
  line-height:1.75;
}}
img {{ display:block; max-width:100%; }}
.wrap {{
  width:min(100%,1180px);
  margin:0 auto;
  padding:28px 18px 84px;
}}
.hero {{
  padding:30px 0 40px;
}}
.hero-grid {{
  display:grid;
  grid-template-columns:1.05fr .95fr;
  gap:34px;
  align-items:center;
}}
.eyebrow {{
  font-size:14px;
  letter-spacing:.14em;
  color:#93776d;
  margin-bottom:18px;
}}
h1 {{
  margin:0 0 18px;
  font-size:clamp(42px,7vw,82px);
  line-height:1.06;
  letter-spacing:-0.04em;
}}
.lead {{
  margin:0 0 22px;
  color:var(--sub);
  font-size:clamp(18px,2.5vw,30px);
}}
.benefit-row {{
  display:grid;
  grid-template-columns:repeat(3,1fr);
  gap:16px;
  margin:26px 0 20px;
}}
.benefit-card {{
  background:rgba(255,255,255,.8);
  border:1px solid var(--line);
  border-radius:24px;
  padding:20px 18px;
  min-height:110px;
  display:flex;
  align-items:center;
  font-size:18px;
}}
.cta {{
  display:inline-flex;
  align-items:center;
  justify-content:center;
  min-height:68px;
  padding:0 30px;
  border-radius:999px;
  background:#1f1f22;
  color:#fff;
  text-decoration:none;
  font-size:20px;
  font-weight:800;
  letter-spacing:.01em;
  margin-top:4px;
}}
.subline {{
  margin-top:18px;
  color:#7f726c;
  font-size:16px;
}}
.hero-visual {{
  min-height:560px;
  border-radius:34px;
  border:1px solid var(--line);
  background-size:cover;
  background-position:center;
  position:relative;
  overflow:hidden;
  display:flex;
  align-items:center;
  justify-content:center;
}}
.hero-product {{
  width:86%;
  max-width:520px;
  object-fit:contain;
  filter:drop-shadow(0 20px 30px rgba(0,0,0,.12));
}}
.placeholder {{
  flex-direction:column;
  color:#997f74;
  text-align:center;
}}
.placeholder-over {{
  font-size:18px;
  letter-spacing:.14em;
  margin-bottom:18px;
}}
.placeholder-name {{
  font-size:62px;
  font-weight:800;
  line-height:1.08;
}}
.section {{
  padding:58px 0;
}}
.section-grid {{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:28px;
}}
.card {{
  background:var(--paper);
  border:1px solid var(--line);
  border-radius:30px;
  padding:30px;
}}
.card h2 {{
  margin:0 0 16px;
  font-size:clamp(28px,4vw,52px);
  line-height:1.12;
  letter-spacing:-0.03em;
}}
.card p, .card li {{
  font-size:18px;
}}
.card ul {{
  margin:16px 0 0;
  padding-left:1.2em;
}}
.gallery-wrap {{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:18px;
  margin-top:18px;
}}
.gallery-item {{
  min-height:280px;
  border-radius:24px;
  border:1px solid var(--line);
  background-size:cover;
  background-position:center;
  display:flex;
  align-items:center;
  justify-content:center;
  overflow:hidden;
}}
.gallery-product {{
  width:82%;
  object-fit:contain;
  filter:drop-shadow(0 14px 24px rgba(0,0,0,.10));
}}
.placeholder-small {{
  color:#9b7f75;
  font-size:28px;
  font-weight:700;
}}
.summary-grid {{
  display:grid;
  grid-template-columns:.92fr 1.08fr;
  gap:28px;
  align-items:center;
}}
.summary-shot {{
  min-height:460px;
  border-radius:30px;
  border:1px solid var(--line);
  background-size:cover;
  background-position:center;
  display:flex;
  align-items:center;
  justify-content:center;
  overflow:hidden;
  background-image:url('{svg_bg_data(name.upper(), "#f0e6dc", "#faf5ef", "#cfb7a3")}');
}}
.summary-shot img {{
  width:84%;
  object-fit:contain;
  filter:drop-shadow(0 16px 26px rgba(0,0,0,.12));
}}
@media (max-width:900px) {{
  .hero-grid,
  .section-grid,
  .summary-grid,
  .benefit-row,
  .gallery-wrap {{
    grid-template-columns:1fr;
  }}
  .hero-visual {{ min-height:420px; }}
  .summary-shot {{ min-height:340px; }}
  h1 {{ font-size:clamp(40px,12vw,66px); }}
}}
</style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="hero-grid">
        <div>
          <div class="eyebrow">BB BASE MAKE / {html.escape(name.upper())}</div>
          <h1>{html.escape(main_copy)}</h1>
          <p class="lead">{html.escape(sub_copy)}</p>
          <div class="benefit-row">{render_cards(benefits)}</div>
          <a class="cta" href="{html.escape(prod_url)}" target="_blank" rel="noopener noreferrer">{html.escape(cta)}</a>
          <div class="subline">{html.escape(subline)}</div>
        </div>
        <div>{hero_html(name, hero)}</div>
      </div>
    </section>

    <section class="section">
      <div class="section-grid">
        <div class="card">
          <h2>こんな方へ</h2>
          <p>{html.escape(concern)}</p>
          {render_list(target_items)}
        </div>
        <div class="card">
          <h2>{html.escape(name)} の価値</h2>
          <p>{html.escape(value)}</p>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-grid">
        <div class="card">
          <h2>成分発想</h2>
          <p>{html.escape(ingredient)}</p>
        </div>
        <div class="card">
          <h2>使用イメージ</h2>
          <p>{html.escape(usage)}</p>
          <div class="gallery-wrap">
            {gallery_html(name, sub1, "warm")}
            {gallery_html(name, sub2, "soft")}
            {gallery_html(name, hero, "warm")}
            {gallery_html(name, sub1, "soft")}
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="summary-grid">
        <div class="summary-shot">
          {f'<img src="{html.escape(hero)}" alt="{html.escape(name)}">' if hero else f'<div class="placeholder-name" style="font-size:48px;color:#9a8174;">{html.escape(name)}</div>'}
        </div>
        <div class="card">
          <h2>商品要約</h2>
          <p>{html.escape(summary)}</p>
          <div style="height:22px"></div>
          <a class="cta" href="{html.escape(prod_url)}" target="_blank" rel="noopener noreferrer">{html.escape(cta)}</a>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="card">
        <h2>クロージング</h2>
        <p>{html.escape(closing)}</p>
      </div>
    </section>
  </div>
</body>
</html>
'''

    out = HTML_DIR / f"job_{job_id}_lp_v3.html"
    out.write_text(html_text, encoding="utf-8")

    c.execute("""
        delete from conversation_artifacts
        where job_id=?
          and artifact_type='lp_html_export_v3'
    """, (job_id,))
    c.execute("""
        insert into conversation_artifacts(
          job_id, artifact_type, artifact_title, artifact_body, artifact_path, version, created_at
        ) values(?,?,?,?,?,?,datetime('now'))
    """, (
        job_id,
        "lp_html_export_v3",
        "lp_html_export_v3",
        f"HTMLを 書 き 出 し ま し た : {out}",
        str(out),
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
    print(f"reference_rebuild_v3_done job_id={job_id} images={len(urls)} path={out}", flush=True)

def main():
    job_id = int(sys.argv[1]) if len(sys.argv) > 1 else 19
    build(job_id)

if __name__ == "__main__":
    main()
