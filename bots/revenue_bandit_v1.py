#!/usr/bin/env python3
import os
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get(
    "DB_PATH",
    str(Path.home() / "AI/openclaw-factory/data/openclaw.db")
)

MIN_SCORE_TO_JUDGE = float(os.environ.get("REVENUE_BANDIT_MIN_SCORE", "1"))
HORIZON_WEIGHTS = {
    "short_term": {
        "ctr_score": 0.45,
        "conversion_score": 0.35,
        "approval_score": 0.05,
        "revenue_efficiency": 0.10,
        "automation_score": 0.05,
        "sustainability_score": 0.00,
    },
    "mid_term": {
        "ctr_score": 0.20,
        "conversion_score": 0.35,
        "approval_score": 0.15,
        "revenue_efficiency": 0.15,
        "automation_score": 0.10,
        "sustainability_score": 0.05,
    },
    "long_term": {
        "ctr_score": 0.10,
        "conversion_score": 0.25,
        "approval_score": 0.20,
        "revenue_efficiency": 0.15,
        "automation_score": 0.15,
        "sustainability_score": 0.15,
    },
}
RANKING_HORIZON_WEIGHTS = {"short_term": 0.45, "mid_term": 0.35, "long_term": 0.20}
PROFIT_EFFICIENCY_WEIGHT = 80.0
PORTFOLIO_EFFICIENCY_WEIGHT = 60.0

def con():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def has_table(db, name: str) -> bool:
    row = db.execute(
        "select 1 from sqlite_master where type='table' and name=?",
        (name,)
    ).fetchone()
    return row is not None

def table_cols(db, name: str) -> set[str]:
    if not has_table(db, name):
        return set()
    return {r["name"] for r in db.execute(f"pragma table_info({name})").fetchall()}

REQUIRED_SCHEMA = {
    "revenue_opportunities": {
        "id", "source", "domain_key", "title", "description", "market",
        "monetization_type", "expected_profit_score", "validation_speed_score",
        "cost_score", "automation_score", "risk_score", "total_score",
        "status", "rationale", "created_at", "updated_at",
    },
    "revenue_variant_groups": {
        "id", "opportunity_id", "experiment_id", "name", "strategy", "status",
        "winner_experiment_id", "digest_summary", "created_at", "updated_at",
    },
    "revenue_variant_metrics": {
        "id", "group_id", "experiment_id", "variant_key", "artifact_path",
        "views", "clicks", "telegram_clicks", "actions", "conversions",
        "ctr", "cvr", "score", "rank", "status", "source", "captured_at",
    },
    "revenue_variant_loser_archive": {
        "id", "group_id", "experiment_id", "variant_key", "artifact_path",
        "score", "reason", "archived_at",
    },
    "revenue_bandit_digests": {
        "id", "group_id", "summary", "sent_to_telegram", "created_at",
    },
    "revenue_distribution_tasks": {
        "id", "group_id", "experiment_id", "variant_key", "distribution_type",
        "traffic_source", "cta_url", "content", "artifact_path", "status",
        "created_at", "updated_at",
    },
    "revenue_distribution_publish_queue": {
        "id", "distribution_task_id", "group_id", "experiment_id", "variant_key",
        "distribution_type", "traffic_source", "artifact_path",
        "candidate_score", "publish_status", "approval_note", "queued_at",
        "updated_at",
    },
    "revenue_memory_patterns": {
        "id", "memory_type", "pattern", "horizon_type", "economic_summary",
        "portfolio_summary", "domain_summary", "evidence", "score",
        "reuse_count", "last_used_at", "created_at", "updated_at",
    },
    "revenue_strategy_scores": {
        "id", "group_id", "experiment_id", "horizon_type", "ctr_score",
        "conversion_score", "approval_score", "revenue_efficiency",
        "automation_score", "sustainability_score", "total_score", "source",
        "captured_at",
    },
    "revenue_economic_metrics": {
        "id", "group_id", "experiment_id", "estimated_cac", "estimated_ltv",
        "payback_speed", "infra_cost", "human_cost", "automation_savings",
        "expected_profit", "profit_efficiency", "economic_multiplier",
        "suppressed", "source", "captured_at",
    },
    "revenue_real_orders": {
        "id", "group_id", "experiment_id", "variant_key", "order_id",
        "revenue", "gross_profit", "refund_risk", "fulfillment_cost",
        "support_cost", "net_profit", "recovered_days", "source",
        "created_at",
    },
    "revenue_capital_allocations": {
        "id", "opportunity_id", "allocated_budget", "allocated_compute",
        "allocated_time", "expected_roi", "realized_roi", "capital_score",
        "risk_score", "liquidity_score", "source", "updated_at",
    },
    "revenue_business_domains": {
        "id", "domain_key", "domain_type", "capital_allocated",
        "revenue_generated", "net_profit", "volatility_score",
        "scalability_score", "automation_fit", "moat_score", "source",
        "updated_at",
    },
    "revenue_capital_migrations": {
        "id", "from_domain", "to_domain", "migration_reason",
        "migrated_budget", "migrated_compute", "expected_gain",
        "realized_gain", "migration_score", "source", "created_at",
    },
}

def require_schema(db):
    for table, required in REQUIRED_SCHEMA.items():
        missing = sorted(required - table_cols(db, table))
        if missing:
            raise RuntimeError(
                f"schema_missing table={table} cols={','.join(missing)} "
                "apply migrations/20260513_revenue_core_schema_v2.sql first"
            )

def ensure_schema(db):
    require_schema(db)
    db.execute("""
        update revenue_memory_patterns
        set score=score * 0.85,
            updated_at=datetime('now')
        where horizon_type='short_term'
          and coalesce(nullif(last_used_at, ''), created_at) < datetime('now', '-14 days')
    """)
    db.execute("""
        update revenue_memory_patterns
        set score=score * 0.95,
            updated_at=datetime('now')
        where horizon_type='mid_term'
          and coalesce(nullif(last_used_at, ''), created_at) < datetime('now', '-30 days')
    """)
    db.execute("""
        update revenue_memory_patterns
        set score=score * 0.98,
            updated_at=datetime('now')
        where horizon_type='long_term'
          and coalesce(nullif(last_used_at, ''), created_at) < datetime('now', '-60 days')
    """)

