#!/usr/bin/env bash
cd ~/AI/openclaw-factory-daemon || exit 1

source .venv/bin/activate

while true
do
python bots/innovation_engine_v1.py
sleep 7200
done
