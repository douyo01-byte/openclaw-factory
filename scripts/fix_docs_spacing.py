from pathlib import Path
import re

root = Path("docs")

for p in root.rglob("*.md"):
    s = p.read_text(encoding="utf-8")

    for ch in [
        "\u2009",
        "\u200A",
        "\u200B",
        "\u200C",
        "\u200D",
        "\u00A0",
        "\u3000",
    ]:
        s = s.replace(ch, "")

    s = re.sub(r'(?<=[ぁ-んァ-ン一-龯]) +(?=[ぁ-んァ-ン一-龯])', '', s)

    p.write_text(s, encoding="utf-8")

print("docs cleaned")
