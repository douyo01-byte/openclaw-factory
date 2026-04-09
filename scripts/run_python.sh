#!/usr/bin/env bash
set -euo pipefail

ARG="${1:-}"

cd /Users/doyopc/AI/openclaw-factory-daemon || exit 1
mkdir -p tmp_exec

if [[ -z "$ARG" ]]; then
  echo "invalid arg"
  exit 1
fi

if [[ "$ARG" == file=* ]]; then
  FILE="${ARG#file=}"
  /usr/bin/python3 "$FILE"
  echo "run_python_ok file=$FILE"
  exit 0
fi

if [[ "$ARG" == mode=* ]]; then
  MODE="$(printf '%s' "$ARG" | sed -E 's/^mode=([^;]+).*/\1/')"
  TASK="$(printf '%s' "$ARG" | sed -E 's/^mode=[^;]+;task=//')"

  case "$MODE" in
    lpgen_exec)
      FILE="tmp_exec/lp_$(date +%Y%m%d_%H%M%S)_$$.txt"
      {
        echo "[LPGEN]"
        echo "$TASK"
      } > "$FILE"
      ;;
    runbook_gen_exec)
      FILE="tmp_exec/runbook_$(date +%Y%m%d_%H%M%S)_$$.txt"
      {
        echo "[RUNBOOK]"
        echo "$TASK"
      } > "$FILE"
      ;;
    ctogen_exec)
      FILE="tmp_exec/cto_$(date +%Y%m%d_%H%M%S)_$$.txt"
      {
        echo "[CTO TASK]"
        echo "$TASK"
      } > "$FILE"
      ;;
    *)
      echo "unknown mode:$MODE"
      exit 1
      ;;
  esac

  echo "generated:$FILE"
  exit 0
fi

echo "invalid arg:$ARG"
exit 1
