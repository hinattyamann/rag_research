# 教員指摘に対応した日英改稿と再確認結果

2026年11月16日。教員から受領した文章コメント5項目と、訂正Wordの赤字・強調・図1の吹出しを現行稿へ反映し、日英の初稿9を作成した。英語版は8ページ、理解用日本語版は9ページ。英語要旨255語、91対訳単位・7章・2図・10表・14文献である。教員に再確認を依頼できる原稿として検証した。著者・所属・責任著者情報は確認待ちの表記である。

正本は [英語版](../manuscript/iciae2027_manuscript_en.docx) と [日本語版](../manuscript/iciae2027_manuscript_ja.docx)。各版の内容、生成入力、図1、生成Manifestを同じ版にそろえた。[最終検証記録](draft9_validation_20261116.json)に正本・確認PDF・全17ページ画像のHashと検査結果を保存した。

## 文章コメントと理解しにくい箇所への対応

以下の位置は英語改稿の章節を示す。全項目について、対応する日本語本文も確認した。

| 先生の指摘 | 対象 | 加えた改変と確認結果 |
|---|---|---|
| Abstract冒頭からLLMに言及する | Abstract冒頭 | Large language models (LLMs) から始め、検索根拠を使うRAG、内部評価、採用・書換え判断へ順に接続した。 |
| RAGより先にLLMを説明し、modelの意味を明確にする | Introduction第1段落、3.1・3.3・4.2節 | LLMを入力に応じて文章を生成し、生成器・評価器に利用できるものとして導入した。評価呼出しと費用定義にもLLMを明記し、4.2節で二つのLLMの担当を説明した。埋込みは検索の構成要素として記述している。 |
| 短い文の連続を改善する | Abstract、Introduction第2段落 | Using、After、while、Among、Moreover、Howeverを用いて、統制・対象・内訳・費用・限界のつながりを明示した。Introductionは先生案の we propose to compare と It is also necessary to link を採用した。 |
| Introduction末尾に論文の構成を示す | Introduction最終段落 | 第2章の関連研究、第3・4章の設計・設定、第5章の結果、第6章の示唆・限界、第7章の結論・今後の課題を案内した。 |
| 表のNoteの意味と説明対象を明確にする | 表1〜10 | 全表注を改稿し、対応する行・列、集計単位、分子・分母、用語を明記した。各表の詳しい対応は後述する。 |
| Conclusion末尾にFuture workを1〜2文追加する | 第7章末尾 | 人手によるAIラベルの確認と評価器性能水準の比較、対応する日英質問による言語影響の検証を、既存6.3節から2文にまとめた。 |
| 内部評価と初回生成器の関係が分からない | 4.2節末尾の青色強調 | 初回回答を一つのLLMが生成し、別のLLMがその回答の評価と書換えを担うことを説明した。internal はRAGの回答選択処理に組み込まれた評価器を指すと定義した。直前のモデル名と対応する。 |
| CLAPNQに参考文献または説明が必要 | 4.3節の青色強調 | 保存履歴を、過去のCLAPNQ実験における質問と生成回答の記録と定義し、観測済み誤りを評価器の挙動確認へ使うことを説明した。CLAPNQの説明・引用がある4.1節へ参照し、診断資料の文献13も保持した。 |
| Lighter checks … this comparison が分からない | 6.2節末尾の青色強調 | 必要トークン数が少ない評価器、根拠順序間の判断一致を使う選択規則と具体化した。比較対象をOE・AR、比較項目を回答品質・費用と明示し、今後の比較として位置付けた。 |

## Wordの訂正への対応

先生の訂正案を基礎に、文脈や研究上の意味に合わせて調整した。一般コメントと重なる箇所も含めて照合した。

| 対象 | 反映した内容 |
|---|---|
| Abstract・Keywords・IntroductionのRAG表記 | retrieval-augmented generation のハイフンを反映した。 |
| Abstractの比較対象 | evaluations of evidence permutations を採用し、並べ替えた根拠に対する評価を比較すると明確にした。 |
| Abstractの共通書換え | Using a single common rewrite を採用し、回答選択と書換え生成を分離する説明へ接続した。本文3.2節と図1でも同じBを共用する条件を明示した。 |
| Abstractの日英差 | confidence interval for the difference between languages を採用し、直前の言語別結果へwhileで接続した。 |
| Abstractの26問と14・8・4問 | Among the 26 questions を用いて内訳を示した。選択回答の二値品質ラベルが対象であることを明記した。 |
| Abstractの限界 | However, the interpretation of these findings is limited by … の構造を採用し、人手確認、拒否除外、Dataset差を残した。 |
| IntroductionのRAG説明 | 外部情報源を根拠として使うこと、A RAG-based system が評価・書換えを行うことを明示した。 |
| Introductionの主比較と品質 | we propose to compare … と It is also necessary to link … を採用した。 |
| 3.1節の最初の共有試行 | The first of these evaluations is used in both … を採用し、順序比較と反復対照で共有するため最大9試行となる説明を加えた。 |
| 3.1節のシード | 実行順43、シャッフル・生成42を先生案に沿う一文で説明した。 |
| 図1の吹出し | Select A or A rewritten as B を採用した。次の行に共通Bと元順序根拠・Aの入力条件を保持した。 |
| 3.2節の書換え失敗 | If rewriting fails, the system returns A … を採用し、試行の計算費用を計上することを明記した。 |
| 3.3節の再標本化 | within each language dataset を採用した。 |
| 3.3節の品質ラベル | When an answer is a definite failure … while unresolved cases … を採用し、条件とラベルの関係を明示した。 |
| 3.3節の費用 | 各段階の呼出しが消費する入出力トークンを合計する先生案を基礎に、報告指標である呼出し回数も明記した。 |
| 4.1節の選定 | We selected questions … とし、選定方法と過去使用・選定済みグループの除外を2文にした。 |
| 4.2節のCUDA | CUDA is configured to use full offload with graphs disabled を採用した。 |
| 4.3節の診断実行 | was tested on the saved-question diagnostic を採用した。 |
| 4.4節の実使用根拠 | the evidence actually used to generate the answers を採用した。 |
| 4.4節の日本語参照本文 | The bodies of three Japanese reference articles were unavailable として本文欠測を説明した。 |
| 5.2節の日本語欠測 | For each policy, one Japanese question has no resulting answer … を採用した。 |
| 5.3節の蝶・蛾 | 名称に関する事実と、生物学的差異との因果関係を具体化した先生の一文を採用した。元の回答抜粋とF・Yは照合済み。 |
| 5.4節のトークン比 | 2.36 times as many tokens as AR と2.99 times as manyを用い、比較の構文を整えた。 |
| 5.5節の非支持観測 | sentence-by-trial observations that were not supported externally を採用した。 |
| 6.1節の頑健性 | robust to changes in evidence order とし、何に対する頑健性かを明示した。提示方法への解釈も先生案に沿って展開した。 |
| 6.2節の費用解釈 | 支持判定の計算費用が、不要な書換えの回避による節約を上回ったという先生の一文を採用した。 |
| 第7章の結び | achieves a poorer observed trade-off between answer quality and computational cost を採用し、固定構成とAIラベル・記録費用への限定を保持した。 |

