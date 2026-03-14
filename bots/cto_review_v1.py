import json
import os
import sqlite3
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

DB_PATH = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

ROOT = Path("/Users/doyopc/AI/openclaw-factory-daemon")
DB = os.environ.get("DB_PATH", str(Path("/Users/doyopc/AI/openclaw-factory/data/openclaw.db")))
STATE = ROOT / "data/cto_review_v1.state"
BOT = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
CHAT = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()

def tg(text: str):
    if not BOT or not CHAT:
        print("[cto_review] missing telegram env", flush=True)
        return
    data = urllib.parse.urlencode({"chat_id": CHAT, "text": text}).encode()
    url = f"https://api.telegram.org/bot{BOT}/sendMessage"
    with urllib.request.urlopen(url, data=data, timeout=20) as r:
        r.read()

def q(con, sql, args=()):
    row = con.execute(sql, args).fetchone()
    if not row:
        return 0
    v = row[0]
    return 0 if v is None else v

def launchd_running(label: str) -> bool:
    try:
        r = subprocess.run(
            ["launchctl", "print", f"gui/{os.getuid()}/{label}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        txt = (r.stdout or "") + (r.stderr or "")
        return "state = running" in txt
    except Exception:
        return False

def phase_text(maturity: int) -> str:
    if maturity >= 85:
        return "実運用直前"
    if maturity >= 60:
        return "事業準備"
    return "自己強化"


def create_cto_proposal(conn, title: str, body: str):
    cur = conn.cursor()
    row = cur.execute("""
        select id
        from dev_proposals
        where coalesce(source_ai,'')='cto'
          and title=?
          and coalesce(status,'') in ('new','approved','pending')
          and created_at >= datetime('now','-60 minutes')
        order by id desc
        limit 1
    """, (title,)).fetchone()
    if row:
        print(f"[cto_review] duplicate id={row[0]}", flush=True)
        return row[0]

    cur.execute("""
        insert into dev_proposals(
            title, body, status, project_decision, dev_stage, guard_status,
            source_ai, category, target_system, improvement_type, created_at
        ) values(
            ?, ?, 'approved', 'execute_now', 'execute_now', 'safe',
            'cto', 'automation', 'core', 'automation', datetime('now')
        )
    """, (title, body))
    pid = cur.lastrowid
    conn.commit()
    print(f"[cto_review] proposal inserted id={pid}", flush=True)
    return pid

def build_msg():
    con = sqlite3.connect(DB, timeout=30)
    try:
        open_pr = q(con, "select count(*) from dev_proposals where coalesce(pr_status,'')='open'")
        approved = q(con, "select count(*) from dev_proposals where coalesce(status,'')='approved'")
        merged_24h = q(con, """
            select count(*)
            from dev_proposals
            where coalesce(dev_stage,'')='merged'
              and created_at >= datetime('now','-24 hours')
        """)
        coo_open = q(con, """
            select count(*)
            from dev_proposals
            where coalesce(source_ai,'')='coo'
              and coalesce(dev_stage,'') not in ('merged','closed')
        """)
        backlog = q(con, """
            select count(*)
            from dev_proposals
            where coalesce(status,'')='approved'
              and coalesce(project_decision,'')='execute_now'
              and coalesce(dev_stage,'') not in ('merged','closed')
        """)
        latest = con.execute("""
            select id, title
            from dev_proposals
            order by id desc
            limit 1
        """).fetchone()
    finally:
        con.close()

    health_path = ROOT / "obs/company_health_score.json"
    maturity = 0
    if health_path.exists():
        try:
            maturity = int(json.loads(health_path.read_text(encoding="utf-8")).get("maturity_percent", 0) or 0)
        except Exception:
            maturity = 0

    secretary = launchd_running("jp.openclaw.secretary_llm_v1")
    watcher = launchd_running("jp.openclaw.dev_pr_watcher_v1")
    merge_notify = launchd_running("jp.openclaw.dev_merge_notify_v1")
    meeting = launchd_running("jp.openclaw.dev_meeting_telegram_bridge_v1")
    supply = launchd_running("jp.openclaw.mainstream_supply")
    executor = launchd_running("jp.openclaw.dev_command_executor_v1")

    risks = []
    if not supply:
        risks.append("supply停止")
    if backlog >= 10:
        risks.append(f"execute_now滞留 {backlog}件")
    if approved >= 15:
        risks.append(f"approved滞留 {approved}件")
    if not watcher:
        risks.append("watcher停止")
    if not executor:
        risks.append("executor停止")
    if not secretary:
        risks.append("Kaikun02停止")

    if not risks:
        cto = "大きな詰まりは少なめ。このまま供給と実行のバランス監視。"
    else:
        cto = " / ".join(risks[:3])

    latest_line = "なし"
    if latest:
        latest_line = f"#{latest[0]} {latest[1]}"

    msg = []
    msg.append("🧠 Kaikun04 CTOレビュー")
    msg.append("")
    msg.append(f"事業開始達成率: {maturity}%")
    msg.append(f"現在フェーズ: {phase_text(maturity)}")
    msg.append("")
    msg.append("■ 開発ライン")
    msg.append(f"・ merged(24h): {merged_24h}")
    msg.append(f"・ open PR: {open_pr}")
    msg.append(f"・ approved滞留: {approved}")
    msg.append(f"・ execute_now滞留: {backlog}")
    msg.append(f"・ COO未完了: {coo_open}")
    msg.append("")
    msg.append("■ 常駐状態")
    msg.append(f"・ secretary: {'稼働中' if secretary else '停止'}")
    msg.append(f"・ executor: {'稼働中' if executor else '停止'}")
    msg.append(f"・ watcher: {'稼働中' if watcher else '停止'}")
    msg.append(f"・ merge_notify: {'稼働中' if merge_notify else '停止'}")
    msg.append(f"・ meeting_bridge: {'稼働中' if meeting else '停止'}")
    msg.append(f"・ mainstream_supply: {'稼働中' if supply else '停止'}")
    msg.append("")
    msg.append("■ 最新提案")
    msg.append(f"・ {latest_line}")
    msg.append("")
    msg.append("■ CTO判断")
    msg.append(f"・ {cto}")
    return "\n".join(msg)

def load_last():
    try:
        return STATE.read_text(encoding="utf-8").strip()
    except Exception:
        return ""

def save_last(text: str):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(text, encoding="utf-8")

def main():
    while True:
        try:
            msg = build_msg()
            if msg != load_last():
                title = msg.split("\n", 1)[0][:140]
                conn = sqlite3.connect(DB_PATH, timeout=30)
                conn.execute("pragma busy_timeout=30000")
                create_cto_proposal(conn, title, msg)
                conn.close()
                tg(msg)
                save_last(msg)
                print("[cto_review] sent", flush=True)
            else:
                print("[cto_review] skip same", flush=True)
        except Exception as e:
            print(f"[cto_review] error={e!r}", flush=True)
        time.sleep(1200)

if __name__ == "__main__":
    main()
