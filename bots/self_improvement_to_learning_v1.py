from __future__ import annotations
import os
import sqlite3
import time

DB = os.environ.get("OCLAW_DB_PATH") or os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
SLEEP = float(os.environ.get("SELF_IMPROVEMENT_TO_LEARNING_SLEEP", "10"))

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000")
    try:
        c.execute("pragma journal_mode=WAL")
    except Exception:
        pass
    return c

def has_table(c, name: str) -> bool:
    row = c.execute(
        "select 1 from sqlite_master where type='table' and name=?",
        (name,)
    ).fetchone()
    return bool(row)

def cols(c, table: str) -> set[str]:
    return {r["name"] for r in c.execute(f"pragma table_info({table})").fetchall()}

def ensure_cols(c, table: str, adds: dict[str, str]):
    existing = cols(c, table)
    for k, sql in adds.items():
        if k not in existing:
            c.execute(sql)

def ensure_schema(c):
    ensure_cols(c, "self_improvement_log", {
        "learning_bridge_status": "alter table self_improvement_log add column learning_bridge_status text not null default ''",
        "learning_bridge_reason": "alter table self_improvement_log add column learning_bridge_reason text not null default ''",
        "learning_result_id": "alter table self_improvement_log add column learning_result_id integer default 0",
    })

    if not has_table(c, "learning_results"):
        c.execute("""
            create table learning_results(
              id integer primary key autoincrement,
              title text not null default '',
              content text not null default '',
              result text not null default '',
              created_at text default (datetime('now'))
            )
        """)

def fetch_rows(c):
    return c.execute("""
        select
          id,
          parent_task_id,
          child_task_id,
          source_command_id,
          kind,
          coalesce(status,'') as status,
          coalesce(fix,'') as fix,
          coalesce(result,'') as result,
          coalesce(reusable_pattern,'') as reusable_pattern,
          coalesce(parent_reply_head,'') as parent_reply_head,
          coalesce(child_result_head,'') as child_result_head,
          coalesce(learning_bridge_status,'') as learning_bridge_status
        from self_improvement_log
        where coalesce(status,'')='done'
          and coalesce(learning_bridge_status,'')=''
        order by id asc
        limit 20
    """).fetchall()

def build_title(r) -> str:
    return f"self_improvement exec bridge parent={r['parent_task_id']} child={r['child_task_id']}"

def build_content(r) -> str:
    return "\n".join([
        f"kind={r['kind']}",
        f"fix={r['fix']}",
        f"result={r['result']}",
        f"reusable_pattern={r['reusable_pattern']}",
        "",
        "[parent_reply_head]",
        r["parent_reply_head"],
        "",
        "[child_result_head]",
        r["child_result_head"],
    ]).strip()

def build_row_payload(r) -> dict[str, object]:
    return {
        "source": "self_improvement_log",
        "source_ref_id": int(r["id"]),
        "ref_id": int(r["id"]),
        "title": build_title(r),
        "content": build_content(r),
        "body": build_content(r),
        "summary": build_content(r),
        "result": "success",
        "status": "success",
        "kind": "self_improvement_log",
        "note": f"self_improvement_log:{int(r['id'])}",
        "created_at": "datetime('now')",
        "updated_at": "datetime('now')",
    }

def insert_learning_result(c, r) -> int:
    table_cols = cols(c, "learning_results")
    payload = build_row_payload(r)

    normal_values: list[object] = []
    normal_cols: list[str] = []
    sql_values: list[str] = []

    for k, v in payload.items():
        if k not in table_cols:
            continue
        normal_cols.append(k)
        if isinstance(v, str) and v == "datetime('now')":
            sql_values.append("datetime('now')")
        else:
            sql_values.append("?")
            normal_values.append(v)

    if not normal_cols:
        raise RuntimeError("learning_results_has_no_supported_columns")

    sql = f"""
        insert into learning_results(
          {",".join(normal_cols)}
        ) values(
          {",".join(sql_values)}
        )
    """
    c.execute(sql, tuple(normal_values))
    return int(c.execute("select last_insert_rowid()").fetchone()[0])

def mark_done(c, row_id: int, learning_result_id: int):
    c.execute("""
        update self_improvement_log
        set learning_bridge_status='done',
            learning_bridge_reason='',
            learning_result_id=?,
            updated_at=datetime('now')
        where id=?
    """, (learning_result_id, row_id))

def mark_skipped(c, row_id: int, reason: str):
    c.execute("""
        update self_improvement_log
        set learning_bridge_status='skipped',
            learning_bridge_reason=?,
            updated_at=datetime('now')
        where id=?
    """, (reason, row_id))

def tick():
    done = 0
    skipped = 0
    with conn() as c:
        ensure_schema(c)
        rows = fetch_rows(c)
        for r in rows:
            if not r["fix"]:
                mark_skipped(c, int(r["id"]), "empty_fix")
                skipped += 1
                continue
            try:
                lrid = insert_learning_result(c, r)
                mark_done(c, int(r["id"]), lrid)
                done += 1
            except Exception as e:
                mark_skipped(c, int(r["id"]), f"{type(e).__name__}:{e}")
                skipped += 1
        c.commit()
    print(f"[self_improvement_to_learning_v1] done={done} skipped={skipped}", flush=True)

def main():
    while True:
        try:
            tick()
        except Exception as e:
            print(f"[self_improvement_to_learning_v1] fatal err={e!r}", flush=True)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()
