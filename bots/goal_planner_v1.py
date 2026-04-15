from __future__ import annotations
import json
import os
import re
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", str(Path.home() / "AI/openclaw-factory/data/openclaw.db"))

PRIORITY_RULES = [
    {
        "name": "n8n_minimum_integration",
        "match": [
            r"n8n",
            r"最小連携|最 小 連 携",
            r"api_server|workflow|webhook|production webhook",
        ],
        "active_goal": "OpenClaw本体を目的駆動の母艦へ進化させる",
        "current_focus": "n8nとOpenClawの最小連携を安定した主線として固定する",
        "next_action": "n8n起点の入力をsource+text形式へ統一し、api_server常駐化までを1本の主線として固定する",
    },
    {
        "name": "kaikun_decision_layer",
        "match": [
            r"decide_mode|decide_exec_policy|THINK/FAST/DOC/EXEC|判断ルール|判 断 ル ー ル|decision layer",
        ],
        "active_goal": "OpenClaw本体を目的駆動の母艦へ進化させる",
        "current_focus": "Kaikun04の判断層を明文化して計画駆動へ寄せる",
        "next_action": "decide_mode()とdecide_exec_policy()の判定基準を文書化し、router_tasksへ保存される判断値と接続する",
    },
    {
        "name": "runtime_truth_alignment",
        "match": [
            r"runtime|watcher|docs/runtime/DB|docs/runtime/db|完全一致|唯一のソース|唯 一 の ソ ー ス",
        ],
        "active_goal": "OpenClaw本体を目的駆動の母艦へ進化させる",
        "current_focus": "docs・runtime・DBのズレを減らし現在地把握の精度を上げる",
        "next_action": "watcherとruntime確認結果を基準に、docs/current state/handoverとの一致確認を自動化する",
    },
    {
        "name": "fallback_reduction",
        "match": [
            r"fallback|observe|legacy|命名整理|縮退|burn-in",
        ],
        "active_goal": "OpenClaw本体を目的駆動の母艦へ進化させる",
        "current_focus": "primaryとfallbackの運用分類を固定し主線を細く強くする",
        "next_action": "required/observe/fallback分類をDBまたはMD要約へ落とし、legacy fallbackの扱いを固定する",
    },
]

GOAL_FALLBACK = "OpenClaw本体をMD駆動で長期目的を理解し、自分で計画・実行・見直しする母艦に進化させる"
FOCUS_FALLBACK = "基盤強化を優先し、長期目標と現在地の接続を自動化する"
ACTION_FALLBACK = "goal_doc_snapshotsから未完了と優先事項を再スコアし、最も全体目標に寄与する1手をgoal_plan_stateへ保存する"

def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("pragma journal_mode=WAL")
    con.execute("pragma busy_timeout=5000")
    return con

def fetch_rows(con: sqlite3.Connection, section_type: str) -> list[sqlite3.Row]:
    return con.execute("""
    select section_type, item_text, doc_path, line_no, heading, created_at
    from goal_doc_snapshots
    where section_type=?
    order by created_at desc, doc_path, line_no
    """, (section_type,)).fetchall()

