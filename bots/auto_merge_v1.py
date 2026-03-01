import subprocess,json

def get_open_auto_prs():
    out=subprocess.check_output([
        "gh","pr","list",
        "--state","open",
        "--json","number,headRefName"
    ])
    prs=json.loads(out)
    return [p for p in prs if p["headRefName"].startswith("auto-")]

def ci_success(pr_number):
    out=subprocess.check_output([
        "gh","pr","checks",str(pr_number),
        "--json","state"
    ])
    checks=json.loads(out)
    return all(c["state"]=="SUCCESS" for c in checks)

def main():
    prs=get_open_auto_prs()
    for pr in prs:
        n=pr["number"]
        if ci_success(n):
            subprocess.call(["gh","pr","merge",str(n),"--merge","--admin"])

if __name__=="__main__":
    main()
