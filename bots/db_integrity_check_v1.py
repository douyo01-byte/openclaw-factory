import json, os, sqlite3, subprocess, time
from pathlib import Path
from urllib import request, parse

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
OBS = ROOT / "obs"
OBS.mkdir(parents=True, exist_ok=True)
STATE_PATH = OBS / "db_integrity_state.json"

def tg_send(token, chat_id, text):
    if not token or not chat_id or not text:
        return
    data = parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    req = request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    try:
        request.urlopen(req, timeout=20).read()
    except Exception:
        pass

def detect_db():
    cands = []
    if os.environ.get("DB_PATH"):
        cands.append(Path(os.environ["DB_PATH"]))
    cands += [
        ROOT / "data" / "openclaw.db",
        ROOT / "data" / "openclaw_daemon.db",
        ROOT / "data" / "openclaw",
    ]
    for p in cands:
        if p.exists():
            return p
    return None

def table_exists(conn, name):
    cur = conn.execute("select 1 from sqlite_master where type='table' and name=?", (name,))
    return cur.fetchone() is not None

def cols(conn, table):
    return [r[1] for r in conn.execute(f"pragma table_info({table})").fetchall()]

def q1(conn):
    if not table_exists(conn, "ceo_hub_events"):
        return None
    c = set(cols(conn, "ceo_hub_events"))
    if not {"event_type", "proposal_id"}.issubset(c):
        return None
    return conn.execute("""
        select count(*)
        from (
          select proposal_id
          from ceo_hub_events
          where event_type in ('pr_created','proposal_created')
          group by proposal_id
        ) a
        left join (
          select proposal_id
          from ceo_hub_events
          where event_type in ('merged','pr_merged','merge')
          group by proposal_id
        ) b
        on a.proposal_id = b.proposal_id
        where a.proposal_id is not null
          and b.proposal_id is null
    """).fetchone()[0]

def q2(conn):
    if not table_exists(conn, "ceo_hub_events"):
        return None
    c = set(cols(conn, "ceo_hub_events"))
    if not {"event_type", "proposal_id"}.issubset(c):
        return None
    return conn.execute("""
        select count(*)
        from (
          select proposal_id
          from ceo_hub_events
          where event_type in ('merged','pr_merged','merge')
          group by proposal_id
        ) a
        left join (
          select proposal_id
          from ceo_hub_events
          where event_type in ('learning_result','learning','learned')
          group by proposal_id
        ) b
        on a.proposal_id = b.proposal_id
        where a.proposal_id is not null
          and b.proposal_id is null
    """).fetchone()[0]

def q3(conn):
    if not table_exists(conn, "dev_proposals") or not table_exists(conn, "ceo_hub_events"):
        return None
    dp = set(cols(conn, "dev_proposals"))
    ev = set(cols(conn, "ceo_hub_events"))
    if not {"id", "status"}.issubset(dp) or not {"proposal_id", "event_type"}.issubset(ev):
        return None
    return conn.execute("""
        with last_evt as (
          select proposal_id, max(id) as max_id
          from ceo_hub_events
          group by proposal_id
        ),
        evt as (
          select e.proposal_id, e.event_type
          from ceo_hub_events e
          join last_evt l
            on e.proposal_id = l.proposal_id
           and e.id = l.max_id
        )
        select count(*)
        from dev_proposals d
        join evt e on d.id = e.proposal_id
        where
          (d.status = 'merged' and e.event_type not in ('merged','pr_merged','merge','learning_result'))
          or
          (d.status = 'approved' and e.event_type in ('rejected','closed'))
    """).fetchone()[0]

def q4(conn):
    if not table_exists(conn, "ceo_hub_events"):
        return None
    c = set(cols(conn, "ceo_hub_events"))
    if not {"proposal_id", "event_type", "created_at"}.issubset(c):
        return None
    rows = conn.execute("""
        select proposal_id, event_type, created_at
        from ceo_hub_events
        where proposal_id is not null
        order by proposal_id, datetime(created_at)
    """).fetchall()
    rank = {
        "proposal_created": 1, "pr_created": 1,
        "approved": 2,
        "merge": 3, "merged": 3, "pr_merged": 3,
        "learning": 4, "learning_result": 4, "learned": 4,
    }
    bad = 0
    prev_pid = None
    prev_rank = 0
    for pid, et, _ in rows:
        r = rank.get(et)
        if r is None:
            continue
        if pid != prev_pid:
            prev_pid = pid
            prev_rank = 0
        if r < prev_rank:
            bad += 1
        prev_rank = max(prev_rank, r)
    return bad

def q5(conn):
    if not table_exists(conn, "dev_proposals"):
        return None
    c = set(cols(conn, "dev_proposals"))
    miss = 0
    for col in ("source", "category", "target_system"):
        if col in c:
            miss += conn.execute(f"select count(*) from dev_proposals where {col} is null or trim({col}) = ''").fetchone()[0]
    return miss

def load_state():
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_state(d):
    STATE_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    db = detect_db()
    if not db:
        raise SystemExit("DB not found")
    conn = sqlite3.connect(str(db))

    res = {
        "pr_created_without_merged": q1(conn),
        "merged_without_learning_result": q2(conn),
        "status_mismatch": q3(conn),
        "lifecycle_anomaly_count": q4(conn),
        "missing_source_category_target_system": q5(conn),
        "checked_at": int(time.time()),
        "db_path": str(db),
    }
    conn.close()

    line = "[db_integrity] " + " ".join(f"{k}={v}" for k, v in res.items() if k not in ("checked_at","db_path"))
    with (LOGS / "db_integrity_check_v1.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")

    state = load_state()
    prev = state.get("last_result", {})
    changed = {k: res[k] for k in res if k in prev and isinstance(res[k], int) and prev.get(k) != res[k]}

    ka01_token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("KAIKUN01_BOT_TOKEN")
    ka01_chat = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("KAIKUN01_CHAT_ID")
    ka02_token = os.environ.get("CEO_TELEGRAM_BOT_TOKEN") or ka01_token
    ka02_chat = os.environ.get("CEO_CHAT_ID") or os.environ.get("KAIKUN02_CHAT_ID")

    severe = []
    if (res["lifecycle_anomaly_count"] or 0) > 0:
        severe.append(f"lifecycle anomaly={res['lifecycle_anomaly_count']}")
    if (res["status_mismatch"] or 0) > 0:
        severe.append(f"status mismatch={res['status_mismatch']}")

    if severe:
        tg_send(
            ka01_token,
            ka01_chat,
            "⚠ OpenClaw DB整合性異常\n" + "\n".join(severe)
        )

    if not state.get("last_daily_sent_date") == time.strftime("%Y-%m-%d"):
        txt = (
            "OpenClaw daily integrity summary\n"
            f"pr_created without merged: {res['pr_created_without_merged']}\n"
            f"merged without learning_result: {res['merged_without_learning_result']}\n"
            f"status mismatch: {res['status_mismatch']}\n"
            f"lifecycle anomaly: {res['lifecycle_anomaly_count']}\n"
            f"missing source/category/target_system: {res['missing_source_category_target_system']}"
        )
        tg_send(ka02_token, ka02_chat, txt)
        state["last_daily_sent_date"] = time.strftime("%Y-%m-%d")

    state["last_result"] = res
    state["last_changed"] = changed
    save_state(state)

if __name__ == "__main__":
    main()
