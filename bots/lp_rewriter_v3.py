import os
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))
ROOT = Path(os.path.expanduser("~/AI/openclaw-factory-daemon"))
OUT = ROOT / "data/lp_research"

TMPL = """<!doctype html>
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
.sub{{color:#d7d9f3}}
.point{{background:#111427;border:1px solid #2a2d4a;border-radius:12px;padding:12px;margin:10px 0}}
</style>
</head>
<body>
<div class="wrap">
  <div class="sec">
    <h1>{hook}</h1>
    <p class="sub">{sub}</p>
    <p>{promise}</p>
    <a class="btn" href="order.html?v={variant}">{cta}</a>
  </div>

  <div class="sec">
    <h2>こんな時に使えます</h2>
    <div class="point">{point1}</div>
    <div class="point">{point2}</div>
    <div class="point">{point3}</div>
  </div>

  <div class="sec">
    <h2>無料で分かること</h2>
    <div class="point">今の状況の見え方</div>
    <div class="point">焦って動くべきかどうか</div>
    <div class="point">続きを読む価値があるか</div>
  </div>

  <div class="sec">
    <p class="price">詳しい読み解きと行動のヒント：760円</p>
    <a class="btn" href="order.html?v={variant}">まずは無料で試す</a>
  </div>
</div>
</body>
</html>
"""

VARIANTS = {
    "A": {
        "hook": "連絡するべきか、少し待つべきか。恋愛の迷いを無料で整理します",
        "sub": "相手の気持ちが見えない時ほど、焦って動くより先に状況を整理することが大切です。",
        "promise": "まずは無料で、今の関係の見え方と次の一手の考え方を確認できます。",
        "cta": "無料で今の状況を確認する",
        "point1": "今連絡していいのか迷っている",
        "point2": "相手の気持ちが離れていないか不安",
        "point3": "復縁や片思いの動き方を整理したい",
    },
    "B": {
        "hook": "気持ちが見えない恋愛ほど、先に整理すると落ち着いて動けます",
        "sub": "不安なまま動くより、今の状況を言葉にしてから判断する方が失敗しにくくなります。",
        "promise": "無料結果では、今の関係の見え方と次の一手の考え方をまとめて確認できます。",
        "cta": "無料で診断結果を見る",
        "point1": "相手の反応に振り回されてしまう",
        "point2": "今の距離感を見極めたい",
        "point3": "落ち着いて次の行動を決めたい",
    },
    "C": {
        "hook": "恋愛の不安をあおるのではなく、次の一手を落ち着いて整理するための診断です",
        "sub": "感情だけで動かず、状況を整理してから進みたい人向けの恋愛診断です。",
        "promise": "無料で今の見え方を確認し、必要なら詳しい読み解きと行動のヒントを続けて見られます。",
        "cta": "無料で試してみる",
        "point1": "今の状況を客観的に見たい",
        "point2": "連絡のタイミングを考えたい",
        "point3": "続きを見るべきか無料で判断したい",
    },
}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    for variant, d in VARIANTS.items():
        html = TMPL.format(
            title=f"恋愛AI鑑定 v3 {variant}",
            variant=variant,
            **d
        )
        out_path = OUT / f"rewritten_love_lp_{variant}.html"
        out_path.write_text(html, encoding="utf-8")

        cur.execute("""
        insert into lp_rewrites(niche, input_context, output_path, score)
        values(?,?,?,?)
        """, ("恋愛", f"rewriter_v3 variant={variant}", str(out_path), 0))

    con.commit()
    con.close()
    print("lp_rewriter_v3_done", flush=True)

if __name__ == "__main__":
    main()
