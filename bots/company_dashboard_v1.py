import os
import sqlite3
import datetime
import requests

DB = os.environ.get("DB_PATH") or "data/openclaw.db"
FACTORY_DB = os.environ.get("FACTORY_DB_PATH") or os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db")
TOKEN = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def dconn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA busy_timeout=30000")
    try:
        c.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    return c

def fconn():
    c = sqlite3.connect(FACTORY_DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA busy_timeout=30000")
    try:
        c.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    return c

def tg_send(chat_id, text):
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": str(chat_id), "text": text},
        timeout=20,
    )
    r.raise_for_status()

def one(c, q, a=()):
    r = c.execute(q, a).fetchone()
    return r[0] if r else 0

def team_name(display_name):
    n = (display_name or "")
    if "スカウト" in n or "調査" in n or "企画" in n:
        return "海外貿易事業チーム", "SekawakuClaw_bot"
    if "設計" in n or "エンジニア" in n or "監査" in n or "統合" in n:
        return "開発チーム", "Kaikun01_bot"
    return "経営共有チーム", "Kaikun02_bot"

def summarize_event(title):
    t = (title or "").strip()
    if "AI会議結果" in t or "AI会議結果" in t:
        return ("meeting", "AI会議", "次の進め方と優先順位を整理しました")
    if "詳しい解説" in t or "自動解説" in t:
        n = t.split("#")[-1].strip()
        return ("explain", f"案件{n}", "改善内容の詳しい技術報告を追加しました")
    if "案件報告" in t:
        n = t.split("#")[-1].strip()
        return ("report", f"案件{n}", "進捗を社長向けに短く整理しました")
    return ("other", t or "更新", "新しい共有がありました")

def latest_state_label(status, spec_stage, dev_stage):
    if status == "merged" or dev_stage == "merged":
        return "統合済み"
    if status in ("open", "pr_created") or dev_stage in ("open", "pr_created", "executed"):
        return "開発中"
    if spec_stage == "refined":
        return "仕様整理済み"
    if status == "approved":
        return "承認済み"
    return "進行中"

def title_summary(title):
    t = (title or "").lower()
    raw = (title or "").strip()
    if "read-only mode" in t:
        return "セキュリティ事故時に書き込みを止める保護機能を実装しました"
    if "refactor executor" in t:
        return "実行処理の内部構造を整理し、安定性を改善しました"
    if "reduce memory usage" in t:
        return "メモリ消費を抑える改善を入れました"
    if "add cache layer" in t:
        return "処理高速化のためキャッシュ層を追加しました"
    if "security breach" in t:
        return "障害や事故に備える保護処理を追加しました"
    if "logging" in t:
        return "ログ出力まわりを整理し、運用しやすくしました"
    if "cpu" in t:
        return "CPU負荷を下げる改善を入れました"
    if "disk" in t:
        return "ディスク利用や書き込み効率を改善しました"
    if "telemetry" in t:
        return "監視や計測データを取りやすくしました"
    if "health metrics" in t:
        return "状態監視のための指標を追加しました"
    if "admin account security monitor" in t:
        return "管理者アカウントの安全確認を強化しました"
    if "executor" in t:
        return "実行系の処理を整理して安定化しました"
    if "cache" in t:
        return "再利用できる結果を保持し、処理効率を上げました"
    return f"{raw} に関する改善を進めました"

def build_today_section(hub_recent):
    if not hub_recent:
        return [
            "【今日の主な動き】",
            "- 今日はまだ大きな更新はありません",
        ]

    items = [summarize_event(r["title"]) for r in hub_recent]
    meeting_count = sum(1 for x in items if x[0] == "meeting")
    explain_count = sum(1 for x in items if x[0] == "explain")
    report_count = sum(1 for x in items if x[0] == "report")
    other_count = sum(1 for x in items if x[0] == "other")

    parts = []
    if meeting_count:
        parts.append(f"AI会議{meeting_count}件")
    if report_count:
        parts.append(f"進捗共有{report_count}件")
    if explain_count:
        parts.append(f"詳報{explain_count}件")
    if other_count:
        parts.append(f"その他{other_count}件")

    lines = [
        "【今日の主な動き】",
        f"- 今日の更新件数: {len(hub_recent)}件",
        f"- 要約: {'、'.join(parts)} が追加されました",
    ]

    seen = set()
    detail_count = 0
    for kind, head, body in items:
        key = (kind, head, body)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"  ・{head}: {body}")
        detail_count += 1
        if detail_count >= 3:
            break

    return lines

def build_consult_section(waiting_answer, answer_received, executing, pr_open):
    lines = ["【専務・幹部から社長への相談 / 共有】"]
    has_issue = False

    if waiting_answer > 0:
        lines.append(f"- 仕様確認の返答待ちが {waiting_answer}件あります。優先順位判断が必要です")
        has_issue = True

    if answer_received > 0:
        lines.append(f"- 返答受領後の後続処理が {answer_received}件あります。詰まりがないか確認推奨です")
        has_issue = True

    if executing >= 30:
        lines.append(f"- 開発中案件が {executing}件あり多めです。統合待ち滞留の有無を週次確認推奨です")
        has_issue = True

    if pr_open >= 30:
        lines.append(f"- Open PRが {pr_open}件あります。長期滞留PRがないか確認すると安全です")
        has_issue = True

    if not has_issue:
        lines.append("- 現時点で緊急の社長判断事項はありません")

    return lines

