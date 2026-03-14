from __future__ import annotations


def missing_call_openai_disabled(*args, **kwargs):
    raise RuntimeError("llm_disabled_for_merge_notify")
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



def human_learning_text(result_type: str, result_note: str) -> str:
    rt = (result_type or "").strip().lower()
    rn = (result_note or "").strip()
    if rt in {"success", "merged", "normal"}:
        if rn:
            return f"今 回 の 変 更 は 安 定 し た 改 善 と し て 取 り 込 ま れ ま し た 。 {rn[:120]}"
        return "今 回 の 変 更 は 通 常 の 改 善 と し て 問 題 な く 取 り 込 ま れ ま し た 。"
    if rt in {"warning", "partial"}:
        if rn:
            return f"反 映 は 進 ん で い ま す が 、 一 部 は 継 続 観 察 が 必 要 で す 。 {rn[:120]}"
        return "反 映 は 進 ん で い ま す が 、 継 続 観 察 が 必 要 で す 。"
    if rt in {"fail", "error"}:
        if rn:
            return f"今 回 の 学 習 反 映 は 課 題 つ き で 、 再 調 整 の 余 地 が あ り ま す 。 {rn[:120]}"
        return "今 回 の 学 習 反 映 は 再 調 整 の 余 地 が あ り ま す 。"
    if rn:
        return rn[:120]
    return "今 回 の 変 更 は 次 の 改 善 に つ な が る 学 習 と し て 記 録 さ れ ま し た 。"

def choose_display_files(row: sqlite3.Row, pr: dict) -> list[str]:
    files = []
    try:
        if pr:
            for f in (pr.get("files") or []):
                path = (f.get("path") or "").strip()
                if not path:
                    continue
                if path.startswith("dev_autogen/"):
                    continue
                files.append(path)
    except Exception:
        pass

    if not files:
        try:
            raw = (row["changed_files"] if "changed_files" in row.keys() else "") or ""
            raw = str(raw).strip()
            if raw:
                for x in raw.replace("\r", "\n").split("\n"):
                    x = x.strip()
                    if not x:
                        continue
                    if x.startswith("dev_autogen/"):
                        continue
                    files.append(x)
        except Exception:
            pass

    seen = set()
    out = []
    for x in files:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)

    out = out[:3]
    if out:
        return out

    try:
        target = ((row["target_system"] or "").strip() if "target_system" in row.keys() else "")
    except Exception:
        target = ""
    try:
        improvement = ((row["improvement_type"] or "").strip() if "improvement_type" in row.keys() else "")
    except Exception:
        improvement = ""
    try:
        title = ((row["title"] or "").strip() if "title" in row.keys() else "")
    except Exception:
        title = ""

    if target:
        return [target]
    if improvement:
        return [improvement]
    if title:
        return [title[:40]]
    return ["core"]