def metric_value(db, experiment_id: int, names: tuple[str, ...]) -> float:
    if not has_table(db, "revenue_metrics"):
        return 0.0
    placeholders = ",".join("?" for _ in names)
    row = db.execute(f"""
        select coalesce(sum(metric_value), 0) as value
        from revenue_metrics
        where experiment_id=?
          and metric_name in ({placeholders})
    """, (experiment_id, *names)).fetchone()
    return float(row["value"] or 0)

def event_count(db, artifact_path: str, event_type: str) -> int:
    if not artifact_path or not has_table(db, "revenue_page_views"):
        return 0
    if "event_type" not in table_cols(db, "revenue_page_views"):
        if event_type != "page_view":
            return 0
        row = db.execute("""
            select count(*) as value
            from revenue_page_views
            where path=?
               or path like ?
        """, (artifact_path, f"%{Path(artifact_path).name}")).fetchone()
        return int(row["value"] or 0)
    row = db.execute("""
        select count(*) as value
        from revenue_page_views
        where event_type=?
          and (
            path=?
            or path like ?
          )
    """, (event_type, artifact_path, f"%{Path(artifact_path).name}")).fetchone()
    return int(row["value"] or 0)

def source_ctr_rows(db, artifact_path: str):
    if not artifact_path or not has_table(db, "revenue_page_views"):
        return []
    cols = table_cols(db, "revenue_page_views")
    if "event_type" not in cols or "traffic_source" not in cols:
        return []
    rows = db.execute("""
        select
          coalesce(traffic_source, '') as traffic_source,
          sum(case when event_type='page_view' then 1 else 0 end) as views,
          sum(case when event_type='cta_click' then 1 else 0 end) as clicks
        from revenue_page_views
        where path=?
           or path like ?
        group by coalesce(traffic_source, '')
        order by clicks desc, views desc, traffic_source asc
        limit 5
    """, (artifact_path, f"%{Path(artifact_path).name}")).fetchall()
    out = []
    for r in rows:
        views = int(r["views"] or 0)
        clicks = int(r["clicks"] or 0)
        out.append({
            "source": r["traffic_source"] or "direct",
            "views": views,
            "clicks": clicks,
            "ctr": clicks / views if views else 0.0,
        })
    return out

def approval_stats(db, group_id: int, experiment_id: int) -> tuple[int, int]:
    if not has_table(db, "revenue_distribution_publish_queue"):
        return 0, 0
    row = db.execute("""
        select
          count(*) as total,
          sum(case when publish_status='approved' then 1 else 0 end) as approved
        from revenue_distribution_publish_queue
        where group_id=?
          and experiment_id=?
    """, (group_id, experiment_id)).fetchone()
    return int(row["approved"] or 0), int(row["total"] or 0)

def generated_distribution_count(db, group_id: int, experiment_id: int) -> int:
    if not has_table(db, "revenue_distribution_tasks"):
        return 0
    row = db.execute("""
        select count(*) as value
        from revenue_distribution_tasks
        where group_id=?
          and experiment_id=?
          and coalesce(artifact_path, '') != ''
    """, (group_id, experiment_id)).fetchone()
    return int(row["value"] or 0)

def bounded(value: float, limit: float = 100.0) -> float:
    return max(0.0, min(limit, float(value or 0)))

def real_order_feedback(db, group_id: int, experiment_id: int) -> dict[str, float]:
    if not has_table(db, "revenue_real_orders"):
        return {
            "order_count": 0,
            "revenue": 0.0,
            "gross_profit": 0.0,
            "net_profit": 0.0,
            "refund_risk": 0.0,
            "recovered_days": 0.0,
        }
    row = db.execute("""
        select
          count(*) as order_count,
          coalesce(sum(revenue), 0) as revenue,
          coalesce(sum(gross_profit), 0) as gross_profit,
          coalesce(sum(net_profit), 0) as net_profit,
          coalesce(avg(refund_risk), 0) as refund_risk,
          coalesce(avg(recovered_days), 0) as recovered_days
        from revenue_real_orders
        where group_id=?
          and experiment_id=?
    """, (group_id, experiment_id)).fetchone()
    return {
        "order_count": int(row["order_count"] or 0),
        "revenue": float(row["revenue"] or 0),
        "gross_profit": float(row["gross_profit"] or 0),
        "net_profit": float(row["net_profit"] or 0),
        "refund_risk": float(row["refund_risk"] or 0),
        "recovered_days": float(row["recovered_days"] or 0),
    }

