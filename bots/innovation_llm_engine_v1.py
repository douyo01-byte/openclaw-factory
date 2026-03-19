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
        "innovation_engine_v1.py", "innovation_llm_engine_v1.py",
        ".txt", ".md", ".json", ".csv",
        "tg_test.py",
        "/test_", "test/", "/tests/", "_test.py",
        "docs/", "reports/", "obs/", "config/feeds/",
        ".dev_agent_test", "tmp_", "sample", "example"
    )
    files = [x for x in files if not any(d in x for d in deny)]
    allow_prefix = ("bots/", "scripts/")
    files = [x for x in files if x.startswith(allow_prefix)]
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

def ask_llm(path, code, history_text, structural_context, force_structural):
    prompt = f"""
You are improving an autonomous AI software company.
Read the target file and propose ONE concrete improvement.

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
- Avoid duplicate-like titles.
- If prior proposals exist for this target, choose a meaningfully different angle from recent ones.
- Do not repeat the latest proposal's title or same lane unless clearly justified by the code.
- No markdown.
- JSON only.
- Prefer proposals that change system behavior, orchestration, routing, lifecycle, runtime topology, AI employee behavior, business execution bridges, or cross-component automation.

When force_structural is true:
- Do NOT propose small local fixes.
- Do NOT propose logging-only, parsing-only, env-only, timeout-only, guard-only, or single-function micro improvements.
- Prefer architecture-first evolution.
- Prefer multi-component changes over isolated tweaks.
- Prefer proposals that can create follow-up runtime work.

Allowed structural concepts include:
- AI employee
- runtime loop
- routing
- orchestration
- business execution
- cross-agent coordination
- topology
- lifecycle
- autonomous expansion
- follow-up generation

Target path:
{path}

Recent target history:
{history_text}

Recent merged structural context:
{structural_context}

force_structural={force_structural}

Code:
{code}
""".strip()

    r = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You generate precise engineering improvement proposals in strict JSON. Prefer system evolution over local safe fixes when requested."},
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

STRUCTURAL_KEYWORDS = (
    "ai employee", "runtime loop", "routing", "orchestration",
    "business execution", "cross-agent", "cross agent",
    "topology", "lifecycle", "autonomous", "follow-up",
    "follow up", "multi-component", "multi component",
    "organization-scale", "organization scale", "architecture"
)

SMALL_FIX_KEYWORDS = (
    "logging", "log ", "parse", "parsing", "env ", ".env", "timeout",
    "guard", "wrapper", "retry", "truncate", "coerce", "decode",
    "split", "mail", "http fetch", "single-function", "single function",
    "micro", "small fix", "small local", "lightweight logging"
)


UTILITY_PATH_KEYWORDS = (
    "smoke", "test", "example", "sample", "tmp", "helper", "helpers",
    "get_chat_id", "openai_smoke", "browser_smoke", "cleanup",
)

STRUCTURAL_PATH_KEYWORDS = (
    "router", "routing", "orchestr", "employee", "registry", "queue",
    "worker", "lifecycle", "bridge", "proposal", "decision", "spec",
    "runtime", "executor", "watcher", "hub", "meeting", "brain",
    "supply", "self_healing", "self_healing_v2", "coord", "manager",
)

def path_structural_score(path):
    t = (path or "").lower()
    score = 0
    for k in STRUCTURAL_PATH_KEYWORDS:
        if k in t:
            score += 18
    for k in UTILITY_PATH_KEYWORDS:
        if k in t:
            score -= 22
    if t.startswith("bots/team/"):
        score += 8
    if "/chat_to_dev/" in t:
        score += 10
    if t.startswith("scripts/"):
        score -= 8
    return score

def final_sanity_healthy(con):
    row = con.execute("""
    select
      sum(case when coalesce(pr_status,'')='open' then 1 else 0 end) as open_pr,
      sum(case when coalesce(source_ai,'')='' then 1 else 0 end) as blank_source_ai,
      sum(case
            when coalesce(status,'')='merged'
             and (coalesce(result_type,'')='' or result_type is null)
            then 1 else 0 end) as merged_without_result_type,
      sum(case
            when coalesce(status,'')='merged'
             and coalesce(dev_stage,'') not in ('','merged')
            then 1 else 0 end) as stage_divergence
    from dev_proposals
    where coalesce(source_ai,'')<>'innovation_llm_engine_v1'
    """).fetchone()
    if not row:
        return True
    open_pr = int(row[0] or 0)
    blank_source_ai = int(row[1] or 0)
    merged_without_result_type = int(row[2] or 0)
    stage_divergence = int(row[3] or 0)
    return open_pr == 0 and blank_source_ai == 0 and merged_without_result_type == 0 and stage_divergence == 0

def recent_structural_context(con, limit_n=8):
    rows = con.execute("""
    select coalesce(title,''), coalesce(description,'')
    from dev_proposals
    where coalesce(status,'')='merged'
      and coalesce(source_ai,'') in ('mothership','innovation_llm_engine_v1')
    order by id desc
    limit ?
    """, (limit_n,)).fetchall()
    out = []
    for r in rows:
        title = (r[0] or "").strip()
        desc = (r[1] or "").strip()
        text = f"{title} {desc}".lower()
        if any(k in text for k in STRUCTURAL_KEYWORDS):
            out.append(f"- {title}: {desc[:220]}")
    return "\n".join(out[:limit_n]) or "None"

def has_structural_signal(row):
    text = f"{row.get('title','')} {row.get('description','')}".lower()
    return any(k in text for k in STRUCTURAL_KEYWORDS)