def build_fallback(row: sqlite3.Row, pr: dict) -> str:
    title = (row["title"] or "").strip()
    target = (row["target_system"] or "").strip()
    improvement = (row["improvement_type"] or "").strip().lower()
    source_ai = (row["source_ai"] or "").strip()
    pr_url = (pr.get("url") or row["pr_url"] or "").strip()

    target_map = {
        "core": "中 核 ロ ジ ッ ク",
        "telegram": "Telegram ま わ り",
        "dashboard": "ダ ッ シ ュ ボ ー ド",
        "meeting": "会 議 /共 有 系",
        "db": "DB ま わ り",
    }
    target_txt = target_map.get(target.lower(), target or "シ ス テ ム 全 体")

    if improvement in ("logging", "observability"):
        one = f"{target_txt} の 見 え に く さ を 減 ら す 側 の 改 善 を 入 れ ま し た"
        bg1 = "状 況 確 認 に 時 間 が か か る 箇 所 が あ っ た"
        bg2 = "何 が 起 き た か 追 い に く い 瞬 間 が あ っ た"
        fx1 = "出 力 の 粒 度 と 見 え 方 を 整 え た"
        fx2 = "追 跡 に 必 要 な 情 報 を 取 り や す く し た"
        ef1 = "異 常 の 察 知 が 早 く な る"
        ef2 = "原 因 の 切 り 分 け が し や す く な る"
        rs1 = "見 落 と し"
        rs2 = "調 査 の 長 期 化"
    elif improvement in ("refactor", "cleanup"):
        one = f"{target_txt} を い じ り や す く す る 整 理 を 入 れ ま し た"
        bg1 = "同 じ よ う な 処 理 が 分 か れ て い た"
        bg2 = "今 後 の 修 正 で 差 分 管 理 が 面 倒 に な り や す か っ た"
        fx1 = "重 複 気 味 の 処 理 を 整 理 し た"
        fx2 = "読 み や す さ と 保 守 性 を 上 げ た"
        ef1 = "次 の 修 正 を 入 れ や す く な る"
        ef2 = "修 正 漏 れ を 起 こ し に く く な る"
        rs1 = "同 歩 修 正 漏 れ"
        rs2 = "保 守 コ ス ト 増 加"
    elif improvement in ("automation", "workflow"):
        one = f"{target_txt} の 手 作 業 を 減 ら す 方 向 の 調 整 を 入 れ ま し た"
        bg1 = "人 手 を 挟 む と 流 れ が 止 ま り や す い"
        bg2 = "処 理 の 受 け 渡 し が 不 安 定 に な る 場 面 が あ っ た"
        fx1 = "自 動 ラ イ ン に 乗 せ や す い 状 態 へ 整 え た"
        fx2 = "次 の ス テ ー ジ へ 進 み や す く し た"
        ef1 = "流 れ が 途 切 れ に く く な る"
        ef2 = "処 理 の 進 行 速 度 が 安 定 し や す い"
        rs1 = "手 動 漏 れ"
        rs2 = "停 滞"
    elif improvement in ("guard", "safety", "reliability"):
        one = f"{target_txt} で 危 な い 動 き を 減 ら す た め の ガ ー ド を 入 れ ま し た"
        bg1 = "想 定 外 の 入 力 で 崩 れ る 余 地 が あ っ た"
        bg2 = "異 常 系 の と き の 守 り が 薄 い 箇 所 が あ っ た"
        fx1 = "落 ち や す い 条 件 を 先 回 り で 防 い だ"
        fx2 = "危 な い 実 行 に 入 り に く い よ う に し た"
        ef1 = "突 然 止 ま る 事 象 が 減 る"
        ef2 = "安 定 運 用 に 近 づ く"
        rs1 = "異 常 停 止"
        rs2 = "想 定 外 実 行"
    elif improvement in ("optimization", "performance"):
        one = f"{target_txt} を 少 し 軽 く す る 側 の 見 直 し を 行 い ま し た"
        bg1 = "無 駄 な 負 荷 が 積 み 上 が り や す か っ た"
        bg2 = "処 理 の 重 さ が 今 後 の 足 か せ に な り う る 状 態 だ っ た"
        fx1 = "重 く な り や す い 箇 所 を 整 理 し た"
        fx2 = "実 行 コ ス ト を 抑 え る 方 向 へ 調 整 し た"
        ef1 = "反 応 が 安 定 し や す い"
        ef2 = "今 後 の 拡 張 に 耐 え や す い"
        rs1 = "遅 延"
        rs2 = "負 荷 増 大"
    else:
        one = f"{target_txt} の 挙 動 を 安 定 側 に 寄 せ る 調 整 を 行 い ま し た"
        bg1 = "挙 動 の む ら を 減 ら し た か っ た"
        bg2 = "次 の 改 善 を 入 れ や す い 土 台 に し た か っ た"
        fx1 = "不 安 定 要 因 を 減 ら す 見 直 し を 行 っ た"
        fx2 = "継 続 改 善 し や す い 状 態 に 整 え た"
        ef1 = "運 用 の 安 定 性 が 上 が る"
        ef2 = "次 の 改 善 が ス ム ー ズ に な る"
        rs1 = "再 発"
        rs2 = "追 跡 困 難"

    bucket = classify_notify_bucket(title, target_txt, improvement, pr_url)
    scope_txt = bucket_scope_text(bucket)
    reason_lines = bucket_reason_lines(bucket)
    action_items = bucket_action_lines(bucket)
    effects = bucket_effect_lines(bucket)
    avoids = bucket_avoid_lines(bucket)

    lines = []
    lines.append("🧠 OpenClaw 自律開発")
    if title:
        lines.append(f"対象: {title[:120]}")
    else:
        lines.append(f"対象: {target_txt}")
    lines.append(f"種類: {improvement or 'general'}")
    if source_ai:
        lines.append(f"開発AI: {source_ai}")
    if pr_url:
        lines.append(f"PR: {pr_url}")
    return "\n".join(lines)



