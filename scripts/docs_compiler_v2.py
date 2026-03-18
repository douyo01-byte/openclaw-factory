from pathlib import Path
import sqlite3
import subprocess
from datetime import datetime, timezone
import re

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
DB = Path("/Users/doyopc/AI/openclaw-factory/data/openclaw.db")

def sh(args):
    return subprocess.check_output(args, text=True).strip()

def one(cur, sql):
    r = cur.execute(sql).fetchone()
    return r[0] if r and r[0] is not None else 0

def replace_section(text, heading, new_block):
    pat = rf"(^## {re.escape(heading)}\n)(.*?)(?=^\#\# |\Z)"
    m = re.search(pat, text, flags=re.M | re.S)
    if not m:
        return text
    return text[:m.start()] + m.group(1) + new_block.rstrip() + "\n" + text[m.end():]

def replace_line(text, prefix, new_line):
    pat = rf"^{re.escape(prefix)}.*$"
    if re.search(pat, text, flags=re.M):
        return re.sub(pat, new_line, text, count=1, flags=re.M)
    return text

def write_if_changed(path, text):
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    if old != text:
        path.write_text(text, encoding="utf-8")
        print(f"updated: {path}")

def render_current_state_live(cur, old_text):
    now = datetime.now(timezone.utc).isoformat()
    proposals = one(cur, "select count(*) from dev_proposals")
    merged = one(cur, "select count(*) from dev_proposals where coalesce(status,'')='merged'")
    open_pr = one(cur, "select count(*) from dev_proposals where coalesce(pr_status,'')='open'")
    waiting = one(cur, "select count(*) from proposal_state where coalesce(stage,'')='waiting_answer'")
    ceo_events = one(cur, "select count(*) from ceo_hub_events")
    s = old_text
    s = replace_line(s, "- generated_at:", f"- generated_at: {now}")
    s = replace_line(s, "- canonical_db:", f"- canonical_db: {DB}")
    block = "\n".join([
        f"- proposals: {proposals}",
        f"- merged: {merged}",
        f"- open_pr: {open_pr}",
        f"- waiting_answer: {waiting}",
        f"- ceo_events: {ceo_events}",
    ])
    s = replace_section(s, "live counters", block)
    return s

def render_handover_live(cur, old_text):
    now = datetime.now(timezone.utc).isoformat()
    branch = sh(["git", "branch", "--show-current"])
    head = sh(["git", "rev-parse", "--short", "HEAD"])
    latest = cur.execute("""
    select id, title, coalesce(status,''), coalesce(pr_url,'')
    from dev_proposals
    order by id desc
    limit 10
    """).fetchall()
    lines = "\n".join(f"- #{r[0]} {r[1]} | {r[2]} | {r[3]}" for r in latest)
    s = old_text
    s = replace_line(s, "- generated_at:", f"- generated_at: {now}")
    s = replace_line(s, "- branch:", f"- branch: {branch}")
    s = replace_line(s, "- head:", f"- head: {head}")
    s = replace_line(s, "- canonical_db:", f"- canonical_db: {DB}")
    s = replace_section(s, "直 近 案 件", lines)
    return s

def render_db_schema(cur):
    tables = [r[0] for r in cur.execute("select name from sqlite_master where type='table' order by name").fetchall()]
    out = [
        "# OpenClaw DB Schema",
        "",
        f"- generated_at: {datetime.now(timezone.utc).isoformat()}",
        f"- canonical_db: {DB}",
        "",
    ]
    for t in tables:
        out.append(f"## {t}")
        for c in cur.execute(f"pragma table_info({t})").fetchall():
            out.append(f"- {c[1]} | {c[2]}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"

def main():
    DOCS.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    p06 = DOCS / "06_CURRENT_STATE.md"
    p08 = DOCS / "08_HANDOVER.md"
    p10 = DOCS / "10_DB_SCHEMA.md"

    old06 = p06.read_text(encoding="utf-8")
    old08 = p08.read_text(encoding="utf-8")

    write_if_changed(p10, render_db_schema(cur))

    conn.close()

if __name__ == "__main__":
    main()
