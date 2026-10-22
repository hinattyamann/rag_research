# Phase 11 旧15 QA回帰v6はCUDA timeoutで停止

2026年10月22日17:14 JST。固定d9c889b/session78660は最初のCouncil元順序の途中で、
3 Callを記録して停止した。全30条件のうち処理した1条件がError、成功条件0・残り29条件は未試行。
これは意味判定の基準を検証し終えた結果ではなく、Runtime Healthの不通過である。
主/Calibrationの実走は開始しない。

## 返却済み・応答不明・未試行を保持

最初のc1/c2は応答が返り、両支持で原文/Expectedと一致した。
3件目c3は`/completion`接続が応答なしで閉じた。Raw出力/Runtime応答は保存されず、出力Tokenはnull。
以前の同一例の結果からラベルや費用を埋めない。c4〜c7の4文も未試行である。
予定84 Callの記録済み試行は3（応答取得2/不明1）、未試行81。

全予定74確定/支持58判定の精度はnull、集約Fもnull。
元Reportは完全な集約条件だけで精度を計算するためexact_correct=0であり、
別途読んだ成功Leaf2/2をReportの精度へ置き換えない。誤支持0も採用や精度保証を意味しない。
全15 QA/42文/Source25/Expected/基準/曖昧/別保存の裸拒否8は不変。

入力10942 Tokenは失敗要求の準備済み入力も含む。
出力5347 Tokenは返却済み2件だけの既知部分和で、実際の全出力Tokenは不明。
Task秒和141.28143747200374秒は失敗Stepの壁時計42.363277秒を含み、GPU Kernel専用時間ではない。
Nativeログには失敗要求の生成途中経過もあるが、完了応答や正確な全費用として転記しない。
全9Bの記録済みCompletion試行は512（Q4 317/Q5 195）。今回の3には応答不明1を含む。
v12の未使用81と旧v5の未使用42を保持し、自動Retryや別Run名での同条件の埋合せには使わない。

## Runtimeと独立した復旧確認

Nativeログは`CUDA error: the launch timed out and was terminated`で終了した。
Kernelログには16:56:57/16:58:39 JSTのNVRMメモリ確保エラーと、
17:01:04 JSTのwatchdog・Xid8（llama-server）がある。どのメモリ領域が直接の原因か、
確保失敗がtimeoutを引き起こしたかは未確定で、VRAM不足やHost OOMと断定しない。

[NVIDIAのCUDA仕様](https://docs.nvidia.com/cuda/cuda-driver-api/cuda_driver_api/group__CUDA__TYPES.html)は、
Kernel timeout後の同じProcessでCUDA処理を継続できず、Processの終了・再起動が必要とする。
失敗Processは終了済みで、残るllama-serverがないことを確認した。
OS/Driver/Watchdog設定は変更していない。

別ProcessのCUDA12.9製4 Byte/1 ThreadのKernelは正常に7を書き戻し、
compute12.0・kernel_exec_timeout_enabled=1を確認した。GPUは表示にも使われている。
これは短い新Contextでの計算の確認で、長時間のNativeの安定性を証明しない。
GPU/RAM/Process名だけのSnapshot、Kernelログ、ProbeのSource/Binary/結果と一次資料参照を保存した。

## 全Rawの監査と保存

監査47278は95 Source Hash、全保存入力/文ID/実費を照合した。
再開時は元9 File不変、追加Call/Server0で、未知の3件目を再生成していない。
監査付きRaw11を正規Run
`data/runs/semantic_diagnostics/phase11-qwen35-9b-q5-known-regression-v6`へByte一致コピーした。

返却済み2件のNative最終JSONを直接Decodeして独立Draft-7・保存Raw/Native出力Tokenと照合し、
Sourceが全読解済みのCouncil例と同一であることも確認した。逆順序未試行のためSchemaペアの検証はできない。
最初の補助確認は失敗Leafにraw_output Field自体がないためKeyErrorとなり、Source/Logを保持した。
別v2でField欠落を未知として扱い、返却済み2件だけを検証した。Nativeの再試行はない。
AI確認は同じCodex、human_reviewed=false・正確なModel ID不明・履歴分離なし。

AI確認付きRaw12/監査Sidecar10/資源診断5/準備Preflight6/開始記録1の全34 Artifactを
`phase11_known_trace_result_v6.json`へ保存し、固定WTとByte照合した。
旧v17の全意味診断153 Artifact・全旧失敗は変更していない。

## 次の資源候補

現在のContext24576は以前の読解付き候補から保持していた値である。
現行の直接文判定では、全意味70入力の最大3793/旧全回帰84入力の最大3927に対し、
判定出力6144を予約しても12288以内に収まる。全文/文単位/出力・推論予算/Model/Prompt/Sampler/Seedを保ち、
Contextだけを12288へ分ける候補を次に事前登録する。
これは確保量を減らす資源上の仮説で、原因確定や改善保証ではない。
意味判定の既存不一致を直した候補とも扱わない。

旧Runと応答不明はそのまま凍結し、新条件の全生成0/形式/意味/全旧回帰を別Runで検証する。
Native実走には時系列の資源観測を添え、入力を切り捨てず、未知/失敗で停止する。
新候補/予算/実走はこの記録時点では未作成・未実施である。
主/Cal採用・最終N/資源/条件/凍結は未了。Gate 11未通過・Phase 12未実施、Goal継続中。
