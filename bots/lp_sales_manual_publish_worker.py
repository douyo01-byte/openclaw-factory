from __future__ import annotations
import argparse
import os
import re
import sqlite3
from pathlib import Path
from bs4 import BeautifulSoup

DB = os.environ.get("DB_PATH") or f"{Path.home()}/AI/openclaw-factory/data/openclaw.db"

def db():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def section_by_eyebrow(soup, name: str):
    for sec in soup.select("section.section"):
        eb = sec.select_one(".eyebrow")
        if eb and eb.get_text(strip=True) == name:
            return sec
    return None

def append_item(soup, grid, src: str, alt: str, copy: str):
    item = soup.new_tag("div", **{"class": "item"})
    img = soup.new_tag("img")
    img["src"] = src
    img["alt"] = alt
    cap = soup.new_tag("div", **{"class": "copy"})
    cap.string = copy
    item.append(img)
    item.append(cap)
    grid.append(item)

def cleanup_old_generated(soup, keep_base: str):
    prefixes = [
        "https://douyo01-byte.github.io/telegram-os-public/generated_lp/",
        "generated_lp/",
    ]
    keep_tag = keep_base.rstrip("/").split("/")[-1]

    def should_drop(src: str) -> bool:
        if not src:
            return False
        if keep_base in src or keep_tag in src:
            return False
        return any(p in src for p in prefixes)

    for sec_name, grid_sel in [
        ("GENERATED VISUAL", ".generated-grid"),
        ("WHY", ".compare-grid"),
        ("PRODUCT DETAIL", ".generated-grid"),
    ]:
        sec = section_by_eyebrow(soup, sec_name)
        if not sec:
            continue
        grid = sec.select_one(grid_sel)
        if not grid:
            continue
        for item in list(grid.select(".item")):
            img = item.select_one("img")
            src = img.get("src") if img else ""
            if should_drop(src):
                item.decompose()

def ensure_append_generated(soup, base: str):
    gen = section_by_eyebrow(soup, "GENERATED VISUAL")
    if gen:
        grid = gen.select_one(".generated-grid")
        if grid:
            urls = [
                (f"{base}/gen_6.webp", "educate B generated extra 6", "使用感や質感の印象を補うビジュアル"),
                (f"{base}/gen_7.webp", "educate B generated extra 7", "日常で使うイメージを補うビジュアル"),
            ]
            existing = { (img.get("src") or "") for img in grid.select("img") }
            for src, alt, copy in urls:
                if src not in existing:
                    append_item(soup, grid, src, alt, copy)

    why = section_by_eyebrow(soup, "WHY")
    if why:
        grid = why.select_one(".compare-grid")
        if grid:
            src = f"{base}/gen_8.webp"
            existing = { (img.get("src") or "") for img in grid.select("img") }
            if src not in existing:
                append_item(soup, grid, src, "educate B compare 4", "素肌感の印象を補うビジュアル")

    detail = section_by_eyebrow(soup, "PRODUCT DETAIL")
    if detail:
        grid = detail.select_one(".generated-grid")
        if grid:
            src = f"{base}/gen_9.webp"
            existing = { (img.get("src") or "") for img in grid.select("img") }
            if src not in existing:
                append_item(soup, grid, src, "educate B detail extra 4", "成分イメージを補うビジュアル")

    for_you = section_by_eyebrow(soup, "FOR YOU")
    if for_you:
        vis = for_you.select_one(".for-you-visual img")
        if vis:
            vis["src"] = f"{base}/gen_10.webp"
            vis["alt"] = "educate B for you visual"

def ensure_layout_css(soup):
    style = soup.select_one("style")
    if not style:
        return
    css = style.get_text()
    add = """
.offer-visual img{width:100%;display:block;border-radius:20px}
.for-you-visual img{width:100%;display:block;border-radius:20px}
.offer-points{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;margin-top:18px}
.offer-points .feature{min-width:0;overflow:hidden}
.offer-points .feature h2,.offer-points .feature p{word-break:break-word;overflow-wrap:anywhere}
.generated-grid .item img,.compare-grid .item img,.lifestyle-grid .item img{width:100%;display:block;border-radius:20px}
@media (max-width: 920px){
.offer-points{grid-template-columns:1fr}
.generated-grid{grid-template-columns:1fr}
.compare-grid{grid-template-columns:1fr}
}
@media (min-width: 921px){
.generated-grid{grid-template-columns:repeat(5,1fr)}
.compare-grid{grid-template-columns:repeat(4,1fr)}
}
"""
    if add not in css:
        style.string = css + add


import re
def force_jp_normalize(text):
    text = text.replace('\u3000','')
    text = re.sub(r'(?<=[ぁ-んァ-ン一-龥])\s+(?=[ぁ-んァ-ン一-龥])','', text)
    text = re.sub(r'\s{2,}',' ', text)
    return text

