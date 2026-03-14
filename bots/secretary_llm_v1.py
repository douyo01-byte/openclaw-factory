import re
import json
import os
import sqlite3
import time
import subprocess
from pathlib import Path

import requests

DB = os.environ.get("DB_PATH", "/Users/doyopc/AI/openclaw-factory/data/openclaw.db")
BOT_TOKEN = (os.environ.get("TELEGRAM_CEO_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
OPENAI_API_KEY = (os.environ.get("OPENAI_API_KEY") or "").strip()
print(f"[secretary_boot] OPENAI_API_KEY_LEN={len(OPENAI_API_KEY)}", flush=True)
OPENAI_MODEL = (os.environ.get("OPENAI_MODEL") or "gpt-4o-mini").strip()

ROOT = Path(__file__).resolve().parent.parent
OBS = ROOT / "obs"
LOGS = ROOT / "logs"

def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}

def one(conn, sql, params=()):
    r = conn.execute(sql, params).fetchone()
    return r[0] if r else None

def fetch_dashboard_facts(conn):
    total = one(conn, "select count(*) from dev_proposals") or 0
    merged = one(conn, "select count(*) from dev_proposals where coalesce(status,'')='merged'") or 0
    approved = one(conn, "select count(*) from dev_proposals where coalesce(status,'')='approved'") or 0
    open_pr = one(conn, "select count(*) from dev_proposals where coalesce(pr_status,'')='open' or coalesce(status,'')='open'") or 0
    waiting = one(conn, "select count(*) from proposal_state where coalesce(stage,'')='waiting_answer'") or 0
    latest = conn.execute("""
        select id, coalesce(title,'')
        from dev_proposals
        order by id desc
        limit 1
    """).fetchone()
    latest_merged = conn.execute("""
        select id, coalesce(title,'')
        from dev_proposals
        where coalesce(status,'')='merged'
        order by id desc
        limit 1
    """).fetchone()
    top_backlog = conn.execute("""
        select id, coalesce(title,''), coalesce(project_decision,''), coalesce(guard_status,''), coalesce(priority,0)
        from dev_proposals
        where coalesce(status,'')='approved'
          and not (coalesce(project_decision,'')='execute_now' and coalesce(guard_status,'')='safe')
        order by coalesce(priority,0) asc, id desc
        limit 3
    """).fetchall()
    return {
        "total": total,
        "merged": merged,
        "approved": approved,
        "open_pr": open_pr,
        "waiting": waiting,
        "latest": {"id": latest[0], "title": latest[1]} if latest else None,
        "latest_merged": {"id": latest_merged[0], "title": latest_merged[1]} if latest_merged else None,
        "top_backlog": [
            {"id": r[0], "title": r[1], "decision": r[2], "guard": r[3], "priority": r[4]}
            for r in top_backlog
        ],
    }

def build_context(conn):
    health = load_json(OBS / "company_health_score.json")
    supply = load_json(OBS / "supply_adoption_metrics.json")
    integrity_lines = []
    try:
        p = LOGS / "db_integrity_check_v1.log"
        if p.exists():
            integrity_lines = p.read_text(encoding="utf-8").splitlines()[-5:]
    except Exception:
        integrity_lines = []
    ctx = {
        "company_health": health,
        "supply_adoption": supply,
        "db_integrity_recent": integrity_lines,
        "dashboard_facts": fetch_dashboard_facts(conn),
    }
    return json.dumps(ctx, ensure_ascii=False, indent=2)

def ask_llm(user_text, context_text):
    if not OPENAI_API_KEY:
        return (
            "OpenClaw COOです。\n"
            "今は簡易モードです。\n"
            "事実ベースで短く答えます。"
        )
    system = (
        "あなたは OpenClaw 専属の COO / 右腕です。"
        "日本語で自然に、断定しすぎず、OpenClaw の内部事情を知る実務家として答えてください。"
        "事実は context のみを使うこと。推測は禁止。"
        "質問が経営・弱点・次の一手なら、"
        "1) 結論 2) 根拠 3) 次の一手 の順で簡潔に返す。"
        "必要なら作業チャットに貼れる短い指示も出す。"
        "箇条書きは多くても 4 個まで。"
    )
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"question:\n{user_text}\n\ncontext:\n{context_text}"},
        ],
        "temperature": 0.2,
    }
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"].strip()

