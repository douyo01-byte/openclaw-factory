from __future__ import annotations
import os
import re
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DB = os.environ.get("DB_PATH", str(Path.home() / "AI/openclaw-factory-daemon/data/openclaw_real.db"))

MANUAL_DOCS = {
    "README.md",
    "docs/00_INDEX.md",
    "docs/01_SYSTEM_PROMPT.md",
    "docs/02_MASTER_PLAN.md",
    "docs/03_MOTHERSHIP_ROLE.md",
    "docs/05_DEV_RULES.md",
    "docs/07_ROADMAP.md",
    "docs/12_AI_COMPANY.md",
    "docs/17_EFFICIENCY_RULES.md",
}

AUTO_DOCS = {
    "docs/_auto_progress.md",
    "docs/06_CURRENT_STATE.md",
    "docs/08_HANDOVER.md",
    "docs/09_BOT_CATALOG.md",
    "docs/10_DB_SCHEMA.md",
    "docs/11_OPERATIONS.md",
}

def sh(cmd: str) -> str:
    return subprocess.run(
        cmd,
        shell=True,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        env=os.environ.copy(),
    ).stdout.strip()

def q(sql: str):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(sql)
        return cur.fetchall()
    finally:
        conn.close()

def q1(sql: str, default="0") -> str:
    rows = q(sql)
    if not rows:
        return default
    return str(rows[0][0])

def table_exists(name: str) -> bool:
    return q1(f"select count(*) from sqlite_master where type='table' and name='{name}'") != "0"

def norm(s: str) -> str:
    s = str(s or "")
    s = re.sub(r'(?<=[一-龥ぁ-んァ-ヴー])\s+(?=[一-龥ぁ-んァ-ヴー])', '', s)
    s = re.sub(r'\s{2,}', ' ', s)
    return s.strip()

def get_branch() -> str:
    return sh("git branch --show-current")

def get_head() -> str:
    return sh("git rev-parse --short HEAD")

def get_now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_launchagents() -> list[str]:
    out = sh("launchctl list | grep openclaw || true")
    lines = [x.rstrip() for x in out.splitlines() if x.strip()]
    agents = []
    for line in lines:
        parts = re.split(r"\s+", line.strip())
        if len(parts) >= 3:
            agents.append(parts[-1])
    return sorted(set(agents))

def get_bot_files() -> list[str]:
    bots_dir = ROOT / "bots"
    if not bots_dir.exists():
        return []
    return sorted(
        p.name for p in bots_dir.iterdir()
        if p.is_file() and p.suffix == ".py" and ".bak" not in p.name and "__pycache__" not in p.name
    )

def status_counts() -> list[tuple[str, int]]:
    if not table_exists("dev_proposals"):
        return []
    rows = q("""
        select coalesce(status,'') as k, count(*) as c
        from dev_proposals
        group by status
        order by status
    """)
    return [(str(r["k"]), int(r["c"])) for r in rows]

def proposal_state_counts() -> list[tuple[str, int]]:
    if not table_exists("proposal_state"):
        return []
    rows = q("""
        select coalesce(stage,'') as k, count(*) as c
        from proposal_state
        group by stage
        order by stage
    """)
    return [(str(r["k"]), int(r["c"])) for r in rows]

def event_counts() -> list[tuple[str, int]]:
    if not table_exists("ceo_hub_events"):
        return []
    rows = q("""
        select coalesce(event_type,'') as k, count(*) as c
        from ceo_hub_events
        group by event_type
        order by event_type
    """)
    return [(str(r["k"]), int(r["c"])) for r in rows]

def latest_proposals(limit: int = 15):
    if not table_exists("dev_proposals"):
        return []
    return q(f"""
        select id, title, status, created_at
        from dev_proposals
        order by id desc
        limit {limit}
    """)

def latest_merged(limit: int = 10):
    if not table_exists("dev_proposals"):
        return []
    return q(f"""
        select id, title, status, created_at
        from dev_proposals
        where status='merged'
        order by id desc
        limit {limit}
    """)

def latest_events(limit: int = 20):
    if not table_exists("ceo_hub_events"):
        return []
    return q(f"""
        select id, event_type, title, proposal_id, created_at, sent_at
        from ceo_hub_events
        order by id desc
        limit {limit}
    """)

