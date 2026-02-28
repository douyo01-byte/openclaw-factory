import subprocess

def changed_files():
    r = subprocess.run(["git", "diff", "--name-only"], capture_output=True, text=True)
    files = [x for x in r.stdout.splitlines() if x.strip()]
    return files

def evaluate_risk(files=None):
    files = files if files is not None else changed_files()
    risk = "low"
    for f in files:
        lf = f.lower()
        if "requirements" in lf or ".env" in lf or "secret" in lf or ".github/workflows" in lf:
            return "high"
        if "schema" in lf or "migrations" in lf or "db" in lf:
            risk = "medium"
    return risk