def sync_economic_metrics(db, group_id: int, metrics: dict) -> dict[str, float]:
    generated = generated_distribution_count(db, group_id, metrics["experiment_id"])
    real = real_order_feedback(db, group_id, metrics["experiment_id"])
    infra_cost = metric_value(db, metrics["experiment_id"], ("infra_cost",))
    if infra_cost <= 0:
        infra_cost = metrics["views"] * 0.01 + generated * 0.05
    human_cost = metric_value(db, metrics["experiment_id"], ("human_cost",))
    automation_savings = metric_value(db, metrics["experiment_id"], ("automation_savings",))
    if automation_savings <= 0:
        automation_savings = generated * 2.0
    estimated_ltv = metric_value(db, metrics["experiment_id"], ("estimated_ltv", "ltv"))
    if estimated_ltv <= 0:
        estimated_ltv = metrics["conversions"] * 120.0 + metrics["telegram_clicks"] * 4.0 + metrics["clicks"] * 1.5
    if real["order_count"] > 0:
        estimated_ltv = real["revenue"] / real["order_count"]

    paid_acquisition = metric_value(db, metrics["experiment_id"], ("paid_acquisition_cost", "ad_cost"))
    total_cost = infra_cost + human_cost + paid_acquisition
    estimated_cac = total_cost / max(metrics["conversions"], 1)
    payback_speed = estimated_ltv / max(estimated_cac, 1.0)
    expected_profit = estimated_ltv + automation_savings - total_cost
    if real["order_count"] > 0:
        expected_profit = real["net_profit"] + automation_savings - total_cost
        payback_speed = 999.0 if real["recovered_days"] <= 0 and real["net_profit"] > 0 else max(0.0, 30.0 / max(real["recovered_days"], 1.0))
    profit_efficiency = expected_profit / max(total_cost, 1.0)
    economic_multiplier = 0.25 if expected_profit < 0 else min(1.6, 1.0 + profit_efficiency * 0.05)
    if real["net_profit"] < 0:
        economic_multiplier = 0.10
    suppressed = 1 if expected_profit < 0 or real["net_profit"] < 0 else 0

    out = {
        "real_order_count": real["order_count"],
        "real_revenue": real["revenue"],
        "real_gross_profit": real["gross_profit"],
        "real_net_profit": real["net_profit"],
        "real_refund_risk": real["refund_risk"],
        "real_recovered_days": real["recovered_days"],
        "estimated_cac": estimated_cac,
        "estimated_ltv": estimated_ltv,
        "payback_speed": payback_speed,
        "infra_cost": infra_cost,
        "human_cost": human_cost,
        "automation_savings": automation_savings,
        "expected_profit": expected_profit,
        "profit_efficiency": profit_efficiency,
        "economic_multiplier": economic_multiplier,
        "suppressed": suppressed,
    }
    db.execute("""
        insert into revenue_economic_metrics
        (
          group_id,
          experiment_id,
          estimated_cac,
          estimated_ltv,
          payback_speed,
          infra_cost,
          human_cost,
          automation_savings,
          expected_profit,
          profit_efficiency,
          economic_multiplier,
          suppressed,
          source,
          captured_at
        )
        values
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'bandit_sync', datetime('now'))
        on conflict(group_id, experiment_id) do update set
          estimated_cac=excluded.estimated_cac,
          estimated_ltv=excluded.estimated_ltv,
          payback_speed=excluded.payback_speed,
          infra_cost=excluded.infra_cost,
          human_cost=excluded.human_cost,
          automation_savings=excluded.automation_savings,
          expected_profit=excluded.expected_profit,
          profit_efficiency=excluded.profit_efficiency,
          economic_multiplier=excluded.economic_multiplier,
          suppressed=excluded.suppressed,
          source=excluded.source,
          captured_at=datetime('now')
    """, (
        group_id,
        metrics["experiment_id"],
        out["estimated_cac"],
        out["estimated_ltv"],
        out["payback_speed"],
        out["infra_cost"],
        out["human_cost"],
        out["automation_savings"],
        out["expected_profit"],
        out["profit_efficiency"],
        out["economic_multiplier"],
        out["suppressed"],
    ))
    return out

def capital_allocation(db, opportunity_id: int) -> sqlite3.Row:
    row = db.execute("""
        select *
        from revenue_capital_allocations
        where opportunity_id=?
    """, (opportunity_id,)).fetchone()
    if row:
        return row
    db.execute("""
        insert into revenue_capital_allocations
        (
          opportunity_id,
          allocated_budget,
          allocated_compute,
          allocated_time,
          expected_roi,
          realized_roi,
          capital_score,
          risk_score,
          liquidity_score,
          source,
          updated_at
        )
        values
        (?, 10, 1, 1, 1, 0, 50, 20, 80, 'auto_default', datetime('now'))
    """, (opportunity_id,))
    return db.execute("""
        select *
        from revenue_capital_allocations
        where opportunity_id=?
    """, (opportunity_id,)).fetchone()

def opportunity_domain_key(db, opportunity_id: int) -> str:
    if not has_table(db, "revenue_opportunities") or "domain_key" not in table_cols(db, "revenue_opportunities"):
        return "general"
    row = db.execute("""
        select coalesce(nullif(domain_key, ''), 'general') as domain_key
        from revenue_opportunities
        where id=?
    """, (opportunity_id,)).fetchone()
    return row["domain_key"] if row else "general"

def business_domain(db, opportunity_id: int) -> sqlite3.Row:
    domain_key = opportunity_domain_key(db, opportunity_id)
    row = db.execute("""
        select *
        from revenue_business_domains
        where domain_key=?
    """, (domain_key,)).fetchone()
    if row:
        return row
    db.execute("""
        insert into revenue_business_domains
        (domain_key, domain_type, scalability_score, automation_fit, moat_score, volatility_score, source, updated_at)
        values
        (?, 'general', 50, 50, 10, 30, 'auto_default', datetime('now'))
    """, (domain_key,))
    return db.execute("""
        select *
        from revenue_business_domains
        where domain_key=?
    """, (domain_key,)).fetchone()

def sync_domain_intelligence(db, opportunity_id: int, economics: dict, allocation: dict) -> dict[str, float | str]:
    domain = business_domain(db, opportunity_id)
    volatility = float(domain["volatility_score"] or 0)
    scalability = float(domain["scalability_score"] or 0)
    automation_fit = float(domain["automation_fit"] or 0)
    moat = float(domain["moat_score"] or 0)
    domain_score = bounded(scalability * 0.30 + automation_fit * 0.35 + moat * 0.20 + (100 - volatility) * 0.15, 150)
    domain_multiplier = max(0.1, min(1.6, 0.5 + domain_score / 100))
    if volatility >= 80:
        domain_multiplier = 0.20
    elif automation_fit >= 80:
        domain_multiplier = min(1.8, domain_multiplier + 0.25)
    capital_allocated = max(float(domain["capital_allocated"] or 0), float(allocation.get("allocated_budget") or 0))
    revenue_generated = max(float(domain["revenue_generated"] or 0), float(economics.get("real_revenue") or 0))
    net_profit = max(float(domain["net_profit"] or 0), float(economics.get("real_net_profit") or 0))
    db.execute("""
        update revenue_business_domains
        set capital_allocated=?,
            revenue_generated=?,
            net_profit=?,
            updated_at=datetime('now')
        where id=?
    """, (capital_allocated, revenue_generated, net_profit, domain["id"]))
    simulate_capital_migration(db)
    return {
        "domain_key": domain["domain_key"],
        "domain_type": domain["domain_type"],
        "domain_score": domain_score,
        "domain_multiplier": domain_multiplier,
        "volatility_score": volatility,
        "scalability_score": scalability,
        "automation_fit": automation_fit,
        "moat_score": moat,
        "suppressed": 1 if volatility >= 80 else 0,
    }

