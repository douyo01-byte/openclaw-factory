import os,subprocess,sys,json,re

MAX_FILES=int(os.environ.get("OCLAW_MAX_FILES","20"))
MAX_ADDED=int(os.environ.get("OCLAW_MAX_ADDED","400"))
MAX_DELETED=int(os.environ.get("OCLAW_MAX_DELETED","200"))

DENY=[
 r"^\.env$",
 r"^\.env\..+",
 r"^data/.*\.db$",
 r"^secrets/.*",
 r"^\.github/workflows/.*",
 r"^requirements\.txt$",
 r"^requirements-dev\.txt$",
 r"^Dockerfile$",
 r"^docker-compose\.yml$",
 r"^\.ssh/.*",
 r"^id_rsa$",
 r"^id_ed25519$",
]

SECRET_PATTERNS=[
 r"ghp_[A-Za-z0-9]{30,}",
 r"gho_[A-Za-z0-9]{30,}",
 r"AIza[0-9A-Za-z\-_]{35}",
 r"-----BEGIN (RSA|OPENSSH|EC) PRIVATE KEY-----",
 r"TELEGRAM_BOT_TOKEN\s*=\s*['\"]?\d+:[A-Za-z0-9_\-]{20,}",
]

def sh(*cmd):
    return subprocess.check_output(cmd, text=True).strip()

def changed_files():
    z=sh("git","diff","--name-only","--diff-filter=ACMRT","--")
    return [x for x in z.splitlines() if x]

def stats():
    s=sh("git","diff","--numstat","--")
    a=d=0
    files=0
    for line in s.splitlines():
        if not line: 
            continue
        aa,dd,_=line.split("\t",2)
        if aa.isdigit(): a+=int(aa)
        if dd.isdigit(): d+=int(dd)
        files+=1
    return files,a,d

def deny_match(p):
    for rx in DENY:
        if re.search(rx,p):
            return rx
    return None

def scan_secrets(paths):
    if not paths:
        return []
    out=[]
    for p in paths:
        try:
            t=open(p,"r",encoding="utf-8",errors="ignore").read()
        except Exception:
            continue
        for rx in SECRET_PATTERNS:
            if re.search(rx,t):
                out.append((p,rx))
    return out

def main():
    files,a,d=stats()
    paths=changed_files()
    bad=[]
    for p in paths:
        rx=deny_match(p)
        if rx:
            bad.append(("deny_path",p,rx))
    if files>MAX_FILES:
        bad.append(("too_many_files",str(files),f"MAX_FILES={MAX_FILES}"))
    if a>MAX_ADDED:
        bad.append(("too_many_added",str(a),f"MAX_ADDED={MAX_ADDED}"))
    if d>MAX_DELETED:
        bad.append(("too_many_deleted",str(d),f"MAX_DELETED={MAX_DELETED}"))
    sec=scan_secrets(paths)
    for p,rx in sec:
        bad.append(("secret_detected",p,rx))
    if bad:
        print(json.dumps({"ok":False,"violations":bad},ensure_ascii=False))
        sys.exit(2)
    print(json.dumps({"ok":True,"files":files,"added":a,"deleted":d},ensure_ascii=False))

if __name__=="__main__":
    main()
