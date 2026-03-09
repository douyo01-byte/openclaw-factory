import subprocess,datetime,sqlite3

DB="data/openclaw.db"

agents=[
"jp.openclaw.dev_command_executor_v1",
"jp.openclaw.dev_pr_watcher_v1",
"jp.openclaw.spec_refiner_v2",
"jp.openclaw.innovation_engine",
"jp.openclaw.code_review_engine",
"jp.openclaw.business_engine"
]

def running(label):
    out=subprocess.check_output(
        ["launchctl","list"]
    ).decode()
    return label in out

for a in agents:
    if not running(a):
        subprocess.call(
            ["launchctl","kickstart","-k","gui/"+str(subprocess.getoutput("id -u"))+"/"+a]
        )
        conn=sqlite3.connect(DB)
        c=conn.cursor()
        c.execute("""
        insert into ceo_hub_events(event,created_at)
        values(?,?)
        """,(f"restart:{a}",datetime.datetime.utcnow()))
        conn.commit()
        conn.close()
