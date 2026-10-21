# Phase 11 日本語共通Corpusの全文保持Passage化

確認日: 2026年10月21日。[Source取得・正式Group分割](japanese_dataset_selection.md#8-全取得と正式group分割の完了)の
完了済み記事から、検索用Corpusを作成した。QA/Referenceを入力にせず、質問ごとのGold注入や品質・網羅性による
記事除外を行わない。旧Raw・QA・Split・Corpus/Runを保持する。

## 固定入力と変換

Configは`configs/phase11_japanese_token_corpus_v1.json`。
全2178 Titleの固定Plan Hash・Source Revision・成功/欠測数・一意記事数を結び付ける。
取得完了・保存応答/Revision/本文Hash・同一Pageの整合・指定削除本文エラーの規則を全件確認してから処理する。
未知FieldとQA/Reference Fieldを受け入れず、取得不能記事の本文を捏造しない。

同じPageの別名をまとめ、全2118記事の本文を連続文字Spanへ分割する。
Prefix/Specialを含む実Tokenizerで512 Token以内を確認し、元本文を全て再構成する。
子IDは既存の数字引用形式を保ち、親には過去Page/Revision/実描画本文Hashから作るIdentityを記録する。
親子対応表と全取得TitleのCatalogを別保存し、取得不能50・削除本文エラー2もCatalogに残す。

```bash
uv run python scripts/prepare_japanese_token_corpus.py \
  --snapshot-dir data/raw/wikipedia_human_retrieval_ja/corpus-20231225-v1 \
  --output-dir data/processed/wikipedia_human_retrieval_ja/02e85c8-e5-passages-v1
```

出力は`passages.jsonl`・`parent_map.jsonl`・`article_catalog.jsonl`・`report.json`。
Code/Config/Tokenizer/各記事Hashが一致する場合だけ再利用し、異なる既存出力と未完了Stageの上書きを拒否する。

## 実行・独立検証

| 項目 | 結果 |
|---|---:|
| 取得成功記録 / 一意記事 | 2126 / 2118 |
| 検索Passage | 30065 |
| 保持した元本文の文字数 | 22341944 |
| 最大実入力Token | 501 |
| Passage化区間 | 約47.18秒 |
| ピークRSS | 534818816 Byte |
| Embedding推論 / LLM生成 | 0 / 0 |

別Scriptで全保存Passage・親子対応・Catalogを読み直し、各子の元記事文字Span・本文Hash・実Token数、
全2118記事の全文再構成・別名重複排除、全2178 Titleの成功/欠測保持を確認した。
正規配置の元Raw6494ファイルもHash/容量不変だった。新規12 Testを含む全392 Test成功（ホスト5.03秒）、Ruff成功。
確認根拠は`data/manifests/phase11_japanese_token_corpus_manifest.json`。

## 参照の単位と残る工程

親Identityは日本語の記事単位であり、英語の元Passage単位と粒度が異なる。
関連性と、個々の子Passageが回答の要点を支持するかは区別する。同じ親の子を別々のGold文書として加算しない。
このCorpus生成ではQAを読まず、親IdentityをQAのGoldへ対応させたわけではない。
原QAの`gold_passage_ids=[]`/`pending_passage_build`を保持し、新Corpusも
`pending_qa_parent_and_quote_audit`と明示する。次に引用元記事・引用原文のSpan・人手要約/欠測を監査する。

日本語約3万/英語約18万のCorpus規模、記事/元Passageの参照粒度、時点・検索品質などの差を報告する。
別Dataset間の差を言語単独の因果効果と断定しない。全838 QAを保持し、失敗や欠測の都合によい除外・補充をしない。

英語の新CUDA IndexはCommit ded26faの専用Checkoutで構築中。日本語新Index、参照対応、新RAG接続・
日英Development/意味監査・未使用Calibration・最終固定は未完了。Gate 11未通過、Phase 12未実施。
