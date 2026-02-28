#!/usr/bin/env bash
set -euo pipefail
pr="${1:?pr_number}"
j="$(gh pr view "$pr" --json mergeable,mergeStateStatus,statusCheckRollup,reviewDecision,state --jq '.')"
echo "$j" | jq -e '.state=="OPEN"' >/dev/null
echo "$j" | jq -e '.mergeable=="MERGEABLE"' >/dev/null
echo "$j" | jq -e '.mergeStateStatus=="CLEAN" or .mergeStateStatus=="UNSTABLE"' >/dev/null
echo "$j" | jq -e '(.statusCheckRollup|length)==0 or all(.statusCheckRollup[]; .status=="COMPLETED" and .conclusion=="SUCCESS")' >/dev/null
if echo "$j" | jq -e '.reviewDecision=="CHANGES_REQUESTED"' >/dev/null; then exit 1; fi
gh pr merge "$pr" --merge --delete-branch
