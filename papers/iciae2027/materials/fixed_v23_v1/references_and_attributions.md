# 出典・利用条件・帰属表示

## 原文の出典と利用条件

CLAPNQはprimeqa/clapnqの固定c508d78d8c5c2eecbf172fcf5f789004206e11fb。注釈のApache-2.0原文をlicensesへ複製し、Natural Questions由来本文のCC BY-SA 3.0を別に維持する。元取得記録はprovenance/dataset_records/clapnq_source_manifest.json。Dataset著者とWikipedia contributorsに帰属する。URL: https://github.com/primeqa/clapnq ・ https://ai.google.com/research/NaturalQuestions/download ・ https://creativecommons.org/licenses/by-sa/3.0/legalcode 。

日本語注釈はbaobab-trees/wikipedia-human-retrieval-jaの固定02e85c83a64f345aee62fba3a35af99c075a331f、カードにApache-2.0と宣言。Yusuke OdaとBaobab, Inc.へ帰属する。Wikipedia本文は注釈ライセンスと別で、CC BY-SA 4.0とWikipedia contributorsへの帰属を保持する。URL: https://huggingface.co/datasets/baobab-trees/wikipedia-human-retrieval-ja/tree/02e85c83a64f345aee62fba3a35af99c075a331f ・ https://creativecommons.org/licenses/by-sa/4.0/legalcode 。カードの例示QAは今回の選定外なのでコピーせず、前半の条件/構造説明をlicensesに保存した。

実使用/Goldの各PassageにTitle/ID/元本文SHA/Source Revision/URL/親・文字Spanを付け、provenance/document_attributions.jsonにも一意索引を保存した。日本語は保存済みoldid・Page ID・Revision日時を保持する。英語資産には元WikipediaのRevision IDが記録されていないため、Title由来の記事URLと固定CLAPNQ/元NQ Passage IDを併記し、存在しないoldidは作らない。帰属用URLは著者一覧を含む記事履歴へ戻るための参照である。

原文は既存のPassage分割/日本語脚注投影を保持し、ここでは選定行の抽出・JSON/CSV整形・表示用の先頭抜粋を行った。改変/抽出箇所・全文への対応を記録する。Wikipedia由来の原文/翻案には該当CC BY-SAと帰属・変更表示を維持する。Git/出版物で再利用する際も出典と適用ライセンスを添える。資料の著作権表示を、モデルWeightsや無関係な第三者資料へ一律適用しない。

利用条件の確認元: https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use/en#7._Licensing_of_Content 。2026-11-06に公式の再利用・帰属・変更表示条件とCC公式3.0/4.0の条件を確認した。記事別の第三者表示や参照本文の欠測/要約はqa_source.reference_evidence/reference_corpus_mappingに保持し、利用許諾や本文を捏造しない。

## モデル等

初回Qwen2.5-3B-Instructの元LICENSEはQwen Research LicenseでありApacheとは記さない。元LICENSEをlicensesへ同梱し、Weightsは配布しない。評価/書換えQwen3.5-9B Q6_KはUnslothの固定配布版で、保存ManifestのApache-2.0宣言を記録。モデル名/Revision/量子化/Hashを各manifestで照合する。Embeddingはintfloat/multilingual-e5-smallの固定614241f622f53c4eeff9890bdc4f31cfecc418b3。配布元 https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF ・ https://huggingface.co/unsloth/Qwen3.5-9B-GGUF ・ https://huggingface.co/intfloat/multilingual-e5-small 。

## 関連研究の引用候補と確認範囲

執筆Branchで既に確認した書誌/URL/確認範囲はprovenance/reference_review.md.txtをByte不変で保存した。Lewis et al. (RAG), Lost in the Middle, ConsJudge, RAGVUE, When the Judge Should Not Decide、Dataset/モデルカードが候補。既存の原稿referencesを正本にし、今回、関連論文の全本文を精読・新規性調査したとは主張しない。未確定の著者名/所属・取得不能な実モデル識別子は埋めない。論文本体と日英初稿は本作業で変更しない。

引用候補の著者・題名・年・会議/誌・URLの既存書誌は[reference_bibliography.json](provenance/reference_bibliography.json)、前回の確認範囲はprovenance/reference_review.md.txtを参照。今回の資料共有で文献内容を新たに認定したものではない。