def normalize(s: str) -> str:
    s = s.replace("\u3000", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def score_row(row: sqlite3.Row) -> int:
    text = normalize(row["item_text"])
    heading = normalize(row["heading"] or "")
    score = 0

    if row["section_type"] == "unfinished":
        score += 50
    elif row["section_type"] == "priorities":
        score += 40
    elif row["section_type"] == "goals":
        score += 20
    elif row["section_type"] == "constraints":
        score += 10

    joined = f"{heading} {text}"

    bonus_map = [
        (r"基盤強化|基 盤 強 化", 40),
        (r"n8n", 35),
        (r"最小連携|最 小 連 携", 35),
        (r"api_server|webhook|workflow", 25),
        (r"Kaikun04|decide_mode|decide_exec_policy|THINK/FAST/DOC/EXEC", 30),
        (r"runtime|watcher|docs/runtime/DB|完全一致", 25),
        (r"fallback|observe|legacy|burn-in|命名整理|縮退", 20),
        (r"収益ライン|収 益 ラ イ ン", -20),
        (r"案件処理テンプレ|案 件 処 理 テ ン プ レ", -10),
        (r"新規機能追加はしない|新 規 機 能 追 加 は し な い", 10),
        (r"未実施|未 実 施|必要|要確認|次段|次 段|次フェーズ|次 フ ェ ー ズ", 15),
    ]
    for pat, pts in bonus_map:
        if re.search(pat, joined, re.I):
            score += pts

    if re.search(r"完了|成立済み|残なし|remaining *= *0|pending *= *0", joined, re.I):
        score -= 30

    return score

def choose_focus(rows: list[sqlite3.Row]) -> tuple[sqlite3.Row | None, int]:
    best = None
    best_score = -10**9
    for row in rows:
        sc = score_row(row)
        if sc > best_score:
            best_score = sc
            best = row
    return best, best_score

def classify_plan(row: sqlite3.Row | None) -> tuple[str, str, str, list[str]]:
    if row is None:
        return GOAL_FALLBACK, FOCUS_FALLBACK, ACTION_FALLBACK, []

    text = normalize(row["item_text"])
    heading = normalize(row["heading"] or "")
    joined = f"{heading} {text}"

    matched_rules = []
    for rule in PRIORITY_RULES:
        hit_count = 0
        for pat in rule["match"]:
            if re.search(pat, joined, re.I):
                hit_count += 1
        if hit_count > 0:
            matched_rules.append((hit_count, rule))

    if matched_rules:
        matched_rules.sort(key=lambda x: x[0], reverse=True)
        rule = matched_rules[0][1]
        return rule["active_goal"], rule["current_focus"], rule["next_action"], [rule["name"], text]

    return GOAL_FALLBACK, FOCUS_FALLBACK, ACTION_FALLBACK, [text]

def build_rationale(best_row: sqlite3.Row | None, best_score: int, goals: list[sqlite3.Row], constraints: list[sqlite3.Row]) -> str:
    parts = []
    if best_row is not None:
        parts.append(f"selected={normalize(best_row['item_text'])}")
        parts.append(f"section={best_row['section_type']}")
        parts.append(f"score={best_score}")
        parts.append(f"heading={normalize(best_row['heading'] or '')}")

    goal_texts = [normalize(r["item_text"]) for r in goals[:5]]
    if goal_texts:
        parts.append("goals=" + " | ".join(goal_texts))

    constraint_texts = [normalize(r["item_text"]) for r in constraints[:5]]
    if constraint_texts:
        parts.append("constraints=" + " | ".join(constraint_texts))

    return " ; ".join(parts)

def build_source_docs(rows: list[sqlite3.Row]) -> str:
    docs = []
    for r in rows:
        p = r["doc_path"]
        if p not in docs:
            docs.append(p)
    return json.dumps(docs, ensure_ascii=False)

def insert_plan(con: sqlite3.Connection, active_goal: str, current_focus: str, next_action: str, rationale: str, source_docs: str) -> int:
    cur = con.execute("""
    insert into goal_plan_state
    (active_goal, current_focus, next_action, rationale, source_docs, updated_at)
    values (?, ?, ?, ?, ?, datetime('now'))
    """, (active_goal, current_focus, next_action, rationale, source_docs))
    con.commit()
    return int(cur.lastrowid)

def main() -> None:
    con = connect()

    goals = fetch_rows(con, "goals")
    constraints = fetch_rows(con, "constraints")
    unfinished = fetch_rows(con, "unfinished")
    priorities = fetch_rows(con, "priorities")

    candidate_rows = unfinished + priorities + goals
    best_row, best_score = choose_focus(candidate_rows)

    active_goal, current_focus, next_action, matched = classify_plan(best_row)
    rationale = build_rationale(best_row, best_score, goals, constraints)
    source_docs = build_source_docs(candidate_rows[:50])

    new_id = insert_plan(
        con,
        active_goal=active_goal,
        current_focus=current_focus,
        next_action=next_action,
        rationale=rationale,
        source_docs=source_docs,
    )

    out = {
        "ok": True,
        "id": new_id,
        "active_goal": active_goal,
        "current_focus": current_focus,
        "next_action": next_action,
        "matched": matched,
        "best_score": best_score,
        "best_item": None if best_row is None else {
            "section_type": best_row["section_type"],
            "item_text": normalize(best_row["item_text"]),
            "doc_path": best_row["doc_path"],
            "line_no": best_row["line_no"],
            "heading": normalize(best_row["heading"] or ""),
        },
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    con.close()

if __name__ == "__main__":
    main()
