from __future__ import annotations
import os, re, sqlite3, time, shutil, requests

print("[WATCHER_BOOT] start", flush=True)

GH = os.environ.get("GH_BIN") or shutil.which("gh") or "/opt/homebrew/bin/gh"
DB_PATH = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "data/openclaw.db"
REPO = os.environ.get("GITHUB_REPO") or "douyo01-byte/openclaw-factory"
SLEEP = float(os.environ.get("PR_WATCHER_SLEEP") or "20")

TG_NOTIFY = (os.environ.get("TG_NOTIFY") or "1").strip().lower() not in ("0", "false", "no", "off")
TG_TOKEN = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
TG_CHAT = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
TG_OK = bool(TG_TOKEN and TG_CHAT)

_warned_no_gh = False
_warned_no_tg = False

def tg_send(text: str):
    global _warned_no_tg
    if not TG_NOTIFY:
        return
    if not TG_OK:
        if not _warned_no_tg:
            _warned_no_tg = True
            print("[watcher] telegram disabled (missing TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID)", flush=True)
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data={"chat_id": TG_CHAT, "text": text},
            timeout=(3, 20),
        ).raise_for_status()
    except Exception as e:
        print("[watcher] tg_send failed:", repr(e), flush=True)

def gh_api(path: str):
    global _warned_no_gh
    tok = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
    if not tok:
        if not _warned_no_gh:
            _warned_no_gh = True
            print("[watcher] missing GITHUB_TOKEN/GH_TOKEN", flush=True)
        return None
    url = "https://api.github.com" + path
    try:
        r = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {tok}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "openclaw-dev-pr-watcher",
                "Connection": "close",
            },
            timeout=(3, 7),
        )
        if r.status_code == 403:
            rem = r.headers.get("X-RateLimit-Remaining")
            reset = r.headers.get("X-RateLimit-Reset")
            body = (r.text or "")
            if reset and (rem == "0" or "rate limit" in body.lower()):
                try:
                    wait = max(1, int(reset) - int(time.time()) + 2)
                except Exception:
                    wait = 60
                print("[watcher] rate_limited sleep", wait, flush=True)
                time.sleep(wait)
                return None
        if r.status_code >= 300:
            msg = (r.text or "").replace("\n", " | ")
            print("[watcher] gh_api http", r.status_code, msg[:200], flush=True)
            return None
        return r.json()
    except Exception as e:
        print("[watcher] gh_api exception", repr(e), flush=True)
        return None

