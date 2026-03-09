from __future__ import annotations
import os
import re
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DB = os.environ.get("DB_PATH", str(ROOT / "data" / "openclaw.db"))

MANUAL_DOCS = {
    "README.md",
    "00_INDEX.md",
    "06_CURRENT_STATE.md",
    "08_HANDOVER.md",
}

def sh(cmd: str) -> str:
    return subprocess.run(
        cmd,
        shell=True,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        env=os.environ.copy(),
    ).stdout.strip()

def q(sql: str):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(sql)
        return cur.fetchall()
    finally:
        conn.close()

def q1(sql: str, default="0") -> str:
    rows = q(sql)
    if not rows:
        return default
    row = rows[0]
    if isinstance(row, sqlite3.Row):
        return str(row[0])
    return str(row[0])

def table_exists(name: str) -> bool:
    return q1(f"select count(*) from sqlite_master where type='table' and name='{name}'") != "0"

def get_branch() -> str:
    return sh("git branch --show-current")

def get_head() -> str:
    return sh("git rev-parse --short HEAD")

def get_launchagents() -> list[str]:
    out = sh("launchctl list | grep openclaw || true")
    lines = [x.rstrip() for x in out.splitlines() if x.strip()]
    agents = []
    for line in lines:
        parts = re.split(r"\s+", line.strip())
        if len(parts) >= 3:
            agents.append(parts[-1])
    return sorted(set(agents))

def get_bot_files() -> list[str]:
    bots_dir = ROOT / "bots"
    if not bots_dir.exists():
        return []
    return sorted(
        p.name for p in bots_dir.iterdir()
        if p.is_file() and p.suffix == ".py" and ".bak" not in p.name
    )

def get_status_counts() -> list[tuple[str, str]]:
    if not table_exists("dev_proposals"):
        return []
    rows = q("""
        select coalesce(status,'') as status, count(*) as c
        from dev_proposals
        group by status
        order by status
    """)
    return [(str(r["status"]), str(r["c"])) for r in rows]

def get_proposal_state_counts() -> list[tuple[str, str]]:
    if not table_exists("proposal_state"):
        return []
    rows = q("""
        select coalesce(stage,'') as stage, count(*) as c
        from proposal_state
        group by stage
        order by stage
    """)
    return [(str(r["stage"]), str(r["c"])) for r in rows]

def get_event_counts() -> list[tuple[str, str]]:
    if not table_exists("ceo_hub_events"):
        return []
    rows = q("""
        select coalesce(event_type,'') as event_type, count(*) as c
        from ceo_hub_events
        group by event_type
        order by event_type
    """)
    return [(str(r["event_type"]), str(r["c"])) for r in rows]

def get_latest_proposals(limit: int = 15) -> list[sqlite3.Row]:
    if not table_exists("dev_proposals"):
        return []
    return q(f"""
        select id, title, status, created_at
        from dev_proposals
        order by id desc
        limit {limit}
    """)

def get_tables() -> list[str]:
    rows = q("""
        select name
        from sqlite_master
        where type='table'
        order by name
    """)
    return [str(r["name"]) for r in rows]

def get_columns(table: str) -> list[sqlite3.Row]:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(f"pragma table_info({table})").fetchall()
    finally:
        conn.close()

def render_auto_progress() -> str:
    lines = []
    lines.append("# OpenClaw Auto Progress")
    lines.append("")
    lines.append(f"- branch: `{get_branch()}`")
    lines.append(f"- head: `{get_head()}`")
    lines.append(f"- db: `{DB}`")
    lines.append("")
    lines.append("## dev_proposals status")
    for k, v in get_status_counts():
        lines.append(f"- {k or '(blank)'}: {v}")
    lines.append("")
    lines.append("## proposal_state")
    for k, v in get_proposal_state_counts():
        lines.append(f"- {k or '(blank)'}: {v}")
    lines.append("")
    lines.append("## ceo_hub_events")
    for k, v in get_event_counts():
        lines.append(f"- {k or '(blank)'}: {v}")
    lines.append("")
    lines.append("## latest proposals")
    for r in get_latest_proposals():
        lines.append(f"- {r['id']} | {r['title']} | {r['status']} | {r['created_at']}")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"

