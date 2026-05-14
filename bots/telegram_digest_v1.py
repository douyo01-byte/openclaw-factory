from __future__ import annotations
import argparse
import os
import json
import sqlite3
import urllib.parse
import urllib.request
from collections import defaultdict

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
TG_TOKEN = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
TG_CHAT_ID = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()

WINDOW_MIN = int(os.environ.get("TELEGRAM_DIGEST_WINDOW_MIN", "10"))
MAX_LINES = int(os.environ.get("TELEGRAM_DIGEST_MAX_LINES", "40"))
MAX_GROUPS = int(os.environ.get("TELEGRAM_DIGEST_MAX_GROUPS", "8"))
DRY_RUN = os.environ.get("TELEGRAM_DIGEST_DRY_RUN", "0") == "1"
NOISY_TARGETS = {"telegram_digest", "telegram_report"}
NOISY_MODES = {"DIGEST"}
ARTIFACT_MARKERS = ("public_preview/", "artifact=", ".html", ".md")
IMPORTANCE_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    try:
        c.execute("pragma journal_mode=WAL")
    except Exception:
        pass
    return c

def head(s: str, n: int = 80) -> str:
    s = (s or "").replace("\r", "\n").replace("\n", " ").strip()
    s = " ".join(s.split())
    return s[:n]

def compact(s: str, n: int = 180) -> str:
    s = " ".join((s or "").replace("\r", "\n").replace("\n", " ").split())
    return s[:n]

def strip_exec(text: str) -> str:
    lines = []
    for line in (text or "").replace("\r", "\n").splitlines():
        if line.strip().lower().startswith(("script=", "arg=")):
            lines.append(line.strip())
    return " / ".join(lines)

def artifact_hint(*texts: str) -> str:
    for text in texts:
        for token in (text or "").replace("\r", "\n").split():
            clean = token.strip("`'\"(),[]")
            if any(marker in clean for marker in ARTIFACT_MARKERS):
                return compact(clean, 120)
    return ""

def task_family(row) -> str:
    text = row["task_text"] or ""
    target = row["target_bot"] or "-"
    mode = row["mode"] or "-"
    if "[EXEC]" in text:
        exec_line = strip_exec(text)
        return f"exec:{exec_line or target}"
    if "[REVENUE" in text:
        return "revenue"
    if "[CODEX" in text or "codex" in text.lower():
        return "codex"
    if target in NOISY_TARGETS or mode in NOISY_MODES:
        return "digest-noise"
    return f"{target}:{mode}"

def is_noisy(row) -> bool:
    target = row["target_bot"] or ""
    mode = row["mode"] or ""
    text = row["task_text"] or ""
    reply = row["reply_text"] or ""
    if target in NOISY_TARGETS or mode in NOISY_MODES:
        return True
    if "no new rows" in reply.lower():
        return True
    if text.startswith("[REVENUE_BANDIT_DIGEST]"):
        return False
    return False

def infer_instruction(items) -> str:
    for row in items:
        text = row["clean_prompt"] or row["task_text"]
        if text and not text.strip().startswith("[EXEC]"):
            return compact(text, 160)
    return compact(items[0]["task_text"], 160)

def infer_execution(items) -> str:
    execs = []
    for row in items:
        exec_line = strip_exec(row["task_text"])
        if exec_line and exec_line not in execs:
            execs.append(exec_line)
    if execs:
        return compact(" | ".join(execs[:2]), 180)
    bots = sorted({(r["target_bot"] or "-") for r in items})
    modes = sorted({(r["mode"] or "-") for r in items})
    return f"bots={','.join(bots)} mode={','.join(modes)}"

def infer_result(items) -> str:
    statuses = defaultdict(int)
    for row in items:
        statuses[row["status"] or "-"] += 1
    status_text = ", ".join(f"{k}={v}" for k, v in sorted(statuses.items()))
    for row in reversed(items):
        text = row["result_text"] or row["reply_text"] or row["validation_reason"] or row["exec_bridge_reason"]
        if text:
            artifact = artifact_hint(row["result_text"], row["reply_text"], row["task_text"])
            suffix = f" artifact={artifact}" if artifact else ""
            return compact(f"{status_text}; {text}{suffix}", 220)
    return status_text

