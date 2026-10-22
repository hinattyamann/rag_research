# Phase 11 全文・出力予算を保つ12k Context候補v18

2026年10月23日08:45 JSTの実走前資料。候補は未推論・未採用である。
旧回帰v6のCUDA停止/応答不明1/未試行29条件と全34 Artifactは958ac94へ保存・Push済み。

## 変更理由と範囲

旧回帰は生成0/全層CUDAを通過した後にKernel timeoutで停止した。
Kernelの確保失敗/watchdogは観測したが、原因を特定できたわけではない。
短い独立CUDA Kernelは成功しており、OS/Driver/Watchdog設定は変更しない。
Context確保量を下げることで資源余裕が増すか、別条件として検証する。

候補Configは`configs/phase11_semantic_candidate_v18.yaml`。
元v17との差はStudy Versionとauxiliary_runtime.context_tokensの24576→12288だけ。
同じQ5 Model/固定Revision/Runtime Binary/日英Prompt v11、推論4096/Judge・書換え6144、
Sampler/Seed/文単位/Schema・全対象/Expected/基準を保つ。全文の切捨て・再梱包はしない。
以前の意味不一致を直した候補とは扱わず、旧Runの未知出力を埋めるためにも使わない。

実Loader/Identityと全154 Model入力（意味70+旧全回帰84）のMessages一致を照合した。
生成設定の差は全TaskでContextだけ、Model/Runtime BinaryのIdentityとNative Core27は同一。
旧Tokenizerでの実最大入力3927+出力予約6144は12288以内に収まる。
これは新条件の実Tokenizer確認の代替ではない。意味70の生成0を先に、
旧回帰84は新しい全意味診断/監査/正の登録後に同じ12kで生成0確認する。
今後のMain/Calでも全文入力と出力予約を実際に検査し、超過時は切らずに失敗を保持する。

## 資源の時系列観測

`observe_native_resources.py`は固定Checkoutの新規出力だけで既存CLIを起動する。
既存Native/観測出力は拒否し、未知要求を再開・再試行しない。
Native要求は子の既存Runnerだけが行い、観測処理からModel Callを増やさない。
5秒ごとにGPU全体の使用量/容量、Host RAM/Swap、Native子孫ProcessのRSS等を保存する。
Process名だけを記録し、QA本文やProcess引数は採取しない。

観測に失敗した値はnull/理由を残し、0へ置換しない。子起動失敗/終了Codeも保存する。
観測側が途中で欠測してもNativeを自動再生成せず、実出力・費用と別に欠測範囲を報告する。
NativeのHealth/意味判定は元の採否基準で評価する。
観測した最大/最小は連続計測のPeakではなく、OS/表示/観測自身の負荷も含む。
観測以外の条件を厳密にそろえた資源因果実験や、安定動作の保証とは主張しない。

新規10件を含む全750 Test（29.68秒）/Ruffに成功した。
Testの子Processは小さなPython Fixtureで、LLMの実走成功ではない。
別に現在のGPU/RAMを読み取り、観測エラー0の1点を保存した。追加Model Call/Serverは0。

## 実走上限・依存関係・停止規則

事前登録v13は、新条件の形式10+意味70+全通過時だけの同じ旧全回帰84=最大164 Call/Retry0。
既存の記録済み9B試行512（今回の旧v6に応答不明1）から累積上限676を別登録する。
旧v6の未使用81/旧v5の未使用42を再割当てせず、過去の上限や失敗を書き換えない。

Commit・通常Push後、新固定WTでModel/Runtime/Source/全入力生成0/全層CUDAを確認する。
Contextが違うため、新しい形式10 Callで元の全9 Strict条件を確認する。
形式だけで意味を採用せず、同じ全58条件/70 Callと全元基準を実測する。
全意味基準・全Raw/費用/追加0再開の監査通過後だけ同じ旧15 QA/42文/30条件・84 Callを別登録する。
旧全回帰も最初の負例6 QA/12 Critical条件・42 Callが全一致した場合だけ残る18条件へ進む。

Runtime/未知/入力超過/Task失敗は元方針で停止し、元Rawと全未試行を保持する。
どのStageでも同じ失敗Runへ自動Retryせず、Sweepや基準緩和・新規QA補充をしない。
全旧基準通過後だけ新Main Policy/実費へ進む。
主/予約Cal/Evaluationの新規QAは使っておらず、最終N/資源/条件/凍結は未了。
Gate 11未通過、Phase 12未実施、Goal継続中。
