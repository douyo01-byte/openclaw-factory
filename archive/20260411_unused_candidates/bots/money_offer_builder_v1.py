import os
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))
ROOT = Path(os.path.expanduser("~/AI/openclaw-factory-daemon"))
OUT_DIR = ROOT / "data/fortune/offers"

def build_offer_text():
    return """商品名: 多占学統合AI鑑定
価格仮説:
- お試し簡易鑑定 2,980円
- 標準鑑定 8,980円
- 深掘り鑑定 14,800円

提供価値:
- 同じ入力なら同じ結果
- 数秘術、命理系、質問解釈を固定ロジックで統合
- 無人納品可能
- 結果の一貫性を重視

入力項目:
- 名前
- 生年月日
- 任意の質問
- 任意で出生時間、出生地

納品形式:
- テキスト鑑定書
- 要点サマリー
- 行動提案3つ
- 注意点3つ

販売導線:
- LP
- 注文フォーム
- 決済確認
- 自動納品

検証項目:
- 同一入力で出力一致
- 初回成約率
- 納品完了率
- 返金率
"""

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    trial = cur.execute("""
    select id, theme, phase
    from money_trials
    where theme='AI占い'
    order by priority desc, id asc
    limit 1
    """).fetchone()

    if not trial:
        print("trial_missing", flush=True)
        return

    trial_id, theme, phase = trial
    path = OUT_DIR / f"trial_{trial_id}_offer.txt"
    path.write_text(build_offer_text(), encoding="utf-8")

    cur.execute("""
    insert into money_actions(trial_id, action_type, action_text, status, artifact_path, result_text)
    values(?,?,?,?,?,?)
    """, (
        trial_id,
        "offer_doc",
        "AI占い商品の提案書を作成",
        "done",
        str(path),
        "offer_built"
    ))

    cur.execute("""
    insert into money_results(trial_id, action_id, metric_type, metric_value, score_delta)
    values(?,?,?,?,?)
    """, (
        trial_id,
        cur.lastrowid,
        "offer_doc_created",
        str(path),
        10
    ))

    cur.execute("""
    update money_trials
    set phase='build', updated_at=datetime('now')
    where id=?
    """, (trial_id,))

    con.commit()
    con.close()
    print(f"offer_built_for_trial={trial_id}", flush=True)

if __name__ == "__main__":
    main()
