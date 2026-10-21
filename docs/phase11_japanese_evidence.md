# Phase 11 日本語参照のCorpus対応と原文監査

確認日: 2026年10月21日。全838 QAを保持し、原質問・Reference回答・文書Group/Split・原行Hashを変えず、
既存Corpusの親記事と引用原文の位置を対応させた。QA/Reference情報はOffline専用で、生成/Judge/書換えへ渡さない。
Corpus/IndexへQAの引用断片を追加していない。これは参照の機械監査であり、回答品質・意味支持の認定ではない。

## Version 1の規則と実績

Configは`configs/phase11_japanese_evidence_v1.json`。固定した元Group/Corpus Report Hashへ結び付け、
参照Titleは宣言済みCatalogへのNFC完全一致で対応させる。
引用は原文一致、次に空白差だけを許した一致で全出現位置を保存する。複数箇所なら曖昧さを明記する。
人手要約は原文引用と区別し、本文欠測・未一致を回答不能LabelやQA除外へ変換しない。

| 対象 | 件数 |
|---|---:|
| 全QA / 開発・Calibration・Evaluation | 838 / 545・84・209 |
| 全参照 / 回答から引用された参照 | 1919 / 1741 |
| 引用参照の原文位置を確認 | 834 |
| 引用参照の本文中に原文一致なし | 775 |
| 引用参照に原文引用なし | 102 |
| 原文引用を持つ参照で記事本文を取得できない | 30 |
| 一部でも引用元本文が欠測するQA | 25 |
| 引用元本文を一つも取得できていないQA | 9 |
| 引用した人手要約を含むQA | 94 |

人手要約等102参照を含め、原文引用なしの理由と元のAnnotationを保持する。
未一致は、同じ意味の内容がないことや回答不能を示すLabelではない。
未使用Calibration/Evaluationの質問・回答本文を調整に表示せず、機械変換・原行/Spanの照合と集計だけを行った。

出力は`data/processed/wikipedia_human_retrieval_ja/02e85c8-qa-corpus-v1/`。
原QA/Group/Splitは別Versionのまま保持する。子Passageの重なり、全引用位置/Hash、引用/非引用の対応、
原838 QAの各FieldとSplitを別Scriptで再確認した。新規19 Testを含む全411 Test成功（ホスト5.12秒）、Ruff成功。
根拠は`data/manifests/phase11_japanese_reference_audit_v1.json`。

## 各Fieldの意味と品質資料への引継ぎ

- `gold_parent_ids`: 本文を取得できた引用元の記事親だけ。記事の各子が全要点を支持する意味ではない。
- `unavailable_cited_reference_ids`: 取得できない引用元を別保持。Page IDがなければ未解決Titleの参照単位であり、既知の一意記事数とは断定しない。
- `gold_passage_ids`: 実際に確認した引用文字Spanと重なる子だけ。親単位の検索評価のGoldへ読み替えない。
- `reference_corpus_mapping`: 全参照の使用/未使用、親、原文の全位置/Hash、重なる子、人手要約と欠測を保存する。

記事関連性、回答の必須要点、実使用Contextによる支持を別々に扱う。
新しい検索評価と品質Packetへの接続は未実施で、旧英語のGold ID前提のValidatorへそのまま通したとは扱わない。
欠測と未一致も全838 QAの状況として報告し、品質が不明な例を都合よく除外・補充しない。

## 開発用資料で確認した表示形式差と次の修正

先頭100件から保守的に予約したDevelopmentのSource ID1/10/100の引用を確認した。
`[4]`・`[注釈 1]`・`[3]`・`[2][3]`等の脚注表示が引用にはあり、CorpusのHTML抽出では除かれている差があった。
原文引用や本文を改変せず、Version 1の全結果と未一致を保持する。
上記3例は開発予約内の診断で、未使用QAの本文・Model/品質結果を調整に閲覧していない。

