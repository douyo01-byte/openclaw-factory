from __future__ import annotations
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Iterable

DB_PATH = os.environ.get("DB_PATH", str(Path.home() / "AI/openclaw-factory/data/openclaw.db"))
DOC_ROOT = Path(os.environ.get("OPENCLAW_DOC_ROOT", str(Path.home() / "AI/openclaw-factory-docs")))
DEFAULT_DOCS = [
    "docs/06_CURRENT_STATE.md",
    "docs/08_HANDOVER.md",
]

SECTION_PATTERNS = {
    "goals": [
        r"目的",
        r"長期目的",
        r"目標",
        r"ゴール",
        r"方針",
        r"狙い",
        r"vision",
        r"goal",
        r"objective",
    ],
    "constraints": [
        r"制約",
        r"制限",
        r"禁止",
        r"注意",
        r"前提",
        r"条件",
        r"constraint",
        r"rule",
        r"policy",
    ],
    "unfinished": [
        r"未完",
        r"未完了",
        r"残課題",
        r"課題",
        r"問題",
        r"TODO",
        r"pending",
        r"remaining",
        r"next",
    ],
    "priorities": [
        r"優先",
        r"重点",
        r"次の重点",
        r"next focus",
        r"priority",
        r"priorities",
        r"focus",
    ],
}

BULLET_RE = re.compile(r"^\s*(?:[-*+]|[0-9]+[.)]|[・■□◆◇▶►])\s+(.+?)\s*$")
HEADER_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
CODE_FENCE_RE = re.compile(r"^```")
KV_RE = re.compile(r"^\s*([A-Za-z0-9_ /-]{2,40})\s*[:：]\s*(.+?)\s*$")

def now_sql(con: sqlite3.Connection) -> str:
    return con.execute("select datetime('now')").fetchone()[0]

def ensure_table(con: sqlite3.Connection) -> None:
    con.execute("""
    create table if not exists goal_doc_snapshots (
        id integer primary key autoincrement,
        doc_path text not null,
        section_type text not null,
        item_text text not null,
        line_no integer,
        heading text,
        created_at text not null
    )
    """)
    con.execute("create index if not exists idx_goal_doc_snapshots_doc on goal_doc_snapshots(doc_path, section_type, created_at)")
    con.execute("create index if not exists idx_goal_doc_snapshots_created on goal_doc_snapshots(created_at desc)")
    con.commit()

def clean_line(s: str) -> str:
    s = s.replace("\u3000", " ").strip()
    s = re.sub(r"\s+", " ", s)
    return s

def classify_heading(text: str) -> list[str]:
    t = text.lower()
    matched = []
    for key, pats in SECTION_PATTERNS.items():
        if any(re.search(p, text, re.I) for p in pats) or any(p.lower() in t for p in pats):
            matched.append(key)
    return matched

def extract_items(lines: list[str]) -> list[dict]:
    out: list[dict] = []
    in_code = False
    active_headings: list[tuple[int, str]] = []
    active_buckets: set[str] = set()

    for idx, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n")

        if CODE_FENCE_RE.match(line.strip()):
            in_code = not in_code
            continue
        if in_code:
            continue

        hm = HEADER_RE.match(line)
        if hm:
            level = len(hm.group(1))
            heading = clean_line(hm.group(2))
            active_headings = [x for x in active_headings if x[0] < level]
            active_headings.append((level, heading))
            active_buckets = set(classify_heading(heading))
            continue

        heading = active_headings[-1][1] if active_headings else ""

        bm = BULLET_RE.match(line)
        if bm and active_buckets:
            text = clean_line(bm.group(1))
            if text:
                for bucket in active_buckets:
                    out.append({
                        "section_type": bucket,
                        "item_text": text,
                        "line_no": idx,
                        "heading": heading,
                    })
            continue

        km = KV_RE.match(line)
        if km and active_buckets:
            left = clean_line(km.group(1))
            right = clean_line(km.group(2))
            text = f"{left}: {right}"
            for bucket in active_buckets:
                out.append({
                    "section_type": bucket,
                    "item_text": text,
                    "line_no": idx,
                    "heading": heading,
                })
            continue

        if active_buckets:
            text = clean_line(line)
            if len(text) >= 12 and not text.startswith("#"):
                for bucket in active_buckets:
                    out.append({
                        "section_type": bucket,
                        "item_text": text,
                        "line_no": idx,
                        "heading": heading,
                    })

    dedup = []
    seen = set()
    for row in out:
        key = (row["section_type"], row["item_text"])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(row)
    return dedup

def resolve_docs(args: list[str]) -> list[Path]:
    rels = args if args else DEFAULT_DOCS
    paths = []
    for rel in rels:
        p = Path(rel)
        if not p.is_absolute():
            p = DOC_ROOT / rel
        if p.exists():
            paths.append(p)
    return paths

def ingest_docs(con: sqlite3.Connection, docs: Iterable[Path]) -> dict:
    created_at = now_sql(con)
    counts = {"docs": 0, "goals": 0, "constraints": 0, "unfinished": 0, "priorities": 0}
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        rows = extract_items(text.splitlines())
        if not rows:
            continue
        counts["docs"] += 1
        rel = str(doc)
        con.execute("delete from goal_doc_snapshots where doc_path = ?", (rel,))
        for row in rows:
            con.execute("""
            insert into goal_doc_snapshots
            (doc_path, section_type, item_text, line_no, heading, created_at)
            values (?, ?, ?, ?, ?, ?)
            """, (rel, row["section_type"], row["item_text"], row["line_no"], row["heading"], created_at))
            counts[row["section_type"]] += 1
    con.commit()
    return counts

def build_summary(con: sqlite3.Connection) -> dict:
    summary = {}
    for key in ("goals", "constraints", "unfinished", "priorities"):
        rows = con.execute("""
        select item_text, doc_path, line_no, heading
        from goal_doc_snapshots
        where section_type = ?
        order by doc_path, line_no
        limit 50
        """, (key,)).fetchall()
        summary[key] = [
            {
                "text": r[0],
                "doc_path": r[1],
                "line_no": r[2],
                "heading": r[3],
            }
            for r in rows
        ]
    return summary

def main() -> None:
    import sys
    docs = resolve_docs(sys.argv[1:])
    if not docs:
        print(json.dumps({"ok": False, "error": "no_docs_found"}, ensure_ascii=False))
        raise SystemExit(1)

    con = sqlite3.connect(DB_PATH)
    con.execute("pragma journal_mode=WAL")
    con.execute("pragma busy_timeout=5000")
    ensure_table(con)
    counts = ingest_docs(con, docs)
    summary = build_summary(con)
    print(json.dumps({
        "ok": True,
        "db_path": DB_PATH,
        "docs": [str(p) for p in docs],
        "counts": counts,
        "summary": summary,
    }, ensure_ascii=False, indent=2))
    con.close()

if __name__ == "__main__":
    main()
