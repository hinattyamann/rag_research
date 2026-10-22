# Phase 11 Q5の全層CUDA・新形式検証と意味診断の開始

2026年10月22日12:57 JST時点。[取得と事前登録](phase11_qwen35_q5_candidate.md)を
`be6e6ac`へCommit・Pushし、リモート一致を確認して専用Worktreeへ固定した。
現在の全意味診断の採否は未確定であり、主/予約Calibrationは開始していない。

## 実資源と生成0

専用WTは`.tools/worktrees/phase11-qwen35-9b-q5-v16`。
389 File Binding、不変資源56 Hardlink、内部相対Symlink10を確認した。
旧Q4は履歴用に保持し、実行時にロードするModelはConfig v16のQ5である。
JSON/Rawはコピー、専用GPU環境58 PackageはOfflineで再現した。

session35955は全70実入力/Completion0に通過。最大3478 Token、Context24576、全Layer CUDAを確認した。
VRAM7254/8151 MiBは一点観測であり、全実行の最大値やGPU Kernel時間ではない。
準備/Preflight6 ArtifactはRootと固定WTでByte一致、証拠は`phase11_qwen35_q5_preflight_v1.json`。

## 新Modelでの形式検証

旧Q4の形式通過を再利用せず、session15996で新しい人工10 Callを実行した。
比較用Legacy配列失敗1を保持し、従来5+引用状態4の全9 Strict条件に通過した。
人工専用の推論128/出力512であり、実QAの正解を推論できた証拠ではない。

入力630/出力1802 Token、生成段階の合計34.96400083802291秒。全Layer CUDA。
92 Source Hash、保存された実Tokenizer確認済みNative境界/終了Token位置とGrammarを照合し、
独立Draft-7検証器で全9 Strict出力を再確認した。別Tokenizer/代替Token IDを作っていない。
同じ出力先への再実行はServer/Completion前に拒否され、元14 File不変・追加Call/Server0。
監査付きRaw16と準備/補助8の全24 Artifactを固定WTとByte一致で保存した。
証拠は`phase11_qwen35_q5_format_result_v1.json`。

## 現在の実走と次工程

Q4の実完了317、Q5の人工10から全9B累積327 Callとなった。
同じ固定WTで全58条件/最大70 Callの意味診断をsession95591として開始した。
出力は`data/runs/semantic_diagnostics/phase11-qwen35-9b-q5-v16`、
開始記録は`phase11_qwen35_q5_launch_v1.json`。
全条件/Expected/基準・全文・予算・Sampler/SeedとRetry0、累積上限481を維持する。

同じHandleを継続観測し、終了後だけ全Raw/費用/失敗/未試行と追加0再開を監査・正規保存する。
全診断基準通過後だけ、同じ全旧15 QA/42文/30条件・84 Callの新前提を結ぶ。
旧Q4回帰v4は不採用のまま保持し、Q5の採用に転用しない。
全既知採用後の実主/Cal・最終N/資源/条件/凍結は未了。Gate 11未通過、Phase 12未実施、Goal継続中。
