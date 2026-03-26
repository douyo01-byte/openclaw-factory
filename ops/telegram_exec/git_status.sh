#!/bin/bash
set -euo pipefail
git status -sb
echo
git log --oneline --decorate -5
