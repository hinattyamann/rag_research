# Phase 11 生成温度0.2候補v20の実機確認と意味診断

2026年10月23日15:12 JST時点。[候補v20の事前登録](phase11_q6_temperature_registration_v1.md)を
`17d57c6b4186a158685b85eb50da71fb4d04d93b`へCommit・通常Pushし、リモート一致/追跡差0/0/未Commit0を確認した。
このCommitを固定したWTで、全入力生成0と新形式の全監査を終え、同じWTの日英意味診断を開始した。
形式の成功は意味精度やGate 11全体の採用ではない。

## 固定環境と全70入力生成0

WTは`.tools/worktrees/phase11-qwen35-9b-q6-v20`。
準備99908で1537 File Binding/57不変Hardlink/内部相対Symlink10を照合した。
JSON/Rawはコピー、不変Model/RuntimeだけをHardlinkし、大きいModelはストリームHashで確認した。
全リンクのWT内解決を確認し、GPU環境58 PackageをOffline/40msで再現した。

観測付きPreflight69143は全70実入力・Completion0・Context12288・全層CUDAで成功。
最大3793 Tokenで、全70 Token数は旧Q6 T1と一致した。
Runtime一点は7599/8151 MiB、5秒観測6点/取得エラー0の最大GPU7607 MiB、
最小Host Available4649020 KiB・Observer経過20.336272166秒だった。
準備/環境/生成0/観測/保存Helperの全14 Artifactを
`phase11_qwen35_q6_temperature_preflight_v1.json`へ保存し、Root/WT Byte一致を確認した。

## 新形式と実際の生成温度

同じWTの観測付き形式32143は全10 Callを終了し、全9 Strict条件を通過した。
旧Grammarの配列比較の失敗1件は保持する。入力630/出力1729 Token・生成秒和36.660811455秒、費用不明0。
NativeのQ6_K/33層CUDAとCUDA Model6306.63 MiBを実ログで確認した。

全10 CallのNative実温度は0.20000000298023224で、設定0.2と浮動小数点許容範囲内で一致した。
Seed42と主要Sampler値、動的温度範囲0を照合し、全9 Strictを独立JSON decode/Draft-7検証した。
Grammar/Prefill/Trigger/保存Token位置・実Tokenizerの保存Witnessを確認し、92 Sourceと元14 File不変を照合。
同じ出力先の再実行はServer/Completion前に拒否され、監査による追加Call/Serverは0だった。

資源13点/取得エラー0、観測最大GPU7624/8151 MiB、最小Host Available5267748 KiB、
Observer経過55.417877626秒だった。生成0/形式の両観測を別に再計算し、各元3 FileのHash不変を確認した。
5秒の観測最大を連続Peak、Task秒和をGPU Kernel時間、短い形式試行を長時間安定性や意味精度の証明にはしない。
監査付きRaw16を正規保存し、形式/生成0の全40 Artifactを
`phase11_qwen35_q6_temperature_format_result_v1.json`へ結び、固定WTとByte照合した。
Core27は不変。T1の形式を新温度の実績として流用していない。

## 実行中の意味診断と再開地点

同じWTで元29例/35文/58条件・最大70 Callを、観測付きsession89310として15:10 JSTに開始した。
Rawは`data/runs/semantic_diagnostics/phase11-qwen35-9b-q6-temperature-v20`、
資源は`data/runs/resource_observation/phase11-qwen35-9b-q6-v20-semantic-v1`。
開始記録は`phase11_qwen35_q6_temperature_launch_v1.json`。採否は未確定である。

開始前の全9B記録試行766（Q4 317/Q5 317/Q6 132）は旧応答不明1を含む。
累積上限920・Retry0、全意味採用/全監査後だけの同じ旧全回帰84を維持する。
旧未使用42/42/81/42を埋めず、全Expected/基準/曖昧/別保存の裸拒否8を保持する。

同じ89310を継続観測し、終了前に再起動しない。
全終了後だけ固定WTのGPU uvで、既存汎用Direct監査へConfig v20/新Runを位置引数で渡し、
全Raw/入力/順序/文ID/実費/未知/失敗/未試行・追加0再開を確認する。
独立Native JSON/Schema・全最終理由/Sourceと資源を監査し、正規保存/WT照合する。
稼働中の全Raw Inventoryは固定せず、取得していない応答を作らない。

WT内の実コピーはmodelscreening/q6-v20の`launch.json`/`fresh_format_binding.json`/`preflight_binding.json`。
Rootの新Manifestが過去固定Commitに存在したとは仮定せず、このAliasとのByte一致を確認した。
全意味採用/監査後だけ同じ旧全15 QAの新前提を作り、負例12条件の完全一致後だけ残18正例条件へ進む。
Main/予約Cal/Evaluationの新規QAは使っていない。Main/Cal/最終N/資源/条件/凍結は未了、
Gate 11未通過・Phase 12未実施・Goal継続中である。モデル/Raw/環境はGit Pushでは転送されない。
