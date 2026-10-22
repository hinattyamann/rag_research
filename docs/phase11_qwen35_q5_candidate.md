# Phase 11 同じ9BのQ5候補・取得と事前登録

2026年10月22日。旧回帰v4は誤支持4で不通過となり、Q4から主/Calibrationへ進まない。
[全失敗/未試行の結果](phase11_known_trace_direct_result_v4.md)を保持した上で、
同じ固定Repository RevisionのGGUF精度を変える候補を別登録する。
量子化が誤支持の原因とは断定せず、改善を約束しない。

## 固定した取得とIdentity

- Repository: `unsloth/Qwen3.5-9B-GGUF`。
- Revision: `3885219b6810b007914f3a7950a8d1b469d598a5`。
- File: `Qwen3.5-9B-Q5_K_M.gguf`、6577841376 Byte。
- SHA256: `dc2a39aef291f91a9116ad214058da0d86eb648743a124bd8c333787c4b9c91c`。
- [公開File/Hash](https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/blob/3885219b6810b007914f3a7950a8d1b469d598a5/Qwen3.5-9B-Q5_K_M.gguf)、
  保存済み取得前Metadata、新Spec、取得後の全ファイルHashが一致した。GGUF Magicも確認した。
- LicenseはApache-2.0。Unslothの変換物で、元Qwen重みの厳密な変換Base Revisionを独立に証明した扱いにはしない。

旧Q4のファイル/Manifest/Runを保持し、別Manifest `phase11_auxiliary_qwen35_9b_q5_manifest_v1.json`へ保存した。
取得記録は`phase11_qwen35_q5_acquisition_v1.json`。取得前のCode/Spec/Metadata Snapshotと全取得Logを残す。
モデル取得は推論ではなく、Q5のQA/Completion Callは0である。

取得CLIがManifestの量子化名をQ4へ固定していたため、Specの宣言を伝播するよう修正した。
宣言と固定File名の不一致、Q5 FileにQ4既定値を適用しようとする指定はダウンロード前に拒否する。
旧Q4 Specの既定動作を保つ。隔離FixtureのManifestディレクトリ不足による初回2 Test失敗も記録し、
Fixtureを修正後、追加6件を含む全740 Test（28.29秒）/Ruffに成功した。
テストは取得を代替し、実取得のHash確認をテストだけで達成したとは扱わない。

## 宣言上の変更と採用前の確認

Config v16はv15からStudy VersionとModel Manifestだけを変更した。
同じ日英Prompt v10、直接固定文照合、Schema v3、Context24576、推論4096/判定・書換え6144、
Sampler/Seed、閾値/拒否方針、全29例/35文/58条件と全旧15 QA/42文/30条件のExpected・基準を維持する。
Native Core/Probe27 Hashも同じである。初回生成は既存3Bの条件を維持する。

Q4との差約0.90GBはVRAM見積りの参考にすぎない。8GB GPUでの実適合・全Layer CUDA・全入力予算を生成0で検証する。
資源不足ならその失敗を保存し、この候補の予算や本文をその場で縮めない。
Modelが異なるため、旧Q4の形式/意味通過を新Modelの証拠として採用しない。

事前登録v9の新規上限は人工形式10（Strict9）＋全意味70＋通過時だけ全旧回帰84＝164 Call、Retry0。
人工Probe専用の推論128/出力512を明示する。旧Q4実完了317/Q5実完了0からの全9B累積上限は481。
旧回帰v4は42 Callで停止済みのまま保存し、残る18条件を成功や未使用Calibrationに読み替えない。

新Commit/専用WTへ固定し、生成0→新Native形式→同じ全日英意味→全旧回帰の順に確認する。
各停止/失敗/未試行・実費を保持し、全採用基準通過後だけ主Developmentへ進む。
主/予約Cal/Evaluationの新規QAは使用していない。
実主/Cal・最終N/条件/凍結は未了。Gate 11未通過、Phase 12未実施、Goal継続中。
