#!/bin/bash
cd /Users/doyopc/AI/openclaw-factory
export PATH="/opt/homebrew/bin:/usr/bin:/bin"
export PYTHONUNBUFFERED=1
export PYTHONPATH=/Users/doyopc/AI/openclaw-factory
set -a
source .env.openclaw
exec /bin/bash -lc "source .venv/bin/activate && sed -i '' 's/\"gh\"/\"\/opt\/homebrew\/bin\/gh\"/g' bots/dev_executor_v1.py && python bots/dev_executor_v1.py"
