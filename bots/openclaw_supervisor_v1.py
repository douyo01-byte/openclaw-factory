import subprocess,time,os

PROCESSES={
"self_improve":"bots/self_improve_generator_v1.py",
"business_brain":"bots/business_brain_v1.py",
"market_brain":"bots/market_brain_v1.py",
"revenue_brain":"bots/revenue_brain_v1.py",
"project_brain":"bots/project_brain_v4.py",
"llm_decider":"bots/llm_decider_v1.py",
"executor_guard":"bots/executor_guard_v2.py",
"learning_brain":"bots/learning_brain_v1.py",
"infra_brain":"bots/infra_brain_v2.py",
"mothership":"bots/mothership_brain_v2.py"
}

running={}

def start(name,script):
    print("starting",name,flush=True)
    p=subprocess.Popen(["python",script],env=os.environ)
    running[name]=p

while True:
    for name,script in PROCESSES.items():
        p=running.get(name)
        if p is None or p.poll() is not None:
            start(name,script)
    time.sleep(10)
