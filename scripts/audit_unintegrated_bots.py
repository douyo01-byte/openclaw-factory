from pathlib import Path
import re

ROOT = Path(".")
bots = sorted([p for p in (ROOT / "bots").glob("*.py") if p.name != "__init__.py"])
script_text = ""
for p in (ROOT / "scripts").glob("*.sh"):
    try:
        script_text += p.read_text(encoding="utf-8", errors="ignore") + "\n"
    except Exception:
        pass

la_text = ""
la_repo = ROOT / "launchagents"
if la_repo.exists():
    for p in la_repo.glob("*.plist"):
        try:
            la_text += p.read_text(encoding="utf-8", errors="ignore") + "\n"
        except Exception:
            pass

home_la = Path.home() / "Library" / "LaunchAgents"
if home_la.exists():
    for p in home_la.glob("jp.openclaw*.plist"):
        try:
            la_text += p.read_text(encoding="utf-8", errors="ignore") + "\n"
        except Exception:
            pass

print("=== unintegrated bot candidates ===")
for b in bots:
    name = b.name
    stem = b.stem
    in_runner = name in script_text or stem in script_text
    in_plist = name in la_text or stem in la_text
    if not (in_runner or in_plist):
        print(name)

print()
print("=== runner without repo track ===")
for p in sorted((ROOT / "scripts").glob("run_*")):
    if not p.exists():
        continue
    try:
        txt = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        txt = ""
    if "bots/" in txt:
        m = re.search(r"bots/([A-Za-z0-9_]+\.py)", txt)
        bot = m.group(1) if m else "-"
        print(f"{p.name} -> {bot}")

print()
print("=== launchagent templates in repo ===")
for p in sorted((ROOT / "launchagents").glob("*.plist")):
    print(p.name)
