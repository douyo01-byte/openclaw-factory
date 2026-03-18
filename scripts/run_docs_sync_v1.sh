#!/bin/bash
cd /Users/doyopc/AI/openclaw-factory-docs || exit 1
/usr/bin/python3 /Users/doyopc/AI/openclaw-factory-docs/scripts/docs_compiler_v2.py >> /Users/doyopc/AI/openclaw-factory-docs/logs/docs_sync_v1.out 2>> /Users/doyopc/AI/openclaw-factory-docs/logs/docs_sync_v1.err
