import os, sqlite3, time, requests

DB = os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
TG_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TG_CHAT = os.environ["TELEGRAM_CHAT_ID"]

def tg(text):
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data={"chat_id": TG_CHAT, "text": text},
        timeout=20
    )

def main():
    while True:
        try:
            con = sqlite3.connect(DB)
            cur = con.cursor()

            rows = cur.execute("""
            select id,title,source_ai,status
            from dev_proposals
            where id >= (select max(id)-10 from dev_proposals)
            order by id desc
            """).fetchall()

            merged = cur.execute("""
            select id from dev_proposals
            where status='merged'
            order by id desc
            limit 5
            """).fetchall()

            text = "🧠 OpenClaw 進化ログ\n\n"

            text += "■ 新規提案\n"
            for r in rows[:5]:
                text += f"- {r[0]} {r[1][:30]} ({r[2]})\n"

            text += "\n■ 最近のmerge\n"
            for m in merged:
                text += f"- {m[0]}\n"

            text += "\n■ 状態\n"
            text += "進化方向: 構造進化モード\n"

            tg(text)
            print("evolution_trace_sent", flush=True)

            con.close()

        except Exception as e:
            tg(f"evolution_trace_error: {e}")

        time.sleep(600)

if __name__ == "__main__":
    main()
