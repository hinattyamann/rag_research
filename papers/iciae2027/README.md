# ICIAE 2027 論文執筆

本研究のICIAE 2027向け原稿、投稿条件、図表、引用文献、提出版を管理する専用フォルダ。
2026年11月4日に公式サイト・公式Wordテンプレート・募集要項を確認した。
執筆形式はユーザー指定の **Microsoft Word** とする。
**提出用の英語版と理解用の日本語版を、初回作成から必ず同時に並行して執筆・更新する。**
章・節ごとに両版をそろえ、数値・実験条件・図表番号・引用・主張の強さ・限界の対応を確認する。

目標は **2026年11月20日の初回フルペーパーPDF提出**。
採否通知は2026年12月11日、採択後の最終原稿提出は2027年1月8日である。
初回締切の時刻・タイムゾーンは確認した公式資料に記載されていない。

## 保存先

| 保存先 | 内容・正本 |
|---|---|
| [notes/submission_requirements.md](notes/submission_requirements.md) | 公式投稿条件、書式、未確認事項、提出前チェック |
| [notes/case_studies_and_materials.md](notes/case_studies_and_materials.md) | 具体例の使い分け、ノートPCの資料所在、研究室PCへの書出し依頼 |
| [templates/official/](templates/official/) | 配布元から取得した未編集のWordテンプレートと募集要項PDF |
| [templates/official_sources.json](templates/official_sources.json) | 取得元URL、取得日時、ファイルサイズ、SHA-256、確認方法 |
| [manuscript/](manuscript/) | Word論文本体一組。提出用 `iciae2027_manuscript_en.docx`、理解用 `iciae2027_manuscript_ja.docx` |
| [manuscript/outline.md](manuscript/outline.md) | 本文執筆前の構成案。公式の章構成指定とは区別する |
| [figures/](figures/) | 原稿掲載用に調整した図表と対応する元集計の記録 |
| [references/](references/) | 書誌・引用箇所・主張と出典の照合資料 |
| [submission/](submission/) | 確認済みの提出PDF、提出日時・受付番号等の記録 |

現時点では保存先と構成案を準備した段階で、**論文本体のDOCX・提出PDFは未作成**。
公式テンプレートの例文を研究本文として扱わない。
テンプレート原本を保存したまま、次の執筆工程で英語版・日本語版の本文DOCXを同時に作成する。
日本語版は英語版と同じ内容の忠実な翻訳とし、独自の補足・省略・別の説明を加えない。
ユーザーへの詳しい解説は会話や執筆メモで行い、両言語の論文本体から分ける。
公式の英語・4～8ページ等の提出条件は英語版に適用し、日本語版のページ数・体裁は理解しやすさに合わせる。

## 執筆に使う研究成果

研究工程の正本は引き続き [研究ロードマップ](../../docs/research_roadmap.md)。
実験条件は [研究計画](../../docs/rag_research_plan.md)・[実装計画](../../docs/rag_implementation_plan.md)を参照する。

- 解析・図表の正本: [固定v23の成果](../../reports/fixed_v23_order_study_v1/)
- [結果説明資料](../../reports/fixed_v23_order_study_v1/results_brief.md)
- [執筆前工程の完了確認](../../data/manifests/fixed_v23_prewriting_completion_v1.json)

既存のMain/Calは集合別に記述し、比較欠測、AI採点、人手未確認、停止規則・採点入力方式の事後変更、
外的中断の費用不明を本文へ残す。旧Gate11未通過・Phase12未実施を変更しない。
追加検証は別Protocol・別成果として管理し、採点封印と解析が完了した結果だけを原稿へ取り込む。
今回、追加実験を開始したり、その件数・対象・条件を確定したりしていない。

## ノートPCと研究室PCの分担

執筆は `paper/iciae2027` Branch、追加検証は別Branchと固定Commitの専用Checkout/Worktreeで進める。
研究室PCの実行中CheckoutをPullで変更しない。
ノートPCでは研究用の収集・採点を二重起動しない。

確認済みの変更をCommit・通常Pushし、受け取る側ではFetchして履歴と差分を確認する。
図表は生成元Commit・解析Manifest・元ファイルのHashが分かる形で取り込む。
Raw・モデル・環境はGitでは転送されない。
DOCXは差分統合が難しいため、同じ原稿ファイルを両PCで同時編集しない。

## 次に行うこと

1. タイトル、著者順、全所属の英語表記、責任著者とメールアドレスを確定する。
2. 構成案と図表の選択を確認し、提出用英語版・理解用日本語版の本文DOCXを同時に作成する。
3. 方法・現在の結果・限界を両言語で並行して執筆し、数値・主張・引用の対応と教員確認を行う。
4. 追加検証や訂正は両版へ反映し、既存集合との違いと対応を明記する。
5. 提出用英語PDFの4～8ページ・文字・段組・図表・引用・URLを全ページ確認し、日本語版との内容の一致も確認する。

公式情報: [投稿要領](https://www2.ia-engineers.org/iciae2027/paper-submission/)・
[投稿システムの著者要領](https://www2.ia-engineers.org/conference/index.php/iciae/iciae2027/about/submissions)。
公式掲載が変更された場合は確認日と差分を記録して更新する。
