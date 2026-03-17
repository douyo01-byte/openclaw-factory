from __future__ import annotations
import os
import sqlite3
import time
from datetime import datetime

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = 900

PROPOSALS = [
    {
        "title": "CEO用 Webダッシュボード の 初 期 版 を 自 動 構 想 す る",
        "description": "Telegram依存 を 減 ら し、 CEOが Webで 状態確認 できる 入口 を 用意する 提案。",
        "target_system": "web_dashboard",
        "improvement_type": "ui_platform",
        "priority": 78,
        "branch_name": "ceo-growth/web-dashboard-bootstrap",
    },
    {
        "title": "CEOと 人 間 の 接 点 を Web化 す る 提 案 を 整 理 す る",
        "description": "人間との 接し方 を Telegram中心 から Web中心 へ 移せるよう、 対話導線 を 先に proposal化 する。",
        "target_system": "ceo_interface",
        "improvement_type": "human_interface",
        "priority": 82,
        "branch_name": "ceo-growth/web-human-interface",
    },
    {
        "title": "収 益 化 前 提 の 専 門 bot 増 設 計 画 を 作 る",
        "description": "デザイナー、マーケ、営業、調査など 収益化に向く 専門bot の 増設順 を proposal化 する。",
        "target_system": "ai_employee_factory",
        "improvement_type": "org_expansion",
        "priority": 76,
        "branch_name": "ceo-growth/specialist-bot-plan",
    },
    {
        "title": "Web可 視 化 を 勝 手 に 作 り に 行 け る CEO導 線 を 強 化 す る",
        "description": "Web可視化 自体が 目的ではなく、 CEOが 必要と判断して 自主的に 開発提案できる 状態 を 強化する。",
        "target_system": "ceo_decision_layer_v1",
        "improvement_type": "autonomous_planning",
        "priority": 84,
        "branch_name": "ceo-growth/autonomous-web-direction",
    },
]

def conn():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    return con

def exists_same_title(c, title: str) -> bool:
    r = c.execute("""
        select 1
        from dev_proposals
        where coalesce(title,'')=?
        limit 1
    """, (title,)).fetchone()
    return r is not None

def once():
    con = conn()
    c = con.cursor()
    inserted = 0
    for p in PROPOSALS:
        if exists_same_title(c, p["title"]):
            continue
        c.execute("""
            insert into dev_proposals
            (
              title, description, branch_name, status, risk_level, created_at,
              source_ai, target_system, improvement_type, priority, decision_note
            )
            values
            (
              ?, ?, ?, 'new', 'medium', datetime('now'),
              'ceo_growth_planner_v1', ?, ?, ?, 'next_phase_growth_direction'
            )
        """, (
            p["title"],
            p["description"],
            p["branch_name"],
            p["target_system"],
            p["improvement_type"],
            p["priority"],
        ))
        inserted += 1
    con.commit()
    con.close()
    print(f"{datetime.now().isoformat()} inserted={inserted}", flush=True)

def main():
    while True:
        try:
            once()
        except Exception as e:
            print(f"growth_planner_error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