def domain_momentum(domain) -> float:
    capital = max(float(domain["capital_allocated"] or 0), 1.0)
    return (
        (float(domain["net_profit"] or 0) / capital) * 60
        + (float(domain["revenue_generated"] or 0) / capital) * 15
        + float(domain["scalability_score"] or 0) * 0.25
        + float(domain["automation_fit"] or 0) * 0.25
        + float(domain["moat_score"] or 0) * 0.15
        - float(domain["volatility_score"] or 0) * 0.35
    )

def simulate_capital_migration(db):
    rows = db.execute("select * from revenue_business_domains").fetchall()
    if len(rows) < 2:
        return
    scored = [(r, domain_momentum(r)) for r in rows]
    declining = sorted(
        [x for x in scored if x[1] < 35 or float(x[0]["volatility_score"] or 0) >= 80],
        key=lambda x: (x[1], -float(x[0]["volatility_score"] or 0), x[0]["domain_key"]),
    )
    accelerating = sorted(
        [x for x in scored if x[1] >= 35 and float(x[0]["automation_fit"] or 0) >= 60],
        key=lambda x: (-x[1], -float(x[0]["automation_fit"] or 0), x[0]["domain_key"]),
    )
    if not declining or not accelerating:
        return
    from_domain, from_momentum = declining[0]
    to_domain, to_momentum = accelerating[0]
    if from_domain["domain_key"] == to_domain["domain_key"]:
        return
    migrated_budget = max(1.0, float(from_domain["capital_allocated"] or 0) * 0.15)
    migrated_compute = max(0.25, migrated_budget / 25)
    stagnation_penalty = max(0.0, 35 - from_momentum)
    expected_gain = max(0.0, to_momentum - from_momentum) * migrated_budget / 100
    realized_gain = float(to_domain["net_profit"] or 0) - float(from_domain["net_profit"] or 0)
    migration_score = expected_gain + stagnation_penalty + max(0.0, to_momentum - from_momentum)
    db.execute("""
        insert into revenue_capital_migrations
        (
          from_domain,
          to_domain,
          migration_reason,
          migrated_budget,
          migrated_compute,
          expected_gain,
          realized_gain,
          migration_score,
          source,
          created_at
        )
        values
        (?, ?, 'declining_to_accelerating_domain', ?, ?, ?, ?, ?, 'local_simulation', datetime('now'))
        on conflict(from_domain, to_domain, migration_reason) do update set
          migrated_budget=excluded.migrated_budget,
          migrated_compute=excluded.migrated_compute,
          expected_gain=excluded.expected_gain,
          realized_gain=excluded.realized_gain,
          migration_score=excluded.migration_score,
          created_at=datetime('now')
    """, (
        from_domain["domain_key"],
        to_domain["domain_key"],
        migrated_budget,
        migrated_compute,
        expected_gain,
        realized_gain,
        migration_score,
    ))

def sync_capital_allocation(db, group, economics: dict) -> dict[str, float]:
    allocation = capital_allocation(db, int(group["opportunity_id"] or 0))
    budget = float(allocation["allocated_budget"] or 0)
    compute = float(allocation["allocated_compute"] or 0)
    allocated_time = float(allocation["allocated_time"] or 0)
    liquidity_score = float(allocation["liquidity_score"] or 0)
    risk_score = float(allocation["risk_score"] or 0)
    expected_profit = float(economics["expected_profit"] or 0)
    realized_roi = expected_profit / max(budget + compute + allocated_time, 1.0)
    payback = float(economics["payback_speed"] or 0)
    capital_score = bounded(realized_roi * 50 + payback * 2 + liquidity_score - risk_score, 150)
    portfolio_multiplier = max(0.1, min(1.5, 0.6 + capital_score / 100))
    if liquidity_score < 20:
        portfolio_multiplier = 0.15
    suppressed = 1 if liquidity_score < 20 else 0
    db.execute("""
        update revenue_capital_allocations
        set realized_roi=?,
            capital_score=?,
            updated_at=datetime('now')
        where id=?
    """, (realized_roi, capital_score, allocation["id"]))
    return {
        "allocated_budget": budget,
        "allocated_compute": compute,
        "allocated_time": allocated_time,
        "expected_roi": float(allocation["expected_roi"] or 0),
        "realized_roi": realized_roi,
        "capital_score": capital_score,
        "risk_score": risk_score,
        "liquidity_score": liquidity_score,
        "portfolio_multiplier": portfolio_multiplier,
        "suppressed": suppressed,
    }

