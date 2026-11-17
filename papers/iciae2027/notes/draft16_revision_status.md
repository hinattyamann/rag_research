# 初稿16：教員添削の6点と黄色の推敲の反映

記録：2026-11-17 13:34 JST。初稿15（d3b7282）を基に、教員添削PDFとユーザーの合意を日英同時に反映した。添削PDFの書込みは変更内容を検討する資料として扱い、採否はユーザーの方針に基づく。英語Word/PDFは8ページ、日本語Word/PDFは理解用9ページ。

## 6点への対応

| 番号・位置 | 具体的な変更 | 最終英文の要点 |
|---|---|---|
| 1・要旨 | 抽象的な shared rewrite の目的説明を、質問ごとに一つ生成し全条件で同じA/Bから選ぶ操作へ置換。 | “We generate one rewrite per question; all conditions select between the same initial answer and rewrite, keeping rewrite content fixed.” |
| 2・3.1節 | 入力固定と5順序の比較の間に、評価器へ提示する順序だけを変える接続を追加。 | “With these inputs fixed, we vary only the order of the evidence presented to the evaluator.” 続いて original / reverse / three seeded shuffles を説明。 |
| 3・3.3節 | 各経路の独立した端から端までの実行費用ではなく、必要処理の保存済み実測費用の合算であると明記。NR / AR / 評価経路の構成、共通書換えの経路別計上、実験収集・外部採点との区別を説明。 | “We reconstruct each route's LLM call and input/output token totals by summing recorded costs of required steps, rather than executing each route separately end to end.” |
| 4・表1 | 内部管理番号12を戻さず、Prompts行を追加。実験条件として必要な固定対象を記載。 | “Fixed by language for evaluation and rewriting” |
| 5・表6と5.2節 | 表6は総数26問と品質の3分類（14/8/4）だけに整理。費用行を削除し、表題と注を更新。26問が「書換えを実施した総数」ではなく「順序によって選択判断が変わった質問数」である文脈を保持。費用の差を本文へ移した。 | “All 26 also have different reconstructed token costs across evidence orders, including initial generation, evaluation, and rewriting when requested.” |
| 6・6.3節 | 信頼区間が0を含むことの意味を明示。差を示せないことと同等性の証明を区別し、質問・参照・コーパス差により言語そのものの効果を分離できないと説明。 | “These data do not establish a difference … This does not demonstrate equivalence.” |

全変更の英日Before/Afterとブロック配置の変更は [構造化差分](draft16_before_after_20261117.json) に保存した。

## 黄色の推敲の採否

黄色は教員の改善文として基本的に採用した。赤字の疑問・青色箇所の内容は原稿へ残さない。黄色のまま採用した内容と、調整した内容を区別する。

### そのまま採用した表現・内容

- 要旨冒頭の “using external evidence through retrieval-augmented generation”、複数形の “repeated original-order evaluations”。結果の数値と限界は保持。
- 3.1節の “Then, we fix …” と “Furthermore, reference answers …”。同一入力・seedの反復である説明は保持。
- 3.2節の文ラベルと supported の定義を連続させた文章、書換え段落の “and every condition …”。
- 3.3節の “rewrite decisions use F, and candidate labels are shared across routes.”
- 表6注の “Values represent question counts.”
- 6.1節の “The result reflects presentation changes under a fixed sampling seed; sensitivity across different seeds remains untested.”
- 6.3節の “Moreover” と “while including refusals …” による接続を含む段落全体。
- 結論冒頭の “We evaluated RAG’s evidence-order sensitivity across 200 questions, keeping the evaluator and parameters fixed.”

### そのまま採用しなかった箇所と理由

