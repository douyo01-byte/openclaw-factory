#!/usr/bin/env bash
set -euo pipefail
pr="${1:?pr_number}"
tag="AUTOREVIEW:OK:${pr}"
if gh pr view "$pr" --json comments --jq '.comments[].body' | grep -Fq "$tag"; then
  exit 0
fi
python -m bots.dev_reviewer_v1 --pr "$pr"
gh pr comment "$pr" -b "$tag"
