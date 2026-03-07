import os, sqlite3, requests

FACTORY_DB = os.environ.get("FACTORY_DB_PATH") or os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db")

def conn():
    c = sqlite3.connect(FACTORY_DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA busy_timeout=30000")
    return c

def ensure_tables(c):
    c.execute("""
        create table if not exists kv(
          k text primary key,
          v text
        )
    """)
    c.execute("""
        create table if not exists ceo_hub_events(
          id integer primary key,
          event_type text,
          title text,
          body text,
          proposal_id integer,
          pr_url text,
          created_at text default (datetime('now')),
          sent_at text
        )
    """)

def get_last_sent(c):
    row = c.execute("select v from kv where k='ceo_report_last_sent'").fetchone()
    return row["v"] if row and row["v"] else None

def set_last_sent(c):
    c.execute("""
        insert into kv(k,v) values('ceo_report_last_sent', datetime('now'))
        on conflict(k) do update set v=excluded.v
    """)

def tg_send(text):
    tok = os.environ.get("TELEGRAM_DEV_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_DEV_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        return "skip"
    r = requests.post(
        f"https://api.telegram.org/bot{tok}/sendMessage",
        data={"chat_id": chat, "text": text},
        timeout=20,
    )
    if r.status_code == 429:
        return "rate_limited"
    r.raise_for_status()
    return "sent"

def build_ai_comment(c, since):
    if since:
        rows = c.execute("""
            select
              coalesce(event_type,'') as event_type,
              coalesce(title,'') as title,
              coalesce(body,'') as body
            from ceo_hub_events
            where created_at > ?
            order by id asc
            limit 50
        """, (since,)).fetchall()
    else:
        rows = c.execute("""
            select
              coalesce(event_type,'') as event_type,
              coalesce(title,'') as title,
              coalesce(body,'') as body
            from ceo_hub_events
            order by id desc
            limit 20
        """).fetchall()

    event_types = [r["event_type"] for r in rows]
    titles = [r["title"] for r in rows if r["title"]]
    bodies = [r["body"] for r in rows if r["body"]]

    pr_cnt = sum(1 for x in event_types if x == "pr_created")
    explain_cnt = sum(1 for x in event_types if x == "explain_generated")
    text = " ".join(titles + bodies)

    if pr_cnt >= 3:
        return f"AIコメント: この10分はPR作成が{pr_cnt}件進み、改善案が実行段階へ進みました。"
    if explain_cnt >= 3 and pr_cnt == 0:
        return f"AIコメント: この10分は仕様整理が中心で、Explain生成が{explain_cnt}件進みました。次は実行優先の提案をPR化すると流れがつながります。"
    if "重複" in text or "レート" in text:
        return "AIコメント: 通知運用の安定化が中心です。重複送信やレート制限対策の改善が進んでいます。"
    if "再試行" in text or "失敗" in text:
        return "AIコメント: 実行失敗への耐性強化が中心です。再試行や失敗検知の改善で無人運転の安定性を上げています。"
    if "検索" in text or "信頼性" in text or "要約" in text:
        return "AIコメント: 調査品質の改善が中心です。情報選定や信頼性判定の精度向上が進んでいます。"
    if titles:
        return f"AIコメント: 直近では「{titles[-1]}」などの改善が進みました。"
    return "AIコメント: 今回の時間帯は大きな変化は少なめです。次の実行イベントが入ると要約がより具体的になります。"

def build_text(c, since):
    if since:
        rows = c.execute("""
            select
              id,
              coalesce(event_type,'') as event_type,
              coalesce(title,'') as title,
              coalesce(body,'') as body,
              coalesce(proposal_id,'') as proposal_id,
              coalesce(pr_url,'') as pr_url,
              coalesce(created_at,'') as created_at
            from ceo_hub_events
            where created_at > ?
            order by id asc
            limit 120
        """, (since,)).fetchall()
    else:
        rows = c.execute("""
            select
              id,
              coalesce(event_type,'') as event_type,
              coalesce(title,'') as title,
              coalesce(body,'') as body,
              coalesce(proposal_id,'') as proposal_id,
              coalesce(pr_url,'') as pr_url,
              coalesce(created_at,'') as created_at
            from ceo_hub_events
            order by id desc
            limit 20
        """).fetchall()
        rows = list(reversed(rows))

    lines = []
    lines.append("📌 OpenClaw 10分要約")
    lines.append("")

    if not rows:
        lines.append("・新しいイベントはありません")
        lines.append("")
        lines.append(build_ai_comment(c, since))
        return "\n".join(lines)

    for r in rows:
        t = r["title"].strip()
        b = r["body"].strip()
        lines.append(f"・{t}")
        if b:
            lines.append(f"  {b}")
        if r["pr_url"]:
            lines.append(f"  {r['pr_url']}")
        lines.append("")

    lines.append(build_ai_comment(c, since))
    return "\n".join(lines)

def run_once():
    with conn() as c:
        ensure_tables(c)
        last_sent = get_last_sent(c)
        text = build_text(c, last_sent)
        st = tg_send(text)
        if st == "sent":
            if last_sent:
                c.execute(
                    "update ceo_hub_events set sent_at=datetime('now') where sent_at is null and created_at > ?",
                    (last_sent,)
                )
            else:
                c.execute("update ceo_hub_events set sent_at=datetime('now') where sent_at is null")
            set_last_sent(c)
            c.commit()
            print("report_sent=1", flush=True)
            return
        if st == "rate_limited":
            print("report_sent=rate_limited", flush=True)
            return
        print("report_sent=skip", flush=True)

if __name__ == "__main__":
    run_once()