| 箇所 | 教員版の表現 | 最終対応・理由 |
|---|---|---|
| 要旨・共通書換え | “A shared rewrite separates answer selection from rewrite generation.” の未解決箇所 | 合意した具体的操作へ置換。抽象表現のままでは疑問1を解消しない。 |
| 要旨・研究目的 | “In this paper, we investigate … as well as …” | “We investigate … and …” に整理。意味を保ち、具体的操作の説明を追加しても要旨とKeywordsを第1ページ左段に収める。 |
| 要旨・収集と解析 | “we first collect … Then, a post-hoc pooled analysis covers … and quantified the following findings.” | “With fixed evaluator settings, we collected … A post-hoc pooled analysis covered …” とした。実施済みの収集・解析に過去形を用い、covers / quantified の時制不一致を解消。段階的収集・事後統合・件数は保持し、first / Then と findings の導入の重複を整理。 |
| 要旨・結果の導入 | “These results indicate that under this fixed configuration, …” | “Under this fixed configuration, …” と直接記述。結論の範囲を保って重複を削減。 |
| 要旨・限界の導入 | “While notable, this interpretation is limited by …” | “Interpretation is limited by …” とした。限界3点をすべて保持し、評価的な前置きを省いて左段内へ収めた。 |
| 3.1節 | “I.e., retrieval results …” | “Across these trials, retrieval results …”。前文の同一seed反復と同義の言換えではなく、試行を通じて固定した入力の説明であるため、関係を正確にした。“Furthermore” は採用。 |
| 3.3節・費用 | “rewriting while experimental collection …” | 費用段落全体を指摘3の合意に従い再構成。実測費用の合算と経路別計上が中心となるため、接続語だけの修正にはしなかった。 |
| 表6注 | “Rows 2,3 and 4 partition …” | “The three quality categories partition …”。費用行の削除に合わせて分類名で説明し、見出し行を数えるかによる曖昧さを避けた。 |

## 内容を保った追加整理と組版

初回の文章追加では英語が9ページとなり、要旨のKeywordsが右段へ流れた。文字サイズ・本文行間・余白・段組は変更せず、要旨の上記表現と導入・構成案内・貢献説明・費用考察・結論・具体例導入の重複表現を整理した。主張・条件・限界・結果数値・具体例の引用は保持。全文差分にはこの追加整理も含む。

表6は費用行を除くため題を選択回答品質へ変更。表1はPrompts行を追加。その他の表の数値・図資産・文献は不変。品質遷移の段落を2つに分割し、本文の論理順を維持しながら図表位置を移した。最終英語の12図表は段頭7件／段末5件で、全てキャプション・表注を含む一群として確認。見出しや本文が図表の上に残る状態を段頭とは扱っていない。

## 最終検証

- 日英99本文ブロック、全表注、全14文献のWord・PDF収録と対訳を確認。
- 英語8ページ、日本語9ページ。要旨はWord標準239語（空白区切り237語）、300語未満。Keywordsは5個。
- 現行公式テンプレートを再取得し、保存原本とSHA-256が一致。A4、上下25mm・左右16mm、85mm×2段・間隔8mm、本文Times New Roman 10pt、指定見出し、著者・所属・責任著者、公式の空行と引用書式を照合。
- 最終PDFの全17ページを画像で目視確認。英語要旨とKeywordsは第1ページ左段内。全12図表の段頭／段末検査に合格。
- 両PDFの全14文献リンクと全フォント埋込みを確認。研究条件・元資料・元ラベル・集計・区間に変更なし。新規推論・再採点・区間推定は0件。
- 文書スキルのrender_docx.pyはLibreOffice未導入で実行不能。既存原稿と同じMicrosoft WordからPDFを直接出力し、そのPDFを描画して全ページを検証した。
- 原稿検査29件とRuffの最終結果、および対象Word/PDF/ページ画像のHashは [最終検証](draft16_validation_20261117.json) に記録。

公開要項への適合を確認した。教員の投稿承認・投稿は未実施。次は著者・教員による内容確認と投稿承認、その後に投稿画面の追加条件照合と提出対象PDFの確定を行う。
