import os
import sqlite3
import time

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))
SLEEP = 20.0

def now_sql():
    return "datetime('now')"

def ensure_seed(cur):
    row = cur.execute("select id from money_trials where theme='AI占い' order by id asc limit 1").fetchone()
    if row:
        return
    cur.execute("""
    insert into money_trials(theme,hypothesis,product_type,status,phase,priority,notes)
    values(?,?,?,?,?,?,?)
    """, (
        "AI占い",
        "多占学統合かつ同一入力同一結果の高再現AI占いは、無人販売向きである",
        "ai_fortune",
        "testing",
        "design",
        95,
        "初期仮説"
    ))

def spawn_action(cur):
    trial = cur.execute("""
    select id,theme,phase,attempts,notes
    from money_trials
    where status in ('new','testing','rebuild')
    order by priority desc, id asc
    limit 1
    """).fetchone()
    if not trial:
        return
    trial_id, theme, phase, attempts, notes = trial
    exists = cur.execute("""
    select 1 from money_actions
    where trial_id=? and status in ('new','running')
    limit 1
    """, (trial_id,)).fetchone()
    if exists:
        return

    if phase == "design":
        action_type = "design_offer"
        action_text = "AI占い商品の設計、料金仮説、納品形式、再現性仕様を作る"
    elif phase == "build":
        action_type = "build_engine"
        action_text = "AI占いエンジンと入力固定時同一出力の検証を行う"
    elif phase == "sell":
        action_type = "build_lp"
        action_text = "AI占いの販売LP、CTA、注文導線、納品手順を作る"
    elif phase == "measure":
        action_type = "measure_result"
        action_text = "売上、反応率、納品完了率、再現性の測定を行う"
    else:
        action_type = "improve_offer"
        action_text = "失敗要因を踏まえてAI占い商品を改善する"

    cur.execute("""
    insert into money_actions(trial_id,action_type,action_text,status)
    values(?,?,?,?)
    """, (trial_id, action_type, action_text, "new"))

def advance_phase(cur):
    rows = cur.execute("""
    select t.id,t.phase,
           sum(case when a.status='done' then 1 else 0 end) done_cnt,
           sum(case when a.status='error' then 1 else 0 end) err_cnt
    from money_trials t
    left join money_actions a on a.trial_id=t.id
    where t.status in ('new','testing','rebuild')
    group by t.id,t.phase
    """).fetchall()

    next_map = {
        "design": "build",
        "build": "sell",
        "sell": "measure",
        "measure": "improve",
        "improve": "sell",
    }

    for trial_id, phase, done_cnt, err_cnt in rows:
        if err_cnt and phase != "improve":
            cur.execute("""
            update money_trials
            set phase='improve', updated_at=datetime('now')
            where id=?
            """, (trial_id,))
            continue
        if done_cnt:
            nxt = next_map.get(phase)
            if nxt:
                cur.execute("""
                update money_trials
                set phase=?, attempts=attempts+1, updated_at=datetime('now')
                where id=?
                """, (nxt, trial_id))

def main():
    while True:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        ensure_seed(cur)
        spawn_action(cur)
        advance_phase(cur)
        con.commit()
        con.close()
        print("money_loop_tick", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