def render_bot_catalog() -> str:
    files = get_bot_files()
    lines = []
    lines.append("# OpenClaw Bot Catalog")
    lines.append("")
    lines.append("自動生成。手修正しない。")
    lines.append("")
    for name in files:
        lines.append(f"- {name}")
    lines.append("")
    return "\n".join(lines)

def render_db_schema() -> str:
    lines = []
    lines.append("# OpenClaw DB Schema Notes")
    lines.append("")
    lines.append("自動生成。手修正しない。")
    lines.append("")
    lines.append(f"- branch: `{get_branch()}`")
    lines.append(f"- db: `{DB}`")
    lines.append("")
    lines.append("## table list")
    for t in get_tables():
        lines.append(f"- {t}")
    lines.append("")
    lines.append("## current counts")
    lines.append(f"- dev_proposals: {q1('select count(*) from dev_proposals') if table_exists('dev_proposals') else 'n/a'}")
    lines.append(f"- proposal_state: {q1('select count(*) from proposal_state') if table_exists('proposal_state') else 'n/a'}")
    lines.append(f"- proposal_conversation: {q1('select count(*) from proposal_conversation') if table_exists('proposal_conversation') else 'n/a'}")
    lines.append(f"- inbox_commands: {q1('select count(*) from inbox_commands') if table_exists('inbox_commands') else 'n/a'}")
    lines.append(f"- decisions: {q1('select count(*) from decisions') if table_exists('decisions') else 'n/a'}")
    lines.append(f"- ceo_hub_events: {q1('select count(*) from ceo_hub_events') if table_exists('ceo_hub_events') else 'n/a'}")
    lines.append("")
    lines.append("## proposal_state status counts")
    for k, v in get_proposal_state_counts():
        lines.append(f"- {k or '(blank)'}: {v}")
    lines.append("")
    lines.append("## ceo_hub_events event counts")
    for k, v in get_event_counts():
        lines.append(f"- {k or '(blank)'}: {v}")
    lines.append("")
    lines.append("## columns")
    for t in get_tables():
        lines.append(f"### {t}")
        for c in get_columns(t):
            lines.append(
                f"- {c['name']} | {c['type']} | notnull={c['notnull']} | pk={c['pk']} | default={c['dflt_value']}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"

def render_operations() -> str:
    lines = []
    lines.append("# OpenClaw Operations")
    lines.append("")
    lines.append("自動生成。手修正しない。")
    lines.append("")
    lines.append(f"- branch: `{get_branch()}`")
    lines.append(f"- head: `{get_head()}`")
    lines.append("")
    lines.append("## launchagents")
    for a in get_launchagents():
        lines.append(f"- {a}")
    lines.append("")
    lines.append("## active docs policy")
    for name in sorted(MANUAL_DOCS):
        lines.append(f"- manual: {name}")
    lines.append("- auto: docs/_auto_progress.md")
    lines.append("- auto: docs/09_BOT_CATALOG.md")
    lines.append("- auto: docs/10_DB_SCHEMA.md")
    lines.append("- auto: docs/11_OPERATIONS.md")
    lines.append("")
    return "\n".join(lines)

def write_if_changed(path: Path, text: str) -> bool:
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    if old == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True

def main():
    DOCS.mkdir(parents=True, exist_ok=True)
    changed = []
    mapping = {
        DOCS / "_auto_progress.md": render_auto_progress(),
        DOCS / "09_BOT_CATALOG.md": render_bot_catalog(),
        DOCS / "10_DB_SCHEMA.md": render_db_schema(),
        DOCS / "11_OPERATIONS.md": render_operations(),
    }
    for path, text in mapping.items():
        if write_if_changed(path, text):
            changed.append(str(path.relative_to(ROOT)))
    print("changed:")
    for x in changed:
        print(x)

if __name__ == "__main__":
    main()