def sync_strategy_scores(db, group_id: int, metrics: dict, economics: dict) -> dict[str, float]:
    approved, approval_total = approval_stats(db, group_id, metrics["experiment_id"])
    approval_rate = approved / approval_total if approval_total else 0.0
    generated = generated_distribution_count(db, group_id, metrics["experiment_id"])
    categories = {
        "ctr_score": bounded(metrics["ctr"] * 1000),
        "conversion_score": bounded(metrics["conversions"] * 80 + metrics["cvr"] * 1000),
        "approval_score": bounded(approval_rate * 100),
        "revenue_efficiency": bounded((metrics["conversions"] * 1000) / max(metrics["views"], 1)),
        "automation_score": bounded(generated * 20),
        "sustainability_score": bounded(
            metrics["cvr"] * 500
            + metrics["telegram_clicks"] * 6
            + approved * 15
            + metrics["views"] * 0.25
        ),
    }
    totals = {}
    for horizon_type, weights in HORIZON_WEIGHTS.items():
        total = sum(categories[name] * weight for name, weight in weights.items())
        total *= economics["economic_multiplier"]
        totals[horizon_type] = total
        db.execute("""
            insert into revenue_strategy_scores
            (
              group_id,
              experiment_id,
              horizon_type,
              ctr_score,
              conversion_score,
              approval_score,
              revenue_efficiency,
              automation_score,
              sustainability_score,
              total_score,
              source,
              captured_at
            )
            values
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'bandit_sync', datetime('now'))
            on conflict(group_id, experiment_id, horizon_type) do update set
              ctr_score=excluded.ctr_score,
              conversion_score=excluded.conversion_score,
              approval_score=excluded.approval_score,
              revenue_efficiency=excluded.revenue_efficiency,
              automation_score=excluded.automation_score,
              sustainability_score=excluded.sustainability_score,
              total_score=excluded.total_score,
              source=excluded.source,
              captured_at=datetime('now')
        """, (
            group_id,
            metrics["experiment_id"],
            horizon_type,
            categories["ctr_score"],
            categories["conversion_score"],
            categories["approval_score"],
            categories["revenue_efficiency"],
            categories["automation_score"],
            categories["sustainability_score"],
            total,
        ))
    totals["ranking_bonus"] = sum(
        totals[horizon] * weight for horizon, weight in RANKING_HORIZON_WEIGHTS.items()
    )
    return totals

def sync_metrics(db, group_id: int):
    group = db.execute("""
        select *
        from revenue_variant_groups
        where id=?
    """, (group_id,)).fetchone()
    rows = db.execute("""
        select
          vm.group_id,
          vm.experiment_id,
          vm.variant_key,
          e.artifact_path
        from revenue_variant_metrics vm
        join revenue_experiments e on e.id = vm.experiment_id
        where vm.group_id=?
    """, (group_id,)).fetchall()

    synced = []
    for r in rows:
        views = event_count(db, r["artifact_path"], "page_view")
        clicks = event_count(db, r["artifact_path"], "cta_click")
        telegram_clicks = event_count(db, r["artifact_path"], "telegram_click")
        event_conversions = event_count(db, r["artifact_path"], "conversion")
        actions = int(metric_value(db, r["experiment_id"], ("action", "actions", "cta", "cta_click")))
        conversions = event_conversions + int(metric_value(db, r["experiment_id"], ("conversion", "conversions", "cv")))
        artifact_score = metric_value(db, r["experiment_id"], ("artifact_score",))
        ctr = clicks / views if views else 0.0
        cvr = conversions / views if views else 0.0
        score = conversions * 1000 + telegram_clicks * 120 + clicks * 60 + actions * 30 + views + artifact_score * 0.2
        metrics = {
            "experiment_id": int(r["experiment_id"]),
            "variant_key": r["variant_key"],
            "artifact_path": r["artifact_path"] or "",
            "views": views,
            "clicks": clicks,
            "telegram_clicks": telegram_clicks,
            "actions": actions,
            "real_conversions": event_conversions,
            "conversions": conversions,
            "ctr": ctr,
            "cvr": cvr,
            "score": score,
        }
        economics = sync_economic_metrics(db, group_id, metrics)
        horizons = sync_strategy_scores(db, group_id, metrics, economics)
        profit_bonus = max(-200.0, min(200.0, economics["profit_efficiency"] * PROFIT_EFFICIENCY_WEIGHT))
        capital = sync_capital_allocation(db, group, economics) if group else {
            "portfolio_multiplier": 1.0,
            "realized_roi": 0.0,
            "capital_score": 0.0,
            "risk_score": 0.0,
            "liquidity_score": 100.0,
            "suppressed": 0,
        }
        portfolio_bonus = max(-150.0, min(150.0, capital["realized_roi"] * PORTFOLIO_EFFICIENCY_WEIGHT))
        metrics["horizon_totals"] = horizons
        metrics["economics"] = economics
        metrics["capital"] = capital
        domain = sync_domain_intelligence(db, int(group["opportunity_id"] or 0), economics, capital) if group else {
            "domain_multiplier": 1.0,
            "domain_score": 0.0,
            "domain_key": "general",
            "domain_type": "general",
            "volatility_score": 0.0,
            "scalability_score": 50.0,
            "automation_fit": 50.0,
            "moat_score": 0.0,
            "suppressed": 0,
        }
        metrics["domain"] = domain
        metrics["score"] = (
            score
            + horizons["ranking_bonus"]
            + profit_bonus
            + portfolio_bonus
        ) * economics["economic_multiplier"] * capital["portfolio_multiplier"] * domain["domain_multiplier"]
        synced.append(metrics)

    ranked = sorted(synced, key=lambda x: (-x["score"], x["experiment_id"]))
    for idx, r in enumerate(ranked, start=1):
        db.execute("""
            update revenue_variant_metrics
            set artifact_path=?,
                views=?,
                clicks=?,
                telegram_clicks=?,
                actions=?,
                conversions=?,
                ctr=?,
                cvr=?,
                score=?,
                rank=?,
                source='bandit_sync',
                captured_at=datetime('now')
            where group_id=?
              and experiment_id=?
        """, (
            r["artifact_path"],
            r["views"],
            r["clicks"],
            r["telegram_clicks"],
            r["actions"],
            r["conversions"],
            r["ctr"],
            r["cvr"],
            r["score"],
            idx,
            group_id,
            r["experiment_id"],
        ))
    return ranked

