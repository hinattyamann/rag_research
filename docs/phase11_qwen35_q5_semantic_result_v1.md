# Phase 11 Q5全意味診断の監査と旧15 QA回帰v5

2026年10月22日14:03 JST時点。Q5 v16は全意味診断の事前基準を満たした。
旧実資料15 QAの回帰は別に必要で、主Development/Calibrationへの採用はまだない。

## 全診断の結果と実費

固定Commit `be6e6ac606abf985c5cc9dfe921360fd14fea0b4`の専用Worktreeで、
session95591が全58条件/70 Callを終了した。

| 対象 | 完了 | 正確一致 | 誤支持 |
|---|---:|---:|---:|
| 既知Critical条件 | 4/4 | 4/4 | 0 |
| 人工英語 | 24/24 | 24/24 | 0 |
| 人工日本語 | 30/30 | 28/30 | 0 |

日本語`ja-count-3`は元/逆とも、選手時代にも優勝したという記載のない主張を矛盾とした。
監督就任後の優勝は選手時代の優勝を否定しない。元Expectedの支持不足を保持し、2件の相違とする。
既存の言語別精度0.9以上/誤支持0などの基準に通過したが、全判定の一致ではない。
Q4 v15の人工日本語は30/30であり、このQ5単一Runから量子化精度による改善を断定しない。

全入力118450/出力209629 Token、Task秒和3781.2331841669657秒、費用不明0、未試行0。
これはTaskの実費合計でありGPU Kernel時間や作業全体の経過時間ではない。
Q4実317/Q5実80（形式10+意味70）で全9B実累積397 Callとなった。

## 原本・Source・意味と形式の監査

終了後の監査session72553は95 Source Hash、全入力/順序/元と子の文ID/実費を照合した。
再開時は元133 File不変、追加Call/Server0。
監査付きRaw135を正規Run
`data/runs/semantic_diagnostics/phase11-qwen35-9b-q5-v16`へByte一致で複製した。
監査Script/途中AI確認/実stdout・stderr4 Artifactも固定WTとByte一致で保存した。

Native応答の`</think>`後を独立にJSONとして読み、全70出力をDraft-7で検証した。
35組のSchemaは元/逆で同一。全27人工例は1文書で両順序の実入力が同じであり、
54条件を独立した文書順序効果の証拠にしない。
全70最終判定/理由と全人工Source、既知原文のAI確認も保存した。
確定68判定中66一致、曖昧2判定は精度だけから除外してFの分母に保持する。
同じ開発履歴のCodex AIによる確認で、human_reviewed=false、正確なModel ID不明、履歴分離なし。

Council c6は両順序とも支持不足だが、元の曖昧なExpectedを変更しない。
Councilはc4の矛盾を含んだまま両F=5/7で閾値0.7以上、Zidaneは両F=0。
ここでは実書換えや品質結果を生成していない。
160文字に達した理由8件と、不完全な末尾を含む原本を保持した。
Council元c7の159文字の末尾の断片も保持するが、160文字上限の到達と同一視しない。
これらをNative出力予算の上限到達と扱わず、文章を補修しない。

全Raw/AI確認/生成0/開始・監査の147 Artifactは
`data/manifests/phase11_qwen35_q5_semantic_result_v1.json`へ保存した。
旧Q4結果と既存Q5形式24 Artifactは不変。

## 旧全15 QA回帰v5の事前登録

未完了前提を拒否した準備Helperの正の経路を実行し、親Run全136 Fileの同一Byteコピー上で
全判定/費用/入力を再検証した。原本/コピー不変、追加Call/Server0を確認した。
旧原版と同じ15 QA/42文/30条件・最大84 Call、Source25/全Expected/基準/曖昧/裸拒否8を保ち、
`configs/phase11_known_trace_regression_v5.json`へ前提を結んだ。
`configs/phase11_known_trace_candidate_v5.yaml`はQ5 v16からStudy VersionとDiagnosticsだけを変更する。
準備7 Artifactと実Config/Planの証拠は
`phase11_qwen35_q5_known_preparation_validation_v1.json`に保存した。
新Config/Planを含む全740 Test（26.07秒）/Ruffに成功し、実Logと全登録へのHash対応を
`phase11_qwen35_q5_known_registration_validation_v1.json`に保存した。製品Sourceの変更はない。

事前登録v10は、v9に含まれていた通過時の旧回帰84 Callだけを具体化する。
既存397/累積上限481、Retry0を維持し、164 Callの親上限を追加で拡張しない。
Native Core/Probe27と新Q5形式証拠が同一なので形式を再利用し、新固定WTで全84入力/生成0から確認する。
最初の12 Critical条件/42 Callが全一致した場合だけ、残る正例18条件へ進む。
旧Q4回帰v4の不採用/18条件未試行を成功へ置き換えない。

次は確認済みの記録/全事前条件をCommit・Pushし、新固定WTの生成0/全旧回帰へ進む。
旧回帰v5の固定WT/実走と全採用、実主/Cal・最終N/資源/条件/凍結は未了。
Gate 11未通過、Phase 12未実施、Goal継続中。
