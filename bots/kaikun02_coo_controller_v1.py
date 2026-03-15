import json
import os
import sqlite3
import subprocess
from pathlib import Path

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
ROOT = Path("/Users/doyopc/AI/openclaw-factory-daemon")
AUDIT = ROOT / "reports" / "audit_20260315"
OUT_MD = AUDIT / "kaikun02_coo_decision.md"
OUT_JSON = AUDIT / "kaikun02_coo_decision.json"

SAFE_PROD = [
    "open_pr_guard_v1",
    "dev_pr_watcher_v1",
    "dev_pr_creator_v1",
    "proposal_promoter_v1",
    "spec_refiner_v2",
    "spec_decomposer_v1",
    "proposal_throttle_engine_v1",
    "learning_result_writer_v1",
]

BLOCKED = [
    "innovation_engine_v1",
    "strategy_engine_v1",
    "proposal_builder_loop_v1",
    "reasoning_engine_v1",
]

DOCS_PRIORITY = [
    "docs/06_CURRENT_STATE.md",
    "docs/10_RUNTIME_AUDIT_STATUS.md",
    "docs/12_KAIKUN02_DECISION_PROTOCOL.md",
    "docs/99_CONNECTED_RUNTIME_PATCH.md",
    "../openclaw-factory-daemon/reports/audit_20260315/final_runtime_status.md",
    "../openclaw-factory-daemon/reports/audit_20260315/final_task_completion.md",
    "../openclaw-factory-daemon/reports/audit_20260315/kaikun02_runtime_memo.md",
]

