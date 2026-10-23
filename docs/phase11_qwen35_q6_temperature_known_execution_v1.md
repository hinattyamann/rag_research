# Phase 11 温度0.2の既知15 QA回帰v9実行記録

最新: 2026年10月23日16:55 JST。72566はCUDA停止・3条件/15試行/未知1で終了し、監査23121も終了した。[不採用全結果](phase11_known_trace_direct_result_v9.md)を再開先とする。Raw26/110 Artifactは正規保存/WT照合済み。以下は開始/待機中時点の履歴であり、同じRunを再起動しない。

2026年10月23日16:28 JST時点。全意味監査/旧全回帰v9登録を
`9727409eee7a3f8c1ca76f879234f32de0462bb9`「温度0.2の全意味監査を保存し旧全回帰v9を登録」へ
Commit・通常Pushし、GitHub mainとの先端一致/追跡差0/0/未Commit0を確認した。
同Commitの固定WTで全84入力生成0を確認し、観測付き回帰を開始した。全採否はまだ未確定。

## 固定環境と生成0確認

WTは`.tools/worktrees/phase11-known-trace-regression-v9`。
準備55169は1763 File Binding/57不変Hardlink/内部相対Symlink10を照合した。
Model/Runtimeの不変FileだけをHardlinkし、JSON/Rawはコピー、大きいModelはストリームHashで確認した。
全リンクはWT内で解決し、専用GPU環境58 PackageをOffline/28msで再現した。
親全意味202 Artifactと新温度形式40 Artifact、Core27を同一Byteで確認した。
旧T1の形式を新温度の実績に流用せず、同じ温度0.2の既検証形式を再利用する。

観測付きPreflight98818は全84実入力・Completion0・Context12288・全層CUDAに通過した。
最大3927 Tokenで、全84入力のToken数は旧Q6 T1と一致した。
Runtime一点は7578/8151 MiB。5秒間隔6観測/取得エラー0、観測最大GPU7578 MiB、
最小Host Available4632600 KiB・Observer経過20.200345748秒だった。
観測最大を連続Peakや長時間安定性の保証にはしない。

準備/環境/生成0/観測/保存Helperの全14 Artifactを
`phase11_qwen35_q6_temperature_known_preflight_v1.json`へ保存し、Root/WT Byte一致を確認した。
新HelperのRuff成功、実験Sourceは全761 Test（30.43秒）/Ruff成功時と同一である。

## 実行中の回帰と再開先

同じ固定WTで、元全15 QA/42文/30条件・最大84 Callを、観測付きsession72566として16:27 JSTに開始した。
Configは`configs/phase11_known_trace_candidate_v9.yaml`、Planは`configs/phase11_known_trace_regression_v9.json`、
別事前登録は`phase11_qwen35_9b_preregistration_v18.json`。
最初の負例12条件/42 Callがすべて正確一致した場合だけ残18正例条件へ進む。
全Source25/Expected/基準/曖昧/別保存の裸拒否8を保持し、誤判定・失敗・未知・未試行を除かない。

開始前の全9B記録試行836（Q4 317/Q5 317/Q6 202）は旧応答不明1を含む。
累積上限920・Retry0、既存v17の条件付き84だけを使い、旧未使用42/42/81/42を再配分しない。
開始記録は`phase11_qwen35_q6_temperature_known_launch_v1.json`。
WT内の実コピーはモデル準備Directoryの`launch.json`/`preflight_binding.json`/`fresh_format_binding.json`。
Rootの新Manifestが過去固定Commitに存在したとは仮定せず、各AliasとのByte一致を確認した。

Raw: `data/runs/semantic_diagnostics/phase11-qwen35-9b-q6-temperature-known-regression-v9`。
資源: `data/runs/resource_observation/phase11-qwen35-9b-q6-temperature-known-v9-semantic-v1`。
同じ72566を継続観測し、終了前に重複起動しない。稼働中の全Raw Inventoryは固定しない。
終了後だけ固定WTのGPU uvで汎用Direct監査へConfig v9/新Runを位置引数で渡し、
全Raw/入力/順序/固定文/実費/未知/失敗/未試行・追加0再開を確認する。
独立Native JSON/Schema/実Sampler、全最終理由/Sourceと資源を監査・正規保存し、Root/WT Byte照合する。
取得していない応答を作らず、全74確定/支持58の予定分母や全採用基準を保つ。

全回帰の採用/監査前に新Main Policyや未使用QAを読み込まない。
Main各20 QA/全匿名品質・Expected封印と証明、予約Cal、最終N/資源/条件/Validator/凍結は未了。
Gate 11未通過・Phase 12未実施・Goal継続中。モデル/Raw/環境はGit Pushでは転送されない。

## 待機中の完了診断だけを使った見積り

[温度0.2の暫定Judge時間](phase11_qwen35_q6_temperature_resource_estimate_v1.md)を終了済み70 Call/202 Artifactだけから計算・検証した。Task平均54.964121秒、既知/人工群平均67.577599/51.226794秒。日英それぞれ各20 QA/平均5文/9試行ならJudgeだけMain25.61〜33.79時間、同規模Cal込み51.23〜67.58時間という仮定で、上限/CI/総時間保証ではない。日英で同じ平均文数を仮定した言語別Call算術を明記し、実際は各言語の原子上限を保つ。Task経過とNative生成秒を分け、7 Artifactを検証・固定WT照合した。追加推論/新規QA読込み0、1660/言語と全基準を維持し、Main Policy/最終Nの採用にはしない。稼働中の同じ72566の費用は混ぜず、終了後だけ全回帰を監査する。
