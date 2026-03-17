# Team Role Asset Plan (2026-03-17)

## Judgment
- team系botは現時点で単体LaunchAgent復帰はしない
- ただし不要資産ではなく、role asset / source_ai asset として再利用対象
- 本流に無理につながず、必要箇所へ責務分解して吸収する

| path | asset_name | core_role | reuse_shape |
|---|---|---|---|
| bots/team/sakura_scout.py | sakura_scout | 探索・候補発見 | scout_market_v2 / 事業探索系の source_ai / persona 資産として再利用 |
| bots/team/kenji_researcher.py | kenji_researcher | 調査・裏取り | chat_research_support_v2 / 補助調査系の persona 資産として再利用 |
| bots/team/miho_finder.py | miho_finder | 発見・候補整理 | 候補抽出 / enrichment / contact整理系の source_ai 資産として再利用 |
| bots/team/daiki_analyst.py | daiki_analyst | 分析・比較 | proposal評価 / 優先度補助 / comparison用 persona 資産として再利用 |
| bots/team/aya_judge.py | aya_judge | 判定・判断補助 | judge / decision / guard補助の source_ai 資産として再利用 |

## Reuse rules
- standalone bot としては戻さない
- source_ai / persona / role prompt / classifier label として再配置する
- 復帰時は既存ACTIVE botへ吸収する
- 新規LaunchAgentを増やす前に責務重複を確認する

## Suggested mapping
- sakura_scout -> scout_market_v2
- kenji_researcher -> chat_research_support_v2
- miho_finder -> enrichment / finder support
- daiki_analyst -> analysis / ranking / proposal compare support
- aya_judge -> decision / judge / guard support

## Decision
- restore_as_standalone: no
- reuse_as_role_asset: yes
- priority: medium
