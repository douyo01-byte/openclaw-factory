import os
import sqlite3
from pathlib import Path
import json

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))
ROOT = Path(os.path.expanduser("~/AI/openclaw-factory-daemon"))
FORM_DIR = ROOT / "data/fortune/forms"
DELIVERY_DIR = ROOT / "data/fortune/delivery"

FORM_DEF = {
    "product": "多占学統合AI鑑定",
    "trial_id": 1,
    "fields": [
        {"name": "plan", "label": "プラン", "type": "select", "options": ["簡易鑑定", "標準鑑定", "深掘り鑑定"], "required": True},
        {"name": "customer_name", "label": "名前", "type": "text", "required": True},
        {"name": "birth_date", "label": "生年月日", "type": "date", "required": True},
        {"name": "birth_time", "label": "出生時間", "type": "text", "required": False},
        {"name": "birth_place", "label": "出生地", "type": "text", "required": False},
        {"name": "question", "label": "相談内容", "type": "textarea", "required": True},
        {"name": "email", "label": "納品先メール", "type": "email", "required": True}
    ]
}

DELIVERY_TEMPLATE = """件名: AI占い鑑定結果のお届け

{{customer_name}} 様

このたびは {{plan}} のご依頼ありがとうございます。
以下、鑑定結果をお届けします。

【総合鑑定】
{{reading_text}}

【要点サマリー】
{{summary}}

【今取るべき行動3つ】
1. {{action1}}
2. {{action2}}
3. {{action3}}

【注意点3つ】
1. {{warn1}}
2. {{warn2}}
3. {{warn3}}

ご利用ありがとうございました。
"""

def main():
    FORM_DIR.mkdir(parents=True, exist_ok=True)
    DELIVERY_DIR.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    form_path = FORM_DIR / "trial_1_order_form.json"
    delivery_path = DELIVERY_DIR / "trial_1_delivery_template.txt"

    form_path.write_text(json.dumps(FORM_DEF, ensure_ascii=False, indent=2), encoding="utf-8")
    delivery_path.write_text(DELIVERY_TEMPLATE, encoding="utf-8")

    cur.execute("""
    insert into money_actions(trial_id, action_type, action_text, status, artifact_path, result_text)
    values(?,?,?,?,?,?)
    """, (
        1,
        "order_form",
        "AI占い注文フォーム定義を作成",
        "done",
        str(form_path),
        "order_form_built"
    ))

    cur.execute("""
    insert into money_results(trial_id, action_id, metric_type, metric_value, score_delta)
    values(?,?,?,?,?)
    """, (
        1,
        cur.lastrowid,
        "order_form_created",
        str(form_path),
        15
    ))

    cur.execute("""
    insert into money_actions(trial_id, action_type, action_text, status, artifact_path, result_text)
    values(?,?,?,?,?,?)
    """, (
        1,
        "delivery_template",
        "AI占い自動納品テンプレートを作成",
        "done",
        str(delivery_path),
        "delivery_template_built"
    ))

    cur.execute("""
    insert into money_results(trial_id, action_id, metric_type, metric_value, score_delta)
    values(?,?,?,?,?)
    """, (
        1,
        cur.lastrowid,
        "delivery_template_created",
        str(delivery_path),
        15
    ))

    cur.execute("""
    update money_trials
    set score=score+30, updated_at=datetime('now')
    where id=1
    """)

    con.commit()
    con.close()
    print("order_assets_built_for_trial=1", flush=True)

if __name__ == "__main__":
    main()
