import os,sqlite3,subprocess,requests,datetime

DB="data/openclaw.db"
REPO="douyo01-byte/openclaw-factory"
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

def create_branch(name):
    subprocess.check_call(["git","checkout","-b",name])
def commit_push(name):
    subprocess.check_call(["git","add","-A"])
    subprocess.check_call(["git","commit","-m",f"auto: {name}"])
    subprocess.check_call(["git","push","-u","origin",name])
def create_pr(name):
    subprocess.check_call([
        "gh","pr","create",
        "--title",f"[auto] {name}",
        "--body","auto generated",
        "--base","main",
        "--head",name
    ])

def main():
    conn=sqlite3.connect(DB)
    rows=conn.execute("select target from decisions where decision='adopt'").fetchall()
    for (target,) in rows:
        branch="auto-"+datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        code=llm(target)
        create_branch(branch)
        open("autogen.py","w").write(code)
        commit_push(branch)
        create_pr(branch)
        conn.execute("update decisions set decision='pr_created' where target=?",(target,))
    conn.commit()
    conn.close()

if __name__=="__main__":
    main()
