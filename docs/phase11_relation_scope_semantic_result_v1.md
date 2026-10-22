# Phase 11 関係・説明の範囲を照合するv17の全意味診断

2026年10月22日17:14 JST追記。旧回帰v6/session78660は3 CallでCUDA timeoutとなり終了した。
応答不明1/残り29条件未試行を保持し、[停止結果と資源診断](phase11_known_trace_direct_result_v6.md)を最新の再開先とする。
以下は全意味診断通過・回帰開始時点の履歴で、同じRunを再生成しない。

2026年10月22日16:49 JST。固定1214dbfのsession6340は全58条件/70 Callを終了し、
Critical4/4・人工英語24/24・日本語28/30・誤支持0で元の事前基準を満たした。
全旧15 QAの採用や、Main/Calibrationの成功を示す結果ではない。

## 実測結果と残る不一致

日本語ja-qualification-3の元/逆は、Expected支持不足に対して両方とも矛盾となった。
由来が不明で一説がある本文について、限定なしの内容主張を明示的な否定と取り違えている。
元の全対象/Expected/基準を保持し、この2件を成功へ変更しない。
以前の候補で矛盾としていたja-count-3は両支持不足となったが、
同じ日本語28/30でも誤る対象が変わっており、全面的な改善とはしない。

既知Council c4は両矛盾、Zidaneも両矛盾でCriticalが一致した。
Council c6は元の曖昧Expected=nullのまま、観測は両支持不足。
曖昧判定は精度からだけ除きFへ残し、CouncilのF5/7は矛盾を含んだまま閾値0.7以上になる。
閾値や矛盾時の新しい拒否規則を後付けしていない。
人工27組は1文書で元/逆の入力が同一で、独立した順序頑健性の証拠ではない。

入力140500/出力181440 Token、Task秒和3288.686712804076秒、費用不明0。
Task秒和はGPU Kernel時間や全作業の経過時間ではない。
全9B実累積509 Call（Q4 317/Q5 192）。v11の新候補154枠のうち意味70を使い、
条件付き旧回帰84を残す。旧v5の未使用42を再割当てせず保存する。

## 全Raw・Native出力・根拠の監査

終了後の監査session49997で95 Source Hashと全入力/順序/文ID/実費を照合した。
元133 Fileは再開で不変、追加Call/Server0。監査付きRaw135を正規Run
`data/runs/semantic_diagnostics/phase11-qwen35-9b-q5-relation-v17`へByte一致で保存した。

全70 Native最終JSONを直接Decodeして保存Rawと照合し、独立Draft-7に通過。
実Native出力Token数の一致/入力非切捨ても確認し、全35組でSchemaが不変だった。
全70最終理由/判定と原文も同じCodexが確認した。human_reviewed=false、正確なModel ID不明、履歴分離なし。
確定68判定は66一致、曖昧2は保持する。全理由・末尾の不完全さ・誤分類は補修しない。
理由が160文字の10件だけでなく159文字でも不完全な末尾があり、長さだけで切断と判定しない。
初期部分メモがCouncil元c3の末尾「No conflict」まで不完全と括った点は、
意味の通る句であり切断と断定できない旨を最終AI確認へ明記した。初期メモも保持する。

AI確認付きRaw136・監査Sidecar10・準備/Preflight6・開始記録1の全153 Artifactを
`phase11_relation_scope_semantic_result_v1.json`へ固定した。
開始記録をRootと同じWT内パスへ誤参照した包装失敗も保存し、WTの実保存先launch.jsonとのByte照合へ直した。
包装失敗後に同じShellが引継ぎ処理へ進んだ事実も明記した。その時点で実診断通過/全Raw監査は終了済みで、
引継ぎは元136 File不変・追加推論0だった。Nativeの再生成・旧失敗の変更はない。
Native Core27/新Q5形式24 Artifactも不変を照合した。

## 同じ旧15 QAへの回帰v6

準備session10028は全親136 FileのByte一致コピー上で前提を再検証して成功した。
元の全15 QA/42文/30条件/最大84 Call・Source25/全Expected/基準/曖昧/別保存の裸拒否8は不変。
Config v6は候補v17からStudy VersionとDiagnosticsだけを変更した。
正の証拠は`phase11_relation_scope_known_preparation_validation_v1.json`、
事前登録v12は既存v11の条件付き84 Callだけを使い、既存509/累積上限593・Retry0を維持する。
最初の負例6 QA/12 Critical条件・42 Callが全一致した場合だけ残る正例9 QA/18条件へ進む。
全740 Test（27.27秒）/Ruff・独立監査HelperのRuffにも成功し、登録検証v1へ保存した。
Native Core27/新Q5形式24 Artifactの不変を再確認した。

全旧基準通過後だけ新しいMain Policy/実費へ進む。
主/予約Cal/Evaluationの新規QAは使っていない。
固定d9c889b上で全84入力の生成0/全層CUDAを確認し、旧回帰v6をsession78660として開始した。
[回帰実行記録](phase11_relation_scope_known_execution_v1.md)を最新の再開先とする。全採否は未確定。
主/Cal採用、最終N/資源/条件/凍結は未了。Gate 11未通過、Phase 12未実施、Goal継続中。
