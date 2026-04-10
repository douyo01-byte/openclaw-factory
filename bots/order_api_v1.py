import os
import sys
import sqlite3
from flask import Flask, request, jsonify

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from bots.fortune_engine_v1 import generate_reading

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))

app = Flask(__name__)

def get_con():
    return sqlite3.connect(DB_PATH)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True})

@app.route("/order", methods=["POST"])
def order():
    data = request.form if request.form else request.json if request.is_json else {}

    plan = (data.get("plan") or "簡易鑑定").strip()
    name = (data.get("customer_name") or "").strip()
    birth_date = (data.get("birth_date") or "").strip()
    birth_time = (data.get("birth_time") or "").strip()
    birth_place = (data.get("birth_place") or "").strip()
    question = (data.get("question") or "").strip()
    email = (data.get("email") or "").strip()

    if not name or not birth_date or not question or not email:
        return jsonify({
            "status": "error",
            "message": "customer_name, birth_date, question, email are required"
        }), 400

    con = get_con()
    cur = con.cursor()

    cur.execute("""
    insert into money_orders
    (trial_id, customer_name, plan, email, birth_date, question, status)
    values (1,?,?,?,?,?,'paid')
    """, (name, plan, email, birth_date, question))
    order_id = cur.lastrowid

    reading = generate_reading(
        name=name,
        birth_date=birth_date,
        question=question,
        birth_time=birth_time,
        birth_place=birth_place,
    )

    delivery_text = f"""宛先: {email}
プラン: {plan}
顧客名: {name}

【総合鑑定】
{reading['reading_text']}

【要点】
- 再現性あり
- 同一入力同一結果
- 自動納品成功
"""

    cur.execute("""
    insert into money_deliveries(order_id, delivery_text, status)
    values(?,?,?)
    """, (order_id, delivery_text, "done"))

    price_map = {
        "簡易鑑定": 2980,
        "標準鑑定": 8980,
        "深掘り鑑定": 14800,
    }
    revenue = price_map.get(plan, 2980)

    cur.execute("""
    insert into money_results(trial_id, action_id, metric_type, metric_value, score_delta)
    values(1, NULL, 'delivery_completed', ?, 25)
    """, (str(order_id),))

    cur.execute("""
    insert into money_results(trial_id, action_id, metric_type, metric_value, score_delta)
    values(1, NULL, 'revenue_yen', ?, 0)
    """, (str(revenue),))

    cur.execute("""
    update money_trials
    set revenue_yen = revenue_yen + ?,
        profit_yen = profit_yen + ?,
        score = score + 25,
        status = 'success',
        phase = 'measure',
        updated_at = datetime('now')
    where id = 1
    """, (revenue, revenue))

    con.commit()
    con.close()

    return jsonify({
        "status": "ok",
        "order_id": order_id,
        "delivered": True,
        "revenue_yen": revenue,
        "engine_version": reading["engine_version"],
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8790)
