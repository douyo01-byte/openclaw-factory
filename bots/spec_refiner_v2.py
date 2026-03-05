import os,time,sqlite3,requests,json

DB=os.environ.get("DB_PATH")

OPENAI=os.environ.get("OPENAI_API_KEY")

def conn():
    c=sqlite3.connect(DB)
    c.row_factory=sqlite3.Row
    return c

def ask_llm(text):
    r=requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization":f"Bearer {OPENAI}",
            "Content-Type":"application/json"
        },
        json={
            "model":"gpt-4o-mini",
            "messages":[
                {"role":"system","content":"You refine software specifications."},
                {"role":"user","content":text}
            ]
        },
        timeout=60
    )
    return r.json()["choices"][0]["message"]["content"]

while True:

    try:
        with conn() as c:

            rows=c.execute(
            """
            select id,title,description
            from dev_proposals
            where status='approved'
            and (spec is null or spec='')
            limit 3
            """
            ).fetchall()

            for r in rows:

                prompt=f"""
                proposal:
                {r["title"]}

                description:
                {r["description"]}

                produce a refined development specification.
                """

                spec=ask_llm(prompt)

                c.execute(
                "update dev_proposals set spec=? where id=?",
                (spec,r["id"])
                )

            c.commit()

    except Exception as e:
        pass

    time.sleep(20)
