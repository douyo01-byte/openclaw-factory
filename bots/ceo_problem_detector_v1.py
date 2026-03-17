from __future__ import annotations
import os, sqlite3, time, hashlib

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = int(os.environ.get("CEO_PROBLEM_DETECTOR_SLEEP", "600"))

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    return c

def slug(s: str) -> str:
    out = []
    for ch in s.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in (" ", "_", "-", "/"):
            out.append("-")
    s2 = "".join(out).strip("-")
    while "--" in s2:
        s2 = s2.replace("--", "-")
    return s2[:48] or "proposal"

def branch_name(title: str) -> str:
    h = hashlib.md5(title.encode("utf-8")).hexdigest()[:8]
    return f"ceo-detect/{slug(title)}-{h}"

def existing_open(c, title: str) -> bool:
    row = c.execute("""
    select 1
    from dev_proposals
    where coalesce(title,'')=?
      and coalesce(status,'') not in ('merged','rejected','closed')
    limit 1
    """, (title,)).fetchone()
    return row is not None

def insert_proposal(c, title: str, description: str, target_system: str, improvement_type: str, priority: int):
    if existing_open(c, title):
        return False
    c.execute("""
    insert into dev_proposals (
      title, description, branch_name, status, risk_level, created_at,
      source_ai, category, target_system, improvement_type, priority,
      spec_stage, spec, result_type, decision_note
    ) values (
      ?, ?, ?, 'new', 'medium', datetime('now'),
      'ceo_problem_detector_v1', 'ops', ?, ?, ?,
      '', '', '', ''
    )
    """, (
      title,
      description,
      branch_name(title),
      target_system,
      improvement_type,
      priority,
    ))
    return True

def detect(c):
    out = []

    open_pr = c.execute("""
    select count(*) from dev_proposals
    where coalesce(pr_status,'')='open'
      and coalesce(pr_url,'')<>''
    """).fetchone()[0]

    router_new = c.execute("""
    select count(*) from router_tasks
    where coalesce(status,'')='new'
    """).fetchone()[0]

    router_started = c.execute("""
    select count(*) from router_tasks
    where coalesce(status,'')='started'
    """).fetchone()[0]

    router_timeout = c.execute("""
    select count(*) from router_tasks
    where coalesce(status,'')='timeout'
    """).fetchone()[0]

    executor_wait = c.execute("""
    select count(*) from dev_proposals
    where coalesce(status,'') in ('decomposed','executor_ready','execute_now','approved','pr_created')
      and coalesce(pr_status,'')<>'merged'
    """).fetchone()[0]

    refined_wait = c.execute("""
    select count(*) from dev_proposals
    where coalesce(status,'') in ('promoted','refining','refined')
    """).fetchone()[0]

    if router_timeout >= 1:
        out.append({
            "title": "router timeout 自動整理と原因記録を強化",
            "description": f"""目的:
router_tasks timeoutの再発防止。

検知理由:
- router_timeout={router_timeout}

必要性:
- burn-in中にtimeout履歴が残ると、本流監視の解像度が落ちる
- timeout原因の自動分類と再発抑止が必要

期待結果:
- timeout原因を分類
- 同種timeoutの再発時に自動で注記/集計
- burn-in監視のノイズを減らす
""",
            "target_system": "router_tasks",
            "improvement_type": "reliability",
            "priority": 90,
        })

    if router_new + router_started >= 5:
        out.append({
            "title": "router queue 可視化サマリを強化",
            "description": f"""目的:
router滞留の見える化強化。

検知理由:
- router_new={router_new}
- router_started={router_started}

必要性:
- queueの増加理由が見えにくい
- started/newの内訳と経過時間の要約が必要

期待結果:
- target_bot別件数
- 経過時間上位
- 自動提案への接続
""",
            "target_system": "task_router_v1",
            "improvement_type": "observability",
            "priority": 80,
        })

    if executor_wait >= 10:
        out.append({
            "title": "executor帯の滞留理由を自動要約する",
            "description": f"""目的:
executor_ready以降の滞留理由を自動要約する。

検知理由:
- executor_wait={executor_wait}

必要性:
- 実装帯の詰まりは収益化前の能力強化に直結
- 何が詰まっているかをAIが説明できる必要がある

期待結果:
- executor帯件数
- 代表案件
- 次に見るべきbot提案
""",
            "target_system": "dev_pr_creator_v1",
            "improvement_type": "ops_intelligence",
            "priority": 85,
        })

    if refined_wait >= 5:
        out.append({
            "title": "spec帯の停滞検知と改善提案を追加",
            "description": f"""目的:
spec_refiner/spec_decomposer帯の停滞検知強化。

検知理由:
- refined_wait={refined_wait}

必要性:
- 開発前の具体化が止まると全体が遅れる
- 具体化停止をCEO視点で先に察知したい

期待結果:
- 停滞帯の自動検知
- 次アクションの提案
""",
            "target_system": "spec_refiner_v2",
            "improvement_type": "ops_intelligence",
            "priority": 75,
        })

    if open_pr >= 1:
        out.append({
            "title": "open PR監視の説明力を強化",
            "description": f"""目的:
open PRの放置理由を説明できるようにする。

検知理由:
- open_pr={open_pr}

必要性:
- PR backlogは本流詰まりの主要兆候
- 件数だけでなく理由説明が必要

期待結果:
- open PR一覧
- 停滞時間
- 自動次アクション
""",
            "target_system": "dev_pr_watcher_v1",
            "improvement_type": "observability",
            "priority": 88,
        })

    return out

def once():
    c = conn()
    try:
        proposals = detect(c)
        inserted = 0
        for p in proposals:
            if insert_proposal(
                c,
                p["title"],
                p["description"],
                p["target_system"],
                p["improvement_type"],
                p["priority"],
            ):
                inserted += 1
        c.commit()
        print(f"detected={len(proposals)} inserted={inserted}", flush=True)
    finally:
        c.close()

def main():
    while True:
        try:
            once()
        except Exception as e:
            print(f"error: {e}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
