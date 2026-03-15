import json
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
REPO = os.environ.get("GITHUB_REPO") or "douyo01-byte/openclaw-factory"
GH = os.environ.get("GH_BIN") or shutil.which("gh") or "/opt/homebrew/bin/gh"
ROOT = Path("/Users/doyopc/AI/openclaw-factory-daemon")
OUT_JSON = ROOT / "reports" / "audit_20260315" / "open_pr_blocked_report.json"
OUT_MD = ROOT / "reports" / "audit_20260315" / "open_pr_blocked_report.md"

def sh(cmd):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stdout.strip())
    return r.stdout.strip()

def db():
    conn = sqlite3.connect(DB, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma busy_timeout=30000")
    try:
        conn.execute("pragma journal_mode=WAL")
    except Exception:
        pass
    return conn

def pick_rows(conn):
    return conn.execute("""
    select
      id,
      coalesce(title,'') as title,
      coalesce(source_ai,'') as source_ai,
      coalesce(pr_number,'') as pr_number,
      coalesce(pr_url,'') as pr_url,
      coalesce(pr_status,'') as pr_status,
      coalesce(dev_stage,'') as dev_stage,
      coalesce(spec_stage,'') as spec_stage
    from dev_proposals
    where coalesce(pr_status,'')='open'
      and coalesce(pr_number,'')<>''
      and coalesce(pr_url,'')<>''
    order by id desc
    limit 200
    """).fetchall()

def pr_view(pr_number):
    out = sh([
        GH, "pr", "view", str(pr_number),
        "--repo", REPO,
        "--json",
        "number,state,isDraft,mergeStateStatus,reviewDecision,mergedAt,url,title"
    ])
    return json.loads(out)

def classify(pr):
    if pr.get("mergedAt"):
        return "merged"
    if bool(pr.get("isDraft")):
        return "draft"
    review = str(pr.get("reviewDecision") or "")
    if review == "CHANGES_REQUESTED":
        return "changes_requested"
    merge_state = str(pr.get("mergeStateStatus") or "")
    if merge_state == "DIRTY":
        return "dirty_conflict"
    if merge_state == "BLOCKED":
        return "blocked"
    if merge_state == "BEHIND":
        return "behind_base"
    if merge_state == "UNKNOWN":
        return "unknown"
    if merge_state == "UNSTABLE":
        return "unstable"
    if str(pr.get("state") or "").upper() == "OPEN":
        return "mergeable_or_waiting"
    return "other"

def main():
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    conn = db()
    try:
        rows = pick_rows(conn)
        out = []
        for r in rows:
            try:
                pr = pr_view(int(r["pr_number"]))
                out.append({
                    "proposal_id": int(r["id"]),
                    "title": str(r["title"]),
                    "source_ai": str(r["source_ai"]),
                    "pr_number": int(r["pr_number"]),
                    "pr_url": str(r["pr_url"]),
                    "dev_stage": str(r["dev_stage"]),
                    "spec_stage": str(r["spec_stage"]),
                    "pr_status": str(r["pr_status"]),
                    "reviewDecision": str(pr.get("reviewDecision") or ""),
                    "mergeStateStatus": str(pr.get("mergeStateStatus") or ""),
                    "isDraft": bool(pr.get("isDraft")),
                    "state": str(pr.get("state") or ""),
                    "bucket": classify(pr),
                })
            except Exception as e:
                out.append({
                    "proposal_id": int(r["id"]),
                    "title": str(r["title"]),
                    "source_ai": str(r["source_ai"]),
                    "pr_number": int(r["pr_number"]),
                    "pr_url": str(r["pr_url"]),
                    "dev_stage": str(r["dev_stage"]),
                    "spec_stage": str(r["spec_stage"]),
                    "pr_status": str(r["pr_status"]),
                    "reviewDecision": "",
                    "mergeStateStatus": "",
                    "isDraft": False,
                    "state": "",
                    "bucket": f"error:{e}",
                })

        OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

        order = [
            "dirty_conflict",
            "changes_requested",
            "blocked",
            "behind_base",
            "unstable",
            "draft",
            "unknown",
            "mergeable_or_waiting",
            "merged",
        ]

        lines = ["# OPEN PR BLOCKED REPORT", ""]
        for bucket in order:
            xs = [x for x in out if x["bucket"] == bucket]
            if not xs:
                continue
            lines.append(f"## {bucket} ({len(xs)})")
            for x in xs:
                lines.append(
                    f"- {x['proposal_id']} | PR#{x['pr_number']} | {x['source_ai']} | {x['title']} | merge={x['mergeStateStatus']} | review={x['reviewDecision']}"
                )
            lines.append("")

        errs = [x for x in out if str(x["bucket"]).startswith("error:")]
        if errs:
            lines.append(f"## errors ({len(errs)})")
            for x in errs:
                lines.append(
                    f"- {x['proposal_id']} | PR#{x['pr_number']} | {x['source_ai']} | {x['title']} | {x['bucket']}"
                )
            lines.append("")

        OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"rows={len(out)}", flush=True)
        print(f"json={OUT_JSON}", flush=True)
        print(f"md={OUT_MD}", flush=True)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