def infer_next_action(items) -> str:
    statuses = {r["status"] for r in items}
    reasons = " ".join((r["validation_reason"] or r["exec_bridge_reason"] or r["reply_text"] or "") for r in items).lower()
    if "failed" in statuses:
        return "failed itemを原因別に確認し、必要なら最小修正して再実行"
    if "new" in statuses or "running" in statuses:
        return "未完了taskの進行を次回digestで確認"
    if "unknown mode" in reasons or "invalid arg" in reasons:
        return "run_python.sh mode/arg 経路を確認"
    if "schema_missing" in reasons:
        return "migration ledger適用状況を確認"
    return "追加対応なし。次のqueued taskを監視"

def infer_risk(items) -> str:
    text = " ".join(
        (r["validation_reason"] or "") + " " + (r["exec_bridge_reason"] or "") + " " + (r["reply_text"] or "")
        for r in items
    ).lower()
    if "schema_missing" in text:
        return "schema migration未適用の可能性"
    if "unable to open database" in text or "database is locked" in text:
        return "DB open/locking risk"
    if "too many open files" in text:
        return "file descriptor leak risk"
    if "unknown mode" in text or "invalid arg" in text:
        return "EXEC arg/mode routing risk"
    if any((r["status"] or "") == "failed" for r in items):
        return "failed taskあり"
    return "明示的な残リスクなし"


def row_text(row) -> str:
    return " ".join(
        str(row[k] or "")
        for k in (
            "task_text",
            "clean_prompt",
            "reply_text",
            "result_text",
            "validation_reason",
            "exec_bridge_reason",
        )
    )


def duplicate_group_key(row) -> str:
    text = row_text(row)
    if "[WINNER_ONLY]" in text:
        theme = text.split("テーマ:", 1)[-1] if "テーマ:" in text else text
        return "winner_only:" + compact(theme, 80)
    if "ConnectionError" in text:
        return "error:ConnectionError"
    if (row["status"] or "") == "failed":
        return f"failure:{task_family(row)}:{compact(text, 80)}"
    parent_id = int(row["parent_task_id"] or 0)
    key_parent = parent_id if parent_id > 0 else int(row["id"])
    return f"{task_family(row)}:{key_parent}"


def score_digest_item(row, compressed_count: int = 0) -> dict:
    text = row_text(row)
    low = text.lower()
    status = row["status"] or ""
    family = task_family(row)
    if status == "failed" or "schema_missing" in low or "database is locked" in low:
        importance = "critical"
        actionability = "now"
    elif "connectionerror" in low or "timeout" in low or status in {"retry", "invalid_output"}:
        importance = "high"
        actionability = "now" if compressed_count else "watch"
    elif "[winner_only]" in low or status in {"new", "started", "running"}:
        importance = "medium"
        actionability = "later" if "[winner_only]" in low else "watch"
    elif is_noisy(row):
        importance = "low"
        actionability = "ignore"
    else:
        importance = "low" if status == "done" else "medium"
        actionability = "watch"
    return {
        "importance": importance,
        "actionability": actionability,
        "duplicate_group_key": duplicate_group_key(row),
        "compressed_count": compressed_count,
        "family": family,
    }


def scored_digest_items(rows) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[duplicate_group_key(row)].append(row)
    items = []
    for key, group in groups.items():
        group = sorted(group, key=lambda r: int(r["id"]))
        primary = group[-1]
        score = score_digest_item(primary, max(0, len(group) - 1))
        statuses = defaultdict(int)
        for row in group:
            statuses[row["status"] or "-"] += 1
        group_text = "\n".join(row_text(row).lower() for row in group)
        if statuses.get("failed", 0) or "schema_missing" in group_text or "database is locked" in group_text:
            score["importance"] = "critical"
            score["actionability"] = "now"
        elif "connectionerror" in group_text and len(group) > 1:
            score["importance"] = "high"
            score["actionability"] = "now"
        items.append({
            "key": key,
            "rows": group,
            "primary": primary,
            "score": score,
            "statuses": dict(statuses),
            "count": len(group),
        })
    return sorted(
        items,
        key=lambda item: (
            IMPORTANCE_ORDER.get(item["score"]["importance"], 9),
            0 if item["score"]["actionability"] == "now" else 1,
            -item["count"],
            -int(item["primary"]["id"]),
        ),
    )


