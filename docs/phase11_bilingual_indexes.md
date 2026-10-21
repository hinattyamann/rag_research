# Phase 11 日英全CorpusのCUDA Embedding Index

確認日: 2026年10月21日。[正式GPU入口の監査](phase11_embedding_cuda.md)を通したCommit
`ded26fa76f076e502b406296c466ceaa46f5da96`を専用Checkoutへ固定し、日英それぞれの新Indexを構築した。
入力はQA/Referenceを含まない全共通Corpusで、未使用QAの結果を見て条件を変えていない。

## 固定条件と結果

両言語とも公式Multilingual E5 smallの同一Revision/FP32 ONNX、CUDA Device0・TF32無効、
Batch16・CPU6 Threads、専用uv Lockを使った。各構築の前にCode/Corpus/親対応/LockのHash、
GPUと実行計画を保存した。旧Corpus・Index・Runを保持した。

| 項目 | 英語 | 日本語 |
|---|---:|---:|
| Corpus Passage数 | 183889 | 30065 |
| 構築区間 | 633.53秒 | 168.23秒 |
| ピークRSS Byte | 1582141440 | 1319391232 |
| 切詰め | 0 | 0 |
| 完了後の再開追加Embedding Batch | 0 | 0 |
| 合成質問の検索Batch | 1 | 1 |

全Vectorの有限性・384次元Float32・L2正規化、全Corpus行とID/Byte Offsetの対応、
元の全親参照との対応を別Scriptで読み直して確認した。
完成Indexを正規配置へ複製し、各5ファイルの同一Byte/HashとManifestを照合した。固定Checkout側の原本も保持した。
実GPU Encoderで両Indexを再開して構築追加0 Batch、合成質問の検索・全Indexファイル不変を確認した。
合成質問は動作確認だけであり、QA/Reference本文・正解関連性・回答品質を評価していない。

正規配置は次のとおり。

- 英語: `data/indexes/clapnq/c508d78-e5-cuda-v1/embedding/`
- 日本語: `data/indexes/wikipedia_human_retrieval_ja/02e85c8-e5-cuda-v1/embedding/`
- 固定Checkout: `.tools/worktrees/phase11-multilingual-index-v1/`
- 計画・ログ・全件検証: `data/runs/index_build/phase11-{en,ja}-e5-cuda-v1/`

小さいHash Manifestは`data/manifests/phase11_bilingual_dense_index_manifest.json`。
大きいData/Model/Index/RunはGit同期対象外であり、別PCで利用する際は別途配置・Hash確認・uv環境再現を行う。
今回の単位は保存結果と文書の更新で、実装Testは直前の全392 Test/Ruff成功を参照する。
新たなTest実施とは記録しない。旧Run2500/英語Index23ファイルのHashも不変を確認した。

## 次工程

全Corpusの新しいBM25/Hybrid検索はまだ構築・接続していない。
日本語QAの引用元親記事・引用原文Span・人手要約/本文欠測の対応と、新日英RAG/指示文/予算/品質入出力を整備する。
Development実走・意味監査・英語既知問題の確認後、結果前に未使用Calibrationの対象/候補/採用・停止規則を固定する。
このIndex構築だけで検索精度や回答品質の妥当性を認定せず、Gate 11未通過・Phase 12未実施を維持する。