def build_text():
    with dconn() as d, fconn() as f:
        emp_rows = d.execute(
            """
            select display_name, role_name
            from ai_employees
            where is_enabled=1
            order by id asc
            """
        ).fetchall()

        total_props = one(f, "select count(*) from dev_proposals")
        approved = one(f, "select count(*) from dev_proposals where coalesce(status,'')='approved'")
        refined = one(f, "select count(*) from dev_proposals where coalesce(spec_stage,'')='refined'")
        executing = one(f, "select count(*) from dev_proposals where coalesce(dev_stage,'') in ('executed','pr_created','open')")
        merged = one(f, "select count(*) from dev_proposals where coalesce(status,'')='merged' or coalesce(dev_stage,'')='merged'")
        waiting_answer = one(f, "select count(*) from proposal_state where coalesce(stage,'')='waiting_answer'")
        answer_received = one(f, "select count(*) from proposal_state where coalesce(stage,'')='answer_received'")
        pr_open = one(f, "select count(*) from dev_proposals where coalesce(pr_status,'')='open'")
        pr_merged = one(f, "select count(*) from dev_proposals where coalesce(pr_status,'')='merged'")

        recent = f.execute(
            """
            select id, title, coalesce(status,''), coalesce(spec_stage,''), coalesce(dev_stage,'')
            from dev_proposals
            order by id desc
            limit 5
            """
        ).fetchall()

        hub_recent = d.execute(
            """
            select title
            from ceo_hub_events
            order by id desc
            limit 5
            """
        ).fetchall()

    trade = []
    dev = []
    execs = []

    for r in emp_rows:
        team, bot = team_name(r["display_name"])
        line = f"- {r['display_name']} / {r['role_name']}"
        if team == "海外貿易事業チーム":
            trade.append(line)
        elif team == "開発チーム":
            dev.append(line)
        else:
            execs.append(line)

    lines = [
        "【OpenClaw経営ダッシュボード】",
        f"時刻: {now()}",
        "",
        "【海外貿易事業チーム】SekawakuClaw_bot",
    ]
    lines.extend(trade or ["- まだ未設定"])

    lines.extend([
        "",
        "【開発チーム】Kaikun01_bot",
    ])
    lines.extend(dev or ["- まだ未設定"])

    lines.extend([
        "",
        "【経営共有チーム】Kaikun02_bot",
    ])
    lines.extend(execs or ["- まだ未設定"])

    lines.extend([
        "",
        "【案件の全体像】",
        f"- これまでの総案件数: {total_props}",
        f"- 承認済みで次工程待ち: {approved}",
        f"- 仕様が固まり開発へ渡せる案件: {refined}",
        f"- 今まさに開発やPR確認が進んでいる案件: {executing}",
        f"- 統合まで完了した案件: {merged}",
        "",
        "【社長の返答が関係する項目】",
        f"- いま返答待ちの仕様確認: {waiting_answer}",
        f"- 返答は受け取ったが後続処理中: {answer_received}",
        "",
        "【GitHubの状況】",
        f"- まだ開いているPR: {pr_open}",
        f"- マージ済みPR: {pr_merged}",
        "",
    ])

    lines.extend(build_today_section(hub_recent))
    lines.extend([
        "",
        "【直近の案件】",
    ])

    for r in recent:
        lines.append(f"- #{r['id']} {r['title']} / {latest_state_label(r[2], r[3], r[4])}")
        lines.append(f"  {title_summary(r['title'])}")

    lines.extend([""])
    lines.extend(build_consult_section(waiting_answer, answer_received, executing, pr_open))
    lines.extend([
        "",
        "【使えるCEOコマンド】",
        "/company",
        "/meeting <議題>",
        "/help",
    ])

    return "\n".join(lines)

def run_once():
    if not TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN empty")

    done = 0
    with dconn() as d:
        rows = d.execute(
            """
            select id, chat_id, text
            from inbox_commands
            where coalesce(processed,0)=0
              and trim(coalesce(text,''))='/company'
            order by id asc
            limit 5
            """
        ).fetchall()

        for r in rows:
            try:
                tg_send(r["chat_id"], build_text())
                d.execute(
                    "update inbox_commands set processed=1,status='company_done',applied_at=? where id=?",
                    (now(), int(r["id"]))
                )
            except Exception as e:
                d.execute(
                    "update inbox_commands set status='company_error', error=?, applied_at=? where id=?",
                    (repr(e), now(), int(r["id"]))
                )
            d.commit()
            done += 1

    print(f"company_done={done}", flush=True)

if __name__ == "__main__":
    run_once()
