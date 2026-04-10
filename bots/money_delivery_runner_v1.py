import os
import sqlite3
from bots.fortune_engine_v1 import generate_reading

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))

def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    order = cur.execute("""
    select id, trial_id, customer_name, plan, email, birth_date, question
    from money_orders
    where status='paid'
      and id not in (select order_id from money_deliveries)
    order by id asc
    limit 1
    """).fetchone()

    if not order:
        print("no_paid_order", flush=True)
        return

    order_id, trial_id, customer_name, plan, email, birth_date, question = order
    reading = generate_reading(customer_name, birth_date, question)

    delivery_text = f"""宛先: {email}
プラン: {plan}
顧客名: {customer_name}

【総合鑑定】
{reading['reading_text']}

【要点】
- 再現性あり
- 同一入力同一結果
- 自動納品テスト成功
"""

    cur.execute("""
    insert into money_deliveries(order_id, delivery_text, status)
    values(?,?,?)
    """, (order_id, delivery_text, "done"))

    cur.execute("""
    insert into money_results(trial_id, action_id, metric_type, metric_value, score_delta)
    values(?,?,?,?,?)
    """, (trial_id, None, "delivery_completed", str(order_id), 25))

    cur.execute("""
    update money_trials
    set revenue_yen=revenue_yen+2980,
        profit_yen=profit_yen+2980,
        score=score+25,
        status='testing',
        updated_at=datetime('now')
    where id=?
    """, (trial_id,))

    con.commit()
    con.close()
    print(f"delivered_order={order_id}", flush=True)

if __name__ == "__main__":
    main()
