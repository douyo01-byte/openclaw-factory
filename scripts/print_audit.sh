#!/usr/bin/env bash
set -euo pipefail
cd "${HOME}/AI/openclaw-factory"
git grep -n "print" -- '*.py' || true
