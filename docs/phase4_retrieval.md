# Phase 4: 共通Corpusの検索Index

## 実装範囲と研究上の位置づけ

Phase 4は、固定Corpusを質問文字列から検索できる状態にする工程である。BM25とEmbeddingは
同じ178,890 Passage、同じ原文順、同じPassage IDを使う。Titleによる検索範囲制限、
QAのReference・Gold・Selected Sentences・Answerability・Provided Passageの検索入力への混入は行わない。
Corpusの本文だけをIndex化し、検索結果からTitle・原文・ID・Source Revisionを取得する。

今回の条件は開発用初期条件である。Phase 5のBaselineはEmbedding検索を使用し、Phase 6で
BM25とのRRFを実装してCalibrationでRetrieverを調整・固定する。3方式比較では同じ固定Retrieverを
共有する。Phase 4ではLLM生成、Failure判定、Recovery、独立品質判定、最終Evaluationは実施しない。

## 固定した検索条件

Index Version: `c508d78-retrieval-v1`。
Corpus: `data/processed/clapnq/c508d78-base-v1/passages.jsonl`。
Corpus SHA-256: `c847751985c2f95987628800a3a8a12aa274da37dee088310f74b6bddb1ea103`。

| 項目 | BM25 | Embedding |
|---|---|---|
| 検索対象 | Passage本文のみ | Passage本文のみ |
| Library | bm25s 0.3.12、NumPy 2.5.3 | ONNX Runtime 1.30.0、tokenizers 0.23.2、NumPy 2.5.3 |
| Algorithm | Lucene BM25、Lucene IDF、k1=1.2、b=0.75 | 全件の厳密Cosine検索、NumPyのBlock内積 |
| Tokenization | Unicode正規表現`(?u)\b\w+\b`、lower、1文字Tokenも保持 | Model付属BERT Tokenizer、特殊Token込み最大256 Token |
| Stopword / Stemmer | どちらもなし | ModelのTokenizerに従う |
| Model | 使用しない | `sentence-transformers/all-MiniLM-L6-v2` |
| Model Revision | 使用しない | `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` |
| 実行する重み | 使用しない | 公式`onnx/model_quint8_avx2.onnx`、CPUExecutionProvider |
| Pooling / Normalization | 使用しない | Attention Mask付きMean Pooling、L2正規化 |
| Vector | BM25 Scoreをfloat32で保存 | 384次元、float32、Row単位で保存 |
| 実行条件 | NumPy Backend | Batch 1、intra-op 6 Threads、inter-op 1 Thread |
| 検索時Memory | Sparse Arrayをmmap Load | Vectorをmmap Load、8,192件ずつ内積、全ScoreのみRAMへ保持 |
| 同点Rule | Score降順、同点はCanonical CorpusのRow順 | 同左 |
| CLIのTop-k | 初期値5。該当Tokenなし・正Scoreなしの場合は空結果 | 初期値5 |

