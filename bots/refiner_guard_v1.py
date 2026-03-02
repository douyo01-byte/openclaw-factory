import os,sqlite3,subprocess,sys,datetime

DB_PATH=os.environ.get("DB_PATH",os.path.expanduser("~/AI/openclaw-factory/data/openclaw.db"))
CORE_PATH=os.path.expanduser("~/AI/openclaw-factory")

def conn():
    return sqlite3.connect(DB_PATH,timeout=30)

def tick():
    c=conn()
    rows=c.execute("""
    select id,title,description
    from dev_proposals
    where status='approved'
      and (spec_stage is null or spec_stage='' or spec_stage='raw')
    order by id asc
    limit 10
    """).fetchall()

    for pid,title,desc in rows:
        p=(title or "")+"\n"+(desc or "")
        low=("TBD" in p) or ("未定" in p) or (len(p)<120)
        if False:
            q="仕様が不足しています。以下を返信してください：\n1) 変更ファイル/場所\n2) 期待挙動\n3) 完了条件\n#"+str(pid)
            c.execute("""
            insert into proposal_conversation(proposal_id,role,message,created_at)
            values(?,?,?,datetime('now'))
            """,(pid,"assistant",q))
            c.execute("""
            insert into proposal_state(proposal_id,stage,pending_question,updated_at)
            values(?,?,?,datetime('now'))
            on conflict(proposal_id) do update set
              stage=excluded.stage,
              pending_question=excluded.pending_question,
              updated_at=excluded.updated_at
            """,(pid,"waiting_answer",q))
            continue

        subprocess.call([sys.executable,"-m","bots.spec_refiner_v2",str(pid)],cwd=CORE_PATH)
        c.execute("""
        update dev_proposals
        set spec_stage='refined'
        where id=? and (spec_stage is null or spec_stage='' or spec_stage='raw')
        """,(pid,))

    c.commit()
    c.close()

if __name__=="__main__":
    tick()