def _status_line(items: list[dict]) -> str:
    if any(i["score"]["importance"] == "critical" for i in items):
        return "unstable / needs attention"
    if any(i["score"]["importance"] == "high" for i in items):
        return "degraded / watch closely"
    return "stable / watch"


def _top_issue(items: list[dict]) -> str:
    if not items:
        return "no material issue"
    first = items[0]
    text = row_text(first["primary"])
    if "ConnectionError" in text:
        return f"LLM ConnectionError repeated {first['count']} time(s)"
    if first["key"].startswith("winner_only:") and first["count"] > 1:
        return f"duplicate WINNER_ONLY tasks detected ({first['count']})"
    if first["score"]["importance"] in {"critical", "high"}:
        return compact(infer_result(first["rows"]), 120)
    return compact(infer_instruction(first["rows"]), 120)


def _goal_summary() -> dict:
    try:
        from openclaw_goal_reader_v1 import read_active_goal

        return read_active_goal()
    except Exception as e:
        return {
            "ok": False,
            "active_goal": "",
            "current_focus": "",
            "next_best_step": "",
            "blocked_by": [f"goal_reader_error:{e!r}"],
            "safety_status": "read-only; goal reader unavailable",
            "expected_value": "",
        }


def _latest_result(items: list[dict]) -> str:
    for item in items:
        for row in reversed(item["rows"]):
            text = row["result_text"] or row["reply_text"] or row["validation_reason"] or row["exec_bridge_reason"]
            if text:
                return compact(text, 120)
    if any(i["primary"]["status"] == "new" for i in items):
        return "new task created"
    return "no material result"


def _runtime_health(items: list[dict]) -> str:
    text = "\n".join(row_text(r) for item in items for r in item["rows"])
    status_core_rows = [
        r for item in items for r in item["rows"]
        if "status_core.sh" in row_text(r)
    ]
    if status_core_rows and any((r["status"] or "") == "done" for r in status_core_rows):
        return "status_core.sh succeeded\n- services appear running"
    if "ConnectionError" in text:
        return "LLM transport unstable\n- local services may still be running"
    if any(item["score"]["importance"] == "critical" for item in items):
        return "runtime needs attention\n- failure group present"
    return "no local runtime failure detected"


def _operator_next(items: list[dict]) -> str:
    if any("ConnectionError" in row_text(r) for item in items for r in item["rows"]):
        return "Review Dev Autopilot dashboard -> approve only dry-run cleanup simulation if recommended."
    if any(item["key"].startswith("winner_only:") and item["count"] > 1 for item in items):
        return "Compress duplicate WINNER_ONLY tasks, then continue only the newest safe item."
    if any(item["score"]["importance"] == "critical" for item in items):
        return "Inspect the top failure group before approving any execution."
    return "Review the top recommendation and keep execution approval-gated."


def _risk_lines(items: list[dict]) -> list[str]:
    text = "\n".join(row_text(r) for item in items for r in item["rows"]).lower()
    risks = []
    if "connectionerror" in text or "timeout" in text:
        risks.append("retry amplification")
    if any(item["key"].startswith("winner_only:") and item["count"] > 1 for item in items):
        risks.append("duplicate task noise")
    if any(item["score"]["importance"] == "critical" for item in items):
        risks.append("failed task requires review")
    if not risks:
        risks.append("unclear task priority")
    return risks[:4]