def send(chat_id, text):
    if not BOT_TOKEN or not chat_id:
        print(f"[secretary_send] missing token/chat bot_len={len(BOT_TOKEN)} chat_id={chat_id}", flush=True)
        return False, "missing_token_or_chat"
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": str(chat_id), "text": text},
            timeout=30,
        )
        r.raise_for_status()
        print(f"[secretary_send] ok chat_id={chat_id} text_head={(text or '')[:60]!r}", flush=True)
        return True, ""
    except Exception as e:
        print(f"[secretary_send] error chat_id={chat_id} err={e!r}", flush=True)
        return False, repr(e)[:500]

def ensure_cols(conn):
    cols = {r[1] for r in conn.execute("pragma table_info(inbox_commands)")}
    if "processed" not in cols:
        conn.execute("alter table inbox_commands add column processed integer default 0")
    if "applied_at" not in cols:
        conn.execute("alter table inbox_commands add column applied_at text")
    if "error" not in cols:
        conn.execute("alter table inbox_commands add column error text")
    if "status" not in cols:
        conn.execute("alter table inbox_commands add column status text default 'new'")
    if "chat_id" not in cols:
        conn.execute("alter table inbox_commands add column chat_id text")

def next_row(conn):
    return conn.execute("""
        select id, coalesce(chat_id,''), coalesce(text,'')
        from inbox_commands
        where coalesce(processed,0)=0
          and coalesce(status,'') not in ('company_done','company_error','secretary_done','secretary_error')
        order by id asc
        limit 1
    """).fetchone()

def mark(conn, rid, status, err=None):
    conn.execute(
        "update inbox_commands set processed=1,status=?,applied_at=datetime('now'),error=? where id=?",
        (status, err, rid),
    )
    conn.commit()



def fetch_recent_decisions(conn):
    try:
        rows = conn.execute("""
            select id, coalesce(target,''), coalesce(decision,''), coalesce(reason,''), coalesce(created_at,'')
            from decisions
            order by id desc
            limit 4
        """).fetchall()
        return rows
    except Exception:
        return []

def employee_block():
    return """■ 海外事業
SekawakuClaw_bot
・さがすけ（探索）
・しらべえ（調査）
・かんがえもん（企画）

■ 開発
Kaikun01_bot
・きめたろう（設計）
・つくるぞう（実装）
・みはるん（監査）
・くっつけ丸（統合）

■ 経営共有
Kaikun02_bot
・ひしょりん（秘書）
・しらせるん（報告）

■ 自動実行
Kaikun03_bot
・とどけるん（通知）
・まわすけ（実行管理）
・なおし丸（自己修復）
・みはりん（監視）"""

