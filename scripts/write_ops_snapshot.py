import os
import sqlite3
import subprocess
from datetime import datetime

DB = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))
OUT = os.path.expanduser("~/AI/openclaw-factory/docs/_auto_progress.md")

def q(conn, sql):
    return conn.execute(sql).fetchall()

def one(conn, sql):
    r = conn.execute(sql).fetchone()
    return r[0] if r else None

def launch_state(label):
    uid = os.getuid()
    try:
        out = subprocess.check_output(
            ["launchctl", "print", f"gui/{uid}/{label}"],
            stderr=subprocess.STDOUT,
            text=True,
        )
    except subprocess.CalledProcessError:
        return "missing"
    state = "unknown"
    pid = ""
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("state ="):
            state = s.split("=", 1)[1].strip()
        if s.startswith("pid ="):
            pid = s.split("=", 1)[1].strip()
    return f"{state}" + (f" pid={pid}" if pid else "")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

status_rows = q(conn, """
select coalesce(status,'') as status, count(*) as n
from dev_proposals
group by coalesce(status,'')
order by status
""")

stage_rows = q(conn, """
select coalesce(stage,'') as stage, count(*) as n
from proposal_state
group by coalesce(stage,'')
order by stage
""")

latest_rows = q(conn, """
select id, title, status
from dev_proposals
order by id desc
limit 10
""")

event_rows = q(conn, """
select event_type, count(*) as n
from ceo_hub_events
group by event_type
order by event_type
""")

executor_queue = one(conn, """
select count(*)
from dev_proposals
where status='approved'
  and coalesce(project_decision,'')='execute_now'
  and coalesce(guard_status,'')='safe'
  and coalesce(spec,'')!=''
  and coalesce(dev_stage,'') in ('','approved')
""")

merged_count = one(conn, "select count(*) from dev_proposals where status='merged'")
open_count = one(conn, "select count(*) from dev_proposals where status='open'")
pr_created_count = one(conn, "select count(*) from dev_proposals where status='pr_created'")

labels = [
    "jp.openclaw.dev_command_executor_v1",
    "jp.openclaw.dev_pr_watcher_v1",
    "jp.openclaw.spec_refiner_v2",
    "jp.openclaw.self_healing_v2",
    "jp.openclaw.supervisor",
]

now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

lines = []
lines.append(f"## {now} 自動進捗スナップショット")
lines.append("")
lines.append("### proposal status")
for r in status_rows:
    lines.append(f"- {r['status'] or '(blank)'}: {r['n']}")
lines.append("")
lines.append("### proposal_state")
for r in stage_rows:
    lines.append(f"- {r['stage'] or '(blank)'}: {r['n']}")
lines.append("")
lines.append("### executor summary")
lines.append(f"- executor_queue: {executor_queue}")
lines.append(f"- merged_count: {merged_count}")
lines.append(f"- pr_created_count: {pr_created_count}")
lines.append(f"- open_count: {open_count}")
lines.append("")
lines.append("### launchagents")
for label in labels:
    lines.append(f"- {label}: {launch_state(label)}")
lines.append("")
lines.append("### latest proposals")
for r in latest_rows:
    lines.append(f"- {r['id']} | {r['title']} | {r['status']}")
lines.append("")
lines.append("### ceo_hub_events")
for r in event_rows:
    lines.append(f"- {r['event_type']}: {r['n']}")
lines.append("")
lines.append("---")
lines.append("")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(OUT)
conn.close()