def 
    jp = r'[ぁ-んァ-ン一-龥ー]'
    pat = re.compile(f'({jp})\\s+({jp})')

    def tight(s: str) -> str:
        s = s.replace("\n", " ")
        while pat.search(s):
            s = pat.sub(r'\1\2', s)
        s = re.sub(r' {2,}', ' ', s)
        return s.strip()

    selectors = [
        ".copy", ".offer-text", ".faq-q", ".faq-a", ".feature p", ".feature h2",
        ".research-note", ".final p", ".points .point", ".hero-proof .proof",
        "h1", "h2", "h3", "p", ".lead", ".num"
    ]
    for sel in selectors:
        for node in soup.select(sel):
            txt = node.get_text(" ", strip=False)
            node.string = force_jp_normalize(tight(txt))

    replacements = {
        "テクスチャやディテールの印象を補うビジュアル": "使用感や質感の印象を補うビジュアル",
        "日常使いの雰囲気を補うビジュアル": "日常で使うイメージを補うビジュアル",
        "成分理解を補うビジュアル": "成分イメージを補うビジュアル",
        "まずは商品詳細と購入ページを確認": "まずは商品詳細を確認してから購入ページへ",
        "使用感・成分・商品情報を確認してから、購入判断へ進みやすい構成です。": "使用感や成分を確認してから購入判断へ進める構成です。",
        "まずは商品詳細で自分に合うか確認": "まずは商品詳細で自分に合うかを確認",
        "使い心地や仕上がりイメージを確認してから、購入ページへ進める構成です。": "使い心地や仕上がりイメージを確認してから購入ページへ進めます。"
    }
    for node in soup.find_all(string=True):
        raw = str(node)
        cleaned = tight(raw)
        if cleaned in replacements:
            cleaned = replacements[cleaned]
        if cleaned != raw.strip():
            node.replace_with(cleaned)



def rewrite_copy_by_section(soup):
    
    def set_copy(section_name, texts):
        sec = section_by_eyebrow(soup, section_name)
        if not sec:
            return
        copies = sec.select(".copy")
        for i, c in enumerate(copies):
            if i < len(texts):
                c.string = texts[i]

    set_copy("GENERATED VISUAL", [
        "軽くのばすだけで、肌が自然に整う感覚",
        "重ねても厚くならず、素肌のような仕上がり"
    ])

    set_copy("WHY", [
        "厚塗りしなくても、自然に整って見える",
        "ベースメイクのストレスを感じにくい仕上がり"
    ])

    set_copy("PRODUCT DETAIL", [
        "軽さとカバーのバランスを考えた処方",
        "毎日使っても負担になりにくい設計"
    ])

    sec = section_by_eyebrow(soup, "FOR YOU")
    if sec:
        p = sec.select_one("p")
        if p:
            p.string = "ナチュラルに整えたい方・ベースメイクを軽くしたい方・素肌感を残したい方におすすめです"

    sec = section_by_eyebrow(soup, "FINAL")
    if sec:
        p = sec.select_one("p")
        if p:
            p.string = "まずは今のベースメイクとの違いを体感してください。軽く整う感覚を知ってから判断できます。"

def process_html(src_path: str, generated_base_url: str, append_generated: bool, cleanup_old: bool, normalize: bool):
    src = Path(src_path).expanduser().resolve()
    if not src.exists():
        raise SystemExit(f"manual_html_missing:{src}")
    soup = BeautifulSoup(src.read_text(encoding="utf-8"), "html.parser")
    if cleanup_old and generated_base_url:
        cleanup_old_generated(soup, generated_base_url)
    if append_generated and generated_base_url:
        ensure_append_generated(soup, generated_base_url)
    if append_generated or cleanup_old:
        ensure_layout_css(soup)
    if normalize:
        normalize_copy(soup)
        rewrite_copy_by_section(soup)
    normalize_copy(soup)
        html = str(soup)
        jp = r'[ぁ-んァ-ン一-龥ー]'
        pat = re.compile(f'({jp})\\s+({jp})')
        while pat.search(html):
            html = pat.sub(r'\1\2', html)
        html = re.sub(r' {2,}', ' ', html)
        
        html = str(soup)
        html = re.sub(r'([ぁ-んァ-ン一-龥ー])\s+([ぁ-んァ-ン一-龥ー])', r'\1\2', html)
        html = re.sub(r'\s{2,}', ' ', html)
        src.write_text(html, encoding="utf-8")
        return

    src.write_text(str(soup), encoding="utf-8")

def export_manual_html(job_id: int, version: int, src_path: str, artifact_type: str = "lp_html_export_v3", title: str = ""):
    src = Path(src_path).expanduser().resolve()
    if not src.exists():
        raise SystemExit(f"manual_html_missing:{src}")
    if not title:
        title = f"lp_html_export_v{version}_manual"
    con = db()
    c = con.cursor()
    c.execute(
        """
        delete from conversation_artifacts
        where job_id=?
          and artifact_type=?
          and version=?
        """,
        (job_id, artifact_type, version),
    )
    c.execute(
        """
        insert into conversation_artifacts(
          job_id, artifact_type, artifact_title, artifact_body, artifact_path, version, created_at
        ) values(?,?,?,?,?,?,datetime('now'))
        """,
        (
            job_id,
            artifact_type,
            title,
            "",
            str(src),
            version,
        ),
    )
    c.execute(
        """
        update conversation_jobs
        set current_phase='lp_html_export_done',
            updated_at=datetime('now')
        where id=?
        """,
        (job_id,),
    )
    con.commit()
    con.close()
    print(f"manual_export_done job_id={job_id} version={version} path={src}", flush=True)

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("job_id", type=int)
    ap.add_argument("version", type=int)
    ap.add_argument("src_path")
    ap.add_argument("artifact_type", nargs="?", default="lp_html_export_v3")
    ap.add_argument("title", nargs="?", default="")
    ap.add_argument("--generated-base-url", default="")
    ap.add_argument("--generated-version-tag", default="")
    ap.add_argument("--append-generated", action="store_true")
    ap.add_argument("--cleanup-old-generated", action="store_true")
    ap.add_argument("--normalize-copy", action="store_true")
    return ap.parse_args()

def main():
    args = parse_args()
    process_html(
        src_path=args.src_path,
        generated_base_url=args.generated_base_url,
        append_generated=args.append_generated,
        cleanup_old=args.cleanup_old_generated,
        normalize=args.normalize_copy,
    )
    export_manual_html(
        job_id=args.job_id,
        version=args.version,
        src_path=args.src_path,
        artifact_type=args.artifact_type,
        title=args.title,
    )

if __name__ == "__main__":
    main()
