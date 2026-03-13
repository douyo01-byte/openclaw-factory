import sqlite3, os, time, random
from proposal_diversity_v1 import backlog_count, pick_first_allowed, insert_proposal

DB = os.environ["DB_PATH"]

IDEAS = [
    ("OpenClaw Cache Optimizer", "Improve execution speed with caching strategy", "dev/revenue-cache-opt", "performance", "performance cache spec", 0.82),
    ("Queue Storage Planner", "Queue and storage planning for higher throughput", "dev/revenue-queue-storage", "infrastructure", "queue storage spec", 0.80),
    ("Parallel Execution Planner", "Parallel execution optimization for pipelines", "dev/revenue-parallel-exec", "performance", "parallel execution spec", 0.83),
    ("Worker Scheduler Upgrade", "Worker scheduling and infra balancing", "dev/revenue-worker-scheduler", "infrastructure", "worker scheduler spec", 0.79),
    ("Latency Reduction Pack", "Reduce end-to-end pipeline latency", "dev/revenue-latency-pack", "performance", "latency reduction spec", 0.81),
    ("Migration Safety Layer", "Safer migrations for runtime infrastructure", "dev/revenue-migration-safety", "infrastructure", "migration safety spec", 0.78),
]

while True:
    try:
        conn = sqlite3.connect(DB)
        if backlog_count(conn) < 2:
            pool = IDEAS[:]
            random.shuffle(pool)
            picked, reason = pick_first_allowed(conn, pool, "revenue_brain")
            if picked:
                t, d, b, c, s, conf = picked
                insert_proposal(conn, t, d, b, s, "revenue_brain", "revenue", conf, c)
                conn.commit()
                print(f"revenue generated: {t} [{c}]", flush=True)
            else:
                print(f"revenue skipped: {reason}", flush=True)
        conn.close()
    except Exception as e:
        print(f"revenue error: {e}", flush=True)
    time.sleep(600)
