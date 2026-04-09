import sqlite3
from flask import Flask, jsonify, Response

DB = "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"

AGENTS = {
  "kaikun04": {"name":"CTO", "emoji":"🧠", "color":"#7c3aed"},
  "ops_exec": {"name":"Executor", "emoji":"⚙️", "color":"#2563eb"},
}

app = Flask(__name__)


def winner_summary():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    winner = cur.execute("""
    select theme,status from active_projects
    where status='winner'
    limit 1
    """).fetchone()
    judge = cur.execute("""
    select avg_score,decision,note
    from winner_rejudge_log
    order by id desc
    limit 1
    """).fetchone()
    con.close()
    return winner, judge


def get_rows():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("""
    select id,target_bot,status,
           substr(coalesce(nullif(reply_text,''), task_text),1,160)
    from router_tasks
    where (
      coalesce(task_text,'') like '[WINNER_ONLY]%'
      or coalesce(task_text,'') like '[WINNER_LOOP]%'
      or coalesce(reply_text,'') like '[WINNER_EXEC_BRIDGED]%'
      or target_bot='ops_exec'
    )
    order by id desc
    limit 30
    """)
    rows = cur.fetchall()
    con.close()
    return rows

@app.route("/state")
def state():
    rows = get_rows()
    agents = {}
    for r in rows:
        bot = r[1]
        agents.setdefault(bot, []).append({
            "id": r[0],
            "status": r[2],
            "text": r[3],
        })
    out = []
    for bot, tasks in agents.items():
        meta = AGENTS.get(bot, {"name": bot, "emoji":"❓", "color":"#6b7280"})
        out.append({
            "bot": bot,
            "name": meta["name"],
            "emoji": meta["emoji"],
            "color": meta["color"],
            "tasks": tasks
        })
    return jsonify(out)

@app.route("/")
def home():
    rows = get_rows()
    agents = {}
    for r in rows:
        bot = r[1]
        agents.setdefault(bot, []).append({
            "id": r[0],
            "status": r[2],
            "text": r[3],
        })

    cards = []
    for bot, tasks in agents.items():
        meta = AGENTS.get(bot, {"name": bot, "emoji":"❓", "color":"#6b7280"})
        items = []
        for t in tasks[:12]:
            status_color = {
                "done": "#16a34a",
                "new": "#f59e0b",
                "started": "#2563eb",
                "skipped_winner_focus": "#6b7280",
                "skipped_winner_loop_dedup": "#6b7280",
            }.get(t["status"], "#6b7280")
            items.append(f"""
            <div class="task">
              <div class="task-head">
                <span class="task-id">#{t['id']}</span>
                <span class="badge" style="background:{status_color}">{t['status']}</span>
              </div>
              <div class="task-text">{t['text']}</div>
            </div>
            """)
        cards.append(f"""
        <section class="card">
          <div class="card-head" style="border-color:{meta['color']}">
            <div class="avatar" style="background:{meta['color']}">{meta['emoji']}</div>
            <div>
              <div class="title">{meta['name']}</div>
              <div class="sub">{bot}</div>
            </div>
          </div>
          <div class="tasks">
            {''.join(items)}
          </div>
        </section>
        """)

    winner, judge = winner_summary()
    winner_theme = winner[0] if winner else 'なし'
    winner_status = winner[1] if winner else '-'
    judge_score = judge[0] if judge else '-'
    judge_decision = judge[1] if judge else '-'
    judge_note = judge[2] if judge else '-'

    html = f"""
    <!doctype html>
    <html lang="ja">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <title>OpenClaw Winner Flow</title>
      <style>
        body {{
          margin:0; padding:24px; background:#0b1020; color:#f8fafc;
          font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
        }}
        .wrap {{ max-width:1200px; margin:0 auto; }}
        h1 {{ font-size:28px; margin:0 0 8px; }}
        .desc {{ color:#94a3b8; margin-bottom:20px; }}
        .grid {{
          display:grid;
          grid-template-columns:repeat(auto-fit,minmax(340px,1fr));
          gap:18px;
        }}
        .card {{
          background:#111827; border:1px solid #1f2937; border-radius:20px;
          padding:18px; box-shadow:0 8px 30px rgba(0,0,0,.25);
        }}
        .card-head {{
          display:flex; align-items:center; gap:14px; padding-bottom:14px;
          border-bottom:3px solid #374151; margin-bottom:14px;
        }}
        .avatar {{
          width:54px; height:54px; border-radius:999px;
          display:flex; align-items:center; justify-content:center;
          font-size:28px;
        }}
        .title {{ font-size:20px; font-weight:700; }}
        .sub {{ color:#94a3b8; font-size:13px; }}
        .tasks {{ display:flex; flex-direction:column; gap:12px; }}
        .task {{
          background:#0f172a; border:1px solid #1e293b; border-radius:14px; padding:12px;
        }}
        .task-head {{
          display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;
        }}
        .task-id {{ color:#93c5fd; font-size:12px; }}
        .badge {{
          font-size:11px; padding:4px 8px; border-radius:999px; color:white; font-weight:700;
        }}
        .task-text {{ white-space:pre-wrap; line-height:1.45; color:#e5e7eb; font-size:14px; }}
        .topbar {{
          display:flex; justify-content:space-between; align-items:end; gap:12px; margin-bottom:18px;
        }}
        .link a {{ color:#93c5fd; text-decoration:none; }}
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="topbar">
          <div>
            <h1>OpenClaw Winner Flow</h1>
            <div class="desc">勝ち案件だけを進める現在の流れ</div><div class="desc">Winner: {winner_theme} / status: {winner_status} / avg_score: {judge_score} / decision: {judge_decision} / note: {judge_note}</div>
          </div>
          <div class="link"><a href="/state">JSON</a></div>
        </div>
        <div class="grid">
          {''.join(cards)}
        </div>
      </div>
    </body>
    </html>
    """
    return Response(html, mimetype="text/html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8789)
