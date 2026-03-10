import json, os, sqlite3, time, urllib.request, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(os.environ.get("DB_PATH") or (ROOT / "data" / "openclaw_real.db"))
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
BOT_TOKEN = (os.environ.get("TELEGRAM_CEO_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()

def tg_send(chat_id, text, reply_to_message_id=None):
    if not BOT_TOKEN or not chat_id or not text:
        return False, "missing telegram env"
    data = {"chat_id": str(chat_id), "text": text}
    if reply_to_message_id:
        data["reply_to_message_id"] = str(reply_to_message_id)
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=body)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            r.read()
        return True, None
    except Exception as e:
        return False, str(e)

def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}

def one(c, q, p=()):
    row = c.execute(q, p).fetchone()
    return row[0] if row else None

def build_context(c):
    total = one(c, "select count(*) from dev_proposals") or 0
    merged = one(c, "select count(*) from dev_proposals where coalesce(status,'')='merged'") or 0
    approved = one(c, "select count(*) from dev_proposals where coalesce(status,'')='approved'") or 0
    open_pr = one(c, "select count(*) from dev_proposals where coalesce(pr_status,'')='open' or coalesce(status,'')='open' or coalesce(dev_stage,'')='open'") or 0
    backlog = one(c, """
        select count(*)
        from dev_proposals
        where coalesce(status,'')='approved'
          and (
            coalesce(project_decision,'')='backlog'
            or (coalesce(guard_status,'')!='' and coalesce(guard_status,'')!='safe')
          )
    """) or 0

    maturity = load_json(ROOT / "obs" / "company_health_score.json")
    integ = {}
    p = ROOT / "logs" / "db_integrity_check_v1.log"
    if p.exists():
        try:
            line = p.read_text(encoding="utf-8").strip().splitlines()[-1]
            for token in line.replace("[db_integrity]", "").split():
                if "=" in token:
                    k, v = token.split("=", 1)
                    try:
                        integ[k] = int(v)
                    except Exception:
                        integ[k] = v
        except Exception:
            pass

    supply = load_json(ROOT / "obs" / "supply_adoption_metrics.json")
    top_source = None
    rows = supply.get("rows") or []
    if rows:
        rows = sorted(rows, key=lambda x: (-(x.get("mergeds") or 0), -(x.get("proposals") or 0), str(x.get("source") or "")))
        top_source = rows[0]

    latest = c.execute("""
        select id, title, coalesce(status,''), coalesce(project_decision,''), coalesce(guard_status,'')
        from dev_proposals
        order by id desc
        limit 5
    """).fetchall()

    return {
        "maturity_percent": maturity.get("maturity_percent"),
        "proposals_total": total,
        "merged": merged,
        "approved": approved,
        "open_pr": open_pr,
        "backlog": backlog,
        "integrity": integ,
        "top_source": top_source,
        "latest_proposals": latest,
    }

def build_fallback_reply(q, ctx):
    qn = (q or "").replace(" ", "").replace("　", "").lower()
    blockers = []
    integ = ctx["integrity"]
    if integ.get("pr_created_without_merged", 0):
        blockers.append(f"未merge {integ['pr_created_without_merged']}")
    if integ.get("merged_without_learning_result", 0):
        blockers.append(f"未learning {integ['merged_without_learning_result']}")
    if integ.get("lifecycle_anomaly_count", 0):
        blockers.append(f"lifecycle異常 {integ['lifecycle_anomaly_count']}")
    if integ.get("missing_source_category_target_system", 0):
        blockers.append(f"属性欠損 {integ['missing_source_category_target_system']}")

    if "maturity" in qn or "成熟度" in qn:
        return f"OpenClaw 秘書報告\nmaturity: {ctx['maturity_percent']}%"
    if "詰" in q or "問題" in q or "阻害" in q:
        return "OpenClaw 秘書報告\n詰まり: " + (" / ".join(blockers[:4]) if blockers else "大きな異常なし")
    if "優先" in q:
        if ctx["open_pr"] > 0:
            return f"OpenClaw 秘書報告\n次に優先: open PRの消化\nopen_pr={ctx['open_pr']}"
        if ctx["backlog"] > 0:
            return f"OpenClaw 秘書報告\n次に優先: backlog整理\nbacklog={ctx['backlog']}"
        return "OpenClaw 秘書報告\n次に優先: 72h burn-in 継続監視"
    if "72" in qn or "開始" in q:
        ok = ctx["maturity_percent"] is not None and ctx["maturity_percent"] >= 80
        severe = (integ.get("status_mismatch", 0) or 0) > 0
        return f"OpenClaw 秘書報告\n72h開始可否: {'yes' if ok and not severe else 'no'}"
    return (
        "OpenClaw 秘書報告\n"
        f"maturity: {ctx['maturity_percent']}%\n"
        f"merged: {ctx['merged']}\n"
        f"approved: {ctx['approved']}\n"
        f"open_pr: {ctx['open_pr']}\n"
        f"backlog: {ctx['backlog']}"
    )

def call_openai(query, ctx):
    if not OPENAI_API_KEY:
        return None
    prompt = f"""あなたはOpenClawのCEO秘書です。
事実は与えられた context のみを使い、短く日本語で返してください。
推測を広げすぎず、社長への秘書報告として答えてください。
必要なら次の一手を1つだけ述べてください。

query:
{query}

context:
{json.dumps(ctx, ensure_ascii=False)}
"""
    payload = {
        "model": "gpt-5-mini",
        "input": prompt,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            data = json.loads(r.read().decode())
        text = data.get("output_text", "").strip()
        return text or None
    except Exception:
        return None

def ensure_cols(c):
    cols = {r[1] for r in c.execute("pragma table_info(inbox_commands)")}
    if "status" not in cols:
        c.execute("alter table inbox_commands add column status text default 'new'")
    if "processed" not in cols:
        c.execute("alter table inbox_commands add column processed integer default 0")
    if "applied_at" not in cols:
        c.execute("alter table inbox_commands add column applied_at text")
    if "error" not in cols:
        c.execute("alter table inbox_commands add column error text")

def should_handle(text):
    t = (text or "").lower()
    n = t.replace(" ", "").replace("　", "").replace("\n", "")
    keys = [
        "今どう", "今の状態", "進捗", "状況", "maturity", "成熟度",
        "何が詰まってる", "何を優先", "72h", "72時間", "開始できる",
        "何が問題", "阻害要因", "どれくらい進化"
    ]
    return any(k in n for k in keys)

def main():
    print(f"DB={DB}", flush=True)
    conn = sqlite3.connect(str(DB))
    ensure_cols(conn)
    rows = conn.execute("""
        select id, chat_id, message_id, text, coalesce(status,'') as status
        from inbox_commands
        where coalesce(processed,0)=0
          and (
            coalesce(status,'') in ('', 'new', 'pending')
            or status like 'company_%'
          )
        order by id asc
        limit 20
    """).fetchall()

    done = 0
    for rid, chat_id, message_id, text, status in rows:
        if not should_handle(text):
            continue
        ctx = build_context(conn)
        reply = call_openai(text, ctx) or build_fallback_reply(text, ctx)
        ok, err = tg_send(chat_id, reply, message_id)
        if ok:
            conn.execute(
                "update inbox_commands set processed=1,status='secretary_done',applied_at=datetime('now'),error=null where id=?",
                (rid,),
            )
            done += 1
        else:
            conn.execute(
                "update inbox_commands set status='secretary_error',error=?,applied_at=datetime('now') where id=?",
                (err, rid),
            )
    conn.commit()
    conn.close()
    print(f"secretary_done={done}", flush=True)

if __name__ == "__main__":
    main()