### 研究上の意味に合わせた調整

共通Bの説明は、全順序で同じ書換え候補を使う実験上の統制が伝わる表現にした。費用の説明では、呼出し回数と入出力トークンをそれぞれの指標として記した。6.2節の比較候補は、先生が理解しにくいとした語句の意図を具体化した編集判断である。

先生案にあった Three Japanese reference article were … はarticlesを用いた自然な文へ整えた。times as many AR's tokens もtimes as many tokens as ARへ修正した。Human-verifiedの大文字表記は、human verificationを用いる文章へ整理した。

## 表注の説明対象

| 表 | 対応する行・列と説明 |
|---|---|
| 1 | EN/JAと、生成・評価設定のContext・Output・Batch・Task and reasoning limitsのトークン単位。 |
| 2 | Support recall・Non-support specificityの2行、Saved EN QA、元順序・逆順の統合、曖昧な期待ラベル5文の除外、非支持の区分。 |
| 3 | Mean D行のO_i−R_i、pp、同じ指標の日英差と95%区間、書換え失敗時の初回回答A。 |
| 4 | 各行100問、NR/OE/AR、Y=1/0列、Unclear列、Missing列。 |
| 5 | 初回A・成功した書換えB、既知Y、OE missed・OE harmfulの分子と対応する組数の分母。 |
| 6 | 質問数、先頭26問を区分する品質3行、同じYの内訳、Route tokens vary行の意味。 |
| 7 | F列の支持文数/全固定文数、Selected / Y列の候補と外部品質ラベル。 |
| 8 | Calls・Tokens列の対象100 EN/99 JA、初回生成、入出力トークン、同言語のARを基準とする比、不明費用の除外。 |
| 9 | External negatives列の文×試行の観測数、False support列、Rateの分母・分子。 |
| 10 | Threshold列を適用するF、EN D・JA D列の平均増分、表3と同じ比較対象、運用閾値0.7。 |

## 書式と周辺記述への影響の確認

- 公式投稿ページを再取得し、英語PDF・図表を含む4〜8ページを確認した。現行配布WordのSHA-256は保存原本と一致した。
- 英語8ページ、要旨255語、キーワード5件。公式テンプレートと用紙・余白・段組のセクションXMLが完全一致し、表幅も段幅と一致した。本文・表の文字サイズと行間を縮小していない。
- 初回描画は追加説明によって英語9ページとなった。貢献説明・関連研究・具体例の導入・考察・表注の重複を日英で縮約し、8ページに収めた。実出力の引用は保持し、保存回答の抜粋として検証した。
- 日本語版は理解用として9ページを使用する。日本語の式2が導入文から離れる問題を描画で発見し、その段落を次の式と一緒に配置する設定を加えた。
- Microsoft Wordで読取専用PDF出力し、documentsスキルのrender_docx.pyをWindows用アダプタで使用して140dpi画像化した。英語8・日本語9の全17ページを目視確認した。最終の微修正後、英語7頁と日本語2〜4頁を再確認し、他ページは確認済み画像とのHash一致を確認した。
- 図表題・表注の分離、文字切れ・重なり・文字化け、表の欠け、不要な空白ページは確認されなかった。参考文献14件のリンクを確認PDFで照合した。
- 91対訳単位の章節・条件・意味・主張の強さ・限界を確認し、要旨・結果・表注の数値の多重集合と引用順を機械照合した。
- 最終原稿関連pytestは27件成功（5.43秒）、Ruffも成功。実Wordの全表セル、具体例の逐語抜粋、元資料のHash、公式セクション、対訳表の数値、生成Manifestとの一致を既存検査で確認した。
- 研究用src/scripts/configs/tests、依存、元資料、統合集計・区間、図2には差分がない。新規研究推論・再採点・新しい区間推定は0。研究全体pytestは今回の対象外で、原稿と既存解析の検証を実施した。

## 次に取り組むべき内容

1. 教員の再確認を受け、説明・表注・結論への指摘が解消したとの確認を得る。
2. 著者名・順序・所属・責任著者メールを確定し、日英一組へ反映する。
3. 著者情報を確定した英語Wordから投稿用PDFを出力し、4〜8ページ、全ページ表示、リンクと投稿画面の条件を確認する。
