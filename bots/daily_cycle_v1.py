#!/usr/bin/env python3
import os
import subprocess
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, cwd=ROOT)
    if p.returncode != 0:
        raise SystemExit(p.returncode)

def main() -> None:
    # 1) role_training (候補取得→学習/ブリーフ更新)
    run([__import__("sys").executable, "-m", "bots.role_training_v1", "--db", "data/openclaw.db", "--role", "all", "--limit", "5"])

    # 2) meeting (会議生成)
    run([__import__("sys").executable, "-m", "bots.meeting_from_db_v1"])

    # 3) chat_research（未処理job消化）
    # ※ モジュール名が違う場合はここだけ直す
    run([__import__("sys").executable, "-m", "bots.chat_research_v1"])

    # 4) reflection (自動反省会)
    run([__import__("sys").executable, "-m", "bots.reflection_v1", "--limit", "50"])

    # 5) reflection worker (生成)
    run([__import__("sys").executable, "-m", "bots.reflection_worker_v1", "--limit", "5"])

    # 4) healthcheck（生存ログ）
    print(f"[daily_cycle] OK {datetime.now().isoformat()}")

if __name__ == "__main__":
    main()