def compact_text(x: str) -> str:
    return " ".join((x or "").replace("\n", " ").split()).strip()

def classify_notify_bucket(title: str, target_txt: str, improvement: str, pr_url: str) -> str:
    x = " ".join([
        compact_text(title).lower(),
        compact_text(target_txt).lower(),
        compact_text(improvement).lower(),
        compact_text(pr_url).lower(),
    ])
    if any(k in x for k in ["telegram", "notify", "notification", "message", "reply", "chat"]):
        return "notification"
    if any(k in x for k in ["router", "route", "dispatch", "handover"]):
        return "routing"
    if any(k in x for k in ["watcher", "merge", "automerge", "pr"]):
        return "pr_flow"
    if any(k in x for k in ["db", "database", "sqlite", "schema", "migration"]):
        return "database"
    if any(k in x for k in ["timeout", "watchdog", "guard", "healing", "health"]):
        return "stability"
    if any(k in x for k in ["ceo", "cto", "meeting", "decision", "hub"]):
        return "decision"
    if any(k in x for k in ["docs", "readme", "handover", ".md"]):
        return "docs"
    return "general"

def bucket_scope_text(bucket: str) -> str:
    mp = {
        "notification": "通 知 ま わ り",
        "routing": "振 り 分 け 導 線",
        "pr_flow": "PR / マ ー ジ 導 線",
        "database": "DB / ス キ ー マ",
        "stability": "安 定 化",
        "decision": "判 断 / 会 議 導 線",
        "docs": "文 書 / 引 き 継 ぎ",
        "general": "中 核 ロ ジ ッ ク",
    }
    return mp.get(bucket, "中 核 ロ ジ ッ ク")

def bucket_reason_lines(bucket: str) -> list[str]:
    mp = {
        "notification": [
            "通 知 が 埋 も れ る と 状 況 把 握 が 遅 れ や す い",
            "似 た 文 面 が 続 く と 変 化 点 が 見 え に く い",
        ],
        "routing": [
            "受 け 渡 し が ず れ る と 全 体 が 詰 ま り や す い",
            "次 の 担 当 に 渡 る 精 度 を 上 げ た い",
        ],
        "pr_flow": [
            "PR / マ ー ジ 導 線 が 崩 れ る と 開 発 ル ー プ が 止 ま り や す い",
            "反 映 状 態 を 読 み や す く し た い",
        ],
        "database": [
            "DB の 整 合 が 崩 れ る と 後 段 判 定 が 不 安 定 に な る",
            "土 台 側 の 情 報 を 揃 え て お き た い",
        ],
        "stability": [
            "停 滞 や timeout を 減 ら し た い",
            "再 実 行 頼 み に な る 状 態 を 減 ら し た い",
        ],
        "decision": [
            "判 断 経 路 が 弱 い と 次 ア ク シ ョ ン が 遅 れ や す い",
            "会 議 / CEO / CTO 層 へ 流 れ や す く し た い",
        ],
        "docs": [
            "引 き 継 ぎ の 精 度 が 低 い と 継 続 実 装 が 遅 く な る",
            "文 書 と 実 装 の ず れ を 減 ら し た い",
        ],
        "general": [
            "人 手 を 挟 む と 流 れ が 止 ま り や す い",
            "次 の 改 善 を 入 れ や す い 土 台 に し た い",
        ],
    }
    return mp.get(bucket, mp["general"])