def build_readable_digest(rows) -> str:
    visible = [r for r in rows if not is_noisy(r)]
    noisy_count = len(rows) - len(visible)
    items = scored_digest_items(visible)
    compressed_count = noisy_count + sum(max(0, item["count"] - 1) for item in items)
    hidden_count = compressed_count + max(0, len(items) - 3)
    goal = _goal_summary()
    winner_items = [i for i in items if i["key"].startswith("winner_only:")]
    conn_items = [i for i in items if i["key"] == "error:ConnectionError"]
    top_items = items[:3]

    lines = [
        f"OpenClaw digest {WINDOW_MIN}m",
        f"Status: {_status_line(items)}",
        f"Top issue: {_top_issue(items)}",
        f"Queue: {len(rows)} rows, {hidden_count} compressed",
        "",
        "1. Goal progress",
        f"- OpenClaw mothership goal is {'active' if goal.get('ok') else 'unavailable'}",
        f"- current focus: {goal.get('current_focus') or '-'}",
        f"- latest result: {_latest_result(top_items)}",
        "",
        "2. Revenue/WINNER loop",
    ]
    if winner_items:
        newest = max(int(r["id"]) for item in winner_items for r in item["rows"])
        duplicate_total = sum(max(0, item["count"] - 1) for item in winner_items)
        lines.append(f"- duplicate WINNER_ONLY tasks detected: {duplicate_total} compressed, newest id={newest}")
        lines.append("- action: compress duplicates, continue only newest")
    else:
        lines.append("- no duplicate WINNER_ONLY group detected")
        lines.append("- action: keep revenue work approval-gated")

    lines.extend([
        "",
        "3. Runtime health",
    ])
    for health_line in _runtime_health(items).splitlines():
        lines.append(f"- {health_line}" if not health_line.startswith("- ") else health_line)
    if conn_items:
        lines.append(f"- ConnectionError count summarized once: {sum(i['count'] for i in conn_items)}")

    if top_items:
        lines.extend(["", "Top scored items:"])
        for item in top_items:
            score = item["score"]
            ids = f"{item['rows'][0]['id']}-{item['rows'][-1]['id']}" if item["count"] > 1 else str(item["primary"]["id"])
            lines.append(
                f"- {score['importance']}/{score['actionability']} ids={ids} "
                f"duplicate_group_key={score['duplicate_group_key']} compressed_count={score['compressed_count']}"
            )

    lines.extend([
        "",
        "Operator next:",
        _operator_next(items),
        "",
        "Risks:",
    ])
    lines.extend(f"- {risk}" for risk in _risk_lines(items))
    if hidden_count:
        lines.append(f"- hidden/compressed count: {hidden_count}")

    out = "\n".join(lines).strip()
    return out[:3500] + ("\n\n[truncated]" if len(out) > 3500 else "")


def build_digest(rows) -> str:
    return build_readable_digest(rows)


def build_legacy_digest(rows) -> str:
    visible = [r for r in rows if not is_noisy(r)]
    noisy_count = len(rows) - len(visible)
    groups = defaultdict(list)
    for row in visible:
        parent_id = int(row["parent_task_id"] or 0)
        key_parent = parent_id if parent_id > 0 else int(row["id"])
        groups[(task_family(row), key_parent)].append(row)

    ordered = sorted(
        groups.items(),
        key=lambda kv: max(int(x["id"]) for x in kv[1]),
        reverse=True,
    )

    lines = [
        "OpenClaw execution digest",
        f"window={WINDOW_MIN}m rows={len(rows)} grouped={len(ordered)} noisy_compressed={noisy_count}",
        "",
    ]

    for idx, ((family, parent_id), items) in enumerate(ordered[:MAX_GROUPS], start=1):
        items = sorted(items, key=lambda x: int(x["id"]))
        ids = f"{items[0]['id']}-{items[-1]['id']}" if len(items) > 1 else str(items[0]["id"])
        lines.extend([
            f"{idx}. {family} p={parent_id} ids={ids} items={len(items)}",
            f"   instruction: {infer_instruction(items)}",
            f"   execution: {infer_execution(items)}",
            f"   result: {infer_result(items)}",
            f"   next: {infer_next_action(items)}",
            f"   risk: {infer_risk(items)}",
        ])

    rest = len(ordered) - MAX_GROUPS
    if rest > 0:
        lines.append(f"... {rest} groups compressed")
    if noisy_count:
        lines.append(f"noise: {noisy_count} digest/report housekeeping tasks compressed")

    out = "\n".join(lines).strip()
    return out[:3500] + ("\n\n[truncated]" if len(out) > 3500 else "")


