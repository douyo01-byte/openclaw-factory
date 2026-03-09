#!/usr/bin/env bash
cd ~/AI/openclaw-factory-daemon || exit 1

source .venv/bin/activate

while true
do
python bots/revenue_engine_v1.py
sleep 21600
done
