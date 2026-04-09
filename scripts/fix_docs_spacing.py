from pathlib import Path

for p in Path("docs").rglob("*.md"):
    s = p.read_text(encoding="utf-8")
    s = s.replace("  ", " ")
    p.write_text(s, encoding="utf-8")

print("spacing_fixed")
