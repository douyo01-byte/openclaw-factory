import os
import sqlite3
import time
import subprocess
import json
from datetime import datetime, timezone
from openai import OpenAI

DB = os.environ["OCLAW_DB_PATH"]
FACTORY = "/Users/doyopc/AI/openclaw-factory"
MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-mini")
MERGED_REPROPOSE_HOURS = int(os.environ.get("MERGED_REPROPOSE_HOURS", "4"))
CLOSED_REPROPOSE_HOURS = int(os.environ.get("CLOSED_REPROPOSE_HOURS", "18"))
INSERT_LIMIT = int(os.environ.get("INNOVATION_INSERT_LIMIT", "2"))
client = OpenAI()

def sh(cmd, cwd=FACTORY):
    r = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""

def list_targets():
    out = sh(["git", "ls-files"])
    files = [x for x in out.splitlines() if x.endswith(".py") and not x.endswith("__init__.py") and (x.startswith("bots/") or x.startswith("scripts/"))]
    deny = (
        ".bak", "__pycache__", "archive/", "logs/", "tmp/",
        "innovation_engine_v1.py", "innovation_llm_engine_v1.py"
    )
    files = [x for x in files if not any(d in x for d in deny)]
    return files[:300]

def read_text(path, limit=7000):
    try:
        with open(os.path.join(FACTORY, path), "r", encoding="utf-8") as f:
            return f.read(limit)
    except:
        return ""

def recent_titles(con, n=300):
    rows = con.execute("""
    select lower(coalesce(title,''))
    from dev_proposals
    order by id desc
    limit ?
    """, (n,)).fetchall()
    return {r[0] for r in rows if r[0]}

def target_history(con, path, n=5):
    return con.execute("""
    select
      id,
      coalesce(title,'') as title,
      coalesce(status,'') as status,
      coalesce(dev_stage,'') as dev_stage,
      coalesce(pr_status,'') as pr_status,
      coalesce(improvement_type,'') as improvement_type,
      coalesce(category,'') as category,
      coalesce(source_ai,'') as source_ai,
      coalesce(created_at,'') as created_at
    from dev_proposals
    where lower(coalesce(target_system,'')) = lower(?)
    order by id desc
    limit ?
    """, (path, n)).fetchall()

def parse_created_at(ts):
    if not ts:
        return None
    try:
        return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except:
        return None

