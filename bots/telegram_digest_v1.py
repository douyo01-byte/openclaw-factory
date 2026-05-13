from __future__ import annotations
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

def build_digest(rows) -> str:
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

def main():
    with conn() as c:
        c.execute("""
        create table if not exists telegram_digest_state (
          key text primary key,
          value text,
          updated_at text default (datetime('now'))
        )
        """)
        last_id = get_state(c, "last_router_task_id")

        rows = c.execute(f"""
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
        """, (last_id,)).fetchall()

        if not rows:
            print("[telegram_digest_v1] no new rows", flush=True)
            return

        max_id = max(int(r["id"]) for r in rows)

        text = build_digest(rows)

        send_tg(text)
        if not DRY_RUN:
            set_state(c, "last_router_task_id", max_id)
            c.commit()
        print(f"[telegram_digest_v1] {'dry_run' if DRY_RUN else 'sent'} rows={len(rows)} max_id={max_id}", flush=True)

if __name__ == "__main__":
    main()
