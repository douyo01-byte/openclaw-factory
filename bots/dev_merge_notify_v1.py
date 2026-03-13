from __future__ import annotations
import json
import os
import re
import sqlite3

def should_skip_by_target_policy(row) -> bool:
    try:
        tp = ""
        if isinstance(row, dict):
            tp = str(row.get("target_policy") or "").strip().lower()
        else:
            try:
                tp = str(row["target_policy"] or "").strip().lower()
            except Exception:
                tp = ""
        return tp in {"archived_or_parked", "parked"}
    except Exception:
        return False

import subprocess
import time
from pathlib import Path

import requests

DB_PATH = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
STATE_PATH = Path(os.path.expanduser("~/AI/openclaw-factory-daemon/data/dev_merge_notify_v1.state"))
SLEEP = int(os.environ.get("DEV_MERGE_NOTIFY_SLEEP", "10"))
TG_TOKEN = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
TG_CHAT = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
OPENAI_API_KEY = (os.environ.get("OPENAI_API_KEY") or "").strip()
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_TIMEOUT = int(os.environ.get("DEV_MERGE_NOTIFY_OPENAI_TIMEOUT", "45"))

TITLE_CLEAN_RE = re.compile(r"^(統\s*合\s*完\s*了\s*:?\s*)", re.IGNORECASE)

def tg_send(text: str):
    if not TG_TOKEN or not TG_CHAT:
        print("[merge_notify] telegram env missing", flush=True)
        return
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data={"chat_id": TG_CHAT, "text": text},
        timeout=(3, 20),
    ).raise_for_status()

def load_last_id() -> int:
    try:
        return int((STATE_PATH.read_text(encoding="utf-8").strip() or "0"))
    except Exception:
        return 0

def save_last_id(v: int):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(str(v), encoding="utf-8")

def clean_title(s: str) -> str:
    s = s or ""
    s = TITLE_CLEAN_RE.sub("", s).strip()
    return s

