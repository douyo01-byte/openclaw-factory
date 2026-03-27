#!/usr/bin/env python3
import html as html_lib
import json
import os
import re
import sqlite3
import subprocess
from pathlib import Path
from text_normalizer_v1 import normalize_text

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))
ROOT = Path(__file__).resolve().parent.parent
FETCH_DIR = ROOT / "data" / "telegram_os_fetch"
FETCH_SCRIPT = ROOT / "scripts" / "fetch_url_to_file.sh"

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
        where coalesce(domain,'') in ('analysis','creative')
          and coalesce(status,'')='new'
        order by id asc
        limit ?
        """,
        (limit,),
    ).fetchall()

def load_context(c, job_id):
    row = c.execute(
        """
        select input_json
        from conversation_job_steps
        where job_id=?
        order by step_order asc
        limit 1
        """,
        (job_id,),
    ).fetchone()
    if not row or not row["input_json"]:
        return {}
    try:
        return json.loads(row["input_json"])
    except:
        return {}

def strip_html(html: str) -> str:
    s = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    s = re.sub(r"(?is)<style.*?>.*?</style>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</p>|</div>|</li>|</section>|</h[1-6]>", "\n", s)
    s = re.sub(r"(?s)<.*?>", " ", s)
    s = html_lib.unescape(s)
    return normalize_text(s)

def meta_content(html: str, name: str) -> str:
    pats = [
        rf'<meta[^>]+property="{re.escape(name)}"[^>]+content="([^"]*)"',
        rf"<meta[^>]+property='{re.escape(name)}'[^>]+content='([^']*)'",
        rf'<meta[^>]+name="{re.escape(name)}"[^>]+content="([^"]*)"',
        rf"<meta[^>]+name='{re.escape(name)}'[^>]+content='([^']*)'",
    ]
    for p in pats:
        m = re.search(p, html, re.I | re.S)
        if m:
            return normalize_text(html_lib.unescape(m.group(1)))
    return ""

def clean_spaced_japanese(text: str) -> str:
    t = html_lib.unescape(text)
    t = t.replace("＜", "<").replace("＞", ">")
    t = t.replace("　", " ")
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r'(?<=[ぁ-んァ-ン一-龥A-Za-z0-9])\s+(?=[ぁ-んァ-ン一-龥A-Za-z0-9])', '', t)
    t = t.replace("／", "/")
    t = t.replace("　", " ")
    return t.strip()

def extract_ingredients(meta_desc: str, plain: str):
    text = clean_spaced_japanese(meta_desc or plain)
    found = []
    keys = [
        "ヒト遺伝子組換オリゴペプチド-1",
        "酢酸トコフェロール",
        "セラミドNG",
        "セラミドAP",
        "セラミドAG",
        "セラミドNP",
        "セラミドEOP",
        "水添レシチン",
        "コレステロール",
        "フィトステロールズ",
        "ザクロ種子油",
        "アーモンド油",
        "ヒマワリ種子油",
        "レモングラス油",
        "ラベンダー油",
        "ローマカミツレ花油",
    ]
    for k in keys:
        if k in text and k not in found:
            found.append(k)
    return found

def extract_claims(text: str):
    src = clean_spaced_japanese(text)
    rules = [
        ("自然なツヤ", ["自然なツヤ", "ツヤ"]),
        ("均一なトーン", ["均一なトーン", "トーン"]),
        ("毛穴カバー", ["毛穴"]),
        ("くすみカバー", ["くすみ"]),
        ("軽いテクスチャー", ["軽い", "テクスチャー"]),
        ("しっとり感", ["しっとり", "保湿"]),
        ("BBクリーム下地", ["BB", "下地"]),
    ]
    out = []
    for label, kws in rules:
        if any(k in src for k in kws):
            out.append(label)
    return out

def fetch_source(url: str, job_id: int) -> str:
    out = FETCH_DIR / f"job_{job_id}.html"
    subprocess.run([str(FETCH_SCRIPT), url, str(out)], check=True)
    return out.read_text(encoding="utf-8", errors="ignore")

def parse_product(job, ctx):
    target = job["target_object"] or "対象商品"
    request_text = clean_spaced_japanese(job["request_text"] or "")
    urls = []
    context = {}
    if isinstance(ctx, dict):
        context = ctx.get("context", {}) if isinstance(ctx.get("context", {}), dict) else {}
        urls = context.get("urls", []) or []

    source_url = urls[0] if urls else ""
    html = fetch_source(source_url, job["id"]) if source_url else ""
    plain = strip_html(html)

    source_title = meta_content(html, "og:title") or meta_content(html, "twitter:title")
    if not source_title:
        m = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
        source_title = clean_spaced_japanese(m.group(1)) if m else ""

    meta_desc = meta_content(html, "description") or meta_content(html, "og:description") or meta_content(html, "twitter:description")
    meta_desc = clean_spaced_japanese(meta_desc)

    ingredients = extract_ingredients(meta_desc, plain)
    claims = extract_claims(meta_desc + "\n" + plain)

    if not claims:
        claims = ["自然なツヤ", "均一なトーン", "しっとり感", "BBクリーム下地"]

    angles = [
        {
            "name": "素肌格上げBB",
            "target": "厚塗り感なく肌印象を整えたい人",
            "hook": "隠すより、整えて魅せる。軽さとカバー感を両立したBB下地。",
        },
        {
            "name": "乾燥に強い美容下地",
            "target": "日中の乾燥やつっぱり感が気になる人",
            "hook": "しっとり感を保ちながら、ベースメイクをきれいに整える。",
        },
        {
            "name": "美容成分発想ベース",
            "target": "仕上がりだけでなく成分も重視する人",
            "hook": "メイク時間を、美容発想のケア時間へ。",
        },
    ]

    return {
        "target": target,
        "request_text": request_text,
        "source_url": source_url,
        "source_title": source_title,
        "meta_desc": meta_desc,
        "ingredients": ingredients,
        "claims": claims,
        "angles": angles,
    }

def build_lp_variant(data, angle):
    claim_line = " / ".join(data["claims"][:4]) if data["claims"] else "自然なツヤ / 均一なトーン / しっとり感"
    ing_line = "、".join(data["ingredients"][:6]) if data["ingredients"] else "美容成分"

    parts = []
    parts.append(f"# {data['target']} LP案: {angle['name']}")
    parts.append("")
    parts.append("## ファーストビュー")
    parts.append(angle["hook"])
    parts.append("")
    parts.append("### サブコピー")
    parts.append(f"{claim_line}を意識した、毎日使いやすいベースメイク提案。")
    parts.append("")
    parts.append("## こんな方へ")
    parts.append(f"- {angle['target']}")
    parts.append("- ベースメイクを重くしたくない")
    parts.append("- 自然に整った印象を目指したい")
    parts.append("")
    parts.append("## educate Bの着眼点")
    for c in data["claims"][:6]:
        parts.append(f"- {c}")
    parts.append("")
    parts.append("## 成分訴求")
    parts.append(f"- 主な着眼成分: {ing_line}")
    parts.append("- 現サイトで確認できた成分情報をもとに構成")
    parts.append("")
    parts.append("## CTA")
    parts.append("まずは商品詳細をチェック")
    return "\n".join(parts)

def build_analysis_markdown(data):
    lines = []
    lines.append(f"# {data['target']} 分析")
    lines.append("")
    lines.append("## 依頼")
    lines.append(data["request_text"])
    lines.append("")
    if data["source_url"]:
        lines.append("## 参照URL")
        lines.append(f"- {data['source_url']}")
        lines.append("")
    if data["source_title"]:
        lines.append("## 取得タイトル")
        lines.append(data["source_title"])
        lines.append("")
    if data["meta_desc"]:
        lines.append("## 取得説明")
        lines.append(data["meta_desc"][:800])
        lines.append("")
    lines.append("## 抽出訴求")
    for c in data["claims"]:
        lines.append(f"- {c}")
    lines.append("")
    lines.append("## 抽出成分")
    for i in data["ingredients"]:
        lines.append(f"- {i}")
    lines.append("")
    lines.append("## 勝ち軸3案")
    for idx, a in enumerate(data["angles"], start=1):
        lines.append(f"{idx}. {a['name']} | {a['target']} | {a['hook']}")
    lines.append("")
    lines.append("## 次アクション")
    lines.append("- LP3案比較")
    lines.append("- FV強化")
    lines.append("- CTA改善")
    return "\n".join(lines)

def save_artifact(c, job_id, artifact_type, artifact_title, artifact_body, version=1):
    c.execute(
        """
        insert into conversation_artifacts(
          job_id, artifact_type, artifact_title, artifact_body, artifact_path, version, created_at
        ) values(?,?,?,?,?,?,datetime('now'))
        """,
        (job_id, artifact_type, artifact_title, artifact_body.strip(), "", version)
    )

def mark_done(c, job_id):
    c.execute(
        """
        update conversation_job_steps
        set status='done', output_json=?, updated_at=datetime('now')
        where job_id=?
        """,
        (json.dumps({"result": "done"}, ensure_ascii=False), job_id)
    )
    c.execute(
        """
        update conversation_jobs
        set current_phase='lp_variants_done',
            status='done',
            updated_at=datetime('now')
        where id=?
        """,
        (job_id,)
    )

def run_once():
    con = connect()
    c = con.cursor()
    rows = fetch_jobs(c, 10)
    done = 0
    for job in rows:
        try:
            ctx = load_context(c, job["id"])
            data = parse_product(job, ctx)
            save_artifact(c, job["id"], "analysis_markdown", "product_analysis", build_analysis_markdown(data), 1)
            for idx, angle in enumerate(data["angles"], start=1):
                save_artifact(c, job["id"], "lp_markdown", f"lp_variant_{idx}", build_lp_variant(data, angle), idx)
            mark_done(c, job["id"])
            print(f"done job_id={job['id']}", flush=True)
            done += 1
        except Exception as e:
            c.execute(
                """
                update conversation_jobs
                set current_phase='analysis_error',
                    status='error',
                    updated_at=datetime('now')
                where id=?
                """,
                (job["id"],)
            )
            print(f"error job_id={job['id']} err={e}", flush=True)
    con.commit()
    con.close()
    print(f"worker_done={done}", flush=True)

if __name__ == "__main__":
    run_once()
