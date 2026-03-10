import json, os, sqlite3, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
OBS = ROOT / "obs"
OBS.mkdir(parents=True, exist_ok=True)

SOURCE_CANDIDATES = [
    ("dev_proposals", ["source", "proposal_source", "origin", "provider", "engine", "bot_name"]),
    ("ceo_hub_events", ["source", "proposal_source", "origin", "provider", "engine", "bot_name"]),
    ("decisions", ["source", "proposal_source", "origin", "provider", "engine", "bot_name"]),
    ("inbox_commands", ["source", "proposal_source", "origin", "provider", "engine", "bot_name"]),
]

EVENT_COLS = ["event_type", "type", "kind", "event"]
PROPOSAL_ID_COLS = ["proposal_id", "dev_proposal_id"]
CREATED_AT_COLS = ["created_at", "ts", "event_at", "occurred_at"]
STATUS_COLS = ["status", "state"]

def detect_db():
    cands = []
    if os.environ.get("DB_PATH"):
        cands.append(Path(os.environ["DB_PATH"]))
    cands += [
        ROOT / "data" / "openclaw.db",
        ROOT / "data" / "openclaw_daemon.db",
        ROOT / "data" / "openclaw",
    ]
    for p in cands:
        if p.exists():
            return p
    return None

def table_exists(conn, name):
    cur = conn.execute("select 1 from sqlite_master where type='table' and name=?", (name,))
    return cur.fetchone() is not None

def cols(conn, table):
    return [r[1] for r in conn.execute(f"pragma table_info({table})").fetchall()]

def first_col(existing, candidates):
    for c in candidates:
        if c in existing:
            return c
    return None

def safe_ident(name):
    return '"' + name.replace('"', '""') + '"'

def find_source_base(conn):
    for table, cands in SOURCE_CANDIDATES:
        if not table_exists(conn, table):
            continue
        cs = cols(conn, table)
        sc = first_col(cs, cands)
        if sc:
            return table, sc, cs
    return None, None, []

def fetch_rows_dev_proposals(conn, source_col, dp_cols):
    status_col = first_col(dp_cols, STATUS_COLS)
    approved_case = f"sum(case when {safe_ident(status_col)}='approved' then 1 else 0 end) as approveds," if status_col else "0 as approveds,"
    merged_case = f"sum(case when {safe_ident(status_col)}='merged' then 1 else 0 end) as mergeds," if status_col else "0 as mergeds,"
    sql = f"""
    select
      {safe_ident(source_col)} as source,
      count(*) as proposals,
      {approved_case}
      {merged_case}
      null as avg_lifecycle_sec
    from dev_proposals
    where {safe_ident(source_col)} is not null and trim({safe_ident(source_col)}) <> ''
    group by {safe_ident(source_col)}
    order by mergeds desc, proposals desc, {safe_ident(source_col)} asc
    """
    return [dict(r) for r in conn.execute(sql).fetchall()]

def fetch_rows_events(conn, table, source_col, table_cols):
    event_col = first_col(table_cols, EVENT_COLS)
    pid_col = first_col(table_cols, PROPOSAL_ID_COLS)
    created_col = first_col(table_cols, CREATED_AT_COLS)

    if not event_col:
        sql = f"""
        select
          {safe_ident(source_col)} as source,
          count(*) as proposals,
          0 as approveds,
          0 as mergeds,
          null as avg_lifecycle_sec
        from {safe_ident(table)}
        where {safe_ident(source_col)} is not null and trim({safe_ident(source_col)}) <> ''
        group by {safe_ident(source_col)}
        order by proposals desc, {safe_ident(source_col)} asc
        """
        rows = [dict(r) for r in conn.execute(sql).fetchall()]
        return rows, {}, {}

    rows_map = {}
    for r in conn.execute(f"""
        select {safe_ident(source_col)} as source, count(*) as proposals
        from {safe_ident(table)}
        where {safe_ident(source_col)} is not null and trim({safe_ident(source_col)}) <> ''
          and {safe_ident(event_col)} in ('proposal_created','pr_created','proposal')
        group by {safe_ident(source_col)}
    """).fetchall():
        rows_map[r["source"]] = {
            "source": r["source"],
            "proposals": r["proposals"],
            "approveds": 0,
            "mergeds": 0,
            "avg_lifecycle_sec": None,
        }

    for r in conn.execute(f"""
        select {safe_ident(source_col)} as source, count(*) as approveds
        from {safe_ident(table)}
        where {safe_ident(source_col)} is not null and trim({safe_ident(source_col)}) <> ''
          and {safe_ident(event_col)} in ('approved','approval')
        group by {safe_ident(source_col)}
    """).fetchall():
        rows_map.setdefault(r["source"], {
            "source": r["source"],
            "proposals": 0,
            "approveds": 0,
            "mergeds": 0,
            "avg_lifecycle_sec": None,
        })["approveds"] = r["approveds"]

    for r in conn.execute(f"""
        select {safe_ident(source_col)} as source, count(*) as mergeds
        from {safe_ident(table)}
        where {safe_ident(source_col)} is not null and trim({safe_ident(source_col)}) <> ''
          and {safe_ident(event_col)} in ('merged','pr_merged','merge')
        group by {safe_ident(source_col)}
    """).fetchall():
        rows_map.setdefault(r["source"], {
            "source": r["source"],
            "proposals": 0,
            "approveds": 0,
            "mergeds": 0,
            "avg_lifecycle_sec": None,
        })["mergeds"] = r["mergeds"]

    learning = {}
    for r in conn.execute(f"""
        select {safe_ident(source_col)} as source, count(*) as learning_success
        from {safe_ident(table)}
        where {safe_ident(source_col)} is not null and trim({safe_ident(source_col)}) <> ''
          and {safe_ident(event_col)} in ('learning_result','learning','learned')
        group by {safe_ident(source_col)}
    """).fetchall():
        learning[r["source"]] = r["learning_success"]

    lifecycle = {}
    if pid_col and created_col:
        try:
            for r in conn.execute(f"""
                with created as (
                  select {safe_ident(pid_col)} as proposal_id,
                         {safe_ident(source_col)} as source,
                         min({safe_ident(created_col)}) as created_at
                  from {safe_ident(table)}
                  where {safe_ident(event_col)} in ('proposal_created','pr_created','proposal')
                    and {safe_ident(pid_col)} is not null
                    and {safe_ident(source_col)} is not null
                    and trim({safe_ident(source_col)}) <> ''
                  group by {safe_ident(pid_col)}, {safe_ident(source_col)}
                ),
                merged as (
                  select {safe_ident(pid_col)} as proposal_id,
                         min({safe_ident(created_col)}) as merged_at
                  from {safe_ident(table)}
                  where {safe_ident(event_col)} in ('merged','pr_merged','merge')
                    and {safe_ident(pid_col)} is not null
                  group by {safe_ident(pid_col)}
                )
                select c.source as source,
                       avg(strftime('%s', m.merged_at) - strftime('%s', c.created_at)) as avg_lifecycle_sec
                from created c
                join merged m on c.proposal_id = m.proposal_id
                group by c.source
            """).fetchall():
                lifecycle[r["source"]] = r["avg_lifecycle_sec"]
        except Exception:
            pass

    rows = sorted(rows_map.values(), key=lambda x: (-x["mergeds"], -x["proposals"], x["source"]))
    return rows, learning, lifecycle

