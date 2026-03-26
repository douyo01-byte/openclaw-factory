#!/bin/bash
set -euo pipefail
msg="${1:-}"
[ -n "$msg" ] || { echo "missing commit message"; exit 1; }
git add -A
git commit -m "$msg"
git push
git status -sb