def create_challenger(db, group, winner) -> int:
    existing = db.execute("""
        select id
        from revenue_experiments
        where opportunity_id=?
          and experiment_type='lp_challenger'
          and title like ?
        limit 1
    """, (group["opportunity_id"], f"%group {group['id']}%")).fetchone()
    if existing:
        return int(existing["id"])

    cur = db.execute("""
        insert into revenue_experiments
        (
          opportunity_id,
          experiment_type,
          title,
          hypothesis,
          validation_method,
          expected_signal,
          status,
          created_at,
          updated_at
        )
        values
        (?, 'lp_challenger', ?, 'winner LPを基準にCTA/証拠/Telegram導線を1点だけ強化する', 'bandit challenger', 'winner score uplift', 'routed', datetime('now'), datetime('now'))
    """, (
        group["opportunity_id"],
        f"challenger for bandit group {group['id']}",
    ))
    challenger_exp_id = cur.lastrowid
    task_text = f"""[EXEC]
script=run_python.sh
arg=mode=lpgen_exec;task=[REVENUE_CHALLENGER] group_id={group['id']} winner_experiment_id={winner['experiment_id']} winner_variant={winner['variant_key']} artifact={winner['artifact_path']} の改善版LPを1本だけ生成する
"""
    db.execute("""
        insert into router_tasks
        (
          target_bot,
          mode,
          status,
          task_text,
          created_at,
          updated_at
        )
        values
        ('ops_exec', 'EXEC', 'new', ?, datetime('now'), datetime('now'))
    """, (task_text,))
    return challenger_exp_id

def add_memory(db, memory_type: str, pattern: str, evidence: str, score: float, horizon_type: str = "mid_term", economic_summary: str = "", portfolio_summary: str = "", domain_summary: str = ""):
    pattern = " ".join((pattern or "").split()).strip()[:240]
    if not pattern:
        return
    if horizon_type not in HORIZON_WEIGHTS:
        horizon_type = "mid_term"
    db.execute("""
        insert into revenue_memory_patterns
        (memory_type, pattern, horizon_type, economic_summary, portfolio_summary, domain_summary, evidence, score, reuse_count, created_at, updated_at)
        values
        (?, ?, ?, ?, ?, ?, ?, ?, 0, datetime('now'), datetime('now'))
        on conflict(memory_type, pattern) do update set
          horizon_type=excluded.horizon_type,
          economic_summary=excluded.economic_summary,
          portfolio_summary=excluded.portfolio_summary,
          domain_summary=excluded.domain_summary,
          evidence=excluded.evidence,
          score=max(revenue_memory_patterns.score, excluded.score),
          updated_at=datetime('now')
    """, (memory_type, pattern, horizon_type, economic_summary[:240], portfolio_summary[:240], domain_summary[:240], evidence, score))

def extract_winner_memory(db, group, winner):
    exp = db.execute("""
        select title, hypothesis, artifact_path
        from revenue_experiments
        where id=?
    """, (winner["experiment_id"],)).fetchone()
    if not exp:
        return
    economics = winner.get("economics") or {}
    economic_summary = (
        f"profit={float(economics.get('expected_profit') or 0):.1f} "
        f"real_profit={float(economics.get('real_net_profit') or 0):.1f} "
        f"orders={int(economics.get('real_order_count') or 0)} "
        f"ltv={float(economics.get('estimated_ltv') or 0):.1f} "
        f"cac={float(economics.get('estimated_cac') or 0):.1f} "
        f"payback={float(economics.get('payback_speed') or 0):.2f}"
    )
    capital = winner.get("capital") or {}
    portfolio_summary = (
        f"roi={float(capital.get('realized_roi') or 0):.2f} "
        f"capital={float(capital.get('capital_score') or 0):.1f} "
        f"risk={float(capital.get('risk_score') or 0):.1f} "
        f"liquidity={float(capital.get('liquidity_score') or 0):.1f}"
    )
    domain = winner.get("domain") or {}
    domain_summary = (
        f"domain={domain.get('domain_key') or 'general'} "
        f"type={domain.get('domain_type') or 'general'} "
        f"domain_score={float(domain.get('domain_score') or 0):.1f} "
        f"automation={float(domain.get('automation_fit') or 0):.1f} "
        f"volatility={float(domain.get('volatility_score') or 0):.1f}"
    )
    evidence = f"group_id={group['id']} experiment_id={winner['experiment_id']} score={winner['score']:.1f} {economic_summary} {portfolio_summary} {domain_summary}"
    add_memory(db, "winning_headline", exp["title"], evidence, winner["score"], "short_term", economic_summary, portfolio_summary, domain_summary)
    add_memory(db, "winning_cta", f"variant {winner['variant_key']} CTA near Telegram path", evidence, winner["score"] * 0.8, "short_term", economic_summary, portfolio_summary, domain_summary)
    add_memory(db, "winning_source", f"variant {winner['variant_key']} source mix", evidence, winner["score"] * 0.6, "mid_term", economic_summary, portfolio_summary, domain_summary)
    migration = db.execute("""
        select *
        from revenue_capital_migrations
        order by migration_score desc, id desc
        limit 1
    """).fetchone()
    if migration:
        pattern = f"{migration['from_domain']} -> {migration['to_domain']}"
        migration_summary = (
            f"migration={pattern} "
            f"score={float(migration['migration_score'] or 0):.1f} "
            f"expected_gain={float(migration['expected_gain'] or 0):.1f}"
        )
        add_memory(
            db,
            "winning_distribution",
            pattern,
            f"{evidence} {migration_summary}",
            float(migration["migration_score"] or 0),
            "long_term",
            economic_summary,
            portfolio_summary,
            f"{domain_summary} {migration_summary}",
        )

def archive_losers(db, group_id: int, ranked):
    for r in ranked[1:]:
        db.execute("""
            insert into revenue_variant_loser_archive
            (group_id, experiment_id, variant_key, artifact_path, score, reason, archived_at)
            values
            (?, ?, ?, ?, ?, 'bandit_rank_loser', datetime('now'))
            on conflict(group_id, experiment_id) do update set
              score=excluded.score,
              reason=excluded.reason,
              archived_at=datetime('now')
        """, (group_id, r["experiment_id"], r["variant_key"], r["artifact_path"], r["score"]))
        db.execute("""
            update revenue_variant_metrics
            set status='loser_archived'
            where group_id=?
              and experiment_id=?
        """, (group_id, r["experiment_id"]))
        db.execute("""
            update revenue_experiments
            set status='loser_archived',
                updated_at=datetime('now')
            where id=?
        """, (r["experiment_id"],))

