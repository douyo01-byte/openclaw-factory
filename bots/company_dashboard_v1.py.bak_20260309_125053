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
    import os, sqlite3, subprocess, datetime

    DB = os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "data/openclaw_real.db"

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    total = c.execute("select count(*) from dev_proposals").fetchone()[0]
    merged = c.execute("select count(*) from dev_proposals where coalesce(status,'')='merged' or coalesce(pr_status,'')='merged' or coalesce(dev_stage,'')='merged'").fetchone()[0]
    open_pr = c.execute("select count(*) from dev_proposals where coalesce(pr_status,'')='open'").fetchone()[0]
    approved = c.execute("select count(*) from dev_proposals where coalesce(status,'')='approved'").fetchone()[0]
    pending = c.execute("select count(*) from dev_proposals where coalesce(status,'')='pending'").fetchone()[0]

    waiting_answer = c.execute("select count(*) from proposal_state where coalesce(stage,'')='waiting_answer'").fetchone()[0]
    answer_received = c.execute("select count(*) from proposal_state where coalesce(stage,'')='answer_received'").fetchone()[0]

    executor_queue = approved
    executor_state = "idle" if approved == 0 else "稼働待ちあり"

    latest_merged = c.execute("""
    select id, coalesce(title,'(no title)') as title
    from dev_proposals
    where coalesce(status,'')='merged' or coalesce(pr_status,'')='merged' or coalesce(dev_stage,'')='merged'
    order by id desc
    limit 1
    """).fetchone()

    latest_proposal = c.execute("""
    select id, coalesce(title,'(no title)') as title, coalesce(source_ai, brain_type, decided_by, '不明') as src
    from dev_proposals
    order by id desc
    limit 1
    """).fetchone()

    top_rows = c.execute("""
    select
      id,
      coalesce(title,'(no title)') as title,
      coalesce(priority,0) as priority,
      coalesce(project_decision,'pending') as decision,
      coalesce(source_ai, brain_type, decided_by, '不明') as src
    from dev_proposals
    where coalesce(status,'')='approved'
    order by
      case coalesce(project_decision,'')
        when 'execute_now' then 0
        when 'review' then 1
        else 2
      end,
      coalesce(priority,0) desc,
      id desc
    limit 3
    """).fetchall()

    decision_map = {
        "execute_now": "今すぐ実行",
        "review": "要確認",
        "backlog": "保留 / バックログ",
        "pending": "未判定"
    }

    top_lines = []
    for r in top_rows:
        top_lines.append(
            f"#{r['id']} {r['title']}\n"
            f"優先度: {r['priority']}\n"
            f"判断: {decision_map.get(r['decision'], r['decision'])}\n"
            f"発案AI: {r['src']}"
        )
    if not top_lines:
        top_lines = ["現在、優先表示する承認済み案件はありません"]

    recent_rows = c.execute("""
    select
      id,
      coalesce(title,'(no title)') as title,
      coalesce(status,'') as status,
      coalesce(spec_stage,'') as spec_stage,
      coalesce(dev_stage,'') as dev_stage
    from dev_proposals
    order by id desc
    limit 3
    """).fetchall()

    def state_label(status, spec_stage, dev_stage):
        if status == "merged" or dev_stage == "merged":
            return "統合完了"
        if status in ("open", "pr_created") or dev_stage in ("open", "pr_created", "executed"):
            return "開発中"
        if spec_stage == "refined":
            return "仕様整理済み"
        if status == "approved":
            return "承認済み"
        if status == "pending":
            return "未承認案件"
        return "進行中"

    recent_lines = []
    for r in recent_rows:
        recent_lines.append(f"#{r['id']} {r['title']} / {state_label(r['status'], r['spec_stage'], r['dev_stage'])}")
    if not recent_lines:
        recent_lines = ["直近案件はありません"]

    result_rows = c.execute("""
    select
      id,
      coalesce(result_type,'pending') as result_type,
      result_score
    from dev_proposals
    where result_type is not null
    order by id desc
    limit 4
    """).fetchall()

    decision_lines = []
    for r in result_rows:
        score = "" if r["result_score"] is None else f"\nスコア: {r['result_score']}"
        decision_lines.append(f"#{r['id']} 評価: {r['result_type']}{score}")
    if not decision_lines:
        decision_lines = ["最近の評価記録はありません"]

    try:
        hub_rows = c.execute("""
        select coalesce(title,'') as title
        from ceo_hub_events
        order by id desc
        limit 5
        """).fetchall()
    except Exception:
        hub_rows = []

    meeting_count = 0
    report_count = 0
    explain_count = 0
    other_count = 0
    for r in hub_rows:
        t = r["title"]
        if "AI会議" in t:
            meeting_count += 1
        elif "案件報告" in t:
            report_count += 1
        elif "詳しい解説" in t or "自動解説" in t:
            explain_count += 1
        else:
            other_count += 1

    today_lines = []
    if latest_proposal:
        today_lines.append(f"最新提案: #{latest_proposal['id']} {latest_proposal['title']}")
        today_lines.append(f"発案AI: {latest_proposal['src']}")
    else:
        today_lines.append("最新提案: なし")

    today_summary = []
    if meeting_count:
        today_summary.append(f"AI会議 {meeting_count}件")
    if report_count:
        today_summary.append(f"進捗共有 {report_count}件")
    if explain_count:
        today_summary.append(f"詳報 {explain_count}件")
    if other_count:
        today_summary.append(f"その他 {other_count}件")
    if not today_summary:
        today_summary.append("大きな更新なし")

    consult_lines = []
    if waiting_answer > 0:
        consult_lines.append(f"- 仕様確認の返答待ちが {waiting_answer}件あります")
    if answer_received > 0:
        consult_lines.append(f"- 返答受領後の後続処理が {answer_received}件あります")
    if approved > 0:
        consult_lines.append(f"- 承認済み案件が {approved}件あり、優先順位の監視が必要です")
    if not consult_lines:
        consult_lines.append("- 現時点で緊急の社長判断事項はありません")

    def is_running(label):
        try:
            out = subprocess.check_output(
                ["launchctl", "print", f"gui/{os.getuid()}/{label}"],
                text=True,
                stderr=subprocess.DEVNULL
            )
            return "state = running" in out or "pid =" in out
        except Exception:
            return False

    core = [
        ("supervisor", "jp.openclaw.supervisor"),
        ("project_brain_v4", "jp.openclaw.project_brain_v4"),
        ("self_healing_v2", "jp.openclaw.self_healing_v2"),
    ]
    dev = [
        ("spec_refiner_v2", "jp.openclaw.spec_refiner_v2"),
        ("dev_pr_watcher_v1", "jp.openclaw.dev_pr_watcher_v1"),
        ("dev_command_executor_v1", "jp.openclaw.dev_command_executor_v1"),
    ]
    tg = [
        ("tg_poll_loop", "jp.openclaw.tg_poll_loop"),
        ("tg_private_ingest_v1", "jp.openclaw.tg_private_ingest_v1"),
        ("spec_notify_v1", "jp.openclaw.spec_notify_v1"),
    ]

    def fmt_bot(items):
        lines = []
        for name, label in items:
            lines.append(f"{name}: {'稼働中' if is_running(label) else '停止'}")
        return "\n".join(lines)

    last_merge_line = "最新マージ: なし"
    if latest_merged:
        last_merge_line = f"最新マージ: #{latest_merged['id']} {latest_merged['title']}"

    text = f"""OpenClaw CEOダッシュボード
（AI経営管理システム）

━━━━━━━━━━━━━━━━━━
【今日の主な動き】

概要: {' / '.join(today_summary)}
{chr(10).join(today_lines)}

━━━━━━━━━━━━━━━━━━
【社長の返答待ち項目】

現在 {waiting_answer}件

※ 社長判断が必要な案件がここに表示されます

━━━━━━━━━━━━━━━━━━
【直近の案件（優先順）】

{chr(10).join(top_lines)}

━━━━━━━━━━━━━━━━━━
【専務・幹部から社長への相談 / 共有】

{chr(10).join(consult_lines)}

━━━━━━━━━━━━━━━━━━
【会社状態】

総提案件数: {total}
マージ済み: {merged}
Open PR: {open_pr}
実行待ち案件: {approved}
未承認案件: {pending}
Executor状態: {executor_state}
Executor Queue: {executor_queue}
{last_merge_line}

━━━━━━━━━━━━━━━━━━
【最近の意思決定】

{chr(10).join(decision_lines)}

━━━━━━━━━━━━━━━━━━
【AI社員構成】

■ 海外事業
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
・みはりん（監視）

━━━━━━━━━━━━━━━━━━
【BOT状態】

Core
{fmt_bot(core)}

開発
{fmt_bot(dev)}

Telegram
{fmt_bot(tg)}

━━━━━━━━━━━━━━━━━━
【次の一手】

・Project Brain v4 継続運用
・Learning Brain v2 検討
・実行待ち案件の監視
"""
    conn.close()
    return text[:3500]
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
              and (
                trim(coalesce(text,''))='/company'
                or instr(
                  replace(replace(replace(replace(replace(replace(replace(lower(coalesce(text,'')),' ',''),'　',''),'?',''),'？',''),'。',''),'!',''),'！',''),
                  '進捗'
                ) > 0
                or instr(
                  replace(replace(replace(replace(replace(replace(replace(lower(coalesce(text,'')),' ',''),'　',''),'?',''),'？',''),'。',''),'!',''),'！',''),
                  '状況'
                ) > 0
                or instr(
                  replace(replace(replace(replace(replace(replace(replace(lower(coalesce(text,'')),' ',''),'　',''),'?',''),'？',''),'。',''),'!',''),'！',''),
                  'ボード'
                ) > 0
                or instr(
                  replace(replace(replace(replace(replace(replace(replace(lower(coalesce(text,'')),' ',''),'　',''),'?',''),'？',''),'。',''),'!',''),'！',''),
                  'ダッシュボード'
                ) > 0
                or instr(
                  replace(replace(replace(replace(replace(replace(replace(lower(coalesce(text,'')),' ',''),'　',''),'?',''),'？',''),'。',''),'!',''),'！',''),
                  '会社'
                ) > 0
                or instr(
                  replace(replace(replace(replace(replace(replace(replace(lower(coalesce(text,'')),' ',''),'　',''),'?',''),'？',''),'。',''),'!',''),'！',''),
                  '全体'
                ) > 0
                or instr(
                  replace(replace(replace(replace(replace(replace(replace(lower(coalesce(text,'')),' ',''),'　',''),'?',''),'？',''),'。',''),'!',''),'！',''),
                  '詳しく'
                ) > 0
                or instr(
                  replace(replace(replace(replace(replace(replace(replace(lower(coalesce(text,'')),' ',''),'　',''),'?',''),'？',''),'。',''),'!',''),'！',''),
                  '詳細'
                ) > 0
              )
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