def bot_status_block():
    labels = [
        ("secretary_llm_v1", "jp.openclaw.secretary_llm_v1"),
        ("tg_poll_loop", "jp.openclaw.tg_poll_loop"),
        ("dev_pr_watcher_v1", "jp.openclaw.dev_pr_watcher_v1"),
        ("dev_pr_automerge_v1", "jp.openclaw.dev_pr_automerge_v1"),
        ("mainstream_supply", "jp.openclaw.mainstream_supply"),
        ("self_strength_watchdog_v1", "jp.openclaw.self_strength_watchdog_v1"),
        ("ai_meeting_digest_v1", "jp.openclaw.ai_meeting_digest_v1"),
        ("dev_meeting_telegram_bridge_v1", "jp.openclaw.dev_meeting_telegram_bridge_v1"),
        ("cto_review_v1", "jp.openclaw.cto_review_v1"),
    ]
    out = []
    for name, lb in labels:
        try:
            r = subprocess.run(
                ["launchctl", "print", f"gui/{os.getuid()}/{lb}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            txt = (r.stdout or "") + (r.stderr or "")
            status = "稼働中" if "state = running" in txt else "停止"
        except Exception:
            status = "不明"
        out.append(f"{name}: {status}")
    return "\n".join(out)

def build_dashboard(conn):
    f = fetch_dashboard_facts(conn)
    latest = f.get("latest") or {"id": "-", "title": "な し "}
    latest_merged = f.get("latest_merged") or {"id": "-", "title": "な し "}
    top_backlog = f.get("top_backlog") or []
    decisions = fetch_recent_decisions(conn)
    health = f.get("company_health") or {}
    maturity = int(health.get("maturity_percent", 0) or 0)

    if maturity >= 85:
        phase = "実 運 用 直 前"
    elif maturity >= 60:
        phase = "事 業 準 備"
    else:
        phase = "自 己 強 化"

    txt = "OpenClaw CEOダ ッ シ ュ ボ ー ド \n"
    txt += "━━━━━━━━━━━━━━━━━━\n"
    txt += "【 会 社 状 態 】 \n\n"
    txt += f"事 業 開 始 達 成 率 : {maturity}%\n"
    txt += f"現 在 フ ェ ー ズ : {phase}\n"
    txt += f"総 提 案 件 数 : {f['total']}\n"
    txt += f"マ ー ジ 済 み : {f['merged']}\n"
    txt += f"Open PR: {f['open_pr']}\n"
    txt += f"承 認 済 み : {f['approved']}\n"
    txt += f"社 長 回 答 待 ち : {f['waiting']}\n\n"

    txt += "━━━━━━━━━━━━━━━━━━\n"
    txt += "【 最 新 提 案 】 \n\n"
    txt += f"#{latest['id']} {latest['title']}\n\n"

    txt += "━━━━━━━━━━━━━━━━━━\n"
    txt += "【 最 新 マ ー ジ 】 \n\n"
    txt += f"#{latest_merged['id']} {latest_merged['title']}\n\n"

    txt += "━━━━━━━━━━━━━━━━━━\n"
    txt += "【 優 先 バ ッ ク ロ グ 】 \n\n"
    if top_backlog:
        for r in top_backlog:
            txt += f"#{r['id']} {r['title']}\n"
    else:
        txt += "現 在 0件 \n"
    txt += "\n"

    txt += "━━━━━━━━━━━━━━━━━━\n"
    txt += "【 最 近 の 意 思 決 定 】 \n\n"
    if decisions:
        for r in decisions:
            tgt = r[1] or "-"
            dec = r[2] or "-"
            txt += f"{tgt} 評 価 : {dec}\n"
    else:
        txt += "最 近 の 記 録 な し \n"
    txt += "\n"

    txt += "━━━━━━━━━━━━━━━━━━\n"
    txt += "【 AI社 員 構 成 】 \n\n"
    txt += employee_block() + "\n\n"

    txt += "━━━━━━━━━━━━━━━━━━\n"
    txt += "【 BOT状 態 】 \n\n"
    txt += bot_status_block() + "\n\n"

    txt += "━━━━━━━━━━━━━━━━━━\n"
    txt += "【 次 の 一 手 】 \n\n"
    txt += "・ executorキ ュ ー 監 視 \n"
    txt += "・ 供 給 と PR消 化 バ ラ ン ス 確 認 \n"
    txt += "・ blocked targetの 整 理 \n"
    txt += "・ CTOレ ビ ュ ー の 提 案 接 続 準 備 \n"
    return txt

def normalize_user_text(text):
    t = (text or "").strip()
    t = t.replace("@Kaikun02_bot", "").replace("@kaikun02_bot", "").strip()
    return "".join(t.split())



def infer_targets(text: str):
    t = normalize_user_text(text)
    targets = []
    if any(k in t for k in ["通知", "telegram", "テレグラム", "dm", "送信"]):
        targets.append("Telegram通知系")
    if any(k in t for k in ["会議", "meeting", "digest"]):
        targets.append("AI会議/要約系")
    if any(k in t for k in ["進捗", "dashboard", "ダッシュボード", "ceo"]):
        targets.append("Kaikun02/ダッシュボード系")
    if any(k in t for k in ["自動化", "loop", "launchagent", "常時", "定期"]):
        targets.append("常駐化/LaunchAgent系")
    if any(k in t for k in ["proposal", "提案", "起票"]):
        targets.append("dev_proposals/起票系")
    if any(k in t for k in ["db", "sqlite", "データベース"]):
        targets.append("SQLite/DB系")
    if any(k in t for k in ["pr", "merge", "executor", "review"]):
        targets.append("開発実行/PR系")
    return targets[:4]


def build_coo_plan(text, conn):
    user_text = normalize_user_text(text)
    f = fetch_dashboard_facts(conn)
    backlog = f.get("top_backlog") or []
    targets = infer_targets(text)

    t = user_text.lower()
    tc = re.sub(r"\s+", "", t)

    target_system = "core"
    category = "automation"
    improvement_type = "automation"

    if "telegram" in tc or "通知" in tc or "送信" in tc:
        target_system = "telegram"
    elif "dashboard" in tc or "進捗" in tc:
        target_system = "dashboard"
    elif "meeting" in tc or "会議" in tc or "digest" in tc:
        target_system = "meeting"

    lines = []
    lines.append("【 目 的 】 ")
    lines.append("- 依 頼 内 容 を 実 装 可 能 な 粒 度 に 整 理 す る ")
    lines.append(f"- 入 力 : {user_text}")
    lines.append("")
    lines.append("【 対 象 候 補 】 ")
    if targets:
        for x in targets:
            lines.append(f"- {x}")
    else:
        lines.append("- 対 象 は 未 特 定 ")
    lines.append("")
    lines.append("【 実 装 方 針 】 ")
    lines.append("- 既 存 bot / script / DB / LaunchAgent の 接 続 点 を 先 に 確 認 す る ")
    lines.append("- 人 間 判 断 が 必 要 な 点 だ け 先 に 確 定 す る ")
    lines.append("- そ れ 以 外 は 自 動 実 装 候 補 と し て 分 離 す る ")
    lines.append("")
    lines.append("【 あ な た が 決 め る こ と 】 ")
    lines.append("- 通 知 対 象 の chat_id を 既 存 流 用 か 新 規 か ")
    lines.append("- 手 動 実 行 か 常 駐 自 動 実 行 か ")
    lines.append("- 在 庫 の 変 化 判 定 を DB 起 点 に す る か 外 部 起 点 に す る か ")
    lines.append("")
    lines.append("【 作 業 チ ャ ッ ト 指 示 】 ")
    lines.append("cd ~/AI/openclaw-factory-daemon || exit 1")
    lines.append("launchctl list | grep openclaw")
    lines.append("sqlite3 data/openclaw.db \"select count(*) from dev_proposals;\"")
    lines.append("sqlite3 data/openclaw.db \"select id,title,status,dev_stage from dev_proposals order by id desc limit 10;\"")
    lines.append("grep -Rni 'telegram\\|meeting\\|dashboard\\|proposal\\|executor' bots scripts 2>/dev/null | sed -n '1,120p'")
    lines.append("")
    lines.append("【 推 定 メ タ 情 報 】 ")
    lines.append(f"- category: {category}")
    lines.append(f"- target_system: {target_system}")
    lines.append(f"- improvement_type: {improvement_type}")
    lines.append("")
    lines.append("【 現 在 の 会 社 状 態 】 ")
    lines.append(f"- 総 提 案 件 数 : {f.get('total', 0)}")
    lines.append(f"- マ ー ジ 済 み : {f.get('merged', 0)}")
    lines.append(f"- 承 認 済 み : {f.get('approved', 0)}")
    lines.append(f"- Open PR: {f.get('open_pr', 0)}")
    lines.append("")
    lines.append("【 優 先 バ ッ ク ロ グ 】 ")
    if backlog:
        for r in backlog[:3]:
            lines.append(f"- #{r.get('id')} {r.get('title')}")
    else:
        lines.append("- な し ")
    lines.append("")
    lines.append("【 自 動 化 候 補 】 ")
    lines.append("- 必 要 な ら こ の 内 容 で dev_proposals 化 す る ")
    return "\n".join(lines)

def coo_to_proposal(conn, user_text, reply_text):
    import re
    raw = normalize_user_text(user_text).strip()
    title = raw[:120] or "COO proposal"
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", raw.lower()).strip("-")
    if not slug:
        slug = "coo-proposal"
    branch_name = f"coo/{slug[:40]}"

    tl = raw.lower()
    category = "automation"
    target_system = "core"
    improvement_type = "automation"
    quality_score = 72

    if "telegram" in tl or "通 知 " in raw or "送 信 " in raw:
        target_system = "telegram"
    elif "dashboard" in tl or "ダ ッ シ ュ ボ ー ド " in raw or "進 捗 " in raw:
        target_system = "dashboard"
    elif "meeting" in tl or "会 議 " in raw:
        target_system = "meeting"

    cur = conn.cursor()

    dup = cur.execute("""
        select id
        from dev_proposals
        where coalesce(source_ai,'')='coo'
          and coalesce(title,'')=?
          and coalesce(status,'') in ('approved','new','pending')
          and created_at >= datetime('now','-30 minutes')
        order by id desc
        limit 1
    """, (title,)).fetchone()
    if dup:
        pid = int(dup[0])
        print(f"[coo_proposal] duplicate id={pid}", flush=True)
        return pid

    cur.execute("""
        insert into dev_proposals(
            title,
            description,
            branch_name,
            status,
            project_decision,
            dev_stage,
            guard_status,
            source_ai,
            category,
            target_system,
            improvement_type,
            quality_score
        ) values(?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        title,
        reply_text,
        branch_name,
        "approved",
        "execute_now",
        "execute_now",
        "safe",
        "coo",
        category,
        target_system,
        improvement_type,
        quality_score,
    ))
    conn.commit()
    pid = cur.lastrowid
    print(f"[coo_proposal] inserted id={pid} status=approved decision=execute_now stage=execute_now target={target_system}", flush=True)
    return pid

def is_terminal_dump(text):
    t = (text or "").strip()
    if not t:
        return False
    keys = [
        "Last login:",
        "doyopc@",
        "launchctl ",
        "sqlite3 ",
        "tail -n ",
        "cd ~/AI/",
        "python - <<'PY'",
        "bootout ",
        "bootstrap ",
        "kickstart ",
        "grep -Rni",
        "echo '===",
        "echo \"===",
    ]
    hit = sum(1 for k in keys if k in t)
    if hit >= 2:
        return True
    if "\n" in t and ("launchctl" in t or "sqlite3" in t or "tail -n" in t):
        return True
    return False


def route_special(text):
    t = normalize_user_text(text)
    tl = t.lower()
    tc = re.sub(r"\s+", "", tl)

    if t in ["/start", "start"]:
        return "start"

    if is_terminal_dump(text):
        return "chat"

    dashboard_keys = [
        "進 捗 は ？ ", "進 捗 ", "今 ど う ？ ", "今 ど う ",
        "ダ ッ シ ュ ボ ー ド ", "/進 捗 ", "/dashboard"
    ]
    if any(k.lower() in tl for k in dashboard_keys):
        return "dashboard"

    next_keys = [
        "次 の 作 業 は ？ ", "次 の 作 業 ", "次 や る こ と ",
        "作 業 指 示 ", "/次 作 業 ", "/next"
    ]
    if any(k.lower() in tl for k in next_keys):
        return "next_actions"

    coo_keys = [
        "こ ん な ん 作 っ て ",
        "こ れ を 自 動 化 し た い ",
        "こ の 機 能 を 追 加 し た い ",
        "こ う い う 仕 組 み に し た い ",
        "こ の 案 を 実 装 し た い ",
        "こ れ 作 っ て ",
        "自 動 化 し た い ",
        "機 能 追 加 し た い ",
        "telegramに 自 動 送 信 し た い ",
        "telegram通 知 を 自 動 送 信 し た い ",
        "在 庫 通 知 を telegramに 自 動 送 信 し た い ",
        "在 庫 通 知 を 自 動 送 信 し た い ",
        "telegramへ 自 動 送 信 し た い ",
        "telegramに 通 知 し た い ",
    ]
    if any(k.lower() in tl for k in coo_keys):
        return "coo_intake"

    if "在庫通知をtelegramに自動送信したい" in tc:
        return "coo_intake"
    if "これを自動化したい" in tc:
        return "coo_intake"
    if "この機能を追加したい" in tc:
        return "coo_intake"
    if "進捗は？" in tc or "進捗" == tc:
        return "dashboard"
    if "次の作業は？" in tc or "次の作業" == tc:
        return "next_actions"

    return "chat"

def run_once():
    conn = sqlite3.connect(DB, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma busy_timeout=30000")
    ensure_cols(conn)
    row = next_row(conn)
    if not row:
        print("secretary_done=0", flush=True)
        conn.close()
        return
    rid = int(row[0])
    chat_id = str(row[1] or "").strip()
    text = str(row[2] or "").strip()
    try:
        if is_terminal_dump(text):
            mark(conn, rid, "secretary_skipped_terminal_dump", None)
            print(f"[secretary_skip] rid={rid} terminal_dump=1", flush=True)
            return

        route = route_special(text)
        print(f"[secretary_route] text={text!r} route={route}", flush=True)

        if route == "start":
            reply = (
                "OpenClaw COOで す 。 \n"
                "・ 進 捗 は ？ → CEOダッシュボード \n"
                "・ 次 の 作 業 は ？ → 作業チャット指示 \n"
                "・ こ ん な ん 作 っ て → COO整理で返答 \n"
                "・ そ れ 以 外 → 通常相談に返答 "
            )
        elif route == "dashboard":
            reply = build_dashboard(conn)
        elif route == "next_actions":
            reply = (
                "OpenClaw 次 の 作 業 \n"
                "1. executor安定性チェック \n"
                "2. PR backlog確認 \n"
                "3. supply生成状況確認 \n"
                "4. learning反映確認 \n"
                "5. AI会議ログ確認 \n\n"
                "作業チャット指示例 \n"
                "cd ~/AI/openclaw-factory-daemon\n"
                "launchctl list | grep openclaw\n"
                "sqlite3 data/openclaw.db \"select count(*) from dev_proposals;\""
            )
        elif route == "coo_intake":
            reply = build_coo_plan(text, conn)
            try:
                coo_to_proposal(conn, text, reply)
            except Exception as e:
                print(f"[coo_proposal] error {e!r}", flush=True)
        else:
            context_text = build_context(conn)
            reply = ask_llm(text, context_text)

        ok, err = send(chat_id, reply)
        if ok:
            mark(conn, rid, "secretary_done", None)
            print("secretary_done=1", flush=True)
        else:
            mark(conn, rid, "secretary_error", err)
            print(f"secretary_error={err}", flush=True)
    except Exception as e:
        mark(conn, rid, "secretary_error", repr(e)[:500])
        print(f"secretary_error={e}", flush=True)
    finally:
        conn.close()

if __name__ == "__main__":
    while True:
        run_once()
        time.sleep(5)
