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
| [notes/draft_status.md](notes/draft_status.md) | 初稿の到達点、確認内容、研究室資料受領後の更新箇所 |
| [notes/draft7_revision_status.md](notes/draft7_revision_status.md) | PDFの指摘への対応、短い表題・表注、考察の再構成と検証 |
| [notes/draft6_revision_status.md](notes/draft6_revision_status.md) | 図表の数値網羅性・分母・単位・可読性の改善、確認と残件 |
| [notes/draft5_revision_status.md](notes/draft5_revision_status.md) | 対話を反映した全面改稿、200問の事後統合、確認と残件 |
| [notes/pooled_analysis_readme.md](notes/pooled_analysis_readme.md) | 200問の事後統合集計の定義と再現手順 |
| [notes/draft4_revision_status.md](notes/draft4_revision_status.md) | 追加120問を反映した初稿4の変更箇所、確認内容、残件 |
| [notes/extension_results_readme.md](notes/extension_results_readme.md) | 追加集合の検証・集計手順、分母と旧集合との区別 |
| [notes/draft3_revision_status.md](notes/draft3_revision_status.md) | 初稿3の品質レビュー補強対応、事後集計・原文抜粋の履歴 |
| [notes/order_effects_readme.md](notes/order_effects_readme.md) | 保存済み順序試行から品質/費用へ対応する記述集計の再現手順 |
| [notes/supervisor_readiness_review_20261106.md](notes/supervisor_readiness_review_20261106.md) | 教員に提示できる完成度かのレビュー結果と、投稿前の改善優先順位 |
| [notes/notebook_provenance_review_20261106.md](notes/notebook_provenance_review_20261106.md) | 出典補足の受領検証、執筆可能との判断、未解決事項と本文への反映 |
| [notes/notebook_materials_review_20261106.md](notes/notebook_materials_review_20261106.md) | ノートPCでの受領・検証結果、加筆可能な内容、未取得情報 |
| [notes/case_studies_and_materials.md](notes/case_studies_and_materials.md) | 具体例の使い分け、ノートPCの資料所在、研究室PCへの書出し依頼 |
| [notes/lab_pc_git_materials_prompt.md](notes/lab_pc_git_materials_prompt.md) | 研究室PCで執筆資料を作成・検証しGit共有する実行プロンプト |
| [notes/lab_pc_provenance_audit_prompt.md](notes/lab_pc_provenance_audit_prompt.md) | 未取得3点の原因・回復可能性と元ログを追加調査する依頼文 |
| [materials/provenance_audit_v1/](materials/provenance_audit_v1/README.md) | 日本語歴史版の補足回復・84採点Job・英語版候補の追加調査。未解決と証拠は[引継ぎ](notes/provenance_audit_handoff.md)参照 |
| [materials/](materials/) | 既存Main/Calの[80問資料集](materials/fixed_v23_v1/README.md)。検証・取込は[引継ぎ](notes/materials_handoff.md)を参照 |
| [materials/cal_extension_v1/](materials/cal_extension_v1/README.md) | 別途計画した追加120問の封印済み入力・採点・解析・図表・検証入口。既存Main/Calと別管理 |
| [templates/official/](templates/official/) | 配布元から取得した未編集のWordテンプレートと募集要項PDF |
| [templates/official_sources.json](templates/official_sources.json) | 取得元URL、取得日時、ファイルサイズ、SHA-256、確認方法 |
| [manuscript/](manuscript/) | Word論文本体一組。提出用 `iciae2027_manuscript_en.docx`、理解用 `iciae2027_manuscript_ja.docx` |
| [manuscript/outline.md](manuscript/outline.md) | 本文執筆前の構成案。公式の章構成指定とは区別する |
| [figures/](figures/) | 原稿掲載用に調整した図表と対応する元集計の記録 |
| [references/](references/) | 書誌・引用箇所・主張と出典の照合資料 |
| [submission/](submission/) | 確認済みの提出PDF、提出日時・受付番号等の記録 |

2026年11月11日、**PDFのマーカーを検討し、日英同内容の初稿7へ更新した**。
200問を一つの固定構成の評価実験として説明し、主比較は英語80問・日本語68問。統合集計は事後解析と明記する。
90対訳単位・7章・2図・10表・14文献、日英各8ページ、英語要旨217語。
短い表題と必要な表注を分け、不要な開発履歴・重複記述を削除した。第6章は結果の解釈、回答選択と費用への示唆、今後の検証を述べる3節へ再構成した。
[変更と検証](notes/draft7_revision_status.md)と[再現案内](notes/pooled_analysis_readme.md)を参照する。
今回の新規推論・再採点・新しい区間計算は0。初稿5の事後統合と区間を保持し、元条件・保存ラベル・元資料は変更していない。
著者情報・教員確認・提出は未実施。以下の作業分担と投稿前確認を継続する。

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
2. 更新した両初稿を読み、事後統合の扱い、具体例・分母・出典未確定を含め、主張・引用をレビューする。
3. 方法・結果・限界を両言語で並行して更新し、数値・主張・引用の対応と教員確認を行う。
4. 追加検証や訂正は両版へ反映し、既存集合との違いと対応を明記する。
5. 提出用英語PDFの4～8ページ・文字・段組・図表・引用・URLを全ページ確認し、日本語版との内容の一致も確認する。

公式情報: [投稿要領](https://www2.ia-engineers.org/iciae2027/paper-submission/)・
[投稿システムの著者要領](https://www2.ia-engineers.org/conference/index.php/iciae/iciae2027/about/submissions)。
公式掲載が変更された場合は確認日と差分を記録して更新する。
