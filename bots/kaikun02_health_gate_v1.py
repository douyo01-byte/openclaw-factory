import json
import os
import sqlite3
import subprocess
from pathlib import Path

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
HOME = str(Path.home())
UID = subprocess.check_output(["id", "-u"], text=True).strip()

SAFE_PROD_NOW = [
    "open_pr_guard_v1",
    "dev_pr_watcher_v1",
    "dev_pr_creator_v1",
    "proposal_promoter_v1",
    "spec_refiner_v2",
    "spec_decomposer_v1",
    "proposal_throttle_engine_v1",
    "learning_result_writer_v1",
]

KEEP_STOPPED = [
    "innovation_engine_v1",
    "strategy_engine_v1",
    "proposal_builder_loop_v1",
    "reasoning_engine_v1",
]

DOCS_PRIORITY = [
    "docs/06_CURRENT_STATE.md",
    "docs/10_RUNTIME_AUDIT_STATUS.md",
    "docs/99_CONNECTED_RUNTIME_PATCH.md",
    "../openclaw-factory-daemon/reports/audit_20260315/final_runtime_status.md",
    "../openclaw-factory-daemon/reports/audit_20260315/final_task_completion.md",
    "../openclaw-factory-daemon/reports/audit_20260315/kaikun02_runtime_memo.md",
]

def q1(conn, sql):
    row = conn.execute(sql).fetchone()
    return row[0] if row else 0

def label(name):
    return f"jp.openclaw.{name}"

def launchctl_print(lb):
    try:
        out = subprocess.check_output(
            ["launchctl", "print", f"gui/{UID}/{lb}"],
            text=True,
            stderr=subprocess.STDOUT,
        )
        return out
    except subprocess.CalledProcessError as e:
        return e.output

def is_running(name):
    out = launchctl_print(label(name))
    return "state = running" in out

def stop_label(name):
    lb = label(name)
    plist = f"{HOME}/Library/LaunchAgents/{lb}.plist"
    subprocess.run(["launchctl", "bootout", f"gui/{UID}/{lb}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["launchctl", "disable", f"gui/{UID}/{lb}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if Path(plist).exists():
        subprocess.run(["pkill", "-f", f"{name}.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    conn = sqlite3.connect(DB, timeout=30)
    conn.execute("pragma busy_timeout=30000")

    unique_open_prs = q1(conn, """
        select count(distinct pr_url)
        from dev_proposals
        where coalesce(pr_status,'')='open'
          and coalesce(pr_url,'')<>''
    """)

    duplicate_open_pr_url = q1(conn, """
        select count(*)
        from (
          select pr_url
          from dev_proposals
          where coalesce(pr_status,'')='open'
            and coalesce(pr_url,'')<>''
          group by pr_url
          having count(*) > 1
        )
    """)

    blank_source_open_rows = q1(conn, """
        select count(*)
        from dev_proposals
        where coalesce(pr_status,'')='open'
          and coalesce(pr_url,'')<>''
          and coalesce(source_ai,'')=''
    """)

    docs_gap_exists = int(Path("reports/audit_20260315/docs_live_gap.md").exists())

    open_pr_by_source = conn.execute("""
        select coalesce(source_ai,''), count(distinct pr_url)
        from dev_proposals
        where coalesce(pr_status,'')='open'
          and coalesce(pr_url,'')<>''
        group by 1
        order by 2 desc
    """).fetchall()

    conn.close()

    gate_ok = (
        unique_open_prs <= 15 and
        duplicate_open_pr_url == 0 and
        blank_source_open_rows == 0
    )

    if not gate_ok:
        for b in KEEP_STOPPED:
            stop_label(b)

    running_safe = [b for b in SAFE_PROD_NOW if is_running(b)]
    running_blocked = [b for b in KEEP_STOPPED if is_running(b)]

    reasons = []
    if unique_open_prs > 15:
        reasons.append(f"unique_open_prs={unique_open_prs}>15")
    if duplicate_open_pr_url > 0:
        reasons.append(f"duplicate_open_pr_url={duplicate_open_pr_url}")
    if blank_source_open_rows > 0:
        reasons.append(f"blank_source_open_rows={blank_source_open_rows}")

    result = {
        "gate_ok": gate_ok,
        "reasons": reasons,
        "safe_prod_now": SAFE_PROD_NOW,
        "keep_stopped": KEEP_STOPPED,
        "running_safe": running_safe,
        "running_blocked": running_blocked,
        "unique_open_prs": unique_open_prs,
        "duplicate_open_pr_url": duplicate_open_pr_url,
        "blank_source_open_rows": blank_source_open_rows,
        "open_pr_by_source": open_pr_by_source,
        "docs_priority": DOCS_PRIORITY,
        "docs_gap_exists": docs_gap_exists,
        "judgment": (
            "段階起動してよい"
            if gate_ok else
            "起動禁止。keep_stopped を維持し、safe_prod_now のみ運用"
        ),
    }

    Path("reports/audit_20260315").mkdir(parents=True, exist_ok=True)
    Path("obs/runtime_generated/kaikun02_health_gate.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# KAIKUN02 HEALTH GATE")
    lines.append("")
    lines.append(f"- gate_ok: {'yes' if gate_ok else 'no'}")
    lines.append(f"- unique_open_prs: {unique_open_prs}")
    lines.append(f"- duplicate_open_pr_url: {duplicate_open_pr_url}")
    lines.append(f"- blank_source_open_rows: {blank_source_open_rows}")
    lines.append(f"- docs_gap_exists: {docs_gap_exists}")
    lines.append("")
    lines.append("## judgment")
    lines.append(f"- {result['judgment']}")
    lines.append("")
    lines.append("## reasons")
    if reasons:
        for r in reasons:
            lines.append(f"- {r}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## running_safe")
    for b in running_safe:
        lines.append(f"- {b}")
    lines.append("")
    lines.append("## running_blocked")
    if running_blocked:
        for b in running_blocked:
            lines.append(f"- {b}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## open_pr_by_source")
    for k, v in open_pr_by_source:
        lines.append(f"- {k or '(blank)'}: {v}")
    lines.append("")
    lines.append("## docs_priority")
    for x in DOCS_PRIORITY:
        lines.append(f"- {x}")
    Path("obs/runtime_generated/kaikun02_health_gate.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
