# 出典・利用条件と変更表示

この追加資料は選定済み80問に必要な資料だけを扱う。モデルWeights、全Corpus、未選定QA全文、認証情報、Session原ログ全体は配布しない。

- 日本語回復本文・保存Reference引用・Wikipedia公開メタデータ: Wikipedia contributors, 「ニューラルネットワーク (機械学習)」。[Revision98057227](https://ja.wikipedia.org/w/index.php?oldid=98057227)、[寄稿履歴](https://ja.wikipedia.org/w/index.php?title=%E3%83%8B%E3%83%A5%E3%83%BC%E3%83%A9%E3%83%AB%E3%83%8D%E3%83%83%E3%83%88%E3%83%AF%E3%83%BC%E3%82%AF_(%E6%A9%9F%E6%A2%B0%E5%AD%A6)&action=history)、[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)。元歴史版Wikitext/新しいparse HTMLを保存し、元取得実装でHTMLから読取本文を抽出した。今回の取得日時・応答Hashはevidence/japanese/publicの要求記録参照。抜粋・抽出は表示変更であり、当時の応答との同一性を主張しない。追加取得本文・抜粋は同じCC BY-SA条件を維持する。
- 英語Passage抜粋: Wikipedia contributors。記事Title、元文書URLのoldid、保存本文Hash、一致位置はenglish_passage_revisions.jsonに個別記載。[Natural Questionsの由来](https://github.com/google-research-datasets/natural-questions)、[CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/)。引用URLは候補を含む。特定のCorpus版の証明とは分け、原文の意味・文字列を変更していない。新しい抜粋/派生表も同じ帰属・継承条件を保持する。
- CLAPNQ元文書・README・注釈由来: [PrimeQA/CLAPNQ固定Revision c508d78](https://github.com/primeqa/clapnq/tree/c508d78d8c5c2eecbf172fcf5f789004206e11fb)、Apache License 2.0。注釈/メタデータのライセンスと、由来するWikipedia本文のCC BY-SAを区別する。必要な選定メタデータだけを投影し、元ファイルの位置・Hash・変換を記録。元LICENSEは確定済みfixed_v23_v1/licenses/CLAPNQ-Apache-2.0.txtに同梱されている。本補足にも同じLICENSEを保存する。
- 日本語Reference注釈由来: Oda/Baobab, wikipedia_human_retrieval_ja, 固定Revision02e85c83a64f345aee62fba3a35af99c075a331f。注釈はApache-2.0、Wikipedia本文は別条件。[固定Dataset](https://huggingface.co/datasets/baobab-trees/wikipedia-human-retrieval-ja/tree/02e85c83a64f345aee62fba3a35af99c075a331f)。既存注釈・引用・Labelは訂正せず保持した。
- CLI/Session証拠: 元研究Jobの識別メタデータを最小抽出。Account ID、認証設定、メッセージやツール定義など対象外のフィールドを除外した。マスキング/投影の位置はJob別の行番号・JSON Pointer・元行Hashで追跡する。モデル名やカタログHashをServing版IDへ読み替えない。

今回の資料では出典調査の結果を追加しただけで、元の確定資料、実験条件、採点、主結果、区間、DOCXを変更していない。
