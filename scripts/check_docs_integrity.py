from pathlib import Path
import re
import sys

ROOT = Path(".")
DOCS = ROOT / "docs"
INDEX = DOCS / "00_INDEX.md"

if not INDEX.exists():
    print("ERROR: docs/00_INDEX.md not found")
    sys.exit(1)

text = INDEX.read_text(encoding="utf-8")

sections = {
    "Core": [],
    "Rules": [],
    "Reference Recovered": [],
}

current = None
for line in text.splitlines():
    if line.strip() == "## Core":
        current = "Core"
        continue
    if line.strip() == "## Rules":
        current = "Rules"
        continue
    if line.strip() == "## Reference Recovered":
        current = "Reference Recovered"
        continue
    m = re.match(r"^- (.+\.md)$", line.strip())
    if m and current:
        sections[current].append(m.group(1))

errors = []
seen = set()

for sec, files in sections.items():
    for rel in files:
        p = DOCS / rel
        seen.add(str(p))
        if not p.exists():
            errors.append(f"MISSING [{sec}] {rel}")

core_expected = {
    "docs/00_INDEX.md",
    "docs/01_SYSTEM_PROMPT.md",
    "docs/01_SINGLE_SOURCE_OF_TRUTH.md",
    "docs/02_MASTER_PLAN.md",
    "docs/02_ROLE_REGISTRY.md",
    "docs/03_SYSTEM_OVERVIEW.md",
    "docs/06_CURRENT_STATE.md",
    "docs/08_HANDOVER.md",
    "docs/10_RUNTIME_AUDIT_STATUS.md",
    "docs/11_OPERATIONS.md",
    "docs/12_TELEGRAM_OS_EXEC_PLAN.md",
    "docs/05_DEV_RULES.md",
    "docs/17_EFFICIENCY_RULES.md",
    "docs/19_WORK_START_PROMPT.md",
    "docs/20_DAILY_OPERATION.md",
    "docs/20_DOCS_POLICY_20260313.md",
}

for rel in sorted(core_expected):
    if not Path(rel).exists():
        errors.append(f"EXPECTED CORE FILE MISSING {rel}")

overview = DOCS / "03_SYSTEM_OVERVIEW.md"
if overview.exists():
    ov = overview.read_text(encoding="utf-8")
    if "Referenceの定義" not in ov:
        errors.append("03_SYSTEM_OVERVIEW.md missing reference definition section")

policy = DOCS / "20_DOCS_POLICY_20260313.md"
if policy.exists():
    pt = policy.read_text(encoding="utf-8")
    if "Anti-loss rule" not in pt:
        errors.append("20_DOCS_POLICY_20260313.md missing Anti-loss rule")

handover = DOCS / "08_HANDOVER.md"
if handover.exists():
    ht = handover.read_text(encoding="utf-8")
    if "2026-04-02 docs再構築" not in ht:
        errors.append("08_HANDOVER.md missing 2026-04-02 docs reconstruction entry")

ref_dir = DOCS / "reference_recovered"
if ref_dir.exists():
    for p in sorted(ref_dir.rglob("*.md")):
        if p.name == "00_RECOVERY_SUMMARY.md":
            continue
        t = p.read_text(encoding="utf-8", errors="replace")
        if "現在の正" in t and "snapshot" not in (DOCS / "03_SYSTEM_OVERVIEW.md").read_text(encoding="utf-8", errors="replace"):
            errors.append(f"REFERENCE MAY BE MISREAD AS TRUTH {p.relative_to(ROOT)}")

print("===== DOCS INTEGRITY REPORT =====")
for sec, files in sections.items():
    print(f"{sec}: {len(files)}")

if errors:
    print("RESULT: NG")
    for e in errors:
        print(f"- {e}")
    sys.exit(1)

print("RESULT: OK")
