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
    title = (row["title"] or "").lower()
    category = (row["category"] or "").lower()
    target = (row["target_system"] or "").lower()
    impact = "medium"
    complexity = "medium"
    risk = "medium"
    system_importance = "medium"

    if category in ("automation", "reliability", "performance") or target in ("core", "codebase", "dev_pr_watcher", "learning", "executor"):
        score += 6
        impact = "high"

    if "safety" in title or "guard" in title or "stability" in title or "retry" in title or "recovery" in title:
        score += 6
        system_importance = "high"

    if "refactor" in title or "logging" in title:
        complexity = "low"

    if "revenue" in title or category == "revenue":
        risk = "high"

    reason = f"{reason},impact={impact},complexity={complexity},risk={risk},system={system_importance}"
    title = (row["title"] or "").lower()
    category = (row["category"] or "").lower()
    target = (row["target_system"] or "").lower()
    impact = "medium"
    complexity = "medium"
    risk = "medium"
    system_importance = "medium"

    if category in ("automation", "reliability", "performance") or target in ("core", "codebase", "dev_pr_watcher", "learning", "executor"):
        score += 6
        impact = "high"

    if "safety" in title or "guard" in title or "stability" in title or "retry" in title or "recovery" in title:
        score += 6
        system_importance = "high"

    if "refactor" in title or "logging" in title:
        complexity = "low"

    if "revenue" in title or category == "revenue":
        risk = "high"

    reason = f"{reason},impact={impact},complexity={complexity},risk={risk},system={system_importance}"
    return score, reason
