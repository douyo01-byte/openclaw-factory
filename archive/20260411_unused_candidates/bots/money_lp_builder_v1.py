import os
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))
ROOT = Path(os.path.expanduser("~/AI/openclaw-factory-daemon"))
TPL = ROOT / "templates/fortune/fortune_lp_base.html"
OUT_DIR = ROOT / "data/fortune/lp"

def render(template: str, mp: dict) -> str:
    for k, v in mp.items():
        template = template.replace("{{" + k + "}}", v)
    return template

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    action = cur.execute("""
    select a.id, a.trial_id
    from money_actions a
    join money_trials t on t.id=a.trial_id
    where t.theme='AI占い'
      and a.action_type='build_lp'
      and a.status='new'
    order by a.id asc
    limit 1
    """).fetchone()

    if not action:
        print("lp_action_missing", flush=True)
        return

    action_id, trial_id = action
    html = TPL.read_text(encoding="utf-8")
    rendered = render(html, {
        "TITLE": "多占学統合AI鑑定",
        "SUBTITLE": "同じ入力なら同じ結果。再現性を重視したAI占い。",
        "LEAD": "ただ気分で言葉を返す占いではなく、固定ロジックで何度見ても軸がブレにくい鑑定を目指します。",
        "PRICE": "初回 ¥2,980〜",
        "CTA_TEXT": "鑑定を申し込む",
        "CTA_LINK": "#order",
        "CTA_BODY": "まずは簡易鑑定から反応を見て、成約率と満足度を計測して改善します。"
    })

    out = OUT_DIR / f"trial_{trial_id}_lp.html"
    out.write_text(rendered, encoding="utf-8")

    cur.execute("""
    update money_actions
    set status='done', artifact_path=?, result_text='lp_built', updated_at=datetime('now')
    where id=?
    """, (str(out), action_id))

    cur.execute("""
    insert into money_results(trial_id, action_id, metric_type, metric_value, score_delta)
    values(?,?,?,?,?)
    """, (trial_id, action_id, "lp_created", str(out), 20))

    cur.execute("""
    update money_trials
    set phase='measure', score=score+20, updated_at=datetime('now')
    where id=?
    """, (trial_id,))

    con.commit()
    con.close()
    print(f"lp_built_for_trial={trial_id}", flush=True)

if __name__ == "__main__":
    main()
