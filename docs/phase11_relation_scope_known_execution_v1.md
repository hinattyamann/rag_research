# Phase 11 関係照合候補v17の旧全15 QA回帰v6

2026年10月22日16:59 JST時点。全意味診断/監査と回帰v6の登録を
`d9c889b88a79392fd938a46ac516ca79398d16bd`へCommit・通常Pushし、GitHubとの一致を確認した。
[全意味診断結果](phase11_relation_scope_semantic_result_v1.md)と旧失敗を保持する。

## 固定準備と全入力生成0

専用WTは`.tools/worktrees/phase11-known-trace-regression-v6`。
準備session97158で820 File Binding/56不変Hardlink/内部相対Symlink10を照合した。
JSON/Rawはコピーし、全リンクの作成後に内部解決を確認した。
独立GPU環境58 PackageをOfflineで再現し、準備Helperの構文/Ruffにも成功した。

session42180は全84実入力/Completion0に通過。最大3927 Token、Context24576/全Layer CUDAを確認した。
VRAM7254/8151 MiBは一点観測で、最大値やKernel時間ではない。
準備/Preflight6 Artifactを正規保存して固定WTとByte照合した。
Native Core27/新Q5形式24 Artifactの不変も再確認し、追加の形式推論は0。
証拠は`phase11_relation_scope_known_preflight_v1.json`。

## 実行中の回帰と再開方法

同じ固定WTで全旧15 QA/42文/30条件・最大84 Callをsession78660として開始した。
Rawは`data/runs/semantic_diagnostics/phase11-qwen35-9b-q5-known-regression-v6`、
開始記録は`phase11_relation_scope_known_launch_v1.json`。
元のSource25/Expected/基準/曖昧/別保存の裸拒否8を保持する。
最初の負例6 QA/12 Critical条件・42 Callが全一致した場合だけ残る正例9 QA/18条件へ進む。
事前登録v12は元v11の条件付き84だけを使い、既存509/累積上限593・Retry0と旧未使用42の保存を維持する。

同じHandleを継続観測し、終了前に再起動しない。
終了後だけ固定WTのuvで、保存済み汎用Direct監査
`data/runs/development_screening/phase11-q5-known-v5-audit-v1/audit.py`へ
Config v6/新Runを位置引数で渡す。全Raw/入力/順序/文ID/Source/実費/失敗/未試行と追加0再開を照合する。
全最終理由/SourceのAI確認・独立Native JSON/Schemaも保存し、旧結果を上書きしない。

開始記録のWT内の実保存先は
`data/runs/model_screening/phase11-qwen35-9b-q5-known-regression-v6/launch.json`、
Preflight参照は同じ場所の`preflight_binding.json`。
Rootの`data/manifests`と同じパスが旧固定Commitにあると仮定せず、実保存先とのByte一致を確認する。

全旧基準通過後だけ新Main Policy/実費へ進む。
実主/予約Cal採用・最終N/資源/条件/凍結は未了、Gate 11未通過・Phase 12未実施、Goal継続中。
