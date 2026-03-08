import sqlite3, os, time, random
from proposal_diversity_v1 import backlog_count, pick_first_allowed, insert_proposal

DB = os.environ["DB_PATH"]

IDEAS = [
    ("OpenClaw Metrics Dashboard", "Metrics and visibility dashboard", "dev/market-metrics-dashboard", "telemetry", "telemetry dashboard spec", 0.66),
    ("Cost Drift Monitor", "Monitor cost drift in recurring operations", "dev/market-cost-drift", "cost", "cost monitoring spec", 0.64),
    ("Security Signal Monitor", "Detect suspicious operational patterns", "dev/market-security-signal", "security", "security monitoring spec", 0.67),
    ("Trace Viewer", "Trace viewer for proposal pipeline activity", "dev/market-trace-viewer", "telemetry", "trace viewer spec", 0.65),
    ("Usage Efficiency Analyzer", "Analyze cost and usage efficiency", "dev/market-usage-eff", "cost", "usage efficiency spec", 0.63),
    ("Permission Audit Assistant", "Audit helper for permissions and access", "dev/market-perm-audit", "security", "permission audit spec", 0.68),
]

def trending_score():
    return random.random() > 0.35

while True:
    try:
        conn = sqlite3.connect(DB)
        if backlog_count(conn) < 2 and trending_score():
            pool = IDEAS[:]
            random.shuffle(pool)
            picked, reason = pick_first_allowed(conn, pool, "market_brain")
            if picked:
                t, d, b, c, s, conf = picked
                insert_proposal(conn, t, d, b, s, "market_brain", "market", conf, c)
                conn.commit()
                print(f"market generated: {t} [{c}]", flush=True)
            else:
                print(f"market skipped: {reason}", flush=True)
        conn.close()
    except Exception as e:
        print(f"market error: {e}", flush=True)
    time.sleep(600)
