#!/usr/bin/env python3
import glob
import html
from pathlib import Path

OUTDIR = Path("public_preview/revenue_lp")
OUTDIR.mkdir(parents=True, exist_ok=True)

files = sorted(glob.glob("tmp_exec/lp_*.txt"))[-20:]

for fp in files:
    txt = Path(fp).read_text(errors="ignore")

    title = Path(fp).stem

    body = html.escape(txt)

    html_doc = f"""
<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{
  font-family: sans-serif;
  background:#111;
  color:#eee;
  padding:40px;
  line-height:1.7;
}}
pre {{
  white-space:pre-wrap;
  background:#1a1a1a;
  padding:24px;
  border-radius:12px;
}}
h1 {{
  color:#7dd3fc;
}}
</style>
</head>
<body>
<h1>{title}</h1>
<pre>{body}</pre>
</body>
</html>
"""

    out = OUTDIR / f"{title}.html"
    out.write_text(html_doc)

print(f"generated={len(files)}")