def short(s: str, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[:n] + "..."

def gh_text(args: list[str]) -> str:
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return ""
        return (r.stdout or "").strip()
    except Exception:
        return ""

def gh_json(pr_number: int) -> dict:
    out = gh_text([
        "gh", "pr", "view", str(pr_number),
        "--json",
        "title,body,files,url,number,mergeCommit",
    ])
    if not out:
        return {}
    try:
        return json.loads(out)
    except Exception:
        return {}

def summarize_kind(improvement_type: str) -> tuple[str, list[str], list[str]]:
    t = (improvement_type or "").lower().strip()
    if t in {"bugfix", "bug_fix"}:
        return (
            "不具合を直しました",
            ["エラーや想定外の動きを修正"],
            ["止まりにくくなる", "動作が安定する"],
        )
    if t in {"guard", "safety", "reliability"}:
        return (
            "失敗しやすい処理を守るようにしました",
            ["例外時でも落ちにくい処理を追加"],
            ["途中停止しにくくなる", "自動運転が安定する"],
        )
    if t in {"refactor"}:
        return (
            "コードの整理をしました",
            ["重複や複雑さを減らして保守しやすく調整"],
            ["今後の改修がしやすくなる", "不具合が混ざりにくくなる"],
        )
    if t in {"logging", "observability", "diagnostics"}:
        return (
            "原因を追いやすくしました",
            ["ログや診断情報を追加"],
            ["問題発生時に原因を見つけやすい", "運用が楽になる"],
        )
    if t in {"optimization", "performance"}:
        return (
            "処理を軽くしました",
            ["無駄な処理や通信回数を削減"],
            ["速度改善", "負荷軽減"],
        )
    if t in {"automation"}:
        return (
            "手作業を減らしました",
            ["自動で進む処理を追加または改善"],
            ["放置運転しやすくなる", "人的確認を減らせる"],
        )
    return (
        "内部処理を改善しました",
        ["安定性または保守性を上げる調整"],
        ["全体の運用が安定する"],
    )

def build_fallback(row: sqlite3.Row, pr: dict) -> str:
    title = clean_title((row["title"] or ""))
    target = (row["target_system"] or "").strip()
    source_ai = (row["source_ai"] or "").strip() or "unknown"
    result_type = (row["result_type"] or "").strip()
    result_note = (row["result_note"] or "").strip()
    pr_url = (row["pr_url"] or "").strip()
    pr_number = row["pr_number"] or ""

    files = choose_display_files(target, pr)
    all_files = [(x.get("path") or "").strip() for x in (pr.get("files") or []) if (x.get("path") or "").strip()]
    extra = max(len([x for x in all_files if not x.startswith("dev_autogen/")]) - len(files), 0)

    lower = (title + " " + (row["improvement_type"] or "")).lower()

    if any(x in lower for x in ["retry", "backoff", "timeout"]):
        one = "通信や外部処理が一時的に失敗しても止まりにくくしました"
        prob1 = "一時的な通信エラーや外部APIの不調で処理が失敗することがあった"
        prob2 = "失敗がそのまま表面化し、通知漏れや処理停止につながる可能性があった"
        fix1 = "失敗時に一定回数だけ自動でやり直す仕組みを追加した"
        fix2 = "待ち時間を少しずつ増やしながら再試行するようにした"
        eff1 = "一時的な不安定さで処理全体が止まりにくくなる"
        eff2 = "通知や外部連携の成功率が上がりやすくなる"
        ex1 = "ネット回線が一瞬不安定でも、その場で復旧しやすくなる"
        ex2 = "外部サービスの短い不調で処理が失敗しっぱなしになる事態が減る"
    elif any(x in lower for x in ["log", "logging", "record", "debug"]):
        one = "エラーや処理結果をあとから確認しやすくしました"
        prob1 = "問題が起きたときに、何が原因だったのか追いにくいことがあった"
        prob2 = "成功した処理と失敗した処理の違いが分かりにくいことがあった"
        fix1 = "重要な処理結果やエラー内容を記録する仕組みを追加した"
        fix2 = "あとから見返して原因を追いやすい形に整理した"
        eff1 = "トラブル時の調査が速くなる"
        eff2 = "運用中の問題発見と修正がしやすくなる"
        ex1 = "失敗した理由が分からず長く止まる事態が減る"
        ex2 = "同じ不具合を何度も調べ直す手間が減る"
    elif any(x in lower for x in ["sqlite", "db", "connection", "close", "rollback", "context manager"]):
        one = "データベースまわりが壊れにくく、安全に動くようにしました"
        prob1 = "データベース接続の閉じ忘れや途中失敗で、状態が不安定になる可能性があった"
        prob2 = "放置するとロックや接続残りで次の処理に悪影響が出ることがあった"
        fix1 = "接続を安全に開閉する形へ整理した"
        fix2 = "失敗時にも後片付けが行われるようにした"
        eff1 = "データベースの安定性が上がる"
        eff2 = "ロックや接続残りによる不具合が起きにくくなる"
        ex1 = "処理後に接続が残って次の処理が詰まる事態が減る"
        ex2 = "途中エラー後に状態が中途半端になる問題が起きにくくなる"
    elif any(x in lower for x in ["refactor", "cleanup", "tidy", "duplicate"]):
        one = "コードの整理を行い、今後の保守をしやすくしました"
        prob1 = "同じような処理が散らばり、修正時に見落としが出やすかった"
        prob2 = "読みづらさが将来の改修ミスにつながる可能性があった"
        fix1 = "重複や分かりにくい処理を整理した"
        fix2 = "構造を整えて読みやすくした"
        eff1 = "今後の修正や追加開発がしやすくなる"
        eff2 = "変更時の見落としや事故が減りやすくなる"
        ex1 = "似た修正を複数箇所に入れ忘れる問題が減る"
        ex2 = "後から見たときに処理の流れを理解しやすくなる"
    else:
        one = "内部処理を安定して動きやすい形に改善しました"
        prob1 = "処理の一部で失敗や不安定さが起きる可能性があった"
        prob2 = "放置すると運用時の手戻りや確認コストが増える可能性があった"
        fix1 = "不安定になりやすい箇所を見直した"
        fix2 = "失敗しにくくなるよう安全側の処理を追加した"
        eff1 = "日常運用で止まりにくくなる"
        eff2 = "トラブル時の切り分けがしやすくなる"
        ex1 = "小さな失敗で全体の流れが止まる事態が減る"
        ex2 = "原因不明の不調として残るケースが減る"

    lines = []
    lines.append("🧠 OpenClaw 自律開発")
    lines.append("")
    lines.append("AIがシステムを改善しました")
    lines.append("")
    lines.append("■ 今回ひとことで言うと")
    lines.append(one)
    lines.append("")
    lines.append("■ 何が問題だった？")
    lines.append(f"・ {prob1}")
    lines.append(f"・ {prob2}")
    lines.append("")
    lines.append("■ どう直した？")
    lines.append(f"・ {fix1}")
    lines.append(f"・ {fix2}")
    lines.append("")
    lines.append("■ これで何が良くなる？")
    lines.append(f"・ {eff1}")
    lines.append(f"・ {eff2}")
    lines.append("")
    lines.append("■ たとえば何が起きにくくなる？")
    lines.append(f"・ {ex1}")
    lines.append(f"・ {ex2}")
    lines.append("")
    lines.append("■ 変更ファイル")
    if files:
        for f in files:
            lines.append(f)
        if extra > 0:
            lines.append(f"ほか {extra}件")
    else:
        lines.append("不明")
    lines.append("")
    lines.append("■ 開発AI")
    lines.append(source_ai)
    if result_type or result_note:
        lines.append("")
        lines.append("■ 学習結果")
        lines.append(human_learning_text(result_type, result_note))
    if pr_url or pr_number:
        lines.append("")
        lines.append("■ PR")
        lines.append(pr_url or f"#{pr_number}")
    return "\n".join(lines)

def human_learning_text(result_type: str, result_note: str) -> str:
    rt = (result_type or "").strip().lower()
    rn = (result_note or "").strip()
    if rt == "success":
        if "normal merged change" in rn.lower():
            return "通常の改善として問題なく取り込まれました。"
        return "今回の改善は正常に取り込まれ、今後の判断材料として活用されます。"
    if rt == "neutral":
        if rn:
            return f"大きな問題はありませんが、効果は限定的と判断されました。({rn})"
        return "大きな問題はありませんが、効果は限定的と判断されました。"
    if rt in ("fail", "failed", "error"):
        if rn:
            return f"改善効果は弱い可能性があり、再検討候補として記録されました。({rn})"
        return "改善効果は弱い可能性があり、再検討候補として記録されました。"
    if rn:
        return rn
    return "今回の変更結果は学習データとして保存されました。"

def choose_display_files(target: str, pr: dict) -> list[str]:
    t = (target or "").strip()
    if t and not t.startswith("dev_autogen/"):
        return [t]
    files = [(f.get("path") or "").strip() for f in (pr.get("files") or [])]
    files = [x for x in files if x and not x.startswith("dev_autogen/")]
    if files:
        return files[:3]
    if t:
        return [t]
    raw = [(f.get("path") or "").strip() for f in (pr.get("files") or [])]
    raw = [x for x in raw if x]
    return raw[:3]

def call_openai(prompt: str) -> str:
    if not OPENAI_API_KEY:
        return ""
    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
                "temperature": 0.2,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "あなたはOpenClawの開発通知要約AIです。"
                            "初心者でも分かる日本語で、専門用語を噛み砕いて説明してください。"
                            "出力は指定フォーマットを厳守してください。"
                            "誇張禁止。diffとPR情報から分かることだけを書く。"
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=OPENAI_TIMEOUT,
        )
        r.raise_for_status()
        j = r.json()
        return (((j.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
    except Exception as e:
        print(f"[merge_notify] openai_error {e!r}", flush=True)
        return ""

def build_prompt(row: sqlite3.Row, pr: dict) -> str:
    title = clean_title((row["title"] or ""))
    target = (row["target_system"] or "").strip()
    improvement_type = (row["improvement_type"] or "").strip()
    source_ai = (row["source_ai"] or "").strip()
    result_type = (row["result_type"] or "").strip()
    result_note = (row["result_note"] or "").strip()
    pr_url = (row["pr_url"] or "").strip()
    pr_number = row["pr_number"] or ""
    pr_title = pr.get("title") or ""
    pr_body = pr.get("body") or ""

    all_files = [(f.get("path") or "").strip() for f in (pr.get("files") or []) if (f.get("path") or "").strip()]
    display_files = choose_display_files(target, pr)
    extra = max(len([x for x in all_files if not x.startswith("dev_autogen/")]) - len(display_files), 0)

    diff_files = []
    for path in display_files[:3]:
        patch = gh_text(["gh", "pr", "diff", str(pr_number), "--", path]) if pr_number else ""
        diff_files.append(f"FILE: {path}\n{short(patch, 2500)}")
    changed_text = "\n".join(diff_files) if diff_files else ""

    file_lines = display_files[:]
    if extra > 0:
        file_lines.append(f"ほか {extra}件")
    file_block = "\n".join(file_lines) if file_lines else "不明"

    learning_text = human_learning_text(result_type, result_note)

    return f"""
以下の開発変更を、初心者にも分かる日本語で通知文にしてください。
推測は禁止。分からないことは一般化して表現してください。
専門用語はできるだけ避けてください。
「変更ファイル」は必ず入力情報の display_files を優先して使い、dev_autogen/ だけを単独で出さないでください。
「学習結果」は result_type / result_note をそのまま繰り返さず、自然な説明文にしてください。

必ず次の形式で出力してください。

🧠 OpenClaw 自律開発

AIがシステムを改善しました

■ 今回ひとことで言うと
<初心者向けに1行>

■ 何が問題だった？
・ <変更前の困りごと1>
・ <変更前の困りごと2>

■ どう直した？
・ <修正1>
・ <修正2>
・ <必要なら修正3>

■ これで何が良くなる？
・ <効果1>
・ <効果2>

■ たとえば何が起きにくくなる？
・ <具体例1>
・ <具体例2>

■ 変更ファイル
<display_files をそのまま使用。最大3件。多ければ最後に ほかN件>

■ 開発AI
<source_ai>

■ 学習結果
<learning_text を自然に言い換えて1〜2文>

■ PR
<url>

入力情報:
proposal_title: {title}
target_system: {target}
improvement_type: {improvement_type}
source_ai: {source_ai}
result_type: {result_type}
result_note: {result_note}
learning_text: {learning_text}
pr_number: {pr_number}
pr_url: {pr_url}

display_files:
{file_block}

PR title:
{pr_title}

PR body:
{short(pr_body, 4000)}

changed_diff:
{changed_text}
"""

def build_msg(event_row: sqlite3.Row, proposal_row: sqlite3.Row) -> str:
    pr_number = proposal_row["pr_number"]
    pr = gh_json(int(pr_number)) if pr_number else {}
    prompt = build_prompt(proposal_row, pr)
    msg = call_openai(prompt)
    if msg:
        return msg
    return build_fallback(proposal_row, pr)

def main():
    while True:
        try:
            last_id = load_last_id()
            conn = sqlite3.connect(DB_PATH, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("pragma busy_timeout=30000")
            rows = conn.execute("""
                select id, event_type, proposal_id, title, coalesce(pr_url,'') pr_url
                from ceo_hub_events
                where event_type='merged' and id>?
                order by id asc
            """, (last_id,)).fetchall()
            new_last = last_id
            for r in rows:
                dp = conn.execute("""
                    select
                      id,
                      title,
                      target_system,
                      improvement_type,
                      source_ai,
                      result_type,
                      result_note,
                      pr_number,
                      pr_url
                    coalesce(target_policy,'') as target_policy
                    from dev_proposals
                    where id=?
                    limit 1
                """, (r["proposal_id"],)).fetchone()
                if should_skip_by_target_policy(dp):
                    save_last_id(int(r["id"]))
                    new_last = int(r["id"])
                    continue
                if not dp:
                    new_last = int(r["id"])
                    continue
                try:
                    msg = build_msg(r, dp)
                except Exception as e:
                    print(f"[merge_notify] build_error proposal_id={r['proposal_id']} {e!r}", flush=True)
                    msg = build_fallback(dp, {})
                tg_send(msg)
                new_last = int(r["id"])
                print(f"[merge_notify] sent event_id={new_last} proposal_id={r['proposal_id']}", flush=True)
            conn.close()
            if new_last != last_id:
                save_last_id(new_last)
        except Exception as e:
            print(f"[merge_notify] error {e!r}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