def main():
    db = detect_db()
    if not db:
        raise SystemExit("DB not found")

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row

    base_table, source_col, table_cols = find_source_base(conn)

    rows = []
    learning = {}
    lifecycle = {}
    reason = ""

    if base_table == "dev_proposals":
        rows = fetch_rows_dev_proposals(conn, source_col, table_cols)
        if table_exists(conn, "ceo_hub_events"):
            ev_cols = cols(conn, "ceo_hub_events")
            event_col = first_col(ev_cols, EVENT_COLS)
            pid_col = first_col(ev_cols, PROPOSAL_ID_COLS)
            created_col = first_col(ev_cols, CREATED_AT_COLS)
            dp_id = "id" if "id" in table_cols else None
            if event_col and pid_col and dp_id:
                for r in conn.execute(f"""
                    select d.{safe_ident(source_col)} as source, count(distinct e.{safe_ident(pid_col)}) as learning_success
                    from ceo_hub_events e
                    join dev_proposals d on d.{safe_ident(dp_id)} = e.{safe_ident(pid_col)}
                    where e.{safe_ident(event_col)} in ('learning_result','learning','learned')
                      and d.{safe_ident(source_col)} is not null and trim(d.{safe_ident(source_col)}) <> ''
                    group by d.{safe_ident(source_col)}
                """).fetchall():
                    learning[r["source"]] = r["learning_success"]
                if "created_at" in table_cols and created_col:
                    for r in conn.execute(f"""
                        select d.{safe_ident(source_col)} as source,
                               avg(strftime('%s', m.merged_at) - strftime('%s', d.created_at)) as avg_lifecycle_sec
                        from dev_proposals d
                        join (
                          select {safe_ident(pid_col)} as proposal_id, min({safe_ident(created_col)}) as merged_at
                          from ceo_hub_events
                          where {safe_ident(event_col)} in ('merged','pr_merged','merge')
                          group by {safe_ident(pid_col)}
                        ) m
                        on d.{safe_ident(dp_id)} = m.proposal_id
                        where d.{safe_ident(source_col)} is not null and trim(d.{safe_ident(source_col)}) <> ''
                          and d.created_at is not null
                        group by d.{safe_ident(source_col)}
                    """).fetchall():
                        lifecycle[r["source"]] = r["avg_lifecycle_sec"]
    elif base_table:
        rows, learning, lifecycle = fetch_rows_events(conn, base_table, source_col, table_cols)
    else:
        reason = "source-like column not found in known tables"

    for r in rows:
        p = r.get("proposals") or 0
        m = r.get("mergeds") or 0
        a = r.get("approveds") or 0
        l = learning.get(r["source"], 0)
        r["learning_success"] = l
        r["merge_rate"] = round((m / p * 100.0), 1) if p else 0.0
        r["approval_rate"] = round((a / p * 100.0), 1) if p else 0.0
        r["learning_success_rate"] = round((l / m * 100.0), 1) if m else 0.0
        if r["source"] in lifecycle:
            r["avg_lifecycle_sec"] = lifecycle[r["source"]]

    out = {
        "generated_at": int(time.time()),
        "db_path": str(db),
        "source_base_table": base_table,
        "source_column": source_col,
        "reason": reason,
        "rows": rows,
    }

    (OBS / "supply_adoption_metrics.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    with (LOGS / "supply_adoption_metrics_v1.log").open("a", encoding="utf-8") as f:
        if not rows:
            f.write(f"[supply_adoption] no_rows reason={reason or 'no matching events'}\n")
        else:
            for r in rows:
                f.write(
                    "[supply_adoption] "
                    f"source={r['source']} proposals={r['proposals']} approved={r['approveds']} "
                    f"merged={r['mergeds']} merge_rate={r['merge_rate']} "
                    f"learning_success={r['learning_success']} learning_success_rate={r['learning_success_rate']} "
                    f"avg_lifecycle_sec={r['avg_lifecycle_sec']}\n"
                )

    conn.close()

if __name__ == "__main__":
    main()