def create_digest(db, group, ranked):
    lines = [f"[REVENUE_BANDIT_DIGEST] group_id={group['id']}"]
    memories = db.execute("""
        select memory_type, pattern, horizon_type, score, reuse_count
        from revenue_memory_patterns
        order by score desc, reuse_count desc, id asc
        limit 5
    """).fetchall()
    if memories:
        lines.append(
            "top_memories: "
            + " / ".join(
                f"{r['horizon_type']}:{r['memory_type']}={r['pattern']}({float(r['score'] or 0):.1f},reuse={int(r['reuse_count'] or 0)})"
                for r in memories
            )
        )
    horizon_rows = db.execute("""
        select
          horizon_type,
          avg(total_score) as avg_score,
          max(total_score) as max_score
        from revenue_strategy_scores
        where group_id=?
        group by horizon_type
        order by
          case horizon_type
            when 'short_term' then 0
            when 'mid_term' then 1
            else 2
          end
    """, (group["id"],)).fetchall()
    if horizon_rows:
        lines.append(
            "strategy_horizon: "
            + " / ".join(
                f"{r['horizon_type']} avg={float(r['avg_score'] or 0):.1f} max={float(r['max_score'] or 0):.1f}"
                for r in horizon_rows
            )
        )
    econ_rows = db.execute("""
        select
          count(*) as variants,
          sum(case when suppressed=1 then 1 else 0 end) as suppressed,
          avg(expected_profit) as avg_profit,
          max(expected_profit) as max_profit,
          avg(estimated_cac) as avg_cac,
          avg(estimated_ltv) as avg_ltv,
          avg(payback_speed) as avg_payback
        from revenue_economic_metrics
        where group_id=?
    """, (group["id"],)).fetchone()
    if econ_rows and int(econ_rows["variants"] or 0) > 0:
        lines.append(
            "economic_summary: "
            f"profit_avg={float(econ_rows['avg_profit'] or 0):.1f} "
            f"profit_max={float(econ_rows['max_profit'] or 0):.1f} "
            f"cac_avg={float(econ_rows['avg_cac'] or 0):.1f} "
            f"ltv_avg={float(econ_rows['avg_ltv'] or 0):.1f} "
            f"payback_avg={float(econ_rows['avg_payback'] or 0):.2f} "
            f"suppressed={int(econ_rows['suppressed'] or 0)}"
        )
    if has_table(db, "revenue_real_orders"):
        real_rows = db.execute("""
            select
              count(*) as orders,
              coalesce(sum(revenue), 0) as revenue,
              coalesce(sum(gross_profit), 0) as gross_profit,
              coalesce(sum(net_profit), 0) as net_profit,
              coalesce(avg(refund_risk), 0) as refund_risk,
              coalesce(avg(recovered_days), 0) as recovered_days
            from revenue_real_orders
            where group_id=?
        """, (group["id"],)).fetchone()
        if real_rows and int(real_rows["orders"] or 0) > 0:
            lines.append(
                "real_commerce: "
                f"orders={int(real_rows['orders'] or 0)} "
                f"revenue={float(real_rows['revenue'] or 0):.1f} "
                f"gross_profit={float(real_rows['gross_profit'] or 0):.1f} "
                f"net_profit={float(real_rows['net_profit'] or 0):.1f} "
                f"refund_risk={float(real_rows['refund_risk'] or 0):.2f} "
                f"recovered_days={float(real_rows['recovered_days'] or 0):.1f}"
            )
    if has_table(db, "revenue_capital_allocations"):
        portfolio_rows = db.execute("""
            select
              count(*) as projects,
              sum(allocated_budget) as budget,
              avg(realized_roi) as avg_roi,
              max(realized_roi) as max_roi,
              avg(capital_score) as avg_capital,
              avg(risk_score) as avg_risk,
              avg(liquidity_score) as avg_liquidity,
              sum(case when liquidity_score < 20 then 1 else 0 end) as low_liquidity
            from revenue_capital_allocations
        """).fetchone()
        if portfolio_rows and int(portfolio_rows["projects"] or 0) > 0:
            lines.append(
                "portfolio: "
                f"projects={int(portfolio_rows['projects'] or 0)} "
                f"budget={float(portfolio_rows['budget'] or 0):.1f} "
                f"roi_avg={float(portfolio_rows['avg_roi'] or 0):.2f} "
                f"roi_max={float(portfolio_rows['max_roi'] or 0):.2f} "
                f"capital_avg={float(portfolio_rows['avg_capital'] or 0):.1f} "
                f"risk_avg={float(portfolio_rows['avg_risk'] or 0):.1f} "
                f"liquidity_avg={float(portfolio_rows['avg_liquidity'] or 0):.1f} "
                f"low_liquidity={int(portfolio_rows['low_liquidity'] or 0)}"
            )
    if has_table(db, "revenue_business_domains"):
        domain_rows = db.execute("""
            select *
            from revenue_business_domains
            order by net_profit desc, automation_fit desc, scalability_score desc, domain_key asc
            limit 5
        """).fetchall()
        if domain_rows:
            lines.append(
                "domain_leaderboard: "
                + " / ".join(
                    f"{r['domain_key']}:{r['domain_type']} profit={float(r['net_profit'] or 0):.1f} "
                    f"automation={float(r['automation_fit'] or 0):.1f} volatility={float(r['volatility_score'] or 0):.1f}"
                    for r in domain_rows
                )
            )
    if has_table(db, "revenue_capital_migrations"):
        migration_rows = db.execute("""
            select *
            from revenue_capital_migrations
            order by migration_score desc, id desc
            limit 3
        """).fetchall()
        if migration_rows:
            lines.append(
                "capital_migration: "
                + " / ".join(
                    f"{r['from_domain']}->{r['to_domain']} budget={float(r['migrated_budget'] or 0):.1f} "
                    f"gain={float(r['expected_gain'] or 0):.1f} score={float(r['migration_score'] or 0):.1f}"
                    for r in migration_rows
                )
            )
    dist = db.execute("""
        select
          distribution_type,
          count(*) as total,
          sum(case when coalesce(artifact_path,'') != '' then 1 else 0 end) as generated
        from revenue_distribution_tasks
        where group_id=?
        group by distribution_type
        order by distribution_type
    """, (group["id"],)).fetchall()
    if dist:
        lines.append(
            "distribution: "
            + " / ".join(
                f"{r['distribution_type']}={int(r['generated'] or 0)}/{int(r['total'] or 0)}"
                for r in dist
            )
        )
    if has_table(db, "revenue_distribution_publish_queue"):
        queue_rows = db.execute("""
            select publish_status, count(*) as count
            from revenue_distribution_publish_queue
            where group_id=?
            group by publish_status
            order by publish_status
        """, (group["id"],)).fetchall()
        if queue_rows:
            lines.append(
                "publish_queue: "
                + " / ".join(f"{r['publish_status']}={int(r['count'] or 0)}" for r in queue_rows)
            )
            lines.append(
                "approval_summary: "
                + " / ".join(f"{r['publish_status']}={int(r['count'] or 0)}" for r in queue_rows)
            )
        top = db.execute("""
            select distribution_type, variant_key, traffic_source, candidate_score
            from revenue_distribution_publish_queue
            where group_id=?
              and publish_status='queued'
            order by candidate_score desc, id asc
            limit 3
        """, (group["id"],)).fetchall()
        if top:
            lines.append(
                "publish_candidates: "
                + " / ".join(
                    f"{r['distribution_type']}:{r['variant_key']}:{r['traffic_source']}={float(r['candidate_score'] or 0):.1f}"
                    for r in top
                )
            )
    for r in ranked:
        lines.append(
            f"rank={r.get('rank', 0) or '?'} variant={r['variant_key']} exp={r['experiment_id']} "
            f"score={r['score']:.1f} views={r['views']} cta={r['clicks']} telegram={r['telegram_clicks']} "
            f"actions={r['actions']} conversions={r['conversions']} ctr={r['ctr']:.3f} cvr={r['cvr']:.3f}"
        )
        economics = r.get("economics") or {}
        if economics:
            lines.append(
                "economic: "
                f"profit={float(economics['expected_profit']):.1f} "
                f"real_profit={float(economics.get('real_net_profit') or 0):.1f} "
                f"orders={int(economics.get('real_order_count') or 0)} "
                f"ltv={float(economics['estimated_ltv']):.1f} "
                f"cac={float(economics['estimated_cac']):.1f} "
                f"multiplier={float(economics['economic_multiplier']):.2f} "
                f"suppressed={int(economics['suppressed'])}"
            )
        capital = r.get("capital") or {}
        if capital:
            lines.append(
                "portfolio_variant: "
                f"roi={float(capital['realized_roi']):.2f} "
                f"capital={float(capital['capital_score']):.1f} "
                f"risk={float(capital['risk_score']):.1f} "
                f"liquidity={float(capital['liquidity_score']):.1f} "
                f"multiplier={float(capital['portfolio_multiplier']):.2f} "
                f"suppressed={int(capital['suppressed'])}"
            )
        domain = r.get("domain") or {}
        if domain:
            lines.append(
                "domain_variant: "
                f"domain={domain['domain_key']} "
                f"type={domain['domain_type']} "
                f"score={float(domain['domain_score']):.1f} "
                f"automation={float(domain['automation_fit']):.1f} "
                f"volatility={float(domain['volatility_score']):.1f} "
                f"multiplier={float(domain['domain_multiplier']):.2f} "
                f"suppressed={int(domain['suppressed'])}"
            )
        source_rows = source_ctr_rows(db, r["artifact_path"])
        if source_rows:
            lines.append(
                "source_ctr: "
                + " / ".join(
                    f"{x['source']}={x['ctr']:.3f}({x['clicks']}/{x['views']})"
                    for x in source_rows
                )
            )
    summary = "\n".join(lines)
    db.execute("""
        insert into revenue_bandit_digests
        (group_id, summary, sent_to_telegram, created_at)
        values
        (?, ?, 0, datetime('now'))
    """, (group["id"], summary))
    db.execute("""
        insert into router_tasks
        (target_bot, mode, status, task_text, reply_text, created_at, updated_at)
        values
        ('telegram_digest', 'DIGEST', 'done', ?, 'REVENUE_BANDIT_DIGEST_READY', datetime('now'), datetime('now'))
    """, (summary,))
    return summary

