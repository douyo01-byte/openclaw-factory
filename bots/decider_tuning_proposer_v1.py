import os
import sqlite3

DB = os.environ.get("DB_PATH", "data/openclaw.db")


def mk_branch_name(source_ai, decision, matched_band):
    raw = f"chore/decider-tuning-{source_ai}-{decision}-{matched_band}".lower()
    out = []
    for ch in raw:
        if ch.isalnum() or ch in "/-_":
            out.append(ch)
        else:
            out.append("-")
    branch = "".join(out)
    while "--" in branch:
        branch = branch.replace("--", "-")
    return branch[:120].strip("-") or "chore/decider-tuning"


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    conn.execute("""
    create table if not exists decider_tuning_proposals(
      source_ai text not null,
      decision text not null,
      matched_band text not null,
      proposal_id integer,
      created_at text default (datetime('now')),
      primary key (source_ai, decision, matched_band)
    )
    """)

    rows = conn.execute("""
    select
      coalesce(source_ai,'') as source_ai,
      coalesce(decision,'') as decision,
      coalesce(matched_band,'') as matched_band,
      coalesce(sample_count,0) as sample_count,
      coalesce(avg_source_bias,0) as avg_source_bias,
      coalesce(avg_cluster_bias,0) as avg_cluster_bias,
      coalesce(suggested_action,'') as suggested_action,
      coalesce(suggestion_reason,'') as suggestion_reason
    from decider_threshold_advice
    where coalesce(suggested_action,'') in ('consider_lower_source_bias')
    order by sample_count desc, source_ai asc, decision asc, matched_band asc
    """).fetchall()

    done = 0

    for r in rows:
        source_ai = str(r["source_ai"] or "").strip()
        decision = str(r["decision"] or "").strip()
        matched_band = str(r["matched_band"] or "").strip()
        sample_count = int(r["sample_count"] or 0)
        avg_source_bias = float(r["avg_source_bias"] or 0.0)
        avg_cluster_bias = float(r["avg_cluster_bias"] or 0.0)
        suggested_action = str(r["suggested_action"] or "").strip()
        suggestion_reason = str(r["suggestion_reason"] or "").strip()

        if not source_ai or not decision or not matched_band:
            continue

        exists = conn.execute("""
        select proposal_id
        from decider_tuning_proposals
        where source_ai=? and decision=? and matched_band=?
        """, (source_ai, decision, matched_band)).fetchone()
        if exists:
            continue

        title = f"[decider-tuning] lower source bias for {source_ai} {decision} {matched_band}"
        description = "\n".join([
            "Decider threshold advisor suggested a safe tuning proposal.",
            f"source_ai: {source_ai}",
            f"decision: {decision}",
            f"matched_band: {matched_band}",
            f"sample_count: {sample_count}",
            f"avg_source_bias: {avg_source_bias:.4f}",
            f"avg_cluster_bias: {avg_cluster_bias:.4f}",
            f"suggested_action: {suggested_action}",
            f"suggestion_reason: {suggestion_reason}",
            "",
            "This is a proposal only. Do not auto-apply.",
            "Goal: reduce execute_now overconcentration without breaking backlog/archive spread.",
        ])

        dup = conn.execute("""
        select id
        from dev_proposals
        where coalesce(title,'') = ?
           or (
             coalesce(source_ai,'')='decider_threshold_advisor_v1'
             and coalesce(status,'') in ('new','pending','approved','backlog','draft')
             and coalesce(title,'') like '[decider-tuning]%'
             and coalesce(description,'') like ?
           )
        order by id desc
        limit 1
        """, (title, f"%source_ai: {source_ai}%decision: {decision}%matched_band: {matched_band}%")).fetchone()
        if dup:
            conn.execute("""
            insert or replace into decider_tuning_proposals(
              source_ai, decision, matched_band, proposal_id, created_at
            ) values(?,?,?,?,datetime('now'))
            """, (source_ai, decision, matched_band, int(dup[0]),))
            done += 1
            continue

        branch_name = mk_branch_name(source_ai, decision, matched_band)
        cur = conn.execute("""
        insert into dev_proposals(
          title, description, source_ai, status, project_decision, priority, branch_name
        ) values(?,?,?,?,?,?,?)
        """, (
            title,
            description,
            "decider_threshold_advisor_v1",
            "approved",
            "backlog",
            1.0,
            branch_name,
        ))
        proposal_id = cur.lastrowid

        conn.execute("""
        insert or replace into decider_tuning_proposals(
          source_ai, decision, matched_band, proposal_id, created_at
        ) values(?,?,?,?,datetime('now'))
        """, (source_ai, decision, matched_band, proposal_id))
        done += 1

    conn.commit()
    conn.close()
    print(f"decider_tuning_proposals_done={done}", flush=True)

if __name__ == "__main__":
    main()
