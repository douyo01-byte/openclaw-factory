import os,time,sqlite3,requests

DB=os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "data/openclaw.db"
OPENAI=os.environ.get("OPENAI_API_KEY","").strip()

def conn():
    c=sqlite3.connect(DB)
    c.row_factory=sqlite3.Row
    return c

def ask_llm(text):
    r=requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization":f"Bearer {OPENAI}",
            "Content-Type":"application/json"
        },
        json={
            "model":"gpt-4.1-mini",
            "input":[
                {"role":"system","content":"You refine software specifications."},
                {"role":"user","content":text}
            ]
        },
        timeout=120
    )
    r.raise_for_status()
    j=r.json()
    out=(j.get("output_text") or "").strip()
    if out:
        return out
    parts=[]
    for item in j.get("output",[]):
        for c in item.get("content",[]):
            t=c.get("text")
            if t:
                parts.append(t)
    out="\n".join(parts).strip()
    if not out:
        raise RuntimeError(f"empty response: {j}")
    return out

def refine_once():
    if not OPENAI:
        raise RuntimeError("OPENAI_API_KEY missing")
    done=0
    with conn() as c:
        rows=c.execute("""
            select id,title,description
            from dev_proposals
            where status='approved'
              and coalesce(spec,'')=''
            order by id desc
            limit 5
        """).fetchall()
        print(f"rows={len(rows)}")
        for r in rows:
            prompt=f"""proposal:
{r["title"]}

description:
{r["description"]}

Produce a concrete refined development specification in plain text with:
1. goal
2. scope
3. required behavior
4. inputs/outputs
5. edge cases
6. implementation notes
7. acceptance criteria
"""
            spec=ask_llm(prompt)
            c.execute(
                "update dev_proposals set spec=? where id=?",
                (spec,int(r["id"]))
            )
            c.execute("""
                update proposal_state
                set stage='refined',
                    pending_question='',
                    pending_questions='',
                    updated_at=datetime('now')
                where proposal_id=?
            """,(int(r["id"]),))
            c.execute("""
                insert into proposal_conversation(proposal_id,role,message,created_at)
                values(?,?,?,datetime('now'))
            """,(int(r["id"]),"assistant","[spec_refiner_v2] refined"))
            print(f"refined id={int(r['id'])} spec_len={len(spec)}")
            done+=1
        c.commit()
    return done

if __name__=="__main__":
    while True:
        try:
            n=refine_once()
            print(f"done={n}")
        except Exception as e:
            print("REFINER ERROR:",repr(e))
        time.sleep(20)
