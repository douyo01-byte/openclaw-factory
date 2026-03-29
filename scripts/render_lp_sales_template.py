from __future__ import annotations
import json
import re
import sys
from pathlib import Path

PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")

def collect_keys(template_text: str) -> list[str]:
    seen = set()
    out = []
    for m in PLACEHOLDER_RE.finditer(template_text):
        k = m.group(1)
        if k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out

def normalize_rendered_html(s: str) -> str:
    s = s.replace("\r", "")
    s = re.sub(r'[　 ]+', ' ', s)
    s = re.sub(r' *\n *', '\n', s)
    return s

def render(template_path: str, out_path: str, values: dict[str, str]) -> None:
    p = Path(template_path)
    s = p.read_text(encoding="utf-8")
    keys = collect_keys(s)
    for k in keys:
        s = s.replace("{{" + k + "}}", str(values.get(k, "")))
    s = normalize_rendered_html(s)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(s, encoding="utf-8")
    print(f"rendered {out}")

def main() -> None:
    if len(sys.argv) in (4, 5) and sys.argv[1] == "--json":
        template_path = sys.argv[2]
        json_path = sys.argv[3]
        payload = json.loads(Path(json_path).read_text(encoding="utf-8"))
        out_path = sys.argv[4] if len(sys.argv) == 5 else payload["OUT_PATH"]
        render(template_path, out_path, payload)
        return

    if len(sys.argv) < 4:
        raise SystemExit(
            "usage:\n"
            "  render_lp_sales_template.py --json <template> <json_path> [out_path]\n"
            "  render_lp_sales_template.py <template> <out> <KEY=VALUE> ..."
        )

    template_path = sys.argv[1]
    out_path = sys.argv[2]
    values: dict[str, str] = {}
    for arg in sys.argv[3:]:
        if "=" not in arg:
            raise SystemExit(f"invalid_arg:{arg}")
        k, v = arg.split("=", 1)
        values[k] = v
    render(template_path, out_path, values)

if __name__ == "__main__":
    main()