def get_tables() -> list[str]:
    rows = q("""
        select name
        from sqlite_master
        where type='table'
        order by name
    """)
    return [str(r["name"]) for r in rows]

def get_columns(table: str):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(f"pragma table_info({table})").fetchall()
    finally:
        conn.close()

def launchagent_state(label: str) -> str:
    uid = os.getuid()
    try:
        out = subprocess.check_output(
            ["launchctl", "print", f"gui/{uid}/{label}"],
            stderr=subprocess.STDOUT,
            text=True,
        )
    except Exception:
        return "not_found"
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("state ="):
            return s.split("=", 1)[1].strip()
    return "unknown"

def count_of(key: str, items: list[tuple[str, int]]) -> int:
    for k, v in items:
        if k == key:
            return v
    return 0

def detect_level() -> str:
    agents = set(get_launchagents())
    score = 0
    keys = [
        "jp.openclaw.dev_command_executor_v1",
        "jp.openclaw.dev_pr_watcher_v1",
        "jp.openclaw.dev_pr_automerge_v1",
        "jp.openclaw.spec_refiner_v2",
        "jp.openclaw.spec_notify_v1",
        "jp.openclaw.spec_reply_v1",
        "jp.openclaw.tg_poll_loop",
        "jp.openclaw.self_healing_v2",
        "jp.openclaw.self_repair_engine",
        "jp.openclaw.innovation_engine",
        "jp.openclaw.business_engine",
        "jp.openclaw.revenue_engine",
        "jp.openclaw.ai_employee_factory",
        "jp.openclaw.ai_meeting_engine",
        "jp.openclaw.ai_ceo_engine",
    ]
    for k in keys:
        if k in agents:
            score += 1
    if score >= 12:
        return "Lv6〜Lv7（自律開発ループ成立）"
    if score >= 8:
        return "Lv5.5〜Lv6"
    if score >= 5:
        return "Lv5前後"
    return "Lv4〜Lv5未満"

def render_auto_progress() -> str:
    sc = status_counts()
    pc = proposal_state_counts()
    ec = event_counts()
    lines = []
    lines.append("# OpenClaw Auto Progress")
    lines.append("")
    lines.append(f"- generated_at: `{get_now()}`")
    lines.append(f"- branch: `{get_branch()}`")
    lines.append(f"- head: `{get_head()}`")
    lines.append(f"- db: `{DB}`")
    lines.append("")
    lines.append("## dev_proposals status")
    for k, v in sc:
        lines.append(f"- {k or '(blank)'}: {v}")
    lines.append("")
    lines.append("## proposal_state")
    for k, v in pc:
        lines.append(f"- {k or '(blank)'}: {v}")
    lines.append("")
    lines.append("## ceo_hub_events")
    for k, v in ec:
        lines.append(f"- {k or '(blank)'}: {v}")
    lines.append("")
    lines.append("## latest proposals")
    for r in latest_proposals():
        lines.append(f"- {r['id']} | {norm(r['title'])} | {r['status']} | {r['created_at']}")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"