def age_hours(ts):
    dt = parse_created_at(ts)
    if not dt:
        return 999999
    return int((datetime.now(timezone.utc) - dt).total_seconds() // 3600)

def is_active(row):
    status = (row["status"] or "").lower()
    dev_stage = (row["dev_stage"] or "").lower()
    pr_status = (row["pr_status"] or "").lower()
    if status in ("approved", "open", "pr_created", "pr_ready", "executing", "execute_now"):
        return True
    if dev_stage in ("approved", "open", "pr_created", "pr_ready", "executing", "execute_now"):
        return True
    if pr_status in ("open", "ready", "pr_created"):
        return True
    return False

def allow_target(history):
    if not history:
        return True, "new_target", None
    latest = history[0]
    if is_active(latest):
        return False, "active_exists", latest
    latest_status = (latest["status"] or "").lower()
    h = age_hours(latest["created_at"])
    if latest_status == "merged" and h < MERGED_REPROPOSE_HOURS:
        return False, f"merged_cooldown:{h}h", latest
    if latest_status == "closed" and h < CLOSED_REPROPOSE_HOURS:
        return False, f"closed_cooldown:{h}h", latest
    return True, f"reproposal_after_{latest_status or 'unknown'}:{h}h", latest

def render_history(history):
    if not history:
        return "No prior proposals for this target."
    lines = []
    for r in history[:5]:
        lines.append(
            f"id={r['id']} status={r['status']} dev_stage={r['dev_stage']} pr_status={r['pr_status']} "
            f"improvement_type={r['improvement_type']} category={r['category']} created_at={r['created_at']} "
            f"title={r['title']}"
        )
    return "\n".join(lines)

def ask_llm(path, code, history_text):
    prompt = f"""
You are improving an autonomous AI software company.
Read the target file and propose ONE concrete, low-risk improvement.

Return strict JSON only:
{{
  "title": "...",
  "description": "...",
  "category": "reliability|performance|observability|self_healing|safety|automation|analysis",
  "improvement_type": "bugfix|refactor|optimization|guard|logging|automation|diagnostics",
  "priority": 0-100,
  "quality_score": 0-1,
  "score": 0-100
}}

Rules:
- Be specific to the file content.
- Prefer a small concrete change.
- Avoid duplicate-like titles.
- If prior proposals exist for this target, choose a meaningfully different angle from recent ones.
- Do not repeat the latest proposal's title or same lane unless clearly justified by the code.
- No markdown.
- JSON only.

Target path:
{path}

Recent target history:
{history_text}

Code:
{code}
""".strip()

    r = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You generate precise engineering improvement proposals in strict JSON."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    txt = r.choices[0].message.content
    data = json.loads(txt)
    return {
        "title": str(data.get("title", "")).strip()[:140],
        "description": str(data.get("description", "")).strip()[:2000],
        "category": str(data.get("category", "analysis")).strip()[:40] or "analysis",
        "improvement_type": str(data.get("improvement_type", "diagnostics")).strip()[:40] or "diagnostics",
        "priority": int(float(data.get("priority", 60))),
        "quality_score": float(data.get("quality_score", 0.72)),
        "score": float(data.get("score", 72)),
    }

def clamp(row):
    row["priority"] = max(0, min(100, row["priority"]))
    row["quality_score"] = max(0, min(1, row["quality_score"]))
    row["score"] = max(0, min(100, row["score"]))
    if not row["title"]:
        row["title"] = "Improve reliability in target module"
    if not row["description"]:
        row["description"] = "AI generated concrete low-risk improvement proposal."
    return row

def same_lane(a, b):
    if not a or not b:
        return False
    return (
        (a.get("improvement_type", "") or "").strip().lower() == (b["improvement_type"] or "").strip().lower()
        and
        (a.get("category", "") or "").strip().lower() == (b["category"] or "").strip().lower()
    )

def main():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    try:
        con.execute("pragma journal_mode=WAL")
    except:
        pass

    seen_titles = recent_titles(con)
    targets = list_targets()
    inserted = 0

    for path in targets:
        code = read_text(path, 7000)
        if not code.strip():
            continue

        history = target_history(con, path, 5)
        ok, reason, latest = allow_target(history)
        if not ok:
            print(f"[skip] target={path} reason={reason}", flush=True)
            continue

        try:
            row = clamp(ask_llm(path, code, render_history(history)))
        except Exception as e:
            print(repr(e), flush=True)
            continue

        if row["title"].lower() in seen_titles:
            print(f"[skip] target={path} reason=duplicate_title", flush=True)
            continue

        if latest and same_lane(row, latest):
            print(f"[skip] target={path} reason=same_lane_as_latest", flush=True)
            continue

        con.execute("""
        insert into dev_proposals(
            title,description,branch_name,status,
            category,target_system,improvement_type,
            priority,quality_score,score,spec,source_ai,confidence
        ) values(?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            row["title"],
            row["description"],
            "",
            "approved",
            row["category"],
            path,
            row["improvement_type"],
            row["priority"],
            row["quality_score"],
            row["score"],
            "auto generated by innovation_llm_engine_v1",
            "innovation_llm_engine_v1",
            row["quality_score"]
        ))
        con.commit()
        seen_titles.add(row["title"].lower())
        inserted += 1
        print(f"innovation_llm_created target={path} title={row['title']} reason={reason}", flush=True)
        if inserted >= INSERT_LIMIT:
            break

    if inserted == 0:
        print("[innovation] no_insert", flush=True)

    con.close()

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(repr(e), flush=True)
        time.sleep(300)
