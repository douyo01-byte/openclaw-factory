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
  NOW="$(date '+%Y-%m-%d %H:%M:%S')"
  case "$MODE" in
    lpgen_exec)
      FILE="tmp_exec/lp_$(date +%Y%m%d_%H%M%S)_$$.txt"
      {
        echo "[LPGEN]"
        echo "task: $TASK"
        echo "generated_at: $NOW"
        echo "目的"
        echo "- 次 に 試 す 改 善 案 を 3件 に 絞 る 。"
        echo
        echo "改善案1"
        echo "- 仮説: ヒ ー ロ ー 見 出 し を 価 値 直 球 型 に 変 え る と 1st view の 離 脱 が 減 る 。"
        echo "- 変更点: 見 出 し / サ ブ 見 出 し / CTA文 言 を 一 貫 化 。"
        echo "- 計測: CTR / CVR / ス ク ロ ー ル 率 。"
        echo
        echo "改善案2"
        echo "- 仮説: 証 拠 を 上 に 上 げ る と 不 安 が 下 が り CTA率 が 上 が る 。"
        echo "- 変更点: 口 コ ミ / 実 績 / FAQ を CTA手 前 に 再 配 置 。"
        echo "- 計測: CTA CTR / 滞 在 時 間 / FAQ到 達 率 。"
        echo
        echo "改善案3"
        echo "- 仮説: CTA直 前 の 障 壁 除 去 を 強 め る と CVR が 上 が る 。"
        echo "- 変更点: 保 証 / 初 回 特 典 / 購 入 後 の 流 れ を 明 示 。"
        echo "- 計測: CTA CTR / CVR / 離 脱 率 。"
        echo
        echo "優先順位"
        echo "- 1位: 改善案1"
        echo "- 2位: 改善案2"
        echo "- 3位: 改善案3"
        echo
        echo "次の実作業"
        echo "- AB文面 を 3案 作 る 。"
        echo "- 反 映 箇 所 を HTML 上 で 特 定 す る 。"
        echo "- 計 測 イ ベ ン ト 名 を 固 定 し て evaluate 対 象 に す る 。"
      } > "$FILE"
      ;;
    runbook_gen_exec)
      FILE="tmp_exec/runbook_$(date +%Y%m%d_%H%M%S)_$$.txt"
      {
        echo "[RUNBOOK]"
        echo "task: $TASK"
        echo "generated_at: $NOW"
        echo "目 的"
        echo "- 実 行 知 見 を 再 利 用 可 能 な 形 で 残 す 。"
        echo "記 録 項 目"
        echo "1. 実 施 内 容"
        echo "- $TASK"
        echo "2. 有 効 だ っ た 理 由"
        echo "- 勝 者 ま た は 改 善 要 因 を 一 文 で 要 約 す る 。"
        echo "3. 再 利 用 条 件"
        echo "- 類 似 LP / 類 似 訴 求 / 類 似 KPI改 善 時 に 流 用 す る 。"
        echo "4. 注 意 点"
        echo "- 実 デ ー タ 閾 値 と 人 の 最 終 確 認 を 併 用 す る 。"
        echo "登 録 テ ン プ レ"
        echo "- title: $TASK"
        echo "- summary: 実 行 結 果 か ら 得 た 知 見 を 次 回 施 策 へ 転 用 す る 。"
        echo "- reuse_when: 類 似 案 件 で 同 じ 勝 ち 筋 が 見 え た 時 。"
        echo "- caution: 閾 値 未 達 の 状 態 で 自 動 本 番 反 映 し な い 。"
      } > "$FILE"
      ;;
    ctogen_exec)
      FILE="tmp_exec/cto_$(date +%Y%m%d_%H%M%S)_$$.txt"
      {
        echo "[CTO TASK]"
        echo "task: $TASK"
        echo "generated_at: $NOW"
        echo "目 的"
        echo "- 実 装 前 に dry-run で 安 全 確 認 す る 。"
        echo "実 施 方 針"
        echo "1. 対 象 確 認"
        echo "- $TASK"
        echo "2. 確 認 項 目"
        echo "- 入 力 条 件"
        echo "- 依 存 関 係"
        echo "- 既 存 処 理 へ の 影 響"
        echo "- ロ ー ル バ ッ ク 可 否"
        echo "出 力 物"
        echo "- 実 行 メ モ"
        echo "- 差 分 要 約"
        echo "- 次 の 実 作 業"
        echo "次 の 実 作 業"
        echo "- 実 対 象 を 洗 い 出 す 。"
        echo "- dry-run結 果 を 保 存 す る 。"
        echo "- 問 題 な け れ ば 本 実 装 へ 接 続 す る 。"
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
