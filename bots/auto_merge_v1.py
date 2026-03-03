import subprocess,json
import time

def _run(args, tries=4, base_sleep=2):
    for k in range(tries):
        try:
            return subprocess.check_output(args)
        except subprocess.CalledProcessError as e:
            msg=(getattr(e,'output',b'') or b'').decode('utf-8','ignore')
            if 'HTTP 502' in msg or '502 Bad Gateway' in msg or 'api.github.com/graphql' in msg:
                time.sleep(base_sleep*(2**k))
                continue
            raise
    return b''

def pr_mergeable(pr_number):
    out=_run([
        "gh","pr","view",str(pr_number),
        "--json","mergeable,mergeStateStatus"
    ])
    try:
        x=json.loads(out)
    except Exception:
        return ("UNKNOWN","UNKNOWN")
    return (x.get("mergeable") or "UNKNOWN", x.get("mergeStateStatus") or "UNKNOWN")

def get_open_auto_prs():
    out=_run([
        "gh","pr","list",
        "--state","open",
        "--json","number,headRefName"
    ])
    prs=json.loads(out)
    return [p for p in prs if p["headRefName"].startswith("auto-")]

def ci_success(head_ref):
    out=_run([
        "gh","run","list",
        "--workflow","ci.yml",
        "--branch",head_ref,
        "--limit","1",
        "--json","status,conclusion"
    ])
    try:
        xs=json.loads(out)
    except Exception:
        return False
    if not xs:
        return False
    x=xs[0]
    return x.get("status")=="completed" and x.get("conclusion")=="success"
    return bool(checks) and all(c.get("state")=="SUCCESS" for c in checks)

def main():
    prs=get_open_auto_prs()
    for pr in prs:
        n=pr["number"]
        if ci_success(pr["headRefName"]):
            m,ms=pr_mergeable(n)
            if m=="MERGEABLE" and ms=="CLEAN":
                subprocess.call(["gh","pr","merge",str(n),"--merge","--admin"])
            else:
                subprocess.call(["gh","pr","merge",str(n),"--merge","--auto"])

if __name__=="__main__":
    main()
