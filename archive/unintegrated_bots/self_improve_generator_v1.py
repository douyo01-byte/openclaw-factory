import sqlite3, os, time, random
from proposal_diversity_v1 import backlog_count, pick_first_allowed, insert_proposal

DB = os.environ["DB_PATH"]

IDEAS = [
    ("Watcher Recovery Guard", "Improve watcher recovery and restart behavior", "dev/self-watch-recovery", "reliability", "watcher recovery spec", 0.90),
    ("Decision Feedback Loop", "Strengthen learning feedback from outcomes", "dev/self-decision-feedback", "learning", "decision feedback spec", 0.92),
    ("Executor Stability Guard", "Improve executor safety and stability", "dev/self-exec-stability", "reliability", "executor stability spec", 0.91),
    ("Pattern Learning Refresh", "Refresh learning patterns from recent results", "dev/self-pattern-refresh", "learning", "pattern refresh spec", 0.93),
    ("Self Healing Retry Rules", "Refine retry rules for daemon reliability", "dev/self-healing-retry", "reliability", "retry rules spec", 0.89),
    ("Learning Score Calibrator", "Calibrate learning score updates", "dev/self-score-calib", "learning", "learning score calibration spec", 0.94),
]

while True:
    try:
        conn = sqlite3.connect(DB)
        if backlog_count(conn) < 2:
            pool = IDEAS[:]
            random.shuffle(pool)
            picked, reason = pick_first_allowed(conn, pool, "self_improve")
            if picked:
                t, d, b, c, s, conf = picked
                insert_proposal(conn, t, d, b, s, "self_improve", "internal", conf, c)
                conn.commit()
                print(f"self_improve generated: {t} [{c}]", flush=True)
            else:
                print(f"self_improve skipped: {reason}", flush=True)
        conn.close()
    except Exception as e:
        print(f"self_improve error: {e}", flush=True)
    time.sleep(120)