def render_current_state() -> str:
    sc = status_counts()
    pc = proposal_state_counts()
    ec = event_counts()
    agents = get_launchagents()
    lines = []
    lines.append("# OpenClaw Current State")
    lines.append("")
    lines.append("## 現在地")
    lines.append("")
    lines.append("開発AI:")
    lines.append(detect_level())
    lines.append("")
    lines.append("理由:")
    lines.append("")
    for x in [
        "jp.openclaw.dev_command_executor_v1",
        "jp.openclaw.dev_pr_watcher_v1",
        "jp.openclaw.dev_pr_automerge_v1",
        "jp.openclaw.spec_refiner_v2",
        "jp.openclaw.spec_reply_v1",
        "jp.openclaw.spec_notify_v1",
        "jp.openclaw.tg_poll_loop",
        "jp.openclaw.self_healing_v2",
    ]:
        if x in agents:
            lines.append(f"- {x} 稼働")
    lines.append("")
    lines.append("### 自律開発ループ")
    lines.append("")
    lines.append("proposal生成  ")
    lines.append("↓  ")
    lines.append("spec refinement  ")
    lines.append("↓  ")
    lines.append("code generation  ")
    lines.append("↓  ")
    lines.append("PR作成  ")
    lines.append("↓  ")
    lines.append("PR merge  ")
    lines.append("↓  ")
    lines.append("learning反映  ")
    lines.append("")
    lines.append("この主幹ループが実運用で成立。")
    lines.append("")
    lines.append("### 補助エンジン")
    lines.append("")
    for x in [
        "jp.openclaw.innovation_engine",
        "jp.openclaw.code_review_engine",
        "jp.openclaw.business_engine",
        "jp.openclaw.revenue_engine",
        "jp.openclaw.ai_employee_factory",
    ]:
        if x in agents:
            lines.append(f"- {x.replace('jp.openclaw.','')}")
    lines.append("")
    lines.append("### 経営層")
    lines.append("")
    for x in [
        "jp.openclaw.ai_meeting_engine",
        "jp.openclaw.ai_ceo_engine",
        "jp.openclaw.ceo_dashboard",
    ]:
        if x in agents:
            lines.append(f"- {x.replace('jp.openclaw.','')}")
    lines.append("")
    lines.append("### 自己修復")
    lines.append("")
    for x in [
        "jp.openclaw.self_repair_engine",
        "jp.openclaw.self_healing_v2",
    ]:
        if x in agents:
            lines.append(f"- {x.replace('jp.openclaw.','')}")
    lines.append("")
    lines.append("### DB実測値")
    lines.append("")
    lines.append("dev_proposals")
    lines.append("")
    for k, v in sc:
        lines.append(f"{k or '(blank)'} : {v}  ")
    lines.append("")
    lines.append("proposal_state")
    lines.append("")
    for k, v in pc:
        lines.append(f"{k or '(blank)'} : {v}  ")
    lines.append("")
    lines.append("ceo_hub_events")
    lines.append("")
    for k, v in ec:
        lines.append(f"{k or '(blank)'} : {v}  ")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 現状の課題")
    lines.append("")
    lines.append("1. proposal供給量の不足")
    lines.append("2. learning評価軸の強化余地")
    lines.append("3. CEO判断の質向上")
    lines.append("4. 収益化ロジックの深掘り")
    lines.append("5. 長期安定運用の継続確認")
    lines.append("")
    lines.append("## 現在の評価")
    lines.append("")
    lines.append("OpenClawは")
    lines.append("")
    lines.append("自律開発ループが成立した  ")
    lines.append("**AI開発会社OS**")
    lines.append("")
    lines.append("の状態。")
    lines.append("")
    lines.append("## 次フェーズ")
    lines.append("")
    lines.append("Lv8〜Lv10")
    lines.append("")
    lines.append("- learning強化")
    lines.append("- proposal ranking強化")
    lines.append("- CEO decision強化")
    lines.append("- revenue / AI company 強化")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"

def render_handover() -> str:
    sc = status_counts()
    pc = proposal_state_counts()
    ec = event_counts()
    agents = get_launchagents()
    lines = []
    lines.append("# OpenClaw Handover")
    lines.append("")
    lines.append("## 前提")
    lines.append("")
    lines.append("- この文書は最新の自動引き継ぎ")
    lines.append("- 実ファイル・実DB・実ログ・実プロセスを優先")
    lines.append("- 核ファイルは手動管理、状態ファイルは自動生成")
    lines.append("")
    lines.append("## 今回の自動要約")
    lines.append("")
    lines.append(f"- generated_at: {get_now()}")
    lines.append(f"- branch: {get_branch()}")
    lines.append(f"- head: {get_head()}")
    lines.append(f"- db: {DB}")
    lines.append("")
    lines.append("## 現在の本当の状態")
    lines.append("")
    lines.append("### launchagents")
    for a in agents:
        lines.append(f"- {a}: {launchagent_state(a)}")
    lines.append("")
    lines.append("### dev_proposals")
    for k, v in sc:
        lines.append(f"- {k or '(blank)'}: {v}")
    lines.append("")
    lines.append("### proposal_state")
    for k, v in pc:
        lines.append(f"- {k or '(blank)'}: {v}")
    lines.append("")
    lines.append("### ceo_hub_events")
    for k, v in ec:
        lines.append(f"- {k or '(blank)'}: {v}")
    lines.append("")
    lines.append("### latest proposals")
    for r in latest_proposals(10):
        lines.append(f"- {r['id']} | {norm(r['title'])} | {r['status']}")
    lines.append("")
    lines.append("## 確認できた重要事項")
    lines.append("")
    lines.append("- 非核 docs は自動同期対象")
    lines.append("- 主幹 active pipeline の DB は daemon real db へ統一済み")
    lines.append("- 会社状態表示は live DB と一致する方向に修正済み")
    lines.append("")
    lines.append("## 次チャットで最初に打つコマンド")
    lines.append("")
    lines.append("cd ~/AI/openclaw-factory-daemon || exit 1")
    lines.append("")
    lines.append("## 次に見る項目")
    lines.append("")
    lines.append("1. tg_poll_loop の会社状態表示が live 値と一致しているか")
    lines.append("2. docs/06_CURRENT_STATE.md と docs/08_HANDOVER.md の自動生成内容が十分か")
    lines.append("3. .bak / archive をどこまで整理するか")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"

