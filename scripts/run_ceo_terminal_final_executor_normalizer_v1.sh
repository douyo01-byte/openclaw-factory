#!/bin/zsh
cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
export DB_PATH=/Users/doyopc/AI/openclaw-factory/data/openclaw.db
python3 bots/ceo_terminal_final_executor_normalizer_v1.py >> logs/ceo_terminal_final_executor_normalizer_v1.out 2>> logs/ceo_terminal_final_executor_normalizer_v1.err