def bucket_action_lines(bucket: str) -> list[str]:
    mp = {
        "notification": [
            "・ 通 知 文 面 の 出 し 分 け を 強 め た",
            "・ 同 じ 見 え 方 に な り や す い 表 現 を 減 ら し た",
        ],
        "routing": [
            "・ タ ス ク の 受 け 渡 し 導 線 を 整 え た",
            "・ 次 の 担 当 に 渡 り や す い 状 態 に し た",
        ],
        "pr_flow": [
            "・ PR / マ ー ジ の 流 れ を 追 い や す く し た",
            "・ 状 態 ず れ を 起 こ し に く く し た",
        ],
        "database": [
            "・ DB の 扱 い を 揃 え た",
            "・ 後 段 判 定 で 使 う 情 報 を 安 定 化 し た",
        ],
        "stability": [
            "・ 停 滞 し や す い 部 分 を 減 ら し た",
            "・ 監 視 / 再 試 行 の 前 提 を 整 え た",
        ],
        "decision": [
            "・ 判 断 層 に 情 報 が 流 れ や す い 形 に 整 え た",
            "・ 次 ア ク シ ョ ン を 決 め や す く し た",
        ],
        "docs": [
            "・ 文 書 と 実 装 の ず れ を 減 ら し た",
            "・ 継 続 作 業 の 読 み 取 り を し や す く し た",
        ],
        "general": [
            "・ 自 動 ラ イ ン に 乗 せ や す い 状 態 へ 整 え た",
            "・ 次 の ス テ ー ジ へ 進 み や す く し た",
        ],
    }
    return mp.get(bucket, mp["general"])

def bucket_effect_lines(bucket: str) -> list[str]:
    mp = {
        "notification": [
            "・ 通 知 の 見 分 け が つ き や す く な る",
            "・ 変 更 点 を 早 く 把 握 し や す い",
        ],
        "routing": [
            "・ 担 当 の 振 り 分 け ミ ス が 減 り や す い",
            "・ 受 け 渡 し が 安 定 し や す い",
        ],
        "pr_flow": [
            "・ 開 発 ル ー プ が 途 切 れ に く く な る",
            "・ マ ー ジ 後 の 反 映 が 読 み や す く な る",
        ],
        "database": [
            "・ 判 定 の 土 台 が 安 定 し や す い",
            "・ デ ー タ ず れ に よ る 詰 ま り が 減 る",
        ],
        "stability": [
            "・ 停 滞 や timeout が 起 き に く く な る",
            "・ 運 用 が 安 定 し や す い",
        ],
        "decision": [
            "・ 判 断 か ら 実 行 ま で の 流 れ が 速 く な り や す い",
            "・ 会 議 / CEO 層 の 活 用 が し や す い",
        ],
        "docs": [
            "・ 次 の 作 業 開 始 が 速 く な り や す い",
            "・ 認 識 ず れ が 起 き に く い",
        ],
        "general": [
            "・ 流 れ が 途 切 れ に く く な る",
            "・ 処 理 の 進 行 速 度 が 安 定 し や す い",
        ],
    }
    return mp.get(bucket, mp["general"])

def bucket_avoid_lines(bucket: str) -> list[str]:
    mp = {
        "notification": ["・ 見 落 と し", "・ 同 系 統 通 知 の 埋 没"],
        "routing": ["・ 渡 し 先 の ず れ", "・ 宙 に 浮 く タ ス ク"],
        "pr_flow": ["・ マ ー ジ 漏 れ", "・ 状 態 反 映 漏 れ"],
        "database": ["・ カ ラ ム ず れ", "・ 判 定 ミ ス"],
        "stability": ["・ 停 滞", "・ 再 実 行 の 増 加"],
        "decision": ["・ 判 断 待 ち の 長 期 化", "・ 次 ア ク シ ョ ン の 遅 延"],
        "docs": ["・ 引 き 継 ぎ 漏 れ", "・ 読 み 違 い"],
        "general": ["・ 手 動 漏 れ", "・ 停 滞"],
    }
    return mp.get(bucket, mp["general"])

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
    display_files = choose_display_files(row, pr)
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
    msg = missing_call_openai_disabled(prompt)
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
                conn.execute("""
                    update dev_proposals
                    set notified_at=datetime('now'),
                        notified_msg_id='sent'
                    where id=?
                """, (r["proposal_id"],))
                conn.commit()
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
