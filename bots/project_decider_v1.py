import os
import sqlite3

DB = os.environ.get("DB_PATH", "data/openclaw.db")

KEYWORDS_EXECUTE = [
    "safety",
    "security",
    "merge",
    "executor",
    "automation",
    "pipeline",
    "logging",
]

def load_source_merge_rates(conn):
    rows = conn.execute("""
        select
          lower(coalesce(source_ai,'')) as source_ai,
          count(*) as total,
          sum(case when coalesce(status,'')='merged' then 1 else 0 end) as merged
        from dev_proposals
        where coalesce(source_ai,'') <> ''
        group by lower(coalesce(source_ai,''))
    """).fetchall()
    out = {}
    for source_ai, total, merged in rows:
        total = int(total or 0)
        merged = int(merged or 0)
        out[source_ai] = (merged / total) if total else 0.0
    return out

def source_bias(source_ai, rates):
    s = (source_ai or "").strip().lower()
    if not s:
        return 0.0
    if s == "ceo":
        return 1.0
    rate = rates.get(s, 0.0)
    return round(rate * 0.6, 4)


def load_cluster_bias(conn):
    rows = conn.execute("""
        select
          lower(coalesce(source_ai,'')) as source_ai,
          lower(coalesce(target_system,'')) as target_system,
          lower(coalesce(improvement_type,'')) as improvement_type,
          coalesce(success_count,0) as success_count,
          coalesce(bias_score,0) as bias_score
        from cluster_bias
        where coalesce(source_ai,'') <> ''
    """).fetchall()
    out = {}
    for source_ai, target_system, improvement_type, success_count, bias_score in rows:
        out[(source_ai, target_system, improvement_type)] = (
            int(success_count or 0),
            float(bias_score or 0),
        )
    return out

def cluster_bias(source_ai, title, desc, cluster_map):
    s = (source_ai or "").strip().lower()
    if not s:
        return 0.0
    text = f"{title or ''} {desc or ''}".lower()

    target = ""
    improve = ""

    if "watcher" in text:
        target = "watcher"
    elif "telegram" in text:
        target = "telegram"
    elif "executor" in text:
        target = "executor"
    elif "database" in text or "sqlite" in text or "db" in text:
        target = "database"
    elif "learning" in text:
        target = "learning"
    elif "brain" in text:
        target = "brain"

    if "stabilize" in text or "安 定" in text or "不 具 合" in text or "障 害" in text:
        improve = "stabilize"
    elif "optimize" in text or "最 適 化" in text:
        improve = "optimize"
    elif "refactor" in text or "整 理" in text:
        improve = "refactor"
    elif "monitor" in text or "監 視" in text:
        improve = "monitor"
    elif "extend" in text or "拡 張" in text:
        improve = "extend"

    if not target and not improve:
        return 0.0

    best = 0.0
    for (cs, ct, ci), (succ, bias) in cluster_map.items():
        if cs != s:
            continue
        if target and ct and ct != target:
            continue
        if improve and ci and ci != improve:
            continue
        if succ < 3:
            bias *= 0.5
        elif succ < 6:
            bias *= 0.8
        best = max(best, bias)

    return min(max(best, -0.45), 0.45)

def load_patterns(conn):
    rows = conn.execute(
        """
        select token, weight
        from decision_patterns
        order by abs(weight) desc, updated_at desc
        limit 200
        """
    ).fetchall()
    return [(str(r[0] or "").strip().lower(), float(r[1] or 0)) for r in rows if str(r[0] or "").strip()]

def score(title, desc, patterns, source_ai="", source_rates=None, cluster_map=None):
    text = f"{title or ''} {desc or ''}".lower()
    priority = 0.0
    for k in KEYWORDS_EXECUTE:
        if k in text:
            priority += 1.0
    if "improve" in text or "optimize" in text:
        priority += 0.5
    matched = []
    for token, weight in patterns:
        if token and token in text:
            priority += weight
            matched.append((token, weight))
    sb = source_bias(source_ai, source_rates or {})
    priority += sb
    cb = cluster_bias(source_ai, title, desc, cluster_map or {})
    priority += cb
    if priority > 2.4:
        decision = "execute_now"
    elif priority > 1.15:
        decision = "backlog"
    else:
        decision = "archive"
    return decision, priority, matched, sb, cb

def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    patterns = load_patterns(conn)
    source_rates = load_source_merge_rates(conn)
    cluster_map = load_cluster_bias(conn)
    rows = conn.execute(
        """
        select id, title, description, status, project_decision, coalesce(source_ai,'') as source_ai
        from dev_proposals
        where status='approved'
          and coalesce(project_decision,'') in ('','backlog','archive','execute_now')
          and coalesce(source_ai,'') <> 'decider_threshold_advisor_v1'
          and coalesce(title,'') not like '[decider-tuning]%'
        order by id asc
        """
    ).fetchall()
    done = 0
    for r in rows:
        decision, priority, matched, source_bias_applied, cluster_bias_applied = score(
            r["title"],
            r["description"],
            patterns,
            r["source_ai"],
            source_rates,
            cluster_map,
        )
        conn.execute(
            """
            update dev_proposals
            set project_decision=?,
                priority=?
            where id=?
            """,
            (decision, priority, r["id"]),
        )
        if matched:
            conn.execute(
                """
                insert into dev_events(proposal_id,event_type,payload)
                values(
                  ?, 'decider_patterns_applied',
                  json_object(
                    'decision', ?,
                    'priority', ?,
                    'matched', ?,
                    'matched_count', ?,
                    'source_bias', ?,
                    'cluster_bias', ?,
                    'source', 'decision_patterns'
                  )
                )
                """,
                (
                    r["id"],
                    decision,
                    priority,
                    ",".join([f"{t}:{w}" for t, w in matched]),
                    len(matched),
                    source_bias_applied,
                    cluster_bias_applied,
                ),
            )
        done += 1
    conn.commit()
    conn.close()
    print(f"project_decider_done={done}", flush=True)

if __name__ == "__main__":
    main()
