import os,sqlite3,time,subprocess,sys
DB=os.environ.get("DB_PATH") or os.environ.get("OCLAW_DB_PATH")
CORE=os.environ.get("OCLAW_REPO_PATH")
def run(pid):
    subprocess.call([sys.executable,"-m","spec_refiner_v2",str(pid)],cwd=CORE,env=dict(os.environ,PYTHONPATH=CORE))
def main():
    while True:
        try:
            conn=sqlite3.connect(DB)
            rows=conn.execute("select proposal_id from proposal_state where stage='answer_received' limit 20").fetchall()
            conn.close()
            if not rows:
                print("REFINED 0",flush=True)
                time.sleep(5)
                continue
            for r in rows:
                run(r[0])
        except Exception as e:
            print(str(e),flush=True)
            time.sleep(5)
if __name__=="__main__":
    main()
