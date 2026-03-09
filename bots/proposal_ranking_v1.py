from __future__ import annotations

def _norm(x):
    return (x or "").strip().lower()

CATEGORY_BONUS = {
    "automation": 8,
    "infra": 7,
    "infrastructure": 7,
    "revenue": 6,
    "business": 5,
}

TARGET_BONUS = {
    "dev_executor": 5,
    "executor": 5,
    "dev_pr_watcher": 5,
    "watcher": 5,
    "company_dashboard": 4,
    "dashboard": 4,
    "learning": 4,
}

IMPROVEMENT_BONUS = {
    "reliability": 6,
    "stabilize": 6,
    "observability": 5,
    "monitor": 5,
    "performance": 4,
    "optimize": 4,
    "revenue": 3,
    "monetize": 3,
}

def compute_ranking(row):
    quality = int(row["quality_score"] or 0)
    category = _norm(row["category"])
    target = _norm(row["target_system"])
    improvement = _norm(row["improvement_type"])

    cat_bonus = CATEGORY_BONUS.get(category, 0)
    target_bonus = TARGET_BONUS.get(target, 0)
    imp_bonus = IMPROVEMENT_BONUS.get(improvement, 0)

    score = quality + cat_bonus + target_bonus + imp_bonus
    reason = f"quality={quality},category={cat_bonus},target={target_bonus},improvement={imp_bonus}"
    return score, reason
