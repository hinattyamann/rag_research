# Phase 11 使用済み英語Traceの既知回帰・事前計画

2026年10月21日。v6の既知/日英人工診断通過後、未使用QAの前に旧実例を確認する。
Sourceは既存の固定Traceだけ。新規検索・初回再生成・Reference注入・品質再採点を行わない。

## 対象とExpectedの来歴

既存GPU20問のうち固定文を持つ12問をすべて使う。残る裸拒否8問もPlanへID/Trace/Score nullを保持し、
別の拒否Fallback検証へ渡す。既知GPU12問の中から成功しそうな例を選ばない。
これに、既に記録された旧DevelopmentのArmistice・暖鋒・Tar Heelsの3問を加える。
合計15 QA/42固定文。過去の正例と誤りを含み、v6のCouncil/Zidaneも再検証する。

旧GPUの34単位は保存AI監査のExpected/理由/曖昧Flagをそのまま再利用する。
曖昧5単位は事前どおり採用の正解率から外すが、Model入力・固定文集合・F分母から外さない。
追加3問8単位のExpectedは同じCodex AIが全実使用根拠から事前に保存した。
Armisticeの誤調印時刻2文は矛盾、日付へのtrue結論は支持。暖鋒の接近は支持、通過後の持続雨という列の混同は矛盾。
Tar Heelsの確定的な語源と、異なる伝説をつなぐ句の来歴は支持不足、侮蔑語から誇りへの転用は支持。
未知の語源を矛盾に読み替えず、現行の支持/矛盾/支持不足の定義を保持する。

Expectedは人手正解ではない。`human_reviewed=false`、採点Model IDは取得不能、同じ開発履歴を共有している。
旧結果を既に知るAIの注釈であり、独立・盲検の人手精度評価とはしない。対象3問の新候補出力はまだ生成していない。
全Expected/原Trace・旧監査HashをPlanへ結び、読込み時にも旧34単位の不変とTrace全文/文単位の一致を再検証する。

## 前提・実行・採用基準

- 前提は固定772d1a7のv6診断Report/Manifest Hash、128 Call完了・既知4/4・日英人工基準の通過。
  同じModel/Runtime/Prompt/Schema/予算/Seedを使い、評価・生成・入力構築・保存のCore Sourceも照合する。
- 各QAの質問/初回回答・全固定文・全根拠本文/ID/Titleを保持し、元/逆の提示順だけを変える。
  読解の内部生成結果はその試行内で全単位へ共用し、別試行の読解をCacheしない。
- すべての明確な非支持8単位をCriticalとする。6 QA×2順序=12 Critical条件の全Expected一致後だけ残る正例QAへ進む。
  健全性/形式/実Token超過は即停止、Retry0。未知結果を再試行せず、未試行分も保存する。
- 全37確定単位×2順序=74判定の正確Label一致90%以上、うち支持29単位×2=58判定の支持一致90%以上、
  明確な非支持の誤支持0、Critical全一致、全予定完了・Task失敗/Overflow0をすべて必要とする。
  正例を分けて確認し、すべて棄却する評価器を多数の負例で高精度に見せない。
- Fは42固定文の各QA内全分母で計算する。曖昧単位の採用集計除外とFの分母を混ぜない。
  意味の診断が通っても、F/閾値により誤りを含む回答を採用する場合がある。品質/経路の評価は別に行う。

全30条件、読解30+固定文84=最大114 Completion。負例を先行し、不通過時の正例未試行も明記する。
Context12288・読解4096/判定3072・推論1536・Seed42・CUDA全層を維持する。
v6実測27.43分/128 Callと実例の入力長から30〜60分程度を見積もるが、実時間/Tokenは改めて保存する。
まず固定Commitの専用Worktreeで全114入力の生成0 Preflightを行う。超過時は切詰めず保存して停止する。
予算やModel等を変える場合は別条件として事前保存し、必要なv6相当の再診断から行う。

入口は共通`run_semantic_diagnostics.py`、Configは`phase11_known_trace_candidate_v1.yaml`、
Plan/Expectedは`phase11_known_trace_regression_v1.json`/`phase11_known_trace_expected_v1.json`。
新規9 Testで通過/停止・再開、前提/Model/Core/旧Expected/設定/基準の改変拒否、正例精度を別に確認する条件を検証した。
旧v6のCoreとRunは固定Worktreeに保持する。新規Calibrationや最終Gateの通過は、この回帰だけでは確定しない。

## 実走v1の停止結果

固定2ae5133の全114入力/生成0 Preflightは通過したが、5/30条件目の読解が最終JSON配列で始まり、
条件付きGrammar Triggerに到達せずHealth Gate停止。21 Call/入力84642/出力21107 Token・342.06秒。
最初の4 Critical条件は一致、残る25条件は未試行。全予定精度/支持精度はnull、採用しない。
Raw配列を修復・再試行せず、全43 Artifact・再開37 File不変/追加Call・Server0を
`phase11_known_trace_result_v1.json`に保存した。次は[終了Tag境界の別候補](phase11_json_boundary.md)を
人工Runtime・日英意味診断から検証し、新しい通過Reportを前提に同じExpectedで別Runを用意する。


## v8通過Reportを前提とする回帰v2

新しい`phase11_known_trace_regression_v2.json`は、v1の全15 QA/42固定文・37確定/5曖昧・
全Expected/原Trace/基準/裸拒否8件/最大114 Callを同一内容で保持する。
前提だけを固定43ccf05のv8日英意味診断Report Hashへ結び、親Plan Hashも記録した。
Config v2はv8の全条件を保持し、Study Version/Plan Pathだけを回帰用に変えた。
現SourceでModel/Runtime/Prompt/Core・旧Expectedの読込み照合に成功。新しい実GPU回帰は未実施。
形式修正後の結果を旧v1の継続へ混ぜず、別固定Worktree/Runを使う。
