import json, os, sqlite3, time
from pathlib import Path

DB = os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH") or "/Users/doyopc/AI/openclaw-factory/data/openclaw.db"
OUT = Path("obs/db_integrity_state.json")
LOG = Path("logs/db_integrity_check_v1.log")

SQL = '''
with mismatch_counts as (
  select 'status=merged but others mismatch' as kind, count(*) as cnt
  from dev_proposals
  where coalesce(status,'')='merged'
    and (coalesce(dev_stage,'')!='merged' or coalesce(pr_status,'')!='merged')

  union all
  select 'dev_stage=merged but others mismatch' as kind, count(*) as cnt
  from dev_proposals
  where coalesce(dev_stage,'')='merged'
    and (coalesce(status,'')!='merged' or coalesce(pr_status,'')!='merged')

  union all
  select 'pr_status=merged but others mismatch' as kind, count(*) as cnt
  from dev_proposals
  where coalesce(pr_status,'')='merged'
    and (coalesce(status,'')!='merged' or coalesce(dev_stage,'')!='merged')

  union all
  select 'status=closed but others mismatch' as kind, count(*) as cnt
  from dev_proposals
  where coalesce(status,'')='closed'
    and (coalesce(dev_stage,'')!='closed' or coalesce(pr_status,'')!='closed')

  union all
  select 'dev_stage=closed but others mismatch' as kind, count(*) as cnt
  from dev_proposals
  where coalesce(dev_stage,'')='closed'
    and (coalesce(status,'')!='closed' or coalesce(pr_status,'')!='closed')

  union all
  select 'pr_status=closed but others mismatch' as kind, count(*) as cnt
  from dev_proposals
  where coalesce(pr_status,'')='closed'
    and (coalesce(status,'')!='closed' or coalesce(dev_stage,'')!='closed')
)
select
  (
    select count(*)
    from dev_proposals
    where coalesce(status,'')='pr_created'
      and coalesce(dev_stage,'')!='merged'
  ) as pr_created_without_merged,
  (
    select count(*)
    from dev_proposals
    where coalesce(status,'')='merged'
      and (result_type is null or coalesce(result_type,'')='')
  ) as merged_without_learning_result,
  (
    select count(*)
    from dev_proposals
    where not (
      coalesce(status,'')='pr_created'
      and coalesce(dev_stage,'')='pr_created'
      and coalesce(pr_status,'') in ('', 'pr_created')
    )
      and (
        coalesce(status,'')!=coalesce(dev_stage,'')
        or (
          coalesce(pr_status,'')!=''
          and coalesce(status,'')!=coalesce(pr_status,'')
        )
      )
  ) as status_mismatch,
  (
    select coalesce(sum(cnt),0)
    from mismatch_counts
  ) as lifecycle_anomaly_count,
  (
    select json_group_object(kind, cnt)
    from mismatch_counts
  ) as mismatch_counts_json,
  (
    select count(*)
    from dev_proposals
    where coalesce(source_ai,'')=''
       or coalesce(category,'')=''
       or coalesce(target_system,'')=''
  ) as missing_source_category_target_system
'''


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=30000")
    row = con.execute(SQL).fetchone()
    con.close()

    state = {
        "checked_at": int(time.time()),
        "db_path": DB,
        "merged_without_learning_result": int(row["merged_without_learning_result"] or 0),
        "status_mismatch": int(row["status_mismatch"] or 0),
        "lifecycle_anomaly_count": int(row["lifecycle_anomaly_count"] or 0),
        "mismatch_counts": json.loads(row["mismatch_counts_json"] or "{}"),
        "pr_created_without_merged": int(row["pr_created_without_merged"] or 0),
        "missing_source_category_target_system": int(row["missing_source_category_target_system"] or 0),
    }

    OUT.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(
            "[db_integrity] "
            f"pr_created_without_merged={state['pr_created_without_merged']} "
            f"merged_without_learning_result={state['merged_without_learning_result']} "
            f"status_mismatch={state['status_mismatch']} "
            f"lifecycle_anomaly_count={state['lifecycle_anomaly_count']} "
            f"missing_source_category_target_system={state['missing_source_category_target_system']}\n"
        )
if __name__ == "__main__":
    main()
