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
.label{{display:inline-block;padding:6px 10px;border:1px solid #3b3f67;border-radius:999px;color:#d7d9f3;font-size:12px;margin-bottom:10px}}
</style>
</head>
<body>
<div class="wrap">
  <div class="sec">
    <div class="label">{label}</div>
    <h1>{hook}</h1>
    <p class="sub">{sub}</p>
    <p>{promise}</p>
    <a class="btn" href="order.html?v={variant}">{cta}</a>
  </div>

  <div class="sec">
    <h2>{section_title}</h2>
    <div class="point">{point1}</div>
    <div class="point">{point2}</div>
    <div class="point">{point3}</div>
  </div>

  <div class="sec">
    <h2>{free_title}</h2>
    <div class="point">{free1}</div>
    <div class="point">{free2}</div>
    <div class="point">{free3}</div>
  </div>

  <div class="sec">
    <p class="price">{price_line}</p>
    <a class="btn" href="order.html?v={variant}">{bottom_cta}</a>
  </div>
</div>
</body>
</html>
"""

VARIANTS = {
    "A": {
        "label": "共感して整理するタイプ",
        "hook": "気持ちが見えない恋愛ほど、まずは自分の迷いを整理することが大切です",
        "sub": "不安をあおるためではなく、気持ちを落ち着かせて次の一手を考えるための恋愛診断です。",
        "promise": "無料で、今の関係の見え方と、焦って動くべきかどうかの整理ができます。",
        "cta": "気持ちを整理してみる",
        "section_title": "こんな迷いがある人向けです",
        "point1": "連絡したいけど、今送るのが正解か分からない",
        "point2": "相手の気持ちが離れていないか不安になる",
        "point3": "感情のまま動かず、一度落ち着いて考えたい",
        "free_title": "無料で確認できること",
        "free1": "今の関係をどう見ればよいか",
        "free2": "今すぐ動くべきか、少し待つべきか",
        "free3": "続きを見る必要がある状態かどうか",
        "price_line": "詳しい読み解きと行動のヒント：760円",
        "bottom_cta": "無料で気持ちを整理する",
    },
    "B": {
        "label": "状況を見極めるタイプ",
        "hook": "連絡するべきか、少し待つべきか。恋愛の状況を整理して見極めます",
        "sub": "感情だけで判断するのではなく、今の距離感や動くタイミングを冷静に考えるための診断です。",
        "promise": "無料結果では、今の関係の見え方と、次の一手を決めるための判断材料を確認できます。",
        "cta": "今の状況を確認する",
        "section_title": "こんな時に使えます",
        "point1": "今の距離感を客観的に見たい",
        "point2": "復縁や片思いで、動くタイミングを考えたい",
        "point3": "相手の反応に振り回されずに整理したい",
        "free_title": "無料診断で分かること",
        "free1": "今の関係をどう受け止めるべきか",
        "free2": "焦るべき場面か、落ち着くべき場面か",
        "free3": "続きで深掘りする価値があるか",
        "price_line": "詳しい読み解きと行動の選び方：760円",
        "bottom_cta": "無料で状況を確認する",
    },
    "C": {
        "label": "次の一手を決めるタイプ",
        "hook": "恋愛で迷った時は、感情より先に“次の一手”を整理すると動きやすくなります",
        "sub": "何をするかを決める前に、今の関係の流れと、自分に合う動き方を整理するための診断です。",
        "promise": "無料で、今の状況に対してどう動くべきかの方向性を確認できます。",
        "cta": "次の一手を確認する",
        "section_title": "こんな人に向いています",
        "point1": "今連絡していいのか判断したい",
        "point2": "距離の取り方を間違えたくない",
        "point3": "自分に合う動き方のヒントが欲しい",
        "free_title": "無料で見えること",
        "free1": "今の流れの中で気をつけたいこと",
        "free2": "動くならどんな方向性が合うか",
        "free3": "760円で続きを見る価値があるか",
        "price_line": "行動のヒントを詳しく見る：760円",
        "bottom_cta": "無料で次の一手を見る",
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
        """, ("恋愛", f"rewriter_v3_distinct variant={variant}", str(out_path), 0))

    con.commit()
    con.close()
    print("lp_rewriter_v3_distinct_done", flush=True)

if __name__ == "__main__":
    main()
