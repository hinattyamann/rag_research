# 初稿15：厳密審査の指摘に対する修正

記録：2026-11-16 12:08 JST。対象は初稿14から初稿15への改訂。ユーザー指定の1・3・6・7・8を日英同時に反映し、2・4・5の説明追加・再判定は行っていない。番号は[審査記録](strict_review_20261116.json)のR1〜R8に対応する。

## 番号別のBefore / After

| 指摘 | Before（初稿14） | After（初稿15） |
|---|---|---|
| **1：評価器の呼出し単位** | 各文を支持・矛盾・非支持へ分類するとだけ説明し、全回答を一括評価する方式にも読めた。表1には内部名 `prompt version 12` があった。 | 3.2節に、**1評価試行につき固定した各文に1回のLLM呼出し**を行い、質問・初回回答全文・対象文・根拠を渡すと明記。対象文の全詳細に根拠が必要であり、回答自体を根拠としない基準も追加。表1の内部版名は日英とも削除し、設定値は保持した。 |
| **3：反復対照の解釈** | seed 42を使うとは記載していたが、同一seedの反復とseedを変えたばらつきの区別が弱かった。 | 3.1節で各生成呼出しのseedを42へ戻すことと、**同一入力・同一seedでの再実行対照**であることを明記。6.1節も固定seed下の根拠順序変更の結果へ限定し、異なるseed間の感度は未検証と追記した。 |
| **6：関連研究との差分** | 文献7を「固定候補に対する選択規則の研究」と紹介するだけで、本研究との違いが短かった。 | 文献7も品質・費用を比較することを認めたうえで、先行研究は**選択規則を変更**する一方、本研究は**規則と回答候補を固定して、評価器に提示する根拠順序だけを変更**すると明示。同一seedの反復対照と、採用／一回書換え・選択回答の品質・費用への影響を組み合わせた比較であると説明した。 |
| **7：参考文献** | 題名に引用符がなく著者の後もカンマ区切り。文献1に頁範囲がなく、刊行版の記載とarXivリンクが混在。文献13・14の表示URLが同じで、紙面上は区別しづらかった。 | 全14件を公式例の**著者 : “題名”, 刊行情報**へ統一。文献1に**pp. 9459–9474**を追加しNeurIPS 2020公式刊行版へリンク。13・14は **Development diagnostic report / Evaluation archive** と区別した。両者の実際のリンク先は初稿14時点で既に異なっていたため、固定先自体は維持した。 |
| **8：意味を変えない可読性改善** | 式2に `mean D`、具体例のラベルと本文の区別が弱い箇所、引用符の不統一、モデルURLの不自然な折返しがあった。 | 式2を **D̄** に変更し、A/B/Evidenceのラベルを太字化、英語の抜粋を曲線引用符へ統一。文献11のリンク表示を **Model card** に変更。具体例の引用内部は一字も削らず保持。品質結果の本文と表4注を意味・数値・分類を保って簡潔にし、既出のppの重複展開を除いた。5段落を分割して図表位置を調整した。 |

日本語版も対応する説明・表記・文献を更新した。日英の全文Before / Afterと文献の変更前後は[構造化差分](draft15_before_after_20261116.json)に記録している。

### 代表的な英語本文の変更

**1、3.2節**

- Before: “The evaluator labels each fixed answer sentence as supported, contradicted, or unsupported by the evidence.”
- After: “Each evaluation trial makes one LLM call per fixed sentence, supplying the question, full initial answer, target sentence, and evidence. Support requires evidence for every detail of the target; the answer itself is not evidence.”

**3、3.1節・6.1節**

- Before: “both shuffling and generation are set to seed 42.”
- After: “each generation call resets the seed to 42. Repetitions therefore test repeatability with the same input and seed, not variation across sampling seeds.”
- 考察への追記: “The result concerns presentation changes under a fixed sampling seed; sensitivity across different seeds remains untested.”

**6、関連研究**

- Before: “Evidence-locked selection studies rules over fixed candidates[[7]]. We examine how reordering evidence changes decisions between fixed answers and affects their quality and cost.”
- After: “Zhang et al. compare selection rules over frozen candidates, including quality and cost[[7]]. Their intervention changes the selection rule. We instead keep the rule and answer candidates fixed, vary only the evidence order presented to the evaluator, and compare against same-seed repetitions.”

**8、品質結果の簡潔化**

- Before: “For each policy, one Japanese question has no resulting answer because of an initial-answer generation failure.”
- After: “One Japanese question has no answer under any policy because initial generation failed.”
- 英語51/31/63、日本語41/21/55、全200問、初回生成失敗1問、判定不能と不良の区別をすべて保持した。表4注もNR/OE/ARとY=1/Y=0/Unclear/Missingの定義を保持した。

## 保持した内容と修正の範囲

- **2**：人手による品質ラベル確定や具体例の再判定は行わず、元のAIラベル・解釈を保持した。
- **4**：統合標本・収集手順差の追加説明は行っていない。4.4節の段落は配置のために分割しただけで、文章は変更していない。
- **5**：費用経路の再構成説明・新しい費用内訳・NR行は追加していない。表8の数値・注記も保持した。
- 研究目的・実験条件・閾値・資料・ラベル・統合集計・信頼区間・図資産に変更はない。新規推論・再採点・区間計算は0件。要旨・著者・所属も初稿14と同一。
- 文献7は[著者プレプリントv2](https://arxiv.org/html/2608.07813v2)を再照合。文献1の頁範囲は[公式BibTeX](https://proceedings.neurips.cc/paper_files/paper/2020/file/6b493230205f780e1bc26945df7481e5-Bibtex.bib)に基づく。頁範囲のないモデル／データカードやプレプリントへ架空の頁を付していない。

## 最終確認と成果物

- [英語Word](../manuscript/iciae2027_manuscript_en.docx)・[英語PDF](../manuscript/iciae2027_manuscript_en.pdf)：**8ページ**。
- [理解用日本語Word](../manuscript/iciae2027_manuscript_ja.docx)・[日本語PDF](../manuscript/iciae2027_manuscript_ja.pdf)：**9ページ**。
- ネイティブWordから日英PDFを再出力し、全17ページを画像で確認した。全97本文単位・全表注・全14文献のPDF収録、全14文献リンク、フォント埋込みを検査済み。
- 英語全12図表はキャプション・注とともに段頭9件／段末3件。`check_pdf_layout.py`に合格。段落分割は5件で、本文の論理順序と図表番号を保持した。
- 現行公式テンプレートを再取得し、保存原本とSHA-256が一致。英語WordのA4・余白・段組・書体・文字サイズ・著者欄・引用書式、実際のPDFの要旨／Keywords／図表／文献を再照合した。要旨は初稿14から不変（既確認のWord標準230語、空白区切り228語）、Keywordsは5個。
- 原稿テスト29件・Ruffは通過。検証対象のWord/PDFと全ページ画像のHash、公式URL、配置検査結果は[最終検証](draft15_validation_20261116.json)に保存した。
- **公開要項への書式適合は再確認済み。教員の投稿承認、ログイン後の追加条件照合、投稿は未実施。** 今回保留した2・4・5の審査指摘を解消済みとは扱わない。

次の作業は、著者による変更内容の確認と教員の最終確認・投稿承認。その後、投稿画面の追加条件を照合し、確認済み英語PDFを提出対象として確定する。
