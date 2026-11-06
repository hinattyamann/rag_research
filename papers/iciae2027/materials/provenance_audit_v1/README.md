# 固定v23の出典・採点モデル追加調査 v1

2026-11-06。確定済み80問資料とは別の補足資料。元Run/Corpus/設定/採点封印/Label/日英DOCXは変更せず、新規研究用推論0・再採点0。調査の完了と、未取得情報の解決を区別する。

## 結論と本文への影響

| 対象 | 確認・回復した情報 | 未解決・記述上の制約 |
|---|---|---|
| Main日本語QA857の参照記事 | 元要求はHTTP200で、Page5273510についてCutoff以前の版が返らなかった。公開移動記録から旧Page56523へ追跡し、2023-11-21のRevision98057227の本文を今回取得 | 当時のCorpusには存在しない補足取得。過去の描画本文と同一とは証明しない。保存Reference引用の全文は今回の抽出本文と完全一致せず、部分引用の一致だけを確認 |
| 外部採点84 Job | 対応するCLIイベント・Sessionログを全件確認。歴史的CLI版0.164.0-alpha.11.1、指定モデルgpt-6.1-sol・effort highを回復 | 確認できたモデル名は設定/クライアント記録。厳密なServing Snapshot IDは確認できず。「サービスが非公開」とは断定しない |
| 選定英語40問・222 Passage | 元QA文書のoldid付きURLは36/40問で回復。199/222 Passageには保存上流文書内の完全一致本文とURL候補がある | QA元文書のURLと実検索Corpusの版対応は別。Corpus生成時の直接対応記録がなく、厳密なCorpus版同定は0件。23 Passageは確認範囲で一致候補なし |

## 証拠索引

| ファイル | 読み方 |
|---|---|
| [findings.json](findings.json) | investigation_statusとresolution_statusを別々に記録した結論 |
| [japanese_reference.json](japanese_reference.json) | 元要求、移動、回復版、引用一致、実使用入力5件・既存採点への対応 |
| [evidence/japanese/](evidence/japanese/) | 元Raw記事/要求の同一バイト複製、今回の6公開要求/応答と取得日時・Hash、回復本文 |
| [annotation_jobs.json](annotation_jobs.json) | 84 Jobの集合/言語/採点種別と個別証拠への入口 |
| [evidence/jobs/](evidence/jobs/) | Job別input/output/Packet Hash、匿名候補と元QA/段階、Receipt時刻、イベント型/行/JSON Pointer/元Hash |
| [english_qa_sources.json](english_qa_sources.json) | 40問の元QA IDと元文書URL。元IDが見つからない4問も保持 |
| [english_passage_revisions.json](english_passage_revisions.json) | 222 Passageの本文Hash、QA/用途、候補oldid、元ファイル/行/一致Byte位置。候補を同定済みに格上げしない |
| [english_case_passages.json](english_case_passages.json) | 掲載候補case_01/case_03/case_04から対応Passageへ移る |
| [evidence/english/scope.json](evidence/english/scope.json) | 調査範囲・上流の版重複排除仕様・一致方法と限界 |
| [evidence/source_index.json](evidence/source_index.json) | 歴史的元パス・Byte数・SHA-256。元パスは来歴文字列であり、検証器は開かない |
| [evidence/copy_index.json](evidence/copy_index.json) | 完全複製と元ファイルHashの対応。ログは別途フィールド抽出と記録 |
| [preservation.json](preservation.json) | 元成果3,524ファイルの抽出前後Hash一致。旧資料の登録Source2,627件も照合 |
| [paper_wording_en_ja.md](paper_wording_en_ja.md) | 方法・限界に使用できる日英同内容の文案 |
| [attributions.md](attributions.md) | 出典、固定版、利用条件・帰属・変更表示 |

CLI/Sessionは識別メタデータだけをJSON投影した。元ファイルHash、行番号、元行Hash、JSON Pointer、除外内容を保持し、Account ID/認証設定/メッセージ/巨大ログ全体は共有しない。人工検証・追加実験Jobを混ぜず、既存資料に収録された84 Jobだけを入口にした。

## 日本語記事の原因と回復範囲

当時のRaw要求は2026-10-21T05:00:44.977852UTC、Cutoffは2023-12-25T23:59:59Z。HTTP200、Namespace0、現在タイトル/Page5273510は返ったがrevisionsがなかった。本文parse要求は実行されていない。削除本文のpermissiondeniedや通信エラーが今回の直接原因ではない。

