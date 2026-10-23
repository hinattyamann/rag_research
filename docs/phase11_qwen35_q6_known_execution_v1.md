# Phase 11 Q6の旧全15 QA回帰v8

2026年10月23日13:43 JST時点。[全意味結果・監査・回帰登録](phase11_qwen35_q6_semantic_result_v1.md)を
`262ba082261deaebb97f542025e592f4509f9fae`「Q6全意味診断の監査結果と旧全回帰v8を登録」へ
Commit・通常Pushし、GitHub mainとの一致・追跡差0/0・未Commit0を確認した。
同じCommitを固定したWTで、全入力の生成0確認後に回帰v8を開始した。採否は未確定である。

## 固定環境と全84実入力の生成0

WTは`.tools/worktrees/phase11-known-trace-regression-v8`。
準備96627で1404 File Binding・57不変Hardlink・内部相対Symlink10を照合した。
JSON/Rawはコピーし、不変Model/RuntimeだけをHardlinkした。大きいModelはストリームHashで確認し、
全リンクを作成後にWT内へ解決することを確認した。GPU環境58 PackageをOffline/45msで再現した。

観測付きPreflight38450は全84実入力・Completion0・Context12288・全層CUDAで成功した。
最大3927 Token、全84件の入力Token数は旧Q5と同じだった。
Runtime一点は7582/8151 MiB、5秒観測6点/取得エラー0の観測最大GPU7583 MiB、
最小Host Available4213736 KiB・Observer経過20.182471611秒だった。
観測最大を連続Peakや長時間実行の安定性保証に読み替えない。

準備/環境/生成0/観測/保存Helperの全14 Artifactを正規保存し、WTとByte照合した。
証拠は`data/manifests/phase11_qwen35_q6_known_preflight_v1.json`。
Core27・新Q6形式37・親全意味195 Artifactも不変で、追加形式Callは0。
HelperのRuffと`git diff --check`を確認し、実験Sourceは全761 Test（28.72秒）/Ruff成功時と同一である。

## 実行中の回帰と再開地点

同じWTで全15 QA/42文/30条件・最大84 Callを観測付きsession61821として13:42 JSTに開始した。
NativeのQ6_K・33/33層CUDAも実ログで確認した。
Rawは`data/runs/semantic_diagnostics/phase11-qwen35-9b-q6-context-known-regression-v8`、
資源は`data/runs/resource_observation/phase11-qwen35-9b-q6-context-known-v8-semantic-v1`。
開始記録は`data/manifests/phase11_qwen35_q6_known_launch_v1.json`。

元Source25・全Expected/基準/曖昧/別保存の裸拒否8は不変である。
負例6 QA/12 Critical条件・42 Callが全一致した場合だけ、正例9 QA/残18条件へ進む。
事前登録v16は既存v15の条件付き84だけで、開始前の記録試行714/累積上限798・Retry0。
旧応答不明1、未使用42/81/42を新結果で埋めたり再配分したりしない。

同じ61821で継続観測し、終了前の再起動や終了後監査は行わない。
終了後だけ固定WTのGPU uvで既存汎用Direct監査
`data/runs/development_screening/phase11-q5-known-v5-audit-v1/audit.py`へConfig v8/新Runを位置引数で渡す。
全Raw/入力/順序/文ID/Source/実費/未知/失敗/未試行・追加0再開と、独立Native Schema/全最終理由・Source、
資源の再計算を保存する。エラー/応答不明時には成功した出力だけSchema監査し、未取得出力を作らない。

WT内の開始記録実コピーはモデル準備Directoryの`launch.json`、生成0参照は`preflight_binding.json`。
Rootの新Manifestが過去固定Commitに存在したとは仮定せず、このAliasとのByte一致を確認した。
稼働中Rawの全Inventoryは固定せず、最終正規保存は終了後だけ行う。
全旧基準通過・全監査後だけ新Main Policy/実Mainへ進む。
Main/予約Cal/Evaluationの新規QAは使っていない。
Main/Cal/最終N/資源/条件/凍結は未了で、Gate 11未通過・Phase 12未実施・Goal継続中である。
モデル/Raw/環境はGit Pushでは転送されないため、別PCにはManifest/Hash付きで別途再現する。
