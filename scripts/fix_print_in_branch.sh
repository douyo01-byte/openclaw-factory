#!/usr/bin/env bash
set -euo pipefail
branch="${1:?branch}"
git checkout "$branch"
git grep -n 'print(' -- '*.py' || exit 0
files="$(git grep -l 'print(' -- '*.py' || true)"
[ -z "$files" ] && exit 0
perl -pi -e 's/\bprint\((.*?)\);?$/logging.getLogger(__name__).info($1)/' $files || true
python -m py_compile $(git ls-files '*.py')
git add -A
git commit -m "Replace print() with logging" || exit 0
git push
