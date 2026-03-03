from __future__ import annotations
import os
import sqlite3
import subprocess
import json
import shutil
import time
import requests

print("[WATCHER_BOOT] start", flush=True)

GH = os.environ.get("GH_BIN") or shutil.which("gh") or "/opt/homebrew/bin/gh"
DB_PATH = os.environ.get("OCLAW_DB_PATH") or os.environ.get("DB_PATH") or "data/openclaw.db"
REPO = os.environ.get("GITHUB_REPO") or "douyo01-byte/openclaw-factory"
SLEEP = float(os.environ.get("PR_WATCHER_SLEEP") or "20")

def gh_api(path: str):
    try:
        import requests
        tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
        if not tok:
            print("[watcher] missing GITHUB_TOKEN/GH_TOKEN", flush=True)
            return None
        url = "https://api.github.com" + path
        r = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {tok}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "openclaw-dev-pr-watcher",
                "Connection": "close",
            },
            timeout=(3, 5),
        )
        # rate limit backoff (GitHub API)
        try:
            if r.status_code == 403:
                rem = r.headers.get('X-RateLimit-Remaining')
                reset = r.headers.get('X-RateLimit-Reset')
                body = (r.text or '')
                if reset and (rem == '0' or 'rate limit' in body.lower()):
                    try:
                        wait = max(1, int(reset) - int(time.time()) + 2)
                    except Exception:
                        wait = 60
                    print('[watcher] rate_limited sleep', wait, flush=True)
                    time.sleep(wait)
                    return None
        except Exception as e:
            print('[watcher] rate_limit handler exception', repr(e), flush=True)
        if r.status_code >= 300:
            msg = (r.text or "").replace("\n", " | ")
            print("[watcher] gh_api http", r.status_code, msg[:200], flush=True)
            return None
        return r.json()
    except Exception as e:
        print("[watcher] gh_api exception", repr(e), flush=True)
        return None
        url = "https://api.github.com" + path
        r = requests.get(
            url,
            headers={
                "Authorization": f"token {tok}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "openclaw-dev-pr-watcher",
            },
            timeout=20,
        )
        if r.status_code >= 300:
            msg = (r.text or "").replace("\n", " | ")
            print("[watcher] gh_api http", r.status_code, msg[:200], flush=True)
            return None
        return r.json()
    except Exception as e:
        print("[watcher] gh_api exception", repr(e), flush=True)
        return None
        return json.loads(r.stdout)
    except subprocess.TimeoutExpired:
        print('[watcher] gh_api timeout', path, flush=True)
        return None
    except Exception as e:
        print('[watcher] gh_api exception', repr(e), flush=True)
        return None
def tg_send(text: str):
    tok = os.environ["TELEGRAM_BOT_TOKEN"]
    chat = os.environ["TELEGRAM_CHAT_ID"]
    requests.post(
        f"https://api.telegram.org/bot{tok}/sendMessage",
        data={"chat_id": chat, "text": text},
        timeout=20,
    ).raise_for_status()

def tick_once(conn: sqlite3.Connection):
    prs = conn.execute(
        "select id, pr_number, coalesce(pr_status,'') pr_status from dev_proposals where pr_number is not null and pr_number!='' and pr_number!=0 and coalesce(pr_status,'')!='merged' order by id desc limit 25"
    ).fetchall()

    for r in prs:
        prn = r["pr_number"]
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

        conn.execute("update dev_proposals set pr_status=? where id=?", (new, r["id"]))
        if new == "merged":
            conn.execute(
                "update dev_proposals set status='merged' where id=? and status!='merged'",
                (r["id"],),
            )
        conn.commit()

        msg = (
            "DEV PROPOSAL\nid: %s\npr_number: %s\npr_status: %s\n\nreply:\nok %s\nhold %s\nreq %s <text>"
            % (r["id"], prn, new, r["id"], r["id"], r["id"])
        )
        try:
            tg_send(msg)
        except Exception as e:
            print("[watcher] tg_send failed:", repr(e), flush=True)

def main():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    while True:
        print('[watcher] tick', flush=True)
        conn = sqlite3.connect(DB_PATH, timeout=30)
        try:
            try:
                conn.execute("PRAGMA busy_timeout=30000")
            except Exception:
                pass
            conn.row_factory = sqlite3.Row
            print('[watcher] tick_once enter', flush=True)
            tick_once(conn)
            print('[watcher] tick_once exit', flush=True)
        finally:
            try:
                conn.close()
            except Exception:
                pass
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