公式モデルは384次元・最大256 Word Pieceである。Mean PoolingとL2正規化も公式利用例に沿う。
参照: [公式Model Card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)、
[固定RevisionのFile一覧](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/1110a243fdf4706b3f48f1d95db1a4f5529b4d41)、
[BM25S公式実装](https://github.com/xhluca/bm25s)。

公式量子化版を選んだ理由は、ノートPCのCPU・RAMで全Corpusを生成し、PyTorch/GPUを必要としない
構成にするためである。量子化と256 Tokenへの切詰めは検索結果へ影響し得る。重みFile Hashと
切詰めPassage数を記録し、非量子化版や別Modelと同等の性能は仮定しない。初期条件を変更するときは
新しいIndex Version/出力先で再構築し、比較方式間の共通条件と仕様書を更新する。
切詰めはEmbeddingへの入力にだけ適用し、保存Corpusと検索結果の原文は全文を保持する。

## 実行手順

### CPU実行条件を選んだ測定

固定Corpusの原文順先頭128件で、BatchとONNX intra-op Thread数を測定した。
Batch 1の所要時間は1 Thread=3.525秒、2=3.276秒、4=2.090秒、6=1.759秒、8=1.721秒だった。
4 ThreadsでBatch 8/16/32はそれぞれ3.914/4.098/5.002秒だった。
この環境では単件Batchが速く、6と8 Threadsの差が小さかったため、Batch 1・6 Threadsを選んだ。
これはCPU実行速度に基づく初期条件の選択であり、質問の検索精度を使ったCalibrationではない。
同時に別作業も行ったWindows環境の少量測定であり、全件で同じ速度を保証しない。

Repository Rootで、固定QA・Corpus・Splitを生成した後に実行する。

```powershell
uv sync --locked
uv run python scripts/download_embedding_model.py
uv run python scripts/build_retrieval_index.py --kind bm25
uv run python scripts/build_retrieval_index.py --kind embedding
uv run python scripts/validate_retrieval.py --kind bm25
uv run python scripts/validate_retrieval.py --kind embedding
uv run python scripts/build_retrieval_manifest.py
```

検索の例:

```powershell
uv run python scripts/search_corpus.py "who does the voice of plankton from spongebob" --kind bm25 --top-k 5
uv run python scripts/search_corpus.py "who does the voice of plankton from spongebob" --kind embedding --top-k 5
```

モデル取得には通信が必要である。取得後のIndex構築・検索・検証はローカルFileのみを使い、質問や
Corpusを外部APIへ送信しない。`--offline`でModel File Hashを再検証できる。
Model Cache、Raw/Processed Corpus、Index本体はGit管理しない。

## 成果物と整合性

- `src/rag_research/retrieval/`: Corpusアクセス、BM25/Embedding検索、Manifest検証、Development検証。
- `scripts/*retrieval*.py`、`download_embedding_model.py`、`search_corpus.py`: 取得・構築・検証・検索CLI。
- `tests/retrieval/test_indexes.py`、`test_encoder.py`: 小規模Corpusで順位・同点・ID対応・破損拒否・
  再開・Gold入力分離、Paddingを除外するPoolingとModel Cache保護を確認。
- `data/models/all-MiniLM-L6-v2/{revision}/`: 公式重みとTokenizer、設定、Model Manifest。
- `data/indexes/clapnq/c508d78-retrieval-v1/{bm25,embedding}/`: ID順List、byte offset、検索Array、
  `manifest.json`、実測値`build_measurements.json`。
- `data/processed/retrieval/{bm25,embedding}_development_smoke.json`: 開発用検索結果・Gold照合・時間・Memory。
- `data/manifests/clapnq_retrieval_manifest.json`: Git管理する共通Corpus・Model/Library/Parameter・全Index File Hash。

Index Manifestは日時・絶対Path・実測時間を含めない。Corpus/検索Array/ID対応のSHA-256を検証してから
再利用・検索する。完成済みIndexを異なる条件で上書きしない。別出力先では
`--output-dir data/indexes/clapnq/c508d78-retrieval-v1-verification/bm25`等を指定する。
BM25のByte再現性は実データでも確認する。EmbeddingのFloat計算はCPU/OS/Library差の影響を受け得るため、
他環境でByte一致を保証せず、Hash差と数値差・順位を記録する。全方式は同じ確定Indexを共有する。
別PCで再生成したEmbeddingのHashが固定Manifestと異なる場合は、固定済みIndexを転送して共用するか、
別VersionのManifestで差を記録する。既存の固定Manifestを再生成結果に合わせて上書きしない。

Embedding生成は`.building`内のcheckpointに完了Row・条件・ID対応Hash・完了Vector領域Hashを記録する。
約20秒ごとにVectorをflushしてcheckpointを更新する。中断時は同じコマンドで再開でき、最後の
checkpoint以降は再計算する。条件・Corpus・完了領域が変わった場合は拒否する。BM25はcheckpoint再開に
対応しない。生成一式の初期化途中で失敗した場合は、新しい出力先を使用する。完成直前の移動失敗は
Manifest検証後に再試行できる。Windowsではmmapを閉じてからDirectoryを確定する。
最後のVectorの有限値・L2 Norm検証も8,192件ごとのBlockで実行し、全Vectorの二乗Arrayを
一度にRAMへ作らない。取得済みModelはManifestと照合してOffline再利用し、Hash不一致を再取得で隠さない。

## 開発用確認と限界

Development内のAnswerableを`SHA-256("42:" + record_id)`昇順に並べ、先頭50問を使用する。
選定は性能結果に依存しない。同じ質問で両方式を確認する。Gold IDは検索後のOffline照合だけに使う。
UnanswerableにはGoldがないため、このRecall/MRR/nDCG集計の対象にしない。全QAのGold存在確認は
Corpus/ID対応の検証であり、Calibration/Evaluationの検索性能測定ではない。

Recall@5/10はGold集合に対する取得割合の問ごとの平均、MRR@10は最初のGold順位の逆数、
nDCG@10はGold ID一致をBinary Relevanceとする。Latencyは検索のみ、Resourceは検証Processを
100 ms間隔で測ったPeak RSSとWall Timeである。Peak RSSはOS全体の使用Memoryではない。
50問のSmoke結果から最終精度・方式優劣・信頼性向上は主張しない。調整と最終評価は後続Phaseで行う。

## 2026-10-06の実測結果とGate 4

ノートPC（Ryzen 7 7735U、RAM 16 GiB/OS認識15.21 GiB、Windows）で、両Indexの全178,890件を
生成・検索検証した。同じDevelopment Answerable 50問のStable IDが一致することも確認した。

| 指標 | BM25 | Embedding |
|---|---:|---:|
| 収録Passage数 | 178,890 | 178,890 |
| 全QAのUnique Gold ID数 / 欠損数 | 2,074 / 0 | 2,074 / 0 |
| Development Smoke問数 | 50 | 50 |
| Recall@5 | 0.40 | 0.62 |
| Recall@10 | 0.50 | 0.70 |
| MRR@10 | 0.24494 | 0.40800 |
| nDCG@10 | 0.30590 | 0.47802 |
| 検索Latency p50 / p95 | 2.54 / 3.41 ms | 17.38 / 20.00 ms |
| 検証Process Peak RSS | 162.87 MiB | 408.48 MiB |

BM25構築は22.49秒、Sampled Peak RSS 717.54 MiB。保存した検索ArrayとID対応は計106,311,746 Bytes。
別Directoryで全Index FileとManifestを再生成し、Byte単位で一致した。

Embeddingは60,349件で一度停止し、Hash照合後に同じ条件で再開して全件を完了した。
最初のSegmentはProcess起動から停止まで852.75秒・OS Peak Working Set 234.20 MiB、
再開SegmentはBuild Monitorの1853.54秒・Sampled Peak RSS 413.41 MiB。
測定範囲は異なるが、両Segmentを合わせた所要時間は約45.1分だった。
再開Segmentの測定はEncoder Loadより後、最終Manifest Hash生成より前である。
切詰めは14,598 Passage（約8.16%）、Vector Fileは274,775,168 Bytesである。
全件Embeddingの別Directory再生成・Ubuntuでの数値/順位再現は未実施で、Mini Corpusでの再開結果の
Byte一致と実Corpusでのcheckpoint再開を検証した。

固定Hash:

- Ordered Passage IDs: `3eb9592aaca66faa0ebb7431a72cc5f4055ebcc71e992bc20042beb282f5c3c2`。
- BM25 Index Manifest: `69e521f1d4c350e8e3cfd0c0e153d610ff9e712e6aed650f41d60b5ab106b604`。
- Embedding Index Manifest: `4619ea7372139d66230a202879e6b482b7cd2cd61c87d013808573d20b2327cb`。
- 共通Retrieval Manifest: `1d1c03bffe6a1b6ce402ed16895b5a72cd0fb9d353c6fd53cda828755e335cdd`。

両Indexの共通Corpus/ID順、Gold欠損0、質問だけからTop-k検索、初期条件と生成物Hashを確認したため
**Gate 4通過**とする。RRF、回答生成、自己評価・Recovery、最終Evaluationは未実施である。
この50問の差は最終精度・信頼性改善・方式優劣を示す比較実験ではない。

最終検証: `uv run pytest` 86件成功・Skipなし（21.60秒）、`uv run ruff check .`問題なし。
同条件でのEmbedding構築CLIと共通Manifest固定CLIの再実行も、既存成果物を変更せず成功した。
