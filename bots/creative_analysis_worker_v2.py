#!/usr/bin/env python3
import json
import os
import re
import sqlite3
import subprocess
from pathlib import Path

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

def normalize_text(text: str) -> str:
    text = text.replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"(?<=[ぁ-んァ-ン一-龥A-Za-z0-9])\s+(?=[ぁ-んァ-ン一-龥A-Za-z0-9])", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def strip_html(html: str) -> str:
    s = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    s = re.sub(r"(?is)<style.*?>.*?</style>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</p>|</div>|</li>|</section>|</h[1-6]>", "\n", s)
    s = re.sub(r"(?s)<.*?>", " ", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&")
    return normalize_text(s)

def extract_between(text: str, start: str, end: str):
    m = re.search(re.escape(start) + r"(.*?)" + re.escape(end), text, re.S)
    return normalize_text(m.group(1)) if m else ""

def extract_bullets(text: str, patterns):
    found = []
    for p in patterns:
        for m in re.finditer(p, text, re.I):
            v = normalize_text(m.group(1))
            if v and v not in found:
                found.append(v)
    return found

def fetch_source(url: str, job_id: int) -> str:
    out = FETCH_DIR / f"job_{job_id}.html"
    subprocess.run([str(FETCH_SCRIPT), url, str(out)], check=True)
    return out.read_text(encoding="utf-8", errors="ignore")

def parse_product(job, ctx):
    target = job["target_object"] or "対象商品"
    request_text = normalize_text(job["request_text"] or "")
    urls = []
    context = {}
    if isinstance(ctx, dict):
        context = ctx.get("context", {}) if isinstance(ctx.get("context", {}), dict) else {}
        urls = context.get("urls", []) or []

    source_url = urls[0] if urls else ""
    html = fetch_source(source_url, job["id"]) if source_url else ""
    plain = strip_html(html)

    title = ""
    m = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
    if m:
        title = normalize_text(m.group(1))

    ingredients = []
    for kw in ["ザクロ", "EGF", "ビタミンE", "セラミド", "水添レシチン", "コレステロール", "フィトステロール", "アーモンド油", "ヒマワリ種子油"]:
        if kw in plain and kw not in ingredients:
            ingredients.append(kw)

    claims = []
    claim_candidates = [
        "自然なツヤ", "均一なトーン", "毛穴", "くすみ", "軽いテクスチャー", "しっとり", "保湿", "BBクリーム", "下地"
    ]
    for kw in claim_candidates:
        if kw in plain and kw not in claims:
            claims.append(kw)

    if not claims:
        claims = ["素肌印象を整える", "乾燥を防ぎながら使いやすい", "美容成分発想のベースメイク"]

    angles = [
        {
            "name": "素肌格上げBB",
            "target": "厚塗り感なく肌印象を整えたい人",
            "hook": "隠すより整える。軽さとカバー感の両立。",
        },
        {
            "name": "乾燥に強い美容下地",
            "target": "日中の乾燥やつっぱり感が気になる人",
            "hook": "しっとり感を保ちながらベースを整える。",
        },
        {
            "name": "美容成分発想ベース",
            "target": "仕上がりだけでなく成分も重視する人",
            "hook": "メイク時間を美容時間に寄せる発想。",
        },
    ]

    return {
        "target": target,
        "request_text": request_text,
        "source_url": source_url,
        "source_title": title,
        "ingredients": ingredients,
        "claims": claims,
        "angles": angles,
        "plain_excerpt": plain[:3000],
    }

def build_lp_variant(data, angle):
    target = data["target"]
    claims = data["claims"]
    ingredients = data["ingredients"]
    claim_line = " / ".join(claims[:4]) if claims else "軽さ・ツヤ・カバー感"
    ing_line = "、".join(ingredients[:5]) if ingredients else "美容成分"

    name = angle["name"]
    hook = angle["hook"]
    who = angle["target"]

    parts = []
    parts.append(f"# {target} LP案: {name}")
    parts.append("")
    parts.append("## ファーストビュー")
    parts.append(hook)
    parts.append("")
    parts.append("### サブコピー")
    parts.append(f"{claim_line}を意識した、毎日使いやすいベースメイク提案。")
    parts.append("")
    parts.append("## こんな方へ")
    parts.append(f"- {who}")
    parts.append("- ベースメイクを重くしたくない")
    parts.append("- 自然に整った印象を目指したい")
    parts.append("")
    parts.append("## educate Bの着眼点")
    for c in claims[:5]:
        parts.append(f"- {c}")
    parts.append("")
    parts.append("## 成分訴求")
    parts.append(f"- 主な着眼成分: {ing_line}")
    parts.append("- 現サイトで確認できた成分・訴求をもとに構成")
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
        (job_id, artifact_type, artifact_title, normalize_text(artifact_body), "", version)
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