def launch_state(label: str):
    full = f"jp.openclaw.{label}"
    uid = subprocess.check_output(["id", "-u"], text=True).strip()
    r = subprocess.run(
        ["launchctl", "print", f"gui/{uid}/{full}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    text = r.stdout or ""
    if "could not find service" in text.lower():
        return "stopped"
    if "state = running" in text:
        return "running"
    if "state = spawn scheduled" in text:
        return "spawn_scheduled"
    return "stopped"

def stop_label(label: str):
    full = f"jp.openclaw.{label}"
    uid = subprocess.check_output(["id", "-u"], text=True).strip()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}/{full}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-f", f"{label}.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def db_rows():
    c = sqlite3.connect(DB, timeout=120)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")

    unique_open_prs = c.execute("""
        select count(distinct pr_url)
        from dev_proposals
        where coalesce(pr_status,'')='open'
          and coalesce(pr_url,'')<>''
    """).fetchone()[0]

    duplicate_open_pr_url = c.execute("""
        select count(*)
        from (
          select pr_url
          from dev_proposals
          where coalesce(pr_status,'')='open'
            and coalesce(pr_url,'')<>''
          group by pr_url
          having count(*) > 1
        )
    """).fetchone()[0]

    blank_source_open_rows = c.execute("""
        select count(*)
        from dev_proposals
        where coalesce(pr_status,'')='open'
          and coalesce(pr_url,'')<>''
          and coalesce(source_ai,'')=''
    """).fetchone()[0]

    open_pr_by_source = c.execute("""
        select coalesce(source_ai,''), count(distinct pr_url)
        from dev_proposals
        where coalesce(pr_status,'')='open'
          and coalesce(pr_url,'')<>''
        group by 1
        order by 2 desc, 1 asc
    """).fetchall()

    next_touch = c.execute("""
        select
          id as id,
          coalesce(title,'') as title,
          coalesce(source_ai,'') as source_ai,
          coalesce(dev_stage,'') as dev_stage,
          coalesce(spec_stage,'') as spec_stage,
          coalesce(pr_status,'') as pr_status
        from dev_proposals
        where coalesce(pr_status,'')='open'
          and coalesce(pr_url,'')<>''
        order by
          case
            when coalesce(spec_stage,'')='raw' then 0
            when coalesce(spec_stage,'')='refined' then 1
            when coalesce(spec_stage,'')='decomposed' and coalesce(dev_stage,'') in ('ready','execute_now','pr_created','open') then 2
            else 9
          end,
          id desc
        limit 3
    """).fetchall()

    c.close()
    return {
        "unique_open_prs": int(unique_open_prs),
        "duplicate_open_pr_url": int(duplicate_open_pr_url),
        "blank_source_open_rows": int(blank_source_open_rows),
        "open_pr_by_source": [[str(r[0]), int(r[1])] for r in open_pr_by_source],
        "next_touch": [
            {
                "id": int(r["id"]),
                "title": str(r["title"]),
                "source_ai": str(r["source_ai"]),
                "dev_stage": str(r["dev_stage"]),
                "spec_stage": str(r["spec_stage"]),
                "pr_status": str(r["pr_status"]),
            }
            for r in next_touch
        ],
    }

def docs_gap_exists():
    return 1 if (AUDIT / "docs_live_gap.md").exists() else 0



def build_action_templates(rows):
    out = []
    for r in rows:
        pid = int(r["id"])
        title = str(r["title"] or "")
        src = str(r["source_ai"] or "")
        dev_stage = str(r["dev_stage"] or "")
        spec_stage = str(r["spec_stage"] or "")
        pr_status = str(r["pr_status"] or "")

        if spec_stage == "raw":
            action = f"proposal {pid} は raw のため spec_refiner_v2 の通過確認を優先"
            command = f"sqlite3 /Users/doyopc/AI/openclaw-factory/data/openclaw.db \"select id,title,source_ai,dev_stage,spec_stage,pr_status from dev_proposals where id={pid};\""
        elif spec_stage == "refined":
            action = f"proposal {pid} は refined のため spec_decomposer_v1 の通過確認を優先"
            command = f"sqlite3 /Users/doyopc/AI/openclaw-factory/data/openclaw.db \"select id,title,source_ai,dev_stage,spec_stage,pr_status from dev_proposals where id={pid};\""
        elif spec_stage == "decomposed" and dev_stage in ("ready", "execute_now", "pr_created", "open"):
            action = f"proposal {pid} は decomposed 済みのため creator/watcher 側の進行確認を優先"
            command = f"sqlite3 /Users/doyopc/AI/openclaw-factory/data/openclaw.db \"select id,title,source_ai,dev_stage,spec_stage,pr_status,pr_number,pr_url from dev_proposals where id={pid};\""
        else:
            action = f"proposal {pid} の状態監査を優先"
            command = f"sqlite3 /Users/doyopc/AI/openclaw-factory/data/openclaw.db \"select * from dev_proposals where id={pid};\""

        out.append({
            "id": pid,
            "title": title,
            "source_ai": src,
            "action": action,
            "command": command,
        })
    return out

def main():
    AUDIT.mkdir(parents=True, exist_ok=True)

    safe_state = {b: launch_state(b) for b in SAFE_PROD}
    blocked_state = {b: launch_state(b) for b in BLOCKED}

    rows = db_rows()
    gate_ok = (
        rows["unique_open_prs"] <= 15 and
        rows["duplicate_open_pr_url"] == 0 and
        rows["blank_source_open_rows"] == 0
    )

    reasons = []
    if rows["unique_open_prs"] > 15:
        reasons.append(f"unique_open_prs={rows['unique_open_prs']}>15")
    if rows["duplicate_open_pr_url"] != 0:
        reasons.append(f"duplicate_open_pr_url={rows['duplicate_open_pr_url']}")
    if rows["blank_source_open_rows"] != 0:
        reasons.append(f"blank_source_open_rows={rows['blank_source_open_rows']}")

    if not gate_ok:
        for b, st in blocked_state.items():
            if st in ("running", "spawn_scheduled"):
                stop_label(b)

    blocked_now = {b: launch_state(b) for b in BLOCKED}
    active_now = {b: launch_state(b) for b in SAFE_PROD}

    action = "start_allowed" if gate_ok else "keep_stopped_only"
    reason = "health gate pass" if gate_ok else ("; ".join(reasons) if reasons else "health gate fail")

    result = {
        "gate_ok": gate_ok,
        "action": action,
        "reason": reason,
        "unique_open_prs": rows["unique_open_prs"],
        "duplicate_open_pr_url": rows["duplicate_open_pr_url"],
        "blank_source_open_rows": rows["blank_source_open_rows"],
        "docs_gap_exists": docs_gap_exists(),
        "active_now": [b for b, st in active_now.items() if st in ("running", "spawn_scheduled")],
        "blocked_now": [b for b, st in blocked_now.items() if st in ("running", "spawn_scheduled")],
        "next_touch": rows["next_touch"],
        "open_pr_by_source": rows["open_pr_by_source"],
        "docs_priority": DOCS_PRIORITY,
    }

    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = []
    md.append("# KAIKUN02 COO DECISION")
    md.append("")
    md.append("## judgment")
    md.append(f"- gate_ok: {'yes' if result['gate_ok'] else 'no'}")
    md.append(f"- action: {result['action']}")
    md.append(f"- reason: {result['reason']}")
    md.append("")
    md.append("## active_now")
    if result["active_now"]:
        for x in result["active_now"]:
            md.append(f"- {x}")
    else:
        md.append("- none")
    md.append("")
    md.append("## blocked_now")
    if result["blocked_now"]:
        for x in result["blocked_now"]:
            md.append(f"- {x}")
    else:
        md.append("- none")
    md.append("")
    md.append("## next_touch")
    if result["next_touch"]:
        for x in result["next_touch"]:
            md.append(f"- {x['id']} | {x['title']} | {x['source_ai']} | {x['dev_stage']} | {x['spec_stage']} | {x['pr_status']}")
    else:
        md.append("- none")
    md.append("")
    md.append("## action_templates")
    for x in result["action_templates"]:
        md.append(f"- {x['id']} | {x['action']}")
        md.append(f"  - cmd: {x['command']}")
    md.append("")
    md.append("## db_watch")
    md.append(f"- unique_open_prs: {result['unique_open_prs']}")
    md.append(f"- duplicate_open_pr_url: {result['duplicate_open_pr_url']}")
    md.append(f"- blank_source_open_rows: {result['blank_source_open_rows']}")
    md.append("")
    md.append("## open_pr_by_source")
    for k, v in result["open_pr_by_source"]:
        md.append(f"- {k or '(blank)'}: {v}")
    md.append("")
    md.append("## docs_priority")
    for x in result["docs_priority"]:
        md.append(f"- {x}")

    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
