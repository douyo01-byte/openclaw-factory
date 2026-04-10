import os
import sqlite3
from pathlib import Path
import shutil

DB_PATH = os.environ.get("DB_PATH", os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))
ROOT = Path(os.path.expanduser("~/AI/openclaw-factory-daemon"))

def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    row = cur.execute("""
    select variant, page_path, views, unlocks,
           case when views > 0 then cast(unlocks as float)/views else 0 end as cv
    from lp_variants
    order by cv desc, unlocks desc, id asc
    limit 1
    """).fetchone()

    if not row:
        print("no_variant", flush=True)
        return

    variant, page_path, views, unlocks, cv = row
    src = ROOT / page_path
    dst = ROOT / "deploy/fortune/pages/index.html"
    shutil.copyfile(src, dst)

    cur.execute("update lp_variants set status='candidate'")
    cur.execute("update lp_variants set status='winner' where variant=?", (variant,))
    con.commit()
    con.close()
    print(f"winner_variant={variant} cv={cv}", flush=True)

if __name__ == "__main__":
    main()
