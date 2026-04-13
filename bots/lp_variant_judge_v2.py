import json
import os
import shutil
import sqlite3
import urllib.request
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))
METRICS_URL = os.environ.get("LP_VARIANT_METRICS_URL", "https://openclaw-fortune-order.openclaw-fortune.workers.dev/variant_metrics")
ROOT = Path(os.path.expanduser("~/AI/openclaw-factory-daemon"))

def fetch_metrics():
    req = urllib.request.Request(
        METRICS_URL,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))

def main():
    metrics = fetch_metrics()

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
    insert into lp_variants (variant, page_path, status, views, unlocks, score)
    select 'D', 'deploy/fortune/pages/index_D.html', 'candidate', 0, 0, 0
    where not exists (
      select 1 from lp_variants where variant='D'
    )
    """)

    for variant in ("A", "B", "C", "D"):
        views = int(metrics.get(variant, {}).get("views", 0))
        unlocks = int(metrics.get(variant, {}).get("unlocks", 0))
        score = int((unlocks * 100) / views) if views > 0 else 0

        cur.execute("""
        update lp_variants
        set views=?, unlocks=?, score=?
        where variant=?
        """, (views, unlocks, score, variant))

    row = cur.execute("""
    select variant, page_path, views, unlocks, score
    from lp_variants
    order by score desc, unlocks desc, views desc, id asc
    limit 1
    """).fetchone()

    if not row:
        print("no_variant", flush=True)
        con.close()
        return

    variant, page_path, views, unlocks, score = row
    src = ROOT / page_path
    dst = ROOT / "deploy/fortune/pages/index.html"
    shutil.copyfile(src, dst)

    cur.execute("update lp_variants set status='candidate'")
    cur.execute("update lp_variants set status='winner' where variant=?", (variant,))
    con.commit()
    con.close()

    print(f"winner_variant={variant} views={views} unlocks={unlocks} score={score}", flush=True)

if __name__ == "__main__":
    main()
