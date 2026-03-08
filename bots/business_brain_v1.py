import sqlite3, os, time, random
from proposal_diversity_v1 import backlog_count, pick_first_allowed, insert_proposal

DB = os.environ["DB_PATH"]

IDEAS = [
    ("OpenClaw Workflow Automation", "Workflow automation for dev operations", "dev/biz-workflow-auto", "automation", "automation workflow spec", 0.74),
    ("OpenClaw CLI Workspace", "Developer workspace tooling improvements", "dev/biz-cli-workspace", "dev_experience", "developer workspace spec", 0.72),
    ("AI Proposal Assistant", "AI-assisted proposal drafting flow", "dev/biz-ai-proposal", "AI capability", "ai capability spec", 0.76),
    ("OpenClaw Task Orchestrator", "Task orchestration for multi-step operations", "dev/biz-task-orch", "automation", "task orchestration spec", 0.73),
    ("Developer Debug Toolkit", "Debug toolkit for internal developers", "dev/biz-debug-toolkit", "dev_experience", "developer debug spec", 0.71),
    ("LLM Operator Console", "Operator console for AI-driven workflows", "dev/biz-llm-console", "AI capability", "llm operator spec", 0.77),
]

while True:
    try:
        conn = sqlite3.connect(DB)
        if backlog_count(conn) < 2:
            pool = IDEAS[:]
            random.shuffle(pool)
            picked, reason = pick_first_allowed(conn, pool, "business_brain")
            if picked:
                t, d, b, c, s, conf = picked
                insert_proposal(conn, t, d, b, s, "business_brain", "business", conf, c)
                conn.commit()
                print(f"business generated: {t} [{c}]", flush=True)
            else:
                print(f"business skipped: {reason}", flush=True)
        conn.close()
    except Exception as e:
        print(f"business error: {e}", flush=True)
    time.sleep(300)
