#!/bin/bash
set -euo pipefail
cd "$HOME/AI/openclaw-factory-daemon" || exit 1
exec "$HOME/AI/openclaw-factory-daemon/.venv/bin/python" bots/fortune_text_normalizer_v1.py
