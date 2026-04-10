import os
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))
ROOT = Path(os.path.expanduser("~/AI/openclaw-factory-daemon"))
OUT = ROOT / "data/lp_research"

HTML_TMPL = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{{font-family:sans-serif;background:#0f1020;color:#fff;padding:20px;line-height:1.7}}
.wrap{{max-width:780px;margin:0 auto}}
.sec{{background:#17192d;border:1px solid #2a2d4a;border-radius:18px;padding:20px;margin-bottom:18px}}
.btn{{display:block;width:100%;padding:16px;background:#ff4fa3;color:#fff;text-align:center;border-radius:999px;text-decoration:none;font-weight:bold;box-sizing:border-box}}
.price{{font-size:26px;color:#ffd36b;font-weight:bold}}
</style>
</head>
<body>
<div class="wrap">
  <div class="sec">
    <h1>{hook}</h1>
    <p>{problem}</p>
    <p>{promise}</p>
    <a class="btn" href="/fortune/order.html">{cta}</a>
  </div>
  <div class="sec">
    <h2>この先で分かること</h2>
    <ul>
      <li>相手の本音</li>
      <li>今やるべき行動3つ</li>
      <li>やってはいけないNG行動</li>
    </ul>
  </div>
  <div class="sec">
    <p class="price">{price_hint}</p>
    <a class="btn" href="/fortune/order.html">無料で今の状況を確認する</a>
  </div>
</div>
</body>
</html>
"""

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    niche = "恋愛"
    row = cur.execute("""
    select hook, problem, promise, cta, price_hint
    from lp_patterns
    where notes like '%恋愛%'
    order by score desc, id desc
    limit 1
    """).fetchone()

    if not row:
        print("no_pattern", flush=True)
        return

    hook, problem, promise, cta, price_hint = row
    if not cta:
        cta = "無料で今の状況を確認する"
    if not price_hint:
        price_hint = "続きを見る：760円"

    html = HTML_TMPL.format(
        title="恋愛AI鑑定 改善版",
        hook=hook or "連絡するべきか、待つべきか。今の答えを無料で整理します",
        problem=problem or "相手の気持ちが見えない。動くのが怖い。でも、このまま何もしないのも不安。",
        promise=promise or "まずは無料で現状を確認できます。",
        cta=cta,
        price_hint=price_hint
    )

    out_path = OUT / "rewritten_love_lp.html"
    out_path.write_text(html, encoding="utf-8")

    cur.execute("""
    insert into lp_rewrites(niche, input_context, output_path, score)
    values(?,?,?,?)
    """, (niche, "top_pattern", str(out_path), 0))

    con.commit()
    con.close()
    print(f"lp_rewritten:{out_path}", flush=True)

if __name__ == "__main__":
    main()
