from pathlib import Path
import sqlite3
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
DB = Path("/Users/doyopc/AI/openclaw-factory/data/openclaw.db")

def sh(args):
    return subprocess.check_output(args, text=True).strip()

def one(cur, sql):
    r = cur.execute(sql).fetchone()
    return r[0] if r and r[0] is not None else 0

def render_current_state(cur):
    proposals = one(cur, "select count(*) from dev_proposals")
    merged = one(cur, "select count(*) from dev_proposals where status='merged'")
    open_pr = one(cur, "select count(*) from dev_proposals where coalesce(pr_status,'')='open' or coalesce(status,'')='open'")
    waiting = one(cur, "select count(*) from proposal_state where stage='waiting_answer'")
    ceo_events = one(cur, "select count(*) from ceo_hub_events")
    return f"""# OpenClaw Current State

- generated_at: {datetime.now(timezone.utc).isoformat()}
- canonical_db: {DB}

## 現在地
- AI企業レベル: Lv7〜Lv8
- maturity: 約94%
- 7h burn-in: 準備段階

## live counters
- proposals: {proposals}
- merged: {merged}
- open_pr: {open_pr}
- waiting_answer: {waiting}
- ceo_events: {ceo_events}

## 稼働中の主幹
- dev_command_executor_v1
- dev_pr_watcher_v1
- dev_pr_automerge_v1
- dev_merge_notify_v1
- spec_refiner_v2
- spec_reply_v1
- tg_poll_loop
- secretary_llm_v1
- ai_meeting_engine_v1
- ai_ceo_engine_v1
- proposal_success_optimizer_v1
- adaptive_supply_controller_v1
- mainstream_supply_v1
- pattern_supply_bridge_v1
- db_lifecycle_audit_v1
- db_integrity_watchdog_v1

## 未完了
- docs自動更新の完全運用確認
- 10分 burn-in 実測
- 7時間 burn-in 実績
"""

def render_handover(cur):
    latest = cur.execute("""
    select id, title, status, coalesce(pr_url,'')
    from dev_proposals
    order by id desc
    limit 10
    """).fetchall()
    lines = "\n".join(
        f"- #{r[0]} {r[1]} | {r[2]} | {r[3]}" for r in latest
    )
    return f"""# OpenClaw Handover

- generated_at: {datetime.now(timezone.utc).isoformat()}
- branch: {sh(['git','branch','--show-current'])}
- head: {sh(['git','rev-parse','--short','HEAD'])}
- canonical_db: {DB}

## 現在の本当の状態
- docs正本: ~/AI/openclaw-factory-docs
- 実行repo: ~/AI/openclaw-factory
- canonical DB: ~/AI/openclaw-factory/data/openclaw.db

## 直近案件
{lines}

## 次に見るもの
1. 10分観測で proposals / merged / ceo_events が動くか
2. docs_compiler_v2 の定期更新
3. 7時間 burn-in 開始可否
"""

def render_db_schema(cur):
    tables = [r[0] for r in cur.execute("select name from sqlite_master where type='table' order by name").fetchall()]
    out = [f"# OpenClaw DB Schema\n", f"- generated_at: {datetime.now(timezone.utc).isoformat()}", f"- canonical_db: {DB}\n"]
    for t in tables:
        out.append(f"## {t}")
        for c in cur.execute(f"pragma table_info({t})").fetchall():
            out.append(f"- {c[1]} | {c[2]}")
        out.append("")
    return "\n".join(out)

def write(path, text):
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    if old != text:
        path.write_text(text, encoding="utf-8")
        print(f"updated: {path}")

def main():
    DOCS.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    write(DOCS / "06_CURRENT_STATE.md", render_current_state(cur))
    write(DOCS / "08_HANDOVER.md", render_handover(cur))
    write(DOCS / "10_DB_SCHEMA.md", render_db_schema(cur))
    conn.close()

if __name__ == "__main__":
    main()
