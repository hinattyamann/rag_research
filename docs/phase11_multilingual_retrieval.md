# Phase 11 多言語検索候補・記事Passage分割の実装と確認

確認日: 2026年10月21日。日本語Source・取得方針は[選定記録](japanese_dataset_selection.md)、
工程の正本は[ロードマップ](research_roadmap.md)。本記録はComponent検証であり、
日英の検索品質・日本語RAG全経路・未使用Calibration・本実験条件の採用は未完了である。

## 1. 日英共通の検索候補と選択理由

候補は`intfloat/multilingual-e5-small`、固定Revision
`614241f622f53c4eeff9890bdc4f31cfecc418b3`。
[公式Model Card](https://huggingface.co/intfloat/multilingual-e5-small/blob/614241f622f53c4eeff9890bdc4f31cfecc418b3/README.md)の
非英語にも適用する`query: `/`passage: `、Attention Maskによる平均Pool、L2正規化、最大512 Tokenに従う。
Embeddingは384次元で、既存の厳密なCosine検索・mmap Vector・RRFを再利用できる。

公開元のFP32 ONNXを直接使い、追加のModel Pythonコードや再量子化を使わない。
既存のuv依存で実行でき、実機でピークRSS約1.12 GBに収まったことを候補選定の根拠にする。
大規模モデルとの検索精度比較や、本研究Datasetでの検索優位性を確認したわけではない。
モデルCardはMIT表記。実験上の適合性と最終採用は後続のDevelopment/Calibrationで確認する。

公式9ファイルを固定Revisionから取得し、公開LFS SHA256またはGit Blob、容量を照合した。
計487,850,687 Byte（ONNX470,268,510、Tokenizer17,082,730 Byte等）。
`configs/phase11_multilingual_embedding_v1.json`へ全File SHA256/容量/Blobと条件を保存した。
取得とOffline再照合は`scripts/download_multilingual_embedding.py`による。
既存MiniLMのModel/Manifest/Indexは保持する。

## 2. 実装と本文保持

- `retrieval/multilingual.py`: 用途別Prefix、TokenizerのPadding ID、Mask付き平均Pool/L2、
  384次元・有限値を検査する。512 Token超過は推論前にエラーにし、切詰めない。
- BM25はE5 TokenizerのSubword IDをPrefix/Specialなしで使う候補。日本語にも単語間空白を仮定しない。
  日英で同じTokenizer条件を使えるが、旧英語の単語BM25と同じ条件とは扱わない。
- 共通Corpus読込みはDatasetを明示して新Sourceを扱う。既定はCLAPNQのまま、混在Corpusを拒否する。
  共通Dense構築と検索では文書/質問の用途を分け、既存Encoderの既定Config・呼出しは保持する。
- 新しいIndexは明示した出力先へ作る。Hash・Config・Sourceが異なる既存Indexの再利用を拒否する。
  設定変更・入力超過・未知の完了状態を、既存の成功へ上書きしない。

`data/japanese_passages.py`は記事本文だけを受け取り、QA/ReferenceからCorpusを作らない。
句点/段落境界を優先し、元の文字Spanを連続・重複なしに分ける。各部分のPrefix/Special込み実Token数を検査し、
Spanをそのまま連結して記事全文が戻ることを確認する。長い一文も必要なら分割し、文字を捨てない。
本文・Title・過去Page/Revision・日時・URL・記事/Passage Hashを保存する。
Passage IDはPage/Revision・抽出Version・実際の描画本文Hashの96-bit派生数値と文字Spanから作り、
既存の数値引用記号の形式に対応する。Templateの描画が変われば同Revisionでも別IDとなる。

## 3. 既知1記事の実走と限界

開発予約に属する経済産業省の取得済み1記事（Revision98468367、19,251文字）を使用した。
全Corpusを一部の記事へ縮小した本実験ではなく、既知1記事のComponent Preflightである。

| 確認項目 | 実測/結果 |
|---|---|
| Passage化 | 27件、最大実入力501 Token、全文の文字列再構成に一致 |
| 起動/構築 | Model初期化1.28秒、BM25約0.02秒、Embedding約2.62秒 |
| 条件 | CPUExecutionProvider、6 Threads、Batch4、FP32、RRF20・候補50・Top10 |
| 検索 | 新しく作った日英の質問文2件でBM25/Embedding/Hybridの動作を確認 |
| 保存/再開 | 同じIndexの再利用はEmbedding再実行0回 |
| 入力超過 | 推論前に拒否、切詰め0件 |
| 負担 | Embedding10 Batch（構築7・質問2・合成入力1）、処理区間約3.97秒、ピークRSS1,121,898,496 Byte |

1記事内のPassage検索なので、一般的な検索精度や日英差を測った結果ではない。
上記は保存区間の実測で、LLM生成・内部Judge・品質採点を含まない。LLM生成は0回。
RuntimeのTelemetry保存警告は出たが、実推論と有限L2 Vector・予算・保存を確認できた。

## 4. 英語側の回帰と次の条件整備

共通処理変更前Commit `4f1403f`と既定Dense/BM25 Configが一致した。
旧英語Index23ファイル・旧Run2500ファイルのHashは不変。新規13 Testを含む全351 Test（ホスト5.97秒）とRuff成功。
確認根拠は`data/manifests/phase11_multilingual_retrieval_preflight.json`。

英語Corpus178,890 PassageをQA/Reference/品質結果なしでToken長監査した。
E5 Prefix込み平均162.52、中央値132、p99=653、最大5513 Token。
3,130件（約1.75%）が512 Tokenを超えるため、既存Corpus全体を新Encoderへそのまま渡せない。
英語も元のPassage/Gold参照を保持した分割と対応表を別Versionへ作り、日英に同じ上限を適用できるようにする。
検索単位や語彙処理が変わるため、新しい英語Indexと検索/生成のDevelopment回帰・未使用Calibrationが必要である。
旧Runを新しい検索条件の検証済み結果へ読み替えない。

日本語の本文全取得・Gold引用対応・正式Split、英語側の上限対応、RAG Factory/指示文/品質入出力への接続と
意味監査は未完了。日英に共通の検索候補を用意したことだけで、最終条件やGate 11を採用しない。

## 5. 実行入口

```bash
uv run python scripts/download_multilingual_embedding.py --offline
uv run python scripts/build_retrieval_index.py --kind bm25 --encoder multilingual-e5 \
  --corpus <Passage JSONL> --source-dataset baobab-trees/wikipedia-human-retrieval-ja \
  --output-dir <新しいBM25 Index Directory>
uv run python scripts/build_retrieval_index.py --kind embedding --encoder multilingual-e5 \
  --corpus <Passage JSONL> --source-dataset baobab-trees/wikipedia-human-retrieval-ja \
  --output-dir <新しいEmbedding Index Directory> --batch-size 4 --threads 6
```

正式Corpus/Indexは取得・本文/Gold対応の監査と条件保存後に作成する。長時間構築はCommitを固定した専用Checkoutで行う。