def fetch_digest_rows(c, last_id: int = 0, limit: int | None = None):
    limit_sql = f"limit {int(limit)}" if limit else ""
    return c.execute(f"""
        select
          id,
          coalesce(parent_task_id, 0) as parent_task_id,
          coalesce(task_role, '') as task_role,
          coalesce(target_bot, '') as target_bot,
          coalesce(mode, '') as mode,
          coalesce(status, '') as status,
          coalesce(task_text, '') as task_text,
          coalesce(clean_prompt, '') as clean_prompt,
          coalesce(reply_text, '') as reply_text,
          coalesce(result_text, '') as result_text,
          coalesce(validation_reason, '') as validation_reason,
          coalesce(exec_bridge_reason, '') as exec_bridge_reason,
          coalesce(updated_at, created_at, '') as ts
        from router_tasks
        where id > ?
          and datetime(coalesce(updated_at, created_at)) >= datetime('now', '-{WINDOW_MIN} minutes')
        order by id asc
        {limit_sql}
        """, (last_id,)).fetchall()


def fetch_recent_sample_rows(c, limit: int):
    return list(reversed(c.execute(f"""
        select
          id,
          coalesce(parent_task_id, 0) as parent_task_id,
          coalesce(task_role, '') as task_role,
          coalesce(target_bot, '') as target_bot,
          coalesce(mode, '') as mode,
          coalesce(status, '') as status,
          coalesce(task_text, '') as task_text,
          coalesce(clean_prompt, '') as clean_prompt,
          coalesce(reply_text, '') as reply_text,
          coalesce(result_text, '') as result_text,
          coalesce(validation_reason, '') as validation_reason,
          coalesce(exec_bridge_reason, '') as exec_bridge_reason,
          coalesce(updated_at, created_at, '') as ts
        from router_tasks
        order by id desc
        limit {int(limit)}
        """).fetchall()))

def send_tg(text: str):
    if DRY_RUN:
        print("[telegram_digest_v1] dry_run message_begin", flush=True)
        print(text, flush=True)
        print("[telegram_digest_v1] dry_run message_end", flush=True)
        return
    if not TG_TOKEN or not TG_CHAT_ID:
        print("[telegram_digest_v1] skip send: missing token/chat_id", flush=True)
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": TG_CHAT_ID,
        "text": text,
        "disable_web_page_preview": "true"
    }).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        _ = r.read()

def get_state(c, key: str) -> int:
    row = c.execute("select value from telegram_digest_state where key=?", (key,)).fetchone()
    if not row or row["value"] is None or row["value"] == "":
        return 0
    try:
        return int(row["value"])
    except Exception:
        return 0

def set_state(c, key: str, value: int):
    c.execute("""
    insert into telegram_digest_state(key, value, updated_at)
    values(?, ?, datetime('now'))
    on conflict(key) do update set
      value=excluded.value,
      updated_at=datetime('now')
    """, (key, str(value)))

def parse_args():
    parser = argparse.ArgumentParser(description="Build and optionally send the OpenClaw Telegram digest.")
    parser.add_argument("--sample-recent", action="store_true", help="print a digest from recent router_tasks without updating state")
    parser.add_argument("--limit", type=int, default=40, help="row limit for --sample-recent")
    parser.add_argument("--legacy", action="store_true", help="print the previous verbose digest format")
    return parser.parse_args()


def main():
    args = parse_args()
    with conn() as c:
        c.execute("""
        create table if not exists telegram_digest_state (
          key text primary key,
          value text,
          updated_at text default (datetime('now'))
        )
        """)
        last_id = get_state(c, "last_router_task_id")
        rows = fetch_recent_sample_rows(c, args.limit) if args.sample_recent else fetch_digest_rows(c, last_id)

        if not rows:
            print("[telegram_digest_v1] no new rows", flush=True)
            return

        max_id = max(int(r["id"]) for r in rows)

        text = build_legacy_digest(rows) if args.legacy else build_digest(rows)

        send_tg(text)
        if not DRY_RUN and not args.sample_recent:
            set_state(c, "last_router_task_id", max_id)
            c.commit()
        print(f"[telegram_digest_v1] {'dry_run' if DRY_RUN else 'sent'} rows={len(rows)} max_id={max_id}", flush=True)

if __name__ == "__main__":
    main()