def extract_pr_number(pr_url: str) -> int | None:
    if not pr_url:
        return None
    m = re.search(r"/pull/(\d+)", pr_url)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def hub_event(conn, event_type, title, body, proposal_id, pr_url):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ceo_hub_events(
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
    exists = conn.execute("""
        select 1 from ceo_hub_events
        where event_type=?
          and proposal_id=?
          and coalesce(pr_url,'')=coalesce(?, '')
        limit 1
    """, (event_type, proposal_id, pr_url)).fetchone()
    if not exists:
        conn.execute("""
            insert into ceo_hub_events(event_type,title,body,proposal_id,pr_url)
            values(?,?,?,?,?)
        """, (event_type, title, body, proposal_id, pr_url))

def ensure_aux_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS proposal_state(
          proposal_id integer primary key,
          stage text,
          pending_questions text,
          updated_at datetime default current_timestamp,
          pending_question text
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ceo_hub_events(
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

def tick_once(conn: sqlite3.Connection):
    dirty_head=False
    conn.execute("update dev_proposals set dev_stage='merged' where status='merged' and coalesce(pr_status,'')='merged' and coalesce(dev_stage,'')=''")
    dirty_head=True
    conn.execute("update dev_proposals set status='merged' where pr_number is not null and coalesce(pr_status,'')='merged' and coalesce(status,'')!='merged'")
    dirty_head=True
    conn.execute("update dev_proposals set dev_stage='merged' where pr_number is not null and coalesce(pr_status,'')='merged' and coalesce(dev_stage,'')!='merged'")
    dirty_head=True
    conn.execute("update proposal_state set stage='merged', updated_at=datetime('now') where proposal_id in (select id from dev_proposals where pr_number is not null and coalesce(pr_status,'')='merged') and coalesce(stage,'')!='merged'")
    dirty_head=True
    conn.execute("update dev_proposals set status='closed' where pr_number is not null and coalesce(pr_status,'')='closed' and coalesce(status,'')!='closed'")
    dirty_head=True
    conn.execute("update dev_proposals set dev_stage='closed' where pr_number is not null and coalesce(pr_status,'')='closed' and coalesce(dev_stage,'')!='closed'")
    dirty_head=True
    conn.execute("update dev_proposals set status='open' where pr_number is not null and coalesce(pr_status,'')='open' and coalesce(status,'')!='open'")
    dirty_head=True
    conn.execute("update dev_proposals set dev_stage='open' where pr_number is not null and coalesce(pr_status,'')='open' and coalesce(dev_stage,'')!='open'")
    dirty_head=True
    conn.commit()
    if dirty_head:
        conn.commit()

    merged_rows = conn.execute(
        "select id, coalesce(title,''), coalesce(pr_url,'') "
        "from dev_proposals where coalesce(pr_status,'')='merged' and coalesce(status,'')='merged' and coalesce(dev_stage,'')='merged' "
        "order by id desc limit 50"
    ).fetchall()
    for r in merged_rows:
        exists = conn.execute(
            """
            select 1
            from ceo_hub_events
            where event_type='merged'
              and proposal_id=?
            limit 1
            """,
            (int(r[0]),)
        ).fetchone()
        if not exists:
            hub_event(conn, "merged", f"統 合 完 了 : {r[1]}", "PRが mainへ 統 合 さ れ ま し た ", int(r[0]), r[2])


    rows = conn.execute(
        "select id, pr_number, pr_url, coalesce(pr_status,'') pr_status, coalesce(status,'') status, coalesce(dev_stage,'') dev_stage "
        "from dev_proposals "
        "where (pr_number is null or pr_number='' or pr_number=0 or coalesce(pr_status,'') in ('','open','closed')) "
        "order by id desc limit 500"
    ).fetchall()

    dirty = False
    notify = []

    for r in rows:
        pid = r["id"]
        prn = r["pr_number"]
        pr_url = r["pr_url"] or ""

        if not prn:
            prn2 = extract_pr_number(pr_url)
            if prn2:
                conn.execute("update dev_proposals set pr_number=? where id=? and (pr_number is null or pr_number='' or pr_number=0)", (prn2, pid))
                prn = prn2
                dirty = True

        if not prn:
            continue

        pr = gh_api(f"/repos/{REPO}/pulls/{prn}")
        if not pr:
            print(f"[watcher] PR skipped proposal={pid} reason=gh_api_none", flush=True)
            continue

        print(f"[watcher] PR detected proposal={pid} pr={prn}", flush=True)
        merged = bool(pr.get("merged_at"))
        state = (pr.get("state") or "").lower()
        if merged:
            new = "merged"
        elif state == "closed":
            new = "closed"
        else:
            new = "open"

        if new == (r["pr_status"] or ""):
            print(f"[watcher] PR skipped proposal={pid} reason=no_status_change", flush=True)
            continue

        conn.execute("update dev_proposals set pr_status=? where id=?", (new, pid))
        dirty = True
        if new == "merged":
            print(f"[watcher] PR merged proposal={pid} pr={prn}", flush=True)
            conn.execute("update proposal_state set stage='merged', updated_at=datetime('now') where proposal_id=? and coalesce(stage,'')!='merged'", (pid,))
            dirty = True
        elif new == "closed":
            conn.execute("update proposal_state set stage='closed', updated_at=datetime('now') where proposal_id=? and coalesce(stage,'') not in ('closed','merged')", (pid,))
            dirty = True
        elif new == "open":
            conn.execute("update proposal_state set stage='pr_created', updated_at=datetime('now') where proposal_id=? and coalesce(stage,'') not in ('merged','closed','pr_created')", (pid,))
            dirty = True

        if new == "merged":
            conn.execute("update dev_proposals set status='merged' where id=? and coalesce(status,'')!='merged'", (pid,))
            conn.execute("update dev_proposals set dev_stage='merged' where id=? and coalesce(dev_stage,'')!='merged'", (pid,))
            dirty = True

        notify.append((pid, prn, new))

    if dirty:
        conn.commit()

    for pid, prn, new in notify:
        msg = "DEV_PROPOSAL_DISABLED\nid: %s\npr_number: %s\npr_status: %s\n\nreply:\nok %s\nhold %s\nreq %s <text>" % (pid, prn, new, pid, pid, pid)
        pass

def main():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    while True:
        print("[watcher] tick", flush=True)
        conn = sqlite3.connect(DB_PATH, timeout=30)
        try:
            try:
                conn.execute("PRAGMA busy_timeout=30000")
            except Exception:
                pass
            try:
                conn.execute("PRAGMA journal_mode=WAL")
            except Exception:
                pass
            conn.row_factory = sqlite3.Row
            print("[watcher] tick_once enter", flush=True)
            ensure_aux_tables(conn)
            tick_once(conn)
            print("[watcher] tick_once exit", flush=True)
        finally:
            try:
                conn.close()
            except Exception:
                pass
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