次は、保存済み原HTMLの`sup.reference`の可視文字と位置を検証する別Versionを作る。
単に角括弧内の数字を一括削除せず、原HTML中の実脚注表示を含む描画に引用全体が一致することと、
脚注表示を取り除いた描画が既存Corpus本文へ空白差以外なく対応することを必要条件にする。
引用位置を元のCorpus文字位置へ投影し、実本文Hash・脚注位置の証拠を保存する。
本文中の配列記号等と脚注を混同しない負のTestも設ける。人手要約の原文扱い・意味による類似一致はしない。
これは既知の表示形式差の修正であり、Judge/品質の採用基準を緩めるものではない。

日英BM25の全構築と合成Hybrid動作は[検索基盤の記録](phase11_bilingual_indexes.md)へ記録した。
アプリケーションFactory、新日英RAG/予算/品質、Development意味監査・未使用Calibrationと最終凍結は未完了。
Gate 11未通過、Phase 12未実施。

## Version 2: 原HTMLの脚注位置を検証する投影

`wikipedia_reference_projection.py`と`phase11_japanese_evidence_v2.json`を追加した。
原HTMLの`sup.reference`だけを位置・可視文字・部分HTML Hashとともに記録し、脚注表示を含む描画を作る。
脚注以外の全可視文字が既存Corpus本文へ完全に対応することを確認し、引用全体の空白差だけの一致を探す。
脚注を丸ごと含む一致だけを元本文の文字位置へ投影し、原HTML/Request/本文SpanのHashを保存する。
本文の括弧数字・別位置の脚注・通常の上付き文字・脚注の途中・非表示要素は根拠へ変換しない。
人手要約の扱い、親記事単位と欠測の区別、Corpus本文/Indexは変更しない。

初回の全件処理は可視文字が空の脚注要素で停止し、Dataset未生成を確認してCode/失敗理由を保存した。
空の要素から根拠を作らずに除外する表示処理を追加し、本文の全文字対応条件を保って再実行した。
開発予約3例で事前基準を確認後に同じ規則を全QAへ適用しており、未使用QAの本文/Model・品質結果を調整に閲覧していない。

| 引用された1741参照の状態 | v1 | v2 |
|---|---:|---:|
| 位置確認 | 834 | 1493 |
| うち原HTML脚注の検証による追加 | 0 | 659 |
| 原文不一致 | 775 | 116 |
| 原文引用なし / 原文引用あり本文欠測 | 102 / 30 | 102 / 30 |

欠測を含む25 QA・全引用元本文欠測9 QA、人手要約を引用した94 QAは保持した。
未一致を含むQAは106件であり、全838 QAを除外・補充せず残す。
出力は`data/processed/wikipedia_human_retrieval_ja/02e85c8-qa-corpus-v2/`。v1も保持する。
新規21 Testを含む全432 Test成功（ホスト4.83秒）、Ruff成功。

別Scriptは本体の投影処理を再利用せず、原HTMLを各脚注位置の直前まで描画して本文中の挿入位置を求めた。
保存された脚注表示をその位置へ挿入し直し、引用全体と一致することを全保存投影で確認した。
引用/非引用合わせて665参照、延べ1452脚注表示の位置/Hashと投影先を照合し、v1の全位置・原Field/Group/Split・欠測を保持した。
同条件での再計算・再利用でも全6ファイルのByteが不変だった。
この再計算/再利用区間は28.94秒・ピークRSS168914944 Byteで、初回生成の計測とは区別する。
根拠は`data/manifests/phase11_japanese_reference_projection_v2.json`。

```bash
uv run python scripts/prepare_japanese_evidence.py \
  --config configs/phase11_japanese_evidence_v2.json \
  --groups-dir data/processed/wikipedia_human_retrieval_ja/02e85c8-groups-v2 \
  --corpus-dir data/processed/wikipedia_human_retrieval_ja/02e85c8-e5-passages-v1 \
  --snapshot-dir data/raw/wikipedia_human_retrieval_ja/corpus-20231225-v1 \
  --output-dir data/processed/wikipedia_human_retrieval_ja/02e85c8-qa-corpus-v2
```

これは引用形式の来歴確認で、意味支持や回答品質の認定ではない。残る不一致を類似表現へ置換せず、
参照状況として品質資料へ渡す。次は親単位Metric/品質Packetと、新Factory/RAG/指示文/予算を接続する。
