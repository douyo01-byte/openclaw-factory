import sqlite3,os

DB=os.environ["DB_PATH"]

conn=sqlite3.connect(DB)

rows=conn.execute("""
select
  source_ai,
  count(*) proposals,
  sum(case when pr_status='merged' then 1 else 0 end) merged
from dev_proposals
where source_ai is not null
group by source_ai
""").fetchall()

print("\n=== OpenClaw AI Employee Ranking ===\n")

ranking=[]

for r in rows:
    ai=r[0]
    proposals=r[1]
    merged=r[2]
    score=merged*2+proposals
    ranking.append((ai,proposals,merged,score))

ranking.sort(key=lambda x:x[3],reverse=True)

for i,r in enumerate(ranking,1):
    print(f"{i}. {r[0]}  proposals={r[1]} merged={r[2]} score={r[3]}")

conn.close()
