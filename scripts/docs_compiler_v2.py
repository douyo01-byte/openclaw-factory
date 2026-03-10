import os
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

DB = os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db")

def sh(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    except:
        return ""

def db():
    return sqlite3.connect(DB)

def table_counts():
    c = db()
    cur = c.cursor()
    tables = [
        "dev_proposals",
        "proposal_state",
        "proposal_conversation",
        "company_orders",
        "learning_results",
        "system_metrics",
        "ceo_hub_events",
        "dev_events"
    ]
    out = []
    for t in tables:
        try:
            n = cur.execute(f"select count(*) from {t}").fetchone()[0]
            out.append(f"- {t}: {n}")
        except:
            out.append(f"- {t}: n/a")
    return "\n".join(out)

def launchagents():
    s = sh("launchctl list | grep openclaw")
    lines = []
    for l in s.splitlines():
        name = l.split()[-1]
        lines.append(f"- {name}")
    return "\n".join(lines)

def render_current_state():
    return f"""# OpenClaw Current State

generated_at: {datetime.utcnow()}

## Level
Lv7.99 → Lv8 entry

## Autonomous loop

proposal
↓
spec refine
↓
code generation
↓
PR
↓
merge
↓
learning
↓
adaptive supply

## Supply engines

- innovation_engine
- code_review_engine
- code_supply_engine
- brain_supply_engine
- mainstream_supply

## CEO layer

- ai_ceo_engine
- ai_meeting_engine
- secretary_llm_v1
- ceo_command_router_v1

## Self improvement

- experiment_engine_v1
- adaptive_supply_controller_v1
- self_improvement_engine_v1

## Canonical DB

{DB}

## Table counts

{table_counts()}
"""

def render_handover():
    return f"""# OpenClaw Handover

generated_at: {datetime.utcnow()}

branch: {sh("git rev-parse --abbrev-ref HEAD")}
head: {sh("git rev-parse --short HEAD")}

## LaunchAgents

{launchagents()}

## Canonical DB

{DB}

## Next startup command

cd ~/AI/openclaw-factory-daemon

"""

def render_db_schema():
    c = db()
    cur = c.cursor()

    tables = cur.execute(
        "select name from sqlite_master where type='table'"
    ).fetchall()

    txt = "# OpenClaw DB Schema\n\n"

    for t in tables:
        t = t[0]
        txt += f"## {t}\n"
        cols = cur.execute(f"pragma table_info({t})").fetchall()
        for c in cols:
            txt += f"- {c[1]} | {c[2]}\n"
        txt += "\n"

    return txt

def write(path, txt):
    old = ""
    if path.exists():
        old = path.read_text()

    if old != txt:
        path.write_text(txt)
        print("updated:", path)

def main():
    DOCS.mkdir(exist_ok=True)

    write(DOCS/"06_CURRENT_STATE.md", render_current_state())
    write(DOCS/"08_HANDOVER.md", render_handover())
    write(DOCS/"10_DB_SCHEMA.md", render_db_schema())

if __name__ == "__main__":
    main()
