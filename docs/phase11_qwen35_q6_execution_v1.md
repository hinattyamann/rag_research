# Phase 11 Q6候補v19の実機形式通過と日英意味診断

2026年10月23日12:15 JST時点。[Q6候補/事前登録](phase11_qwen35_q6_candidate.md)を
cf489d9844651995be9986e4d41c0f89de672e63へCommit・通常Pushし、リモート先端一致を確認した。
旧全回帰v7/監査/取得/登録Testは終了済みで、再生成しない。

## 固定準備と生成0

専用WTは`.tools/worktrees/phase11-qwen35-9b-q6-v19`。
準備83147で1191 File Binding/57不変Hardlink/内部相対Symlink10を照合した。
JSON/Rawはコピーし、モデル/RuntimeのHashはストリームで確認した。
GPU環境58 PackageをOfflineで28msで再現し、OSをまたいだvenvの流用はない。

観測付きPreflight77162は全70実入力/Completion0・Context12288/全層CUDAで成功した。
最大3793 Tokenで、全70件の実入力Token数も元Q5と同一だった。
Runtime一点は7589/8151 MiB。5秒観測6点/取得エラー0の最大7577 MiBと差を保持する。
これは連続Peakや、長い意味診断の安定性/精度の確認ではない。
準備/環境/生成0/資源の全11 Artifactを正規保存・WTとByte照合し、
`phase11_qwen35_q6_preflight_v1.json`へ結んだ。

## 新Q6の実Native形式

同じWTの観測付き30605は全10人工Call・全9 Strict条件に通過した。
旧Grammarの配列比較失敗1も保持する。入力630/出力1768 Token・生成秒和37.80482954799663秒、
費用不明0。NativeはQ6_K/33層CUDAを記録し、CUDA Model6306.63/CPU Mapped795.70/KV384.00 MiBだった。

全9 StrictのNative最終JSONを独立decode/Draft-7検証し、実Grammar/Prefill/Trigger/保存Token位置も照合した。
元14 File不変・92 Source一致・同出力先への再実行拒否はServer/Call前で、追加0。
監査付きRaw16を正規保存した。資源13点/取得エラー0、観測最大GPU7601/8151 MiB、
最小Host Available5130740 KiB・Observer経過55.364926630980335秒を別に保存した。
前後の資源3ファイルは再計算してHash不変を確認した。
全37 Artifactを`phase11_qwen35_q6_format_result_v1.json`へ結び、WTとByte照合した。
形式の通過は意味精度や主/Calibrationへの採用ではない。

## 実行中の全意味診断と再開方法

同じ固定WTで全58条件/最大70 Callを観測付きsession98160として開始し、同じHandleの稼働を確認した。
Rawは`data/runs/semantic_diagnostics/phase11-qwen35-9b-q6-context-v19`、
資源は`data/runs/resource_observation/phase11-qwen35-9b-q6-v19-semantic-v1`。
開始記録は`phase11_qwen35_q6_launch_v1.json`。採否は未確定である。

開始前の全9B記録試行644（Q4 317/Q5 317/Q6 10）/累積上限798、当段階70/通過時だけ旧全回帰84・Retry0。
旧未知1/未使用42/81/42は埋めず、再配分しない。全対象/Expected/基準/日英Prompt/12k/予算/Sampler/Core27は不変。
同じHandleで観測し、終了前に再起動しない。終了後だけ固定WTのGPU uvで既存汎用Direct監査
`data/runs/development_screening/phase11-q5-known-v5-audit-v1/audit.py`へConfig v19/新Runを渡す。
全Raw/入力/順序/文ID/実費/未知/失敗/未試行・追加0再開、独立Native Schema/全理由/Sourceと資源を監査する。
稼働中の全Inventoryを固定・コピーしたり、未完了を通過扱いにしたりしない。

開始記録のWT内実コピーはmodelscreening/q6-v19の`launch.json`、新形式は`fresh_format_binding.json`、
生成0は`preflight_binding.json`。Rootと同じdata/manifestsパスが古い固定Commitにあるとは仮定しない。
全意味診断と監査の通過後だけ、同じ旧全15 QA/42文/30条件・84 Callへ新前提を結ぶ。
全旧基準通過前に実Main/予約Calへ進まない。最終N/資源/条件/凍結は未了、
Gate 11未通過・Phase 12未実施、Goal継続中。モデル/Raw/環境はGit Pushの転送対象外である。

## 全意味通過後だけ使う旧全回帰v8の準備

2026年10月23日12:30 JST、全意味診断が未完了の間に、同じ旧15 QA/42文/30条件・84 Callへ
引き継ぐ条件付きHelperを別保存した。`data/runs/development_screening/phase11-known-v8-preparation-v1/prepare.py`は
完全通過・費用既知の58条件/70 Callと終了後監査/追加0再開を先に要求し、全Rawのコピー上で再検証してから
新Config/Planを作る。元Source25/Expected/全基準/曖昧/別保存の裸拒否8は原版不変である。

実行中Q6のWTを親に指定した早期Probeは、Config読込み/Lock/再検証の前で拒否し、
終了済みCouncil元のAggregate/Leaf8ファイルを変えず、Config/Plan/正のReceiptを生成しなかった。
稼働中全Inventoryは固定せず、親指定のOverrideはこの早期拒否だけに使用した。
実Native95 SourceもRoot/WTで不変。追加Model Call/Server・未使用QA読込み0。
構文/Ruff成功と全7 Artifactを`phase11_qwen35_q6_known_preparation_pending_v1.json`へ結んだ。
正の引継ぎ・実旧回帰v8の登録/実走は未了で、未完了の親を採用した証拠にはしない。

12:41 JST追記: 既知4条件/16最終判定の理由を読み、部分AI記録を
`data/runs/development_screening/phase11-q6-v19-semantic-audit-v1/partial_AI_review_v1.json`へ保存した。
Council c4/Zidane c1のCriticalは両順序でC。曖昧のままのCouncil c6は元C/逆NSで、
両F5/7は変わらない。旧Q5の「両NS」を新Q6へ転記しない。16判定/4 Aggregateの20 FileだけをHash参照し、
全稼働中Inventoryは固定しない。human_reviewed=false・同一履歴・非盲検で、全70の終了後監査/採用とは区別する。
