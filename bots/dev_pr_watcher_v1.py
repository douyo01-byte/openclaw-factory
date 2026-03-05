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

def tick_once(conn: sqlite3.Connection):
    dirty_head=False
    conn.execute("update dev_proposals set dev_stage='merged' where status='merged' and coalesce(pr_status,'')='merged' and coalesce(dev_stage,'')=''")
    dirty_head=True
    conn.execute("update dev_proposals set status='merged' where pr_number is not null and coalesce(pr_status,'')='merged' and coalesce(status,'')!='merged'")
    dirty_head=True
    conn.execute("update dev_proposals set dev_stage='merged' where pr_number is not null and coalesce(pr_status,'')='merged' and coalesce(dev_stage,'')!='merged'")
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

    rows = conn.execute(
        "select id, pr_number, pr_url, coalesce(pr_status,'') pr_status, coalesce(status,'') status, coalesce(dev_stage,'') dev_stage "
        "from dev_proposals "
        "where (pr_number is null or pr_number='' or pr_number=0 or coalesce(pr_status,'') in ('','open','closed')) "
        "order by id desc limit 50"
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
            continue

        merged = bool(pr.get("merged_at"))
        state = (pr.get("state") or "").lower()
        if merged:
            new = "merged"
        elif state == "closed":
            new = "closed"
        else:
            new = "open"

        if new == (r["pr_status"] or ""):
            continue

        conn.execute("update dev_proposals set pr_status=? where id=?", (new, pid))
        dirty = True

        if new == "merged":
            conn.execute("update dev_proposals set status='merged' where id=? and coalesce(status,'')!='merged'", (pid,))
            conn.execute("update dev_proposals set dev_stage='merged' where id=? and coalesce(dev_stage,'')!='merged'", (pid,))
            dirty = True

        notify.append((pid, prn, new))

    if dirty:
        conn.commit()

    for pid, prn, new in notify:
        msg = "DEV PROPOSAL\nid: %s\npr_number: %s\npr_status: %s\n\nreply:\nok %s\nhold %s\nreq %s <text>" % (pid, prn, new, pid, pid, pid)
        tg_send(msg)

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
