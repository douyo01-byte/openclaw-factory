#!/usr/bin/env python3
import json
import sqlite3
import subprocess
from pathlib import Path
import os

DB_PATH = os.environ.get(
    "DB_PATH",
    str(Path.home() / "AI/openclaw-factory/data/openclaw.db")
)

SQL = """
select
  path,
  count(*) as views
from revenue_page_views
group by path
order by views desc
limit 100;
"""

def run():
    cmd = [
        "npx",
        "wrangler",
        "d1",
        "execute",
        "openclaw-fortune-db",
        "--remote",
        "--json",
        "--command",
        SQL
    ]

    p = subprocess.run(
        cmd,
        cwd=str(Path.home() / "AI/openclaw-factory-daemon/deploy/fortune/worker"),
        capture_output=True,
        text=True
    )

    print(p.stdout)

if __name__ == "__main__":
    run()
