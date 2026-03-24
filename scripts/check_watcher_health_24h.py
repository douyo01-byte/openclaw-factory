#!/usr/bin/env python3
import json
import sqlite3
import os
from collections import Counter

candidates = []
if os.environ.get("DB_PATH"):
    candidates.append(os.environ["DB_PATH"])
candidates += [
    os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"),
    os.path.expanduser("~/AI/openclaw-factory-daemon/data/openclaw.db"),
]

DB = None
for cand in candidates:
    if not os.path.exists(cand):
        continue
    try:
        con0 = sqlite3.connect(cand)
        cur0 = con0.cursor()
        ok = cur0.execute(
            "select 1 from sqlite_master where type='table' and name='ops_watcher_events'"
        ).fetchone()
        con0.close()
        if ok:
            DB = cand
            break
    except Exception:
        try:
            con0.close()
        except Exception:
            pass

if DB is None:
    raise SystemExit("ops_watcher_events table not found in candidate DBs")

con = sqlite3.connect(DB)
cur = con.cursor()

rows = cur.execute("""
select id, created_at, body
from ops_watcher_events
where created_at >= datetime('now','-24 hours')
order by id desc
""").fetchall()

print("===== watcher 24h summary =====")
print("total events:", len(rows))

restarted_total = 0
escalations_total = 0
notifications_total = 0
proposals_total = 0

label_states = {}

for rid, created_at, body in rows:
    try:
        j = json.loads(body or "{}")
    except Exception:
        continue

    restarted_total += len(j.get("restarted", []))
    escalations_total += len(j.get("escalations", []))
    notifications_total += len(j.get("notifications", []))
    proposals_total += len(j.get("proposals", []))

    for r in j.get("results", []):
        label = r.get("label")
        if not label:
            continue
        label_states[label] = {
            "policy": r.get("policy"),
            "exists": r.get("service_exists"),
            "running": r.get("service_running"),
            "observed_stopped": r.get("observed_stopped"),
        }

print()
print("===== event signals =====")
print("restarted:", restarted_total)
print("escalations:", escalations_total)
print("notifications:", notifications_total)
print("proposals:", proposals_total)

print()
print("===== label states (latest) =====")
for label, s in sorted(label_states.items()):
    print(
        label,
        "| policy=", s["policy"],
        "| exists=", s["exists"],
        "| running=", s["running"],
        "| observed_stopped=", s["observed_stopped"],
    )

print()
print("===== health judgement =====")

if (
    restarted_total == 0
    and escalations_total == 0
    and notifications_total == 0
    and proposals_total == 0
):
    print("OK: no restart/escalation/notification/proposal in 24h")
else:
    print("WARN: some signals detected")

required_ok = True
for label, s in label_states.items():
    if s["policy"] == "required":
        if not s["running"]:
            required_ok = False
            print("ERROR required stopped:", label)

if required_ok:
    print("OK: all required services running")

con.close()
