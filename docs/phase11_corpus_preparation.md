# Phase 11 本文欠測・英語Corpus分割・親参照の監査

確認日: 2026年10月21日。Sourceは[日本語選定記録](japanese_dataset_selection.md)、検索候補は
[多言語検索の記録](phase11_multilingual_retrieval.md)。本書はCorpus準備の記録であり、
日英RAGの実走・意味妥当性・未使用Calibration・最終固定の完了を示さない。

## 1. 削除された過去本文の扱い

固定取得Runの「出家」Page13492・Revision95068750（2023-05-05）に、
APIの`permissiondenied`が返った。保存応答は削除本文の閲覧権限がない旨を示す。
取得済みの原エラー・API応答・Hashは保持し、現在版・別の時点への切替や閲覧制限の迂回はしない。

`configs/phase11_japanese_dataset_v2.json`に欠測規則を明示し、v1とその監査を保持する。
`source_availability.py`は、保存済みの過去Revision照会とPage/Revision/時点の一致、
HTTP200の失敗Parseにおける指定のCode/削除本文メッセージの一致を必要とする。
一致した場合も原`status=error`は変えず、本文取得不能の監査情報を別に保存する。
通信エラー、別の権限エラー、現在版へのParse、未検証のIdentityを同じ欠測へ変換しない。

これはSourceの取得可能性の分類である。QAを除外・補充せず、全838 QAを保持する。
人手回答があることを、共通Corpusに根拠があるというLabelへ変換しない。
日本語Corpusと正式Group生成では、原の成功/取得不能/エラー数と、検証した削除本文欠測を区別して報告する。
未解決の取得エラーは正式生成を止め、取得中のLock・全件記録・Hashの検査も維持する。
実際の保存応答1件で規則を検証し、原エラー・RawのByte不変を確認した。
最終GateやJudgeの採用基準を緩めたわけではない。

## 2. 英語のToken上限への対応

英語Corpus178,890 Passageのうち、新Tokenizerで512 Tokenを超えた3,130件を分割した。
`source_passages()`へ渡すのは元Corpusの6 Fieldだけとし、QA/Referenceの追加Fieldを拒否する。
上限内の175,760件は元IDと本文を保持する。長いPassageには連続文字Spanの子IDを付け、元の親ID・本文Hashを保存する。
本文を捨てず、Prefix/Special込みの実Token数と各親の全文再構成を検査する。

| 項目 | 結果 |
|---|---|
| 元の親Passage | 178,890 |
| 新しい検索Passage | 183,889 |
| 分割した親 / 元IDを保持した親 | 3,130 / 175,760 |
| 最大実入力 | 512 Token |
| 処理区間 | 52.58秒、ピークRSS404,803,584 Byte |
| 元の全本文・Corpus Hash | 保持、不変 |
| Embedding推論 / LLM生成 | 0回 / 0回 |

出力は`data/processed/clapnq/c508d78-e5-passages-v1/`の`passages.jsonl`・`parent_map.jsonl`・`report.json`。
元のQA/Split・Reference回答・Gold IDは書き換えていない。新IndexとRAGの接続は未実施である。

## 3. 親Gold参照と独立検証

Goldの関連単位は元の親Passageのままにする。子が同じGold親へ対応するとき、
複数の子を独立した正解文書として加算しない。`parent_relevance()`は同一親の最初の出現だけを関連ありとする。
これは各子が回答の全要点を含むことの証明ではなく、実使用Contextの支持と品質は別に確認する。
新しい検索評価と品質Packetを親子対応へ接続する作業は残っている。

保存済みの元Corpus・新Corpus・親子対応表を別Scriptで順に読み直し、
全親の文字列再構成・全子のSpan/本文Hash・実Token上限・一意ID・対応表の全行を照合した。
4,345 QAのID/回答有無/Gold親IDだけを機械照合し、回答付き2,254 QA・Gold親2,074種類の対応表欠落0を確認した。
質問・Reference本文を調整に表示・使用せず、推論結果も読んでいない。
元QAのHashも保持し、未使用Calibration/Evaluationを既知の実験結果とは扱わない。

新規14 Testを含む全365 Test（ホスト4.59秒）とRuff成功。旧Run2500/英語Index23ファイルのHashは不変。
確認根拠は`data/manifests/phase11_corpus_preparation_manifest.json`。

## 4. GPU実行環境の予備確認と未達事項

大量Embedding計算に向け、既存CPU環境から分離した`.tools/embedding-gpu-probe`をuvで作り、
公式ONNX Runtime GPU1.30.0とCUDA/cuDNN・固定した主要依存を導入した。
[公式CUDA手順](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html)に従ってRuntimeを読み込み、
合成の日英2文でCUDAを指定した実推論とCPUとの数値照合を行った。
事前にCosine下限0.99999・最大絶対差上限0.0001・CUDA演算Profileを必要条件とし、結果前に保存した。

保存ProfileはCUDA349 Node（MatMul84/FusedMatMul12等）・CPU2 Node。
TF32を無効にし、CPUとの最大Vector差は約5.48e-8、Cosineは両方ほぼ1で基準内だった。
GPU実演算の動作確認であり、全Corpusの速度・検索精度・RAG品質の検証ではない。
CPU/GPU差が全入力で同じ小ささになることも保証しない。
Runtime定義・Lock・Profile・基準・結果のHashを上記Manifestへ保存した。

現行E5 Encoder/Index CLIへのGPU接続と、配布可能な専用uv環境・実行条件の固定は次工程。
未接続の状態で現行CLIを実行してもGPU構築済みとは扱わない。
正式IndexはCodeをCommit固定した専用Checkoutで作り、日本語の全取得/Gold対応・正式Splitと
日英RAG接続・Development実走・意味監査・未使用Calibrationへ進む。

```bash
uv run python scripts/prepare_english_token_corpus.py \
  --output-dir data/processed/clapnq/c508d78-e5-passages-v1
uv run python scripts/prepare_japanese_dataset.py build \
  --config configs/phase11_japanese_dataset_v2.json \
  --source-dir <固定Source Directory> --snapshot-dir <完了済み取得Directory> \
  --output-dir data/processed/wikipedia_human_retrieval_ja/02e85c8-groups-v2
```

日本語の正式生成は全取得記録の検証後に行う。Phase 12は開始しない。
