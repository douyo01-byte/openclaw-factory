import os,sqlite3

DB_PATH=os.environ.get("DB_PATH","data/openclaw.db")

def conn():
    return sqlite3.connect(DB_PATH,timeout=30)

def tick():
    c=conn()

    c.execute("""
    update proposal_state
    set pending_question=pending_questions
    where (pending_question is null or pending_question='')
      and (pending_questions is not null and pending_questions!='')
    """)

    c.execute("""
    update proposal_state
    set pending_questions=pending_question
    where (pending_questions is null or pending_questions='')
      and (pending_question is not null and pending_question!='')
    """)

    c.execute("""
    insert into proposal_state(proposal_id,stage,updated_at)
    select id,'raw',datetime('now')
    from dev_proposals
    where id not in (select proposal_id from proposal_state)
    """)

    c.execute("""
    update proposal_state
    set stage='done',updated_at=datetime('now')
    where proposal_id in (select id from dev_proposals where status='merged')
      and stage!='done'
    """)

    c.execute("""
    update proposal_state
    set stage='approved',updated_at=datetime('now')
    where proposal_id in (select id from dev_proposals where status='approved')
      and stage not in ('waiting_answer','answer_received','done')
    """)

    c.commit()
    c.close()

if __name__=="__main__":
    tick()
