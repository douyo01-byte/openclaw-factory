import os,sqlite3
DB=os.environ.get("DB_PATH") or "data/openclaw.db"

def main():
    c=sqlite3.connect(DB)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=5000")
    c.execute("""CREATE TABLE IF NOT EXISTS ai_employees(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_key TEXT NOT NULL UNIQUE,
        display_name TEXT NOT NULL,
        role_name TEXT NOT NULL,
        mission TEXT NOT NULL,
        is_enabled INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")
    seeds=[
        ("secretary","秘書（ひしょりん）","秘書","CEO補佐と全体整理"),
        ("scout","スカウトマン（さがすけ）","スカウト","案件探索"),
        ("research","調査員（しらべえ）","調査","情報収集と裏取り"),
        ("planner","企画担当（かんがえもん）","企画","提案整理"),
        ("spec","設計士（きめたろう）","設計","仕様整理"),
        ("dev","エンジニア（つくるぞう）","開発","実装"),
        ("audit","監査係（みはるん）","監査","確認"),
        ("merge","統合係（くっつけ丸）","統合","統合処理"),
        ("report","報告係（しらせるん）","報告","CEO報告"),
    ]
    for x in seeds:
        c.execute("insert or ignore into ai_employees(employee_key,display_name,role_name,mission) values(?,?,?,?)",x)
    c.commit()
    c.close()
    print("employee_registry_ok")

if __name__=="__main__":
    main()
