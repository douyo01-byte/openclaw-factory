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
TG_TOKEN = (os.environ.get("TELEGRAM_DEV_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
TG_CHAT = (os.environ.get("TELEGRAM_DEV_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
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
    title = (row["title"] or "").strip()
    target = (row["target_system"] or "").strip()
    improvement = (row["improvement_type"] or "").strip().lower()
    source_ai = (row["source_ai"] or "").strip()
    pr_url = (pr.get("url") or row["pr_url"] or "").strip()

    kind, probs, effs = summarize_kind(improvement)
    prob1 = probs[0] if probs else "同 じ 改 善 点 が 見 え に く い 状 態 が あ っ た"
    prob2 = probs[1] if len(probs) > 1 else "今 後 の 変 更 影 響 を 追 い に く か っ た"
    eff1 = effs[0] if effs else "動 作 を よ り 安 定 さ せ や す く な る"
    eff2 = effs[1] if len(effs) > 1 else "今 後 の 改 善 を 進 め や す く な る"

    target_map = {
        "telegram": "Telegramま わ り",
        "dashboard": "ダ ッ シ ュ ボ ー ド ま わ り",
        "meeting": "会 議 /共 有 ま わ り",
        "core": "中 核 ロ ジ ッ ク",
        "db": "DBま わ り",
    }
    target_txt = target_map.get(target.lower(), target or "シ ス テ ム 全 体")

    style_idx = sum(ord(c) for c in (title + improvement + target)) % 4

    if improvement in ("logging", "observability"):
        one = f"{target_txt} の 見 え に く さ を 減 ら す 調 整 を 入 れ ま し た"
        fix1 = f"{target_txt} で 追 い に く か っ た 情 報 を 見 や す く 整 理 し た"
        fix2 = "状 況 確 認 に 使 う 出 力 の 粒 度 を 整 え た"
        risk1 = "異 常 が 起 き て も 気 づ く の が 遅 れ る 事 態"
        risk2 = "何 が 起 き た か 分 か り に く い 状 態"
    elif improvement in ("refactor", "cleanup"):
        one = f"{target_txt} の コ ー ド を 整 理 し て 今 後 い じ り や す く し ま し た"
        fix1 = "重 複 し て い た 処 理 を ま と め た"
        fix2 = f"{target_txt} の 読 み や す さ と 保 守 性 を 上 げ た"
        risk1 = "同 じ 修 正 を 複 数 箇 所 に 入 れ 忘 れ る 不 具 合"
        risk2 = "小 さ な 変 更 で 壊 れ や す い 状 態"
    elif improvement in ("automation", "auto", "workflow"):
        one = f"{target_txt} の 手 作 業 を 減 ら す 側 の 改 善 を 入 れ ま し た"
        fix1 = "人 手 で や っ て い た 流 れ を 自 動 ラ イ ン に 乗 せ や す く し た"
        fix2 = "次 の 実 行 に つ な が る 状 態 遷 移 を 整 え た"
        risk1 = "手 動 作 業 の 抜 け 漏 れ"
        risk2 = "流 れ が 途 中 で 止 ま る 状 態"
    elif improvement in ("guard", "safety", "reliability"):
        one = f"{target_txt} で 危 な い 動 き を 起 こ し に く く す る 調 整 を 入 れ ま し た"
        fix1 = "異 常 系 で も 壊 れ に く い よ う ガ ー ド を 追 加 し た"
        fix2 = "想 定 外 デ ー タ で 落 ち に く い よ う に し た"
        risk1 = "突 然 の 停 止"
        risk2 = "危 な い 実 行 が そ の ま ま 通 る 状 態"
    elif improvement in ("optimization", "performance"):
        one = f"{target_txt} の 動 作 を 少 し 軽 く す る 側 の 改 善 を 入 れ ま し た"
        fix1 = "無 駄 な 処 理 を 減 ら し た"
        fix2 = "実 行 の 重 さ が 出 や す い 部 分 を 見 直 し た"
        risk1 = "処 理 が だ ん だ ん 重 く な る 状 態"
        risk2 = "負 荷 時 の 反 応 遅 延"
    else:
        one = f"{target_txt} の 安 定 性 を 上 げ る 調 整 を 行 い ま し た"
        fix1 = f"{target_txt} の 挙 動 を 見 直 し て 不 安 定 要 因 を 減 ら し た"
        fix2 = "今 後 の 改 善 を 入 れ や す い 形 に 整 え た"
        risk1 = "同 種 の 不 安 定 動 作"
        risk2 = "原 因 が 追 い に く い 不 具 合"

    headers = [
        ("今 回 の 変 更", "直 し た 理 由", "期 待 で き る 効 果", "起 き に く く な る こ と"),
        ("今 回 や っ た こ と", "背 景", "こ の 変 更 の 効 果", "減 ら し た い リ ス ク"),
        ("今 回 の 改 善 点", "な ぜ 手 を 入 れ た か", "変 更 後 の 見 込 み", "防 ぎ た い 事 象"),
        ("今 回 の 調 整", "課 題 だ っ た 点", "良 く な る 点", "起 き に く く な る 不 具 合"),
    ]
    h1, h2, h3, h4 = headers[style_idx]

    lines = []
    lines.append("🧠 OpenClaw 自 律 開 発")
    lines.append("")
    lines.append(f"■ {h1}")
    lines.append(one)
    if title:
        lines.append(f"・ 対 象 : {title[:120]}")
    lines.append("")
    lines.append(f"■ {h2}")
    lines.append(f"・ {prob1}")
    lines.append(f"・ {prob2}")
    lines.append("")
    lines.append("■ 今 回 入 れ た 手 当 て")
    lines.append(f"・ {fix1}")
    lines.append(f"・ {fix2}")
    lines.append("")
    lines.append(f"■ {h3}")
    lines.append(f"・ {eff1}")
    lines.append(f"・ {eff2}")
    lines.append("")
    lines.append(f"■ {h4}")
    lines.append(f"・ {risk1}")
    lines.append(f"・ {risk2}")
    if source_ai:
        lines.append("")
        lines.append("■ 担 当 AI")
        lines.append(source_ai)
    if pr_url:
        lines.append("")
        lines.append("■ PR")
        lines.append(pr_url)
    return "\n".join(lines)

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

AIがシステムの改善を完了しました

■ まず結論
<初心者向けに1行>

■ 直す前の課題
・ <変更前の困りごと1>
・ <変更前の困りごと2>

■ 今回やったこと
・ <修正1>
・ <修正2>
・ <必要なら修正3>

■ 良くなる点
・ <効果1>
・ <効果2>

■ 防げるトラブル例
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
                      pr_url,
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
