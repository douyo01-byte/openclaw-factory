import os
import sqlite3
import time

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))
SLEEP = 30.0

def score_trial(cur, trial_id: int):
    metrics = cur.execute("""
    select metric_type, metric_value, score_delta
    from money_results
    where trial_id=?
    """, (trial_id,)).fetchall()

    total = 0
    revenue = 0
    cost = 0
    for metric_type, metric_value, score_delta in metrics:
        total += int(score_delta or 0)
        if metric_type == "revenue_yen":
            revenue += int(metric_value or 0)
        if metric_type == "cost_yen":
            cost += int(metric_value or 0)
        if metric_type == "delivery_completed":
            revenue += 2980

    profit = revenue - cost
    total += max(0, min(100, profit // 100))

    status = "testing"
    if revenue > 0 and total >= 120:
        status = "success"
    elif total <= -30:
        status = "fail"

    cur.execute("""
    update money_trials
    set revenue_yen=?, cost_yen=?, profit_yen=?, score=?, status=?, updated_at=datetime('now')
    where id=?
    """, (revenue, cost, profit, total, status, trial_id))

def main():
    while True:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        ids = [r[0] for r in cur.execute("select id from money_trials").fetchall()]
        for trial_id in ids:
            score_trial(cur, trial_id)
        con.commit()
        con.close()
        print("money_learning_tick", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