def render_bot_catalog() -> str:
    files = get_bot_files()
    lines = []
    lines.append("# OpenClaw Bot Catalog")
    lines.append("")
    lines.append("自動生成。手修正しない。")
    lines.append("")
    for name in files:
        lines.append(f"- {name}")
    lines.append("")
    return "\n".join(lines)

def render_db_schema() -> str:
    lines = []
    lines.append("# OpenClaw DB Schema Notes")
    lines.append("")
    lines.append("自動生成。手修正しない。")
    lines.append("")
    lines.append(f"- generated_at: `{get_now()}`")
    lines.append(f"- branch: `{get_branch()}`")
    lines.append(f"- db: `{DB}`")
    lines.append("")
    lines.append("## table list")
    for t in get_tables():
        lines.append(f"- {t}")
    lines.append("")
    lines.append("## current counts")
    for t in ["dev_proposals", "proposal_state", "proposal_conversation", "inbox_commands", "decisions", "ceo_hub_events"]:
        lines.append(f"- {t}: {q1(f'select count(*) from {t}') if table_exists(t) else 'n/a'}")
    lines.append("")
    lines.append("## proposal_state status counts")
    for k, v in proposal_state_counts():
        lines.append(f"- {k or '(blank)'}: {v}")
    lines.append("")
    lines.append("## ceo_hub_events event counts")
    for k, v in event_counts():
        lines.append(f"- {k or '(blank)'}: {v}")
    lines.append("")
    lines.append("## columns")
    for t in get_tables():
        lines.append(f"### {t}")
        for c in get_columns(t):
            lines.append(f"- {c['name']} | {c['type']} | notnull={c['notnull']} | pk={c['pk']} | default={c['dflt_value']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"

def render_operations() -> str:
    lines = []
    lines.append("# OpenClaw Operations")
    lines.append("")
    lines.append("自動生成。手修正しない。")
    lines.append("")
    lines.append(f"- generated_at: `{get_now()}`")
    lines.append(f"- branch: `{get_branch()}`")
    lines.append(f"- head: `{get_head()}`")
    lines.append("")
    lines.append("## launchagents")
    for a in get_launchagents():
        lines.append(f"- {a}")
    lines.append("")
    lines.append("## active docs policy")
    for name in sorted(MANUAL_DOCS):
        lines.append(f"- manual: {name}")
    for name in sorted(AUTO_DOCS):
        lines.append(f"- auto: {name}")
    lines.append("")
    return "\n".join(lines)

def ensure_no_manual_overwrite(paths: list[Path]):
    for p in paths:
        rel = str(p.relative_to(ROOT))
        if rel in MANUAL_DOCS:
            raise SystemExit(f"manual doc overwrite blocked: {rel}")

def write_if_changed(path: Path, text: str) -> bool:
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    if old == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True

def main():
    DOCS.mkdir(parents=True, exist_ok=True)
    mapping = {
        DOCS / "_auto_progress.md": render_auto_progress(),
        DOCS / "06_CURRENT_STATE.md": render_current_state(),
        DOCS / "08_HANDOVER.md": render_handover(),
        DOCS / "09_BOT_CATALOG.md": render_bot_catalog(),
        DOCS / "10_DB_SCHEMA.md": render_db_schema(),
        DOCS / "11_OPERATIONS.md": render_operations(),
    }
    ensure_no_manual_overwrite(list(mapping.keys()))
    changed = []
    for path, text in mapping.items():
        if write_if_changed(path, text):
            changed.append(str(path.relative_to(ROOT)))
    print("changed:")
    for x in changed:
        print(x)

if __name__ == "__main__":
    main()
