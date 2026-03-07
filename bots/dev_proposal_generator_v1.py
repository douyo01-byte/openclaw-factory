import os, sqlite3, datetime, json, random, difflib
from openai import OpenAI

DB = os.environ.get("DB_PATH", "data/openclaw.db")

SYSTEM = """あなたはOpenClaw Factoryの開発提案生成AIです。
短くても具体的で、人間が見て意味が分かる日本語の提案を1件だけ作ってください。

必須:
- title: 自然な日本語タイトル
- description: 何をどう改善するか分かる1文
- category: research / automation / performance / monitoring / improvement のいずれか
- target_system: brain / executor / database / watcher / telegram / learning のいずれか
- improvement_type: extend / optimize / refactor / stabilize / monitor のいずれか

JSONのみ返してください。"""

TARGETS = {
    "brain": {
        "category": "research",
        "items": [
            ("検索ソースの追加", "brainに対して検索ソースの追加を行い、調査情報の網羅性を高める。", "extend"),
            ("信頼性判定の強化", "brainに対して信頼性判定の強化を行い、採用精度を高める。", "extend"),
            ("要約精度の改善", "brainに対して要約精度の改善を行い、調査結果の読みやすさを高める。", "optimize"),
            ("情報選定ロジックの改善", "brainに対して情報選定ロジックの改善を行い、候補選別精度を向上させる。", "refactor"),
        ],
    },
    "executor": {
        "category": "performance",
        "items": [
            ("再試行処理の安定化", "executorに対して再試行処理の安定化を行い、失敗時の復旧性を高める。", "stabilize"),
            ("並列実行の最適化", "executorに対して並列実行の最適化を行い、処理速度を改善する。", "optimize"),
            ("失敗検知の強化", "executorに対して失敗検知の強化を行い、異常終了時の検知精度を高める。", "monitor"),
            ("実行ログ整理", "executorに対して実行ログ整理を行い、障害調査をしやすくする。", "refactor"),
        ],
    },
    "database": {
        "category": "automation",
        "items": [
            ("集計処理の最適化", "databaseに対して集計処理の最適化を行い、集計速度と参照効率を改善する。", "optimize"),
            ("保存効率の改善", "databaseに対して保存効率の改善を行い、運用コストを抑える。", "refactor"),
            ("履歴管理の強化", "databaseに対して履歴管理の強化を行い、監査性を改善する。", "extend"),
            ("コスト可視化の強化", "databaseに対してコスト可視化の強化を行い、調整しやすくする。", "monitor"),
        ],
    },
    "watcher": {
        "category": "monitoring",
        "items": [
            ("状態追跡の強化", "watcherに対して状態追跡の強化を行い、異常検知後の追跡性を高める。", "monitor"),
            ("通知精度の改善", "watcherに対して通知精度の改善を行い、重要イベントの視認性を高める。", "optimize"),
            ("異常検知条件の見直し", "watcherに対して異常検知条件の見直しを行い、誤検知を減らす。", "refactor"),
            ("監視ノイズの削減", "watcherに対して監視ノイズの削減を行い、監視負荷を下げる。", "stabilize"),
        ],
    },
    "telegram": {
        "category": "automation",
        "items": [
            ("重複送信の防止", "telegramに対して重複送信の防止を行い、通知品質を改善する。", "refactor"),
            ("レート制限対策の強化", "telegramに対してレート制限対策の強化を行い、配信失敗を減らす。", "stabilize"),
            ("通知整形の改善", "telegramに対して通知整形の改善を行い、可読性を高める。", "optimize"),
            ("送信順序制御の改善", "telegramに対して送信順序制御の改善を行い、通知を理解しやすくする。", "extend"),
        ],
    },
    "learning": {
        "category": "improvement",
        "items": [
            ("失敗履歴活用の拡張", "learningに対して失敗履歴活用の拡張を行い、再利用性を高める。", "extend"),
            ("成功パターン蓄積の強化", "learningに対して成功パターン蓄積の強化を行い、再利用性を高める。", "extend"),
            ("判断材料の整理", "learningに対して判断材料の整理を行い、再利用しやすくする。", "refactor"),
            ("学習反映速度の改善", "learningに対して学習反映速度の改善を行い、次提案へ活かしやすくする。", "optimize"),
        ],
    },
}

def recent_rows(cur, n=60):
    rows = cur.execute("""
        select title, description, target_system
        from dev_proposals
        order by id desc
        limit ?
    """, (n,)).fetchall()
    return rows

def sim(a, b):
    return difflib.SequenceMatcher(None, a or "", b or "").ratio()

def is_semantic_duplicate(title, description, target_system, recent):
    for t, d, ts in recent:
        if ts == target_system and sim(title, t) >= 0.78:
            return True
        if sim(description, d) >= 0.72:
            return True
    return False

def fallback_pool():
    pool = []
    for target, conf in TARGETS.items():
        for label, desc, improve in conf["items"]:
            pool.append({
                "title": f"{target}の{label}",
                "description": desc,
                "category": conf["category"],
                "target_system": target,
                "improvement_type": improve,
            })
    return pool

def pick_fallback(recent):
    pool = fallback_pool()
    fresh = [x for x in pool if not is_semantic_duplicate(x["title"], x["description"], x["target_system"], recent)]
    return random.choice(fresh if fresh else pool)

def calc_quality(data):
    score = 50
    if len(data["title"]) >= 18:
        score += 10
    if len(data["description"]) >= 35:
        score += 10
    if data["target_system"] in ["brain", "executor", "database"]:
        score += 15
    if data["improvement_type"] in ["extend", "optimize", "refactor"]:
        score += 10
    if data["category"] in ["research", "performance", "automation"]:
        score += 5
    return min(score, 100)

def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    recent = recent_rows(cur, 60)
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    data = pick_fallback(recent)

    if api_key:
        try:
            client = OpenAI(api_key=api_key)
            used_titles = "\n".join([f"- {r[0]}" for r in recent[:40]])
            user = f"直近タイトルや内容と重複しないOpenClaw開発提案を1件、日本語JSONで生成してください。\n直近提案:\n{used_titles}"
            r = client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-5"),
                temperature=1,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
            )
            cand = json.loads(r.choices[0].message.content)
            cand_data = {
                "title": str(cand.get("title", "")).strip()[:120],
                "description": str(cand.get("description", "")).strip()[:400],
                "category": str(cand.get("category", "")).strip(),
                "target_system": str(cand.get("target_system", "")).strip(),
                "improvement_type": str(cand.get("improvement_type", "")).strip(),
            }
            if cand_data["title"] and cand_data["description"] and cand_data["target_system"]:
                if not is_semantic_duplicate(
                    cand_data["title"],
                    cand_data["description"],
                    cand_data["target_system"],
                    recent
                ):
                    data = cand_data
        except Exception:
            pass

    quality_score = calc_quality(data)
    ts = int(datetime.datetime.now(datetime.UTC).timestamp() * 1000)
    branch = f"dev/{data['target_system']}-{data['improvement_type']}-{ts}"

    cur.execute(
        "insert into dev_proposals(title,description,spec,branch_name,status,category,target_system,improvement_type,quality_score) values(?,?,?,?,?,?,?,?,?)",
        (
            data["title"],
            data["description"],
            data["description"],
            branch,
            "approved",
            data["category"],
            data["target_system"],
            data["improvement_type"],
            quality_score,
        ),
    )
    conn.commit()
    print("proposal created", cur.lastrowid, branch, data["title"], quality_score)
    conn.close()

if __name__ == "__main__":
    main()