def main():
    db = con()
    ensure_schema(db)

    groups = db.execute("""
        select *
        from revenue_variant_groups
        where status in ('active', 'judging')
        order by id asc
        limit 5
    """).fetchall()

    judged = 0
    for group in groups:
        ranked = sync_metrics(db, group["id"])
        for idx, r in enumerate(ranked, start=1):
            r["rank"] = idx
        real_events = sum(
            r["views"] + r["clicks"] + r["telegram_clicks"] + r["real_conversions"]
            for r in ranked
        )
        if len(ranked) < 2 or ranked[0]["score"] < MIN_SCORE_TO_JUDGE or real_events <= 0:
            continue

        winner = ranked[0]
        db.execute("""
            update revenue_experiments
            set status='winner_candidate',
                updated_at=datetime('now')
            where id=?
        """, (winner["experiment_id"],))
        db.execute("""
            update revenue_variant_metrics
            set status='winner'
            where group_id=?
              and experiment_id=?
        """, (group["id"], winner["experiment_id"]))
        archive_losers(db, group["id"], ranked)
        extract_winner_memory(db, group, winner)
        challenger_exp_id = create_challenger(db, group, winner)
        summary = create_digest(db, group, ranked)
        db.execute("""
            update revenue_variant_groups
            set status='judged',
                winner_experiment_id=?,
                digest_summary=?,
                updated_at=datetime('now')
            where id=?
        """, (winner["experiment_id"], summary, group["id"]))
        judged += 1
        print(
            f"[revenue_bandit_v1] judged group_id={group['id']} winner_experiment_id={winner['experiment_id']} challenger_experiment_id={challenger_exp_id}",
            flush=True,
        )

    db.commit()
    print(f"[revenue_bandit_v1] judged={judged}", flush=True)

if __name__ == "__main__":
    main()