公開移動Log8295729は2026-07-26T15:45:54Zの移動先「ニューラルネットワーク (機械学習)」と元logpage56523を示す。同時刻に現Page5273510の最古公開版110422898/parentid0が存在する。タイトルに対する現在のPage履歴を引いた結果、Cutoff以前の版が返らなかったという説明を、この証拠に基づく原因解釈として記録した。公開削除履歴に別の版の部分削除はあるが、今回の空応答をその権限エラーと説明しない。Page13492「出家」の別件エラーも使わない。

旧Page56523ではCutoff以前の最新公開版98057227（2023-11-21T16:00:37Z）が取得でき、本文parseも同一Page/Revisionだった。回復はこの歴史版に限定し、現在版/別版で埋めていない。HTML→本文は元取得時のarticle_text実装をそのまま使用。今回の応答/抽出本文Hashと取得日時を固定する。テンプレート展開などが当時と同じという証明ではなく、元の欠落記録もそのまま残す。

保存Referenceには重複した文字列もあり、全文の逐語一致は得られなかった。記録した2つの部分引用は一致するが、同じReference全文を回復したとは扱わない。実使用根拠5文書・A/B・外部採点・比較可能状態は既存資料で追跡できる。当該問の除外、Reference修正、採点修正や感度解析は実施していない。

## 英語版候補の扱い

40問のused/gold/corpus/gold-corpusに登場する222個の異なるPassageだけを対象にした。元CLAPNQ c508d78のoriginal_documentsでは、選定QA IDの対応と対象Passageのdocument_title/document_url/document_plaintextだけを調査し、未選定QAの質問・回答・注釈は調査対象にしない。dev側も選定Passageの上流文書メタデータに限定し、未使用Evaluation結果は読まない。

元文書4ファイルはローカルCRLFをLFへ置換すると固定Git Blobと同一だった。その比較・Git Blob ID・元ファイルHashを保存した。これは調査上の比較で、元ファイルは変更していない。

元QAのURL回復は36問。残る4問は元example_idが保存original_documentsに見つからず、IDの符号変換等で推測して結合していない。222 Passageの候補内訳は1版166件・2版33件・一致なし23件。URLから明示的に読んだoldidと、本文の完全一致Byte位置を保存した。Title/本文の正規化、Passage IDの数字からの版推測、最新Revisionでの補完は行っていない。

上流retrieval READMEは、複数の文書版を高いROUGE一致により重複排除したと記載する。完全一致の抜粋は別版にも存在し得るため、一致候補が1件でもCorpusの厳密な版と断定しない。引き続き固定Dataset Revision/Passage ID/実使用本文Hashで入力を特定し、QA参照元URLとCorpus版を別欄で引用する。追加の元NQ対応台帳は登録取得資料内に見つからなかった。

## オフライン検証

Repository Rootから:

```bash
uv run --no-project python -I papers/iciae2027/materials/provenance_audit_v1/verify_audit.py --audit-open
```

フォルダ単独を別の場所へ移しても同じ検証器で動く。標準ライブラリのみを使い、資料外ファイルとSocketへのアクセスを拒否する。全成果Hash、表と証拠、84 Job、40 QA/222 Passage、候補/不明の状態、回復版の識別と本文抽出を検査する。検証成功は未解決oldid/Serving版IDの解決を意味しない。

既存確定版のverify_materials.py --audit-openも作業前後に実行する。確定版Tree `5fb236667f6e4411a730187dc1e6ce80f27c710f`、missing_information.json、元の主結果・区間を変更しない。

## 抽出処理と任意の公開元再取得

[build_audit.py](build_audit.py)は研究室での読取専用抽出処理。元Source/Runの前後Hash検証を含み、完成済みfindings.jsonの上書きを拒否する。ノート検証では実行不要。

```bash
uv run --no-project python build_audit.py --source-repo /path/to/lab/repo --baseline /path/to/fixed_v23_v1 --public-evidence /path/to/saved-public-responses
```

[fetch_public_evidence.py](fetch_public_evidence.py)は別工程の任意公開元取得。既知の6件だけを新規フォルダへ保存する。実行すると通信するためオフライン検証には使わない。

```bash
uv run --no-project python fetch_public_evidence.py --output /path/to/new/public-evidence
```

今回の実取得では同じ6要求を順に実行し、保存応答の取得時刻/URL/HTTP状態/Hashを残した。後日再取得では描画内容が変わる可能性があり、今回の応答Hashを再現するとは限らない。

今後は元QA→Corpus→Wikipedia版の明示対応台帳と、実サービスが返す識別情報があればそのイベント位置/生応答Hashを保存する案がある。今回は文書提案にとどめ、収集コードや過去来歴は変更していない。著者確認・文献精読・教員確認・投稿は別工程。