def is_small_fix(row):
    text = f"{row.get('title','')} {row.get('description','')}".lower()
    if any(k in text for k in SMALL_FIX_KEYWORDS):
        return True
    imp = (row.get("improvement_type","") or "").strip().lower()
    cat = (row.get("category","") or "").strip().lower()
    if imp in ("logging", "guard", "diagnostics"):
        return True
    if cat in ("observability",) and not has_structural_signal(row):
        return True
    return False

def score_boost_for_strategy(row, force_structural):
    if not force_structural:
        return row
    text = f"{row.get('title','')} {row.get('description','')}".lower()
    score = float(row.get("score", 0) or 0)
    priority = int(row.get("priority", 0) or 0)
    quality = float(row.get("quality_score", 0) or 0)
    if has_structural_signal(row):
        score += 18
        priority += 15
        quality += 0.08
    if "business execution" in text or "ai employee" in text or "runtime loop" in text:
        score += 8
        priority += 8
        quality += 0.04
    row["score"] = score
    row["priority"] = priority
    row["quality_score"] = quality
    return clamp(row)

def total_count(con, path):
    row = con.execute("""
    select count(*)
    from dev_proposals
    where lower(coalesce(target_system,'')) = lower(?)
    """, (path,)).fetchone()
    return int(row[0] or 0) if row else 0

def target_limit_allowed(con, path):
    n = total_count(con, path)
    if n >= 12:
        return False, f"target_total_cap:{n}"
    return True, "ok"


def closed_count(con, path):
    r = con.execute("""
    select count(*)
    from dev_proposals
    where lower(coalesce(target_system,'')) = lower(?)
      and coalesce(status,'')='closed'
    """, (path,)).fetchone()
    try:
        return int(r[0] or 0)
    except:
        return 0

def target_rank(con, path):
    row = con.execute("""
    select id, coalesce(status,'')
    from dev_proposals
    where lower(coalesce(target_system,'')) = lower(?)
    order by id desc
    limit 1
    """, (path,)).fetchone()
    if not row:
        return path_structural_score(path) * 1000
    try:
        last_id = int(row["id"])
        last_status = (row["status"] or "").lower()
    except:
        last_id = int(row[0])
        last_status = (row[1] or "").lower()
    ccount = closed_count(con, path)
    tcount = total_count(con, path)
    closed_bonus = min(ccount * 2500, 15000)
    total_penalty = min(max(tcount - 3, 0) * 3500, 28000)
    structural_bonus = path_structural_score(path) * 1000
    base = last_id
    if last_status == "closed":
        return 900000 + closed_bonus + structural_bonus - total_penalty - base
    if last_status == "merged":
        return 500000 + closed_bonus + structural_bonus - total_penalty - base
    return 100000 + closed_bonus + structural_bonus - total_penalty - base

def recent_improvement_types(con, path, limit_n=3):
    rows = con.execute("""
    select coalesce(improvement_type,'')
    from dev_proposals
    where lower(coalesce(target_system,'')) = lower(?)
      and coalesce(improvement_type,'') != ''
    order by id desc
    limit ?
    """, (path, limit_n)).fetchall()
    vals = set()
    for r in rows:
        try:
            v = r["improvement_type"]
        except:
            v = r[0]
        if v:
            vals.add(str(v).strip().lower())
    return vals

def improvement_cooldown_hours(cur):
    cur = (cur or "").lower()
    if cur in ("guard", "bugfix"):
        return 2
    if cur in ("optimization", "performance"):
        return 3
    if cur in ("refactor", "logging"):
        return 4
    return 3

def improvement_allowed(con, path, row):
    cur = (row["improvement_type"] or "").lower().strip()
    if not cur:
        return True, "ok"
    h = improvement_cooldown_hours(cur)
    last = con.execute("""
    select cast((strftime('%s','now') - strftime('%s', created_at))/3600 as integer)
    from dev_proposals
    where lower(coalesce(target_system,'')) = lower(?)
      and lower(coalesce(improvement_type,'')) = lower(?)
    order by id desc
    limit 1
    """, (path, cur)).fetchone()
    if last and last[0] is not None and int(last[0]) < h:
        return False, f"improvement_cooldown:{cur}:{int(last[0])}h<{h}h"
    return True, "ok"

def main():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    try:
        con.execute("pragma journal_mode=WAL")
    except:
        pass

    seen_titles = recent_titles(con)
    targets = sorted(list_targets(), key=lambda x: target_rank(con, x), reverse=True)
    inserted = 0
    force_structural = final_sanity_healthy(con)
    structural_context = recent_structural_context(con, 8)

    print("[innovation] force_structural=", force_structural, flush=True)
    print("[innovation] structural_context=", structural_context[:500], flush=True)
    print("[innovation] ranked_targets_top=", [(x, target_rank(con, x), path_structural_score(x), closed_count(con, x), total_count(con, x)) for x in targets[:12]], flush=True)
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
            row = clamp(ask_llm(path, code, render_history(history), structural_context, force_structural))
            row = score_boost_for_strategy(row, force_structural)
        except Exception as e:
            print(repr(e), flush=True)
            continue

        if row["title"].lower() in seen_titles:
            print(f"[skip] target={path} reason=duplicate_title", flush=True)
            continue
        if force_structural and is_small_fix(row):
            print(f"[skip] target={path} reason=small_fix_blocked", flush=True)
            continue
        if force_structural and not has_structural_signal(row):
            print(f"[skip] target={path} reason=missing_structural_signal", flush=True)
            continue
        ok2, reason2 = improvement_allowed(con, path, row)
        if not ok2:
            print(f"[skip] target={path} reason={reason2}", flush=True)
            continue
        ok3, reason3 = target_limit_allowed(con, path)
        if not ok3:
            print(f"[skip] target={path} reason={reason3}", flush=True)
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
