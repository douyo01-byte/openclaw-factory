from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MANUAL_DOCS = {
    "README.md",
    "docs/00_INDEX.md",
    "docs/01_SYSTEM_PROMPT.md",
    "docs/02_MASTER_PLAN.md",
    "docs/03_MOTHERSHIP_ROLE.md",
    "docs/05_DEV_RULES.md",
    "docs/07_ROADMAP.md",
    "docs/12_AI_COMPANY.md",
    "docs/17_EFFICIENCY_RULES.md",
}

AUTO_DOCS = {
    "docs/_auto_progress.md",
    "docs/06_CURRENT_STATE.md",
    "docs/08_HANDOVER.md",
    "docs/09_BOT_CATALOG.md",
    "docs/10_DB_SCHEMA.md",
    "docs/11_OPERATIONS.md",
}

def main():
    for x in MANUAL_DOCS:
        p = ROOT / x
        if not p.exists():
            print("missing manual doc:", x)
    for x in AUTO_DOCS:
        p = ROOT / x
        if not p.exists():
            print("missing auto doc:", x)
    overlap = MANUAL_DOCS & AUTO_DOCS
    if overlap:
        raise SystemExit(f"overlap detected: {sorted(overlap)}")
    print("docs guard ok")

if __name__ == "__main__":
    main()
