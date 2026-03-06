import os,time,sqlite3,requests,json

DB=os.environ.get("FACTORY_DB_PATH") or os.environ.get("DB_PATH") or "data/openclaw.db"
OPENAI_API_KEY=(os.environ.get("OPENAI_API_KEY") or "").strip()
OPENAI_MODEL=(os.environ.get("OPENAI_MODEL") or "gpt-4o-mini").strip()

def conn():
    c=sqlite3.connect(DB,timeout=30)
    c.row_factory=sqlite3.Row
    try:
        c.execute("PRAGMA busy_timeout=30000")
    except Exception:
        pass
    try:
        c.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    return c

def ask_llm(prompt:str)->str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY empty")
    r=requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization":f"Bearer {OPENAI_API_KEY}",
            "Content-Type":"application/json",
        },
        json={
            "model":OPENAI_MODEL,
            "temperature":0.2,
            "messages":[
                {
                    "role":"system",
                    "content":"You refine software development specifications. Return only the refined specification in plain text. Be concrete, implementation-oriented, and concise but complete."
                },
                {
                    "role":"user",
                    "content":prompt
                }
            ]
        },
        timeout=120,
    )
    r.raise_for_status()
    j=r.json()
    return j["choices"][0]["message"]["content"].strip()

def render_conversation(c,pid:int)->str:
    rows=c.execute(
        """
        select role,message,created_at
        from proposal_conversation
        where proposal_id=?
        order by id asc
        limit 50
        """,
        (pid,)
    ).fetchall()
    out=[]
    for r in rows:
        out.append(f"[{r['created_at']}] {r['role']}: {r['message']}")
    return "\n".join(out).strip()

def pick_rows(c):
    return c.execute(
        """
        select
          d.id as proposal_id,
          coalesce(d.title,'') as title,
          coalesce(d.description,'') as description,
          coalesce(d.spec,'') as existing_spec,
          coalesce(d.spec_stage,'') as spec_stage,
          coalesce(d.dev_stage,'') as dev_stage,
          coalesce(ps.stage,'') as proposal_stage,
          coalesce(ps.pending_question,'') as pending_question,
          coalesce(ps.pending_questions,'') as pending_questions
        from dev_proposals d
        left join proposal_state ps on ps.proposal_id=d.id
        where d.status='approved'
          and (
            (coalesce(d.spec,'')='' and coalesce(ps.stage,'') in ('','approved','refined','waiting_answer'))
            or coalesce(ps.stage,'')='answer_received'
          )
        order by
          case when coalesce(ps.stage,'')='answer_received' then 0 else 1 end,
          d.id asc
        limit 3
        """
    ).fetchall()

def build_prompt(r,conversation:str)->str:
    return f"""
proposal_id:
{r["proposal_id"]}

title:
{r["title"]}

description:
{r["description"]}

existing_spec:
{r["existing_spec"]}

proposal_state.stage:
{r["proposal_stage"]}

pending_question:
{r["pending_question"]}

pending_questions:
{r["pending_questions"]}

conversation:
{conversation}

task:
Refine this into a single implementation-ready development specification.

requirements:
- absorb the latest user answers from conversation
- if the user answered a pending question, reflect that answer directly
- keep the spec actionable for implementation
- include goal, scope, behavior, inputs/outputs, edge cases, logging policy, files to change, and acceptance criteria
- plain text only
""".strip()

def refine_once():
    done=0
    with conn() as c:
        rows=pick_rows(c)
        print(f"rows={len(rows)}", flush=True)
        for r in rows:
            pid=int(r["proposal_id"])
            conversation=render_conversation(c,pid)
            prompt=build_prompt(r,conversation)
            spec=ask_llm(prompt)
            c.execute(
                """
                update dev_proposals
                set spec=?,
                    spec_stage='refined'
                where id=?
                """,
                (spec,pid),
            )
            c.execute(
                """
                insert into proposal_state(proposal_id,stage,pending_question,pending_questions,updated_at)
                values(?,?,?, ?,datetime('now'))
                on conflict(proposal_id) do update set
                  stage=excluded.stage,
                  pending_question=excluded.pending_question,
                  pending_questions=excluded.pending_questions,
                  updated_at=datetime('now')
                """,
                (pid,"refined","",""),
            )
            c.execute(
                """
                insert into proposal_conversation(proposal_id,role,message,created_at)
                values(?,?,?,datetime('now'))
                """,
                (pid,"assistant","[spec_refiner_v2] refined"),
            )
            print(f"refined id={pid} spec_len={len(spec)}", flush=True)
            done+=1
        c.commit()
    return done

if __name__=="__main__":
    while True:
        try:
            n=refine_once()
            print(f"done={n}", flush=True)
        except Exception as e:
            print("REFINER ERROR:",repr(e), flush=True)
        time.sleep(20)
