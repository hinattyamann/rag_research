# Phase 11 引用状態Schema v3の実機形式検証と意味診断の開始

2026年10月22日10:28 JST時点。実装と事前登録は[候補仕様](phase11_cited_decisions.md)、
実機結果は`data/manifests/phase11_qwen35_9b_format_result_v4.json`へ保存した。
旧仕様の失敗出力を修復せず、新しい生成制約で形式を検証した。意味判定の採用は未確定である。

## 固定条件と準備

- 固定Commit: `55d031ca9c9ff599e0ef362856a8cd05f0b32cb7`。
- 専用Worktree: `.tools/worktrees/phase11-qwen35-9b-v15`。
- Config: `configs/phase11_semantic_candidate_v15.yaml`。事前登録v7の最大164 Call・Retry0を維持する。
- Model/Runtime・日英Prompt v10・24k Context・実診断の推論4096/判定6144・全対象/Expected/採用基準は候補仕様と同じ。
- 準備時は104 File Bindingを照合し、不変資源55 Hardlinkと内部相対Symlink10を配置。
  JSONとRawはコピーし、独立GPU環境58 PackageをOfflineで再現した。
- 全70実入力を生成0で確認し、最大3478 Token、全Layer CUDAを確認した。
  VRAM6526/8151 MiBは一点観測であり、全実行の最大使用量ではない。
- 準備/Preflightの6 Artifactを`phase11_cited_decisions_preflight_v1.json`へ保存した。

## 新しいNative形式検証

人工Probeの10 Callを実行した。Legacy配列比較の既知の失敗1件を保持し、
従来のStrict 5条件と新しい状態別4条件の全9条件に通過した。
人工Probe専用の推論128/出力512であり、実診断の予算と混同しない。

| 新条件 | Boolean状態 | 実出力の引用ID |
|---|---|---|
| 支持を固定 | conflict=false / supported=true | a, b |
| 矛盾を固定 | conflict=true / supported=false | a |
| 支持不足・空引用を固定 | conflict=false / supported=false | 空 |
| 全3状態の選択肢 | conflict=true / supported=false | a |

最初の3条件は人工Schemaで状態を固定する形式検査であり、正しい研究Labelを推論できた証拠ではない。
全選択肢の検査でも、Boolean両true・空引用による支持/矛盾・未知IDを求める指示に対して有効形式を保った。
生成制約によりSamplingのLabel/引用分布が変わる可能性があるため、全意味診断と旧回帰を省略しない。

実費は入力630/出力1679 Token、生成段階の合計29.25531294698885秒、実完了10 Call。
旧9B実完了195と合わせて、意味診断開始時の累積は205 Callとなった。

独立Draft-7検証器で全9 Strict出力を再検査し、保存Native Grammarと実Schemaからの生成結果を照合した。
92 Source Hashと、実行時Tokenizerで検証済みのTrigger/終了Token記録を保持・照合した。
監査でTokenizerやToken IDを代替実装していない。同じ出力先へのCLI再実行はServer生成前に拒否され、
監査前の14 Fileは不変、追加Call/Serverとも0だった。監査資料を加えたRaw16 Fileを正規保存し、
準備/補助9 Fileを含む全25 Artifactが固定WorktreeとByte一致することを確認した。

最初の包装処理は、すでにRootに存在する監査補助Fileまでコピーしようとして存在検査で停止した。
この失敗を`format_packaging_failure_v1.json`へ保持し、同一Byteを確認して不足分だけ配置した。
Nativeの失敗や再試行ではなく、追加推論は行っていない。

## 意味診断の実行状態

`phase11_cited_decisions_launch_v1.json`へ形式/Preflight/事前登録のHashを結んでから、
同じ固定Worktreeで全58条件・最大70 Callの診断を開始した。Sessionは`77717`、
出力先は`data/runs/semantic_diagnostics/phase11-qwen35-9b-cited-v15`。
10:27 JSTの観測では最初の条件が完了し、実行は継続中。全採否は未確定である。

同じHandleを観測し、終了前の再起動や途中の集計再生成をしない。
終了後に全Raw/費用/失敗/未試行と追加0再開を監査・正規保存する。
全診断の基準通過後だけ、同じ全旧15 QA/42文/30条件・最大84 Callを新Versionで検証する。
旧回帰v3の不通過結果を新候補の通過証拠として使用しない。

## 現行Sourceでの最終Validator検証

実装変更で旧検証資料v1のSource Hashは現行コードと一致しなくなったため、v1を保持したまま
`phase11_bilingual_finalization_validation_v2.json`を追加した。
新規33件を含む全734 Test（26.78秒）/Ruffの成功を結び、現行93 Sourceと12 Artifactを照合した。
旧v1の現行検証への流用を拒否し、未決の最終条件からの凍結も実際に拒否した。
両言語の全Index/Embedding Payload30 Fileを照合し、固定Metadataから母集団EN564/JA209を導いた。
Evaluation QA本文の解析と追加推論は0であり、この母集団数は最終Nではない。

主DevelopmentとCalibrationの成功側テストは明示的な代替を使用しており、実採用の証拠ではない。
実主/Cal実走・全採点/採用、最終N/条件と最終凍結Manifestは未了。
Gate 11未通過、Phase 12未実施、Goalは継続中である。
