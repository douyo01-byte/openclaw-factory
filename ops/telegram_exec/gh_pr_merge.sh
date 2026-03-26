#!/bin/bash
set -euo pipefail
pr="${1:-}"
[ -n "$pr" ] || { echo "missing pr number"; exit 1; }
gh pr merge "$pr" --squash --delete-branch
git switch main
git pull --ff-only origin main
git status -sb
git log --oneline --decorate -5
