# Phase 11 12k候補の旧全15 QA回帰v7

2026年10月23日10:55 JSTにsession64437は終了した。12条件/42 Call・Critical一致9/12・誤支持3で不通過。
終了後監査63748・全42独立Schema/全理由/Source・569点の資源再計算と正規保存を完了した。
現在地は[不採用結果と次工程](phase11_known_trace_direct_result_v7.md)を優先する。以下は開始時の履歴である。

2026年10月23日10:08 JST時点。[全意味診断/全監査と回帰v7の前提](phase11_context12k_semantic_result_v1.md)を
`5f4a6b6146b0a00691800dbf01e9854ffd636d61`へCommit・通常Pushし、リモート一致を確認した。
全旧失敗・応答不明1と旧未使用81/42はそのまま保持する。

## 固定準備と全84入力生成0

WTは`.tools/worktrees/phase11-known-trace-regression-v7`。
準備16822で1065 File Binding/56不変Hardlink/内部相対Symlink10を照合した。
JSON/Rawはコピーし、リンクは全作成後に内部解決を確認した。
準備Helperの構文/Ruff成功、GPU環境58 PackageをOfflineで再現した。

観測付きPreflight75177は全84実入力/Completion0・Context12288/全層CUDAで成功した。
最大3927 Tokenで、全84件の入力Token数も元24k時と同じだった。
Runtime一点のVRAM6871/8151 MiBに対し、5秒の資源6点/取得エラー0の観測最大は791 MiB。
短区間を捕捉していない差をそのまま保持し、観測最大をPeakへ読み替えない。
準備/Preflight6+観測3の全9 Artifactを正規保存・WTとByte照合し、
`phase11_context12k_known_preflight_v1.json`へ固定した。
Native Core27/新12k形式32 Artifactの不変も再確認し、追加の形式Callは0。

## 実行中の回帰と再開方法

同じ固定WTで全15 QA/42文/30条件・最大84 Callを観測付きsession64437として開始した。
Rawは`data/runs/semantic_diagnostics/phase11-qwen35-9b-q5-context-known-regression-v7`、
資源は`data/runs/resource_observation/phase11-qwen35-9b-q5-context-known-v7-semantic-v1`。
開始記録は`phase11_context12k_known_launch_v1.json`。
元Source25/全Expected/基準/曖昧/別保存の裸拒否8は不変。
最初の負例6 QA/12 Critical条件・42 Callが全一致した場合だけ残る正例9 QA/18条件へ進む。

事前登録v14は元v13の条件付き84だけを使い、記録試行592/累積上限676・Retry0を維持する。
同じHandleで継続観測し、終了前に再起動しない。
終了後だけ固定WTのuvで、保存済み汎用Direct監査
`data/runs/development_screening/phase11-q5-known-v5-audit-v1/audit.py`へConfig v7/新Runを位置引数で渡す。
全Raw/入力/順序/文ID/Source/実費/未知/失敗/未試行・追加0再開、独立Native Schema/最終理由/SourceのAI確認を保存する。
資源は同じ終了後専用Helperで再計算し、欠測/観測最大の限界をNativeの採用基準と分けて報告する。

WT内の開始記録実コピーはモデル準備Directoryの`launch.json`、Preflight参照は`preflight_binding.json`。
Rootと同じdata/manifestsパスが古い固定Commitにあったとは仮定せず、実保存先とのByte一致を確認する。
全旧基準通過後だけ新Main Policy/実費へ進む。
Main/予約Cal/Evaluationの新規QAは使っていない。
主/Cal採用・最終N/資源/条件/凍結は未了、Gate 11未通過・Phase 12未実施、Goal継続中。
