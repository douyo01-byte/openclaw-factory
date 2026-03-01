import os,sqlite3,subprocess,requests,datetime

DB="data/openclaw.db"
OPENAI=os.getenv("OPENAI_API_KEY")

def llm(spec):
    r=requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization":f"Bearer {OPENAI}",
            "Content-Type":"application/json"
        },
        json={
            "model":"gpt-4.1-mini",
            "input":f"Generate minimal production-ready python file only.\n{spec}"
        }
    )
    data=r.json()
    if "output" not in data:
        raise Exception(data)
    return data["output"][0]["content"][0]["text"]

def main():
    conn=sqlite3.connect(DB)
    row=conn.execute(
        "select target from decisions where decision='adopt' limit 1"
    ).fetchone()

    if not row:
        conn.close()
        return

    target=row[0]
    branch="auto-"+datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    code=llm(target)

    subprocess.check_call(["git","checkout","-b",branch])
    open("autogen.py","w").write(code)
    subprocess.check_call(["git","add","-A"])
    subprocess.check_call(["git","commit","-m",f"auto: {branch}"])
    subprocess.check_call(["git","push","-u","origin",branch])
    subprocess.check_call([
        "gh","pr","create",
        "--title",f"[auto] {target[:50]}",
        "--body","auto generated",
        "--base","main",
        "--head",branch
    ])

    conn.execute(
        "update decisions set decision='pr_created' where target=?",
        (target,)
    )
    conn.commit()
    conn.close()

if __name__=="__main__":
    main()
