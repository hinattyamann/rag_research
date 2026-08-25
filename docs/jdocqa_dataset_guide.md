# JDocQAデータセット理解・Text-only RAG利用仕様書

## Version 1.0

最終確認日: 2026-08-25

本書は、JDocQAそのものの仕様と、本研究「評価駆動型自己制御RAGによる回答信頼性向上手法」
での利用方法を一か所に集約したDataset仕様書である。JDocQAについて疑問が生じた場合は、
まず本書を参照する。

本書では、情報の性質を次の4種類に分ける。

- **公式情報**: 論文、公式Repository、公式Annotation説明に明記された内容。
- **実データ監査結果**: 2026-08-25に特定RevisionのAnnotationを再集計した結果。
- **研究上の決定**: 本研究の目的に合わせて採用する運用。
- **未確定**: PilotまたはValidation Splitで検証後に固定する値。

研究方針や実装を変更した場合は、本書、`rag_research_plan.md`、
`rag_implementation_plan.md`、実装、Test、Dataset Manifestを同時に更新する。

---

# 1. 最初に確認する結論

## 1.1 JDocQAは本研究に利用できるか

JDocQAは、そのままではMultimodal Document QA用Datasetであり、図、表、地図、Layoutなどの
視覚情報を必要とする質問も含む。しかし、日本語の公共文書PDF、4種類の質問形式、
Unanswerable質問、複数Page質問を備えているため、**Text-onlyで回答可能な例を明示的に選別し、
PDF全文から検索Corpusを再構築する**なら、本研究に適している。

JDocQAをそのまま質問回答Datasetとして使うのではなく、次の2段階で利用する。

1. JDocQAから「文章だけで回答可能なQA」を選別する。
2. 対象Split内の全PDF・全PageからText-only検索Corpusを構築し、検索を実際に行う。

## 1.2 本研究で使うもの・使わないもの

| 対象 | 方針 |
|---|---|
| 日本語の質問と正解 | Dataset監査と評価に使用する |
| PDF埋め込みText | Page単位Corpusの第一候補として使用する |
| OCR Text | 埋め込みTextが取得不能または品質不足のPageで使用する |
| PDF Page画像 | Text抽出と人手監査にのみ使用し、RAGへ入力しない |
| 表、Graph、地図、図の視覚情報 | 主実験では使用しない |
| Bounding Box、Layout座標 | RAGへ入力しない |
| `context` | 適格性監査と抽出品質確認にのみ使用し、RAGへ直接入力しない |
| 正解Page、正解Bounding Box | 評価にのみ使用し、検索・生成・Query Rewriteへ渡さない |

## 1.3 現時点で確定している評価Dataset

| 種類 | 件数方針 | 用途 |
|---|---:|---|
| Normal QA | 初期目標150件 | 通常条件の性能評価 |
| Unanswerable QA | Test Split内のText-only適格例を全件 | 回答拒否とHallucinationの評価 |
| Retrieval Failure | 初期目標150件 | Query Rewriteによる検索Recovery評価 |
| Distractor | 初期目標150件 | 類似する誤根拠への耐性評価 |

Unanswerable QAだけは150件へ水増しも切り詰めも行わない。公式Test Annotationには選別前で
145件あり、最終件数はText-only適格性監査後に145件以下となる。

---

# 2. JDocQAの概要

## 2.1 基本情報

JDocQA（Japanese Document Question Answering）は、Onami et al.がLREC-COLING 2024で
発表した日本語Document QA Datasetである。

| 項目 | 内容 |
|---|---|
| PDF文書数 | 5,504件 |
| QA数 | 11,600件 |
| 言語 | 日本語 |
| 文書形式 | Report、Pamphlet、Slide、Website |
| 主な出典 | 国立国会図書館Digital Collection、WARP、政府機関などの公開資料 |
| 質問形式 | Yes/No、Factoid、Numerical、Open-ended |
| 特徴 | 視覚・Text情報、複数Page、Unanswerable、正解手掛かりPageとBounding Box |

対象文書には、経済、教育、労働、保健衛生、農林水産、文化・芸術、歴史、行政施策、
地域生活など、公共部門に関係する幅広いTopicが含まれる。

JDocQAの本来の目的は、Text理解だけでなく図表理解も含むDocument QAの評価である。
したがって、「JDocQAにText Fieldがある」ことと「全質問がText-onlyで回答可能である」ことは
同義ではない。

## 2.2 論文記載の全体内訳

| 質問形式 | 論文記載件数 |
|---|---:|
| Yes/No | 1,855 |
| Factoid | 2,052 |
| Numerical | 1,866 |
| Open-ended | 5,827 |
| 合計 | 11,600 |

論文Table 1では、Multi-pageは1,000件、Unanswerableは1,788件と報告されている。

## 2.3 論文と現行Annotationの差異

固定RevisionのAnnotationを再集計すると、次の差異がある。

| 項目 | 論文 | 現行Annotation | 差 |
|---|---:|---:|---:|
| Yes/No | 1,855 | 1,856 | +1 |
| Factoid | 2,052 | 2,051 | -1 |
| Numerical | 1,866 | 1,866 | 0 |
| Open-ended | 5,827 | 5,827 | 0 |
| Multi-page | 1,000 | 1,000 | 0 |
| Unanswerable | 1,788 | 1,791 | +3 |

これは集計ミスとして独自修正せず、次のように扱う。

- Datasetの説明では、論文値と現行Annotation値を区別して併記する。
- 実験対象の判定には、固定RevisionのAnnotation値を使用する。
- 論文結果との比較では、Revision差があることをLimitationsへ記載する。
- Dataset RevisionとHashをManifestへ必ず保存する。

---

# 3. 配布物、取得方法、License

## 3.1 一次資料

- 論文: <https://aclanthology.org/2024.lrec-main.830/>
- 公式Repository: <https://github.com/mizuumi/JDocQA>
- 公式Dataset説明: <https://github.com/mizuumi/JDocQA/tree/main/dataset>
- Hugging Face Dataset: <https://huggingface.co/datasets/shunk031/JDocQA>
- 非公式だが公開されているHugging Face Loader:
  <https://github.com/shunk031/huggingface-datasets_JDocQA>

論文と公式Repositoryを一次資料とする。Hugging Face Loaderは取得を簡便にする補助実装であり、
元Annotationの意味を決める一次資料ではない。

## 3.2 Annotation File

公式Repositoryには次の3 Fileがある。

```text
dataset/annotation_files/jdocqa_train_all.json
dataset/annotation_files/jdocqa_validation_all.json
dataset/annotation_files/jdocqa_test_all.json
```

拡張子は`.json`だが、実体は**1行に1 JSON Objectを置くJSON Lines形式**である。
File全体を1つのJSON配列として読み込んではならない。

## 3.3 PDFの取得

公式Dataset説明では、Annotation対象PDFのDownloadにGoogle Formへの入力が必要とされている。
Hugging Face Loaderは別のDownload URLを参照しているが、利用可能性は将来変わり得る。

本研究では次の手順を採用する。

1. 公式の案内に従ってPDFを取得する。
2. 取得元、取得日、File数、File HashをManifestへ記録する。
3. `data/raw/jdocqa/`へ保存し、Git管理対象外とする。
4. 5,504件が揃っているか、Annotationの`pdf_name`と対応するか検証する。
5. 欠損PDFがある状態で実験を続ける場合は、欠損IDを明記して別Dataset Revisionとする。

## 3.4 License

JDocQAのAnnotationはCC BY-SA 4.0で配布されている。派生Dataset、論文、公開物では
JDocQA論文を引用し、公式RepositoryへのLinkを記載する。元PDFには各配布元の利用条件が
別途適用されるため、AnnotationのLicenseだけを根拠に元PDFを再配布してはならない。

GitHubへ原本PDF、抽出全文、大容量IndexをCommitしない。Git管理するものは、原則として
取得・変換Script、設定、Hash、ID、選別Label、除外理由、再生成手順とする。

## 3.5 本書で監査したRevision

2026-08-25時点で次を固定して再集計した。

```text
JDocQA official repository:
e65c6c7d4a3ac869b48641eb94ed1f8b0ddf886a

Hugging Face loader repository:
210c48e6385047a082ab8a5f85a2edc17a3700c9
```

Annotation Fileの監査値:

| Split | Byte数 | SHA-256 |
|---|---:|---|
| Train | 92,600,960 | `d64681aeca1d1266c551f273485821f9703c25f500eacc5f08b892ef5fcaa4ad` |
| Validation | 11,124,183 | `edf13c440f199ad37d6a35fe756b14feff8c4268828d7ecf5e3e50444dc055cb` |
| Test | 12,447,975 | `58ebfe539f8272c563617e51e40043dea43ebaf48f224c58113a84234dd93604` |

実装時は可変の`main`ではなく、Commit SHAを含むURLまたはDataset Revisionを使用する。

---

# 4. Split構成と利用ルール

## 4.1 公式Split

| Split | QA数 | 異なるPDF数 | 本研究での用途 |
|---|---:|---:|---|
| Train | 9,290 | 4,403 | 実装、Prompt開発、選別基準Pilot |
| Validation | 1,134 | 550 | 閾値、重み、検索・Chunk Parameter調整 |
| Test | 1,176 | 551 | 設計固定後の最終評価 |
| 合計 | 11,600 | 5,504 | － |

監査したRevisionでは、`pdf_name`のTrain/Validation/Test間重複は0件だった。

現行AnnotationのAnswer Type内訳:

| Split | Yes/No | Factoid | Numerical | Open-ended | 合計 |
|---|---:|---:|---:|---:|---:|
| Train | 1,497 | 1,645 | 1,507 | 4,641 | 9,290 |
| Validation | 190 | 191 | 188 | 565 | 1,134 |
| Test | 169 | 215 | 171 | 621 | 1,176 |
| 合計 | 1,856 | 2,051 | 1,866 | 5,827 | 11,600 |

現行AnnotationのPDF Category別QA内訳:

| Raw Category | Train | Validation | Test | 合計 |
|---|---:|---:|---:|---:|
| `Document` | 3,339 | 437 | 391 | 4,167 |
| `Kouhou` | 3,246 | 371 | 408 | 4,025 |
| `Slide` | 2,705 | 326 | 245 | 3,276 |
| `Website` | 0 | 0 | 132 | 132 |

## 4.2 Data Leakage防止

- Test結果を見てPrompt、閾値、Confidence重み、Chunk長、`top_k`を調整しない。
- Text-only選別基準はTrainで作り、Validationで修正し、Test適用前に固定する。
- Testでは適格性判定だけを行い、Modelの正誤を見て採用・除外しない。
- 同一PDFがSplitをまたいでいないことをLoader Testで毎回確認する。
- Index、BM25 Corpus、Embedding StoreもSplitごとに分離する。
- Testの質問をTrain/Validation用Prompt例へ転用しない。

## 4.3 PDF Categoryに関する注意

Raw値と論文表記には次の対応がある。

| Raw Annotation | 論文・読みやすい表記 |
|---|---|
| `Document` | Report |
| `Kouhou` | Pamphlet |
| `Slide` | Slide |
| `Website` | Website |

現行Annotationでは、4つの`pdf_name`についてQA Record間で`Document`と`Slide`が
一致していなかった。そのため、Category別の異なるPDF数を単純合計すると5,508件となる一方、
重複を除いた全PDF数は5,504件となる。`pdf_category`をPDF単位の絶対的な正解Labelとせず、
Raw Record値を保存し、矛盾時は`category_conflict=true`を記録する。

---

# 5. Raw Field完全辞書

公式Annotationには19 Fieldがある。Hugging Face Loaderはさらに`pdf_filepath`を追加する。

| Field | 意味 | 本研究での扱い |
|---|---|---|
| `pdf_category` | 文書Category | 層別集計用。Retriever入力には不要 |
| `pdf_name` | 元PDF File名 | 文書対応とStable ID作成に使用 |
| `question_page_number` | Annotation時に質問と対応付けられたPage | 評価・監査専用。検索範囲の限定に使わない |
| `question_number` | Annotation内部の質問番号 | Source Keyの一部。ただし単独ではUniqueでない |
| `reason_of_answer_bbox` | 答えの手掛かりを指すBounding Box ID列 | 評価・監査専用。座標そのものとは限らない |
| `answer_type` | `1` Yes/No、`2` Factoid、`3` Numerical、`4` Open-ended | 内部Enumへ変換する |
| `type_of_image` | Page上の視覚要素種別 | Text-only候補のPrefilterにのみ使用 |
| `original_context` | PDFから抽出したText | 監査用。質問単位であるためCorpusに直結しない |
| `context` | 公式説明上は`original_context`からNoise除去したText | 監査用。RAGへ直接渡さない |
| `original_question` | Annotatorが作成した元質問 | 意味確認とAudit用 |
| `question` | Model用指示を付加した質問 | 原Dataset再現用。本研究では質問本文と回答形式指示を分離する |
| `original_answer` | Annotatorが作成した元回答 | Audit用 |
| `answer` | Model評価用に加工された回答 | Reference候補として保存 |
| `normalized_answer` | さらに正規化された回答 | 型を安全にParseし、Reference候補列として使用 |
| `no_reason` | Answerability/Multi-page Flag | 後述の規則でBooleanへ分解する |
| `multiple_select_question` | 4択形式へ変換した質問 | 本研究の生成QAでは使用しない |
| `multiple_select_answer` | 4択の正解A/B/C/D | 本研究の生成QAでは使用しない |
| `text_from_pdf` | 対応Pageから得たPDF埋め込みText | 抽出品質監査用。全文Corpusでは再抽出する |
| `text_from_ocr_pdf` | 対応Page画像から得たOCR Text | 抽出品質監査用。全文Corpusでは再抽出する |
| `pdf_filepath` | HF Loaderが追加するLocal PDF Path | 実行環境依存なのでManifestへ固定値保存しない |

## 5.1 `answer_type`

```text
1 -> yes_no
2 -> factoid
3 -> numerical
4 -> open_ended
```

質問形式はText-only適格性を保証しない。例えばNumericalでも、数値が本文に書かれていれば
対象となり、Graphや表から読み取る必要があれば対象外となる。

## 5.2 `no_reason`

公式説明は次のとおりである。

```text
0   -> Unanswerable
1   -> Answerable
2   -> Multi-page
1,2 -> AnswerableとMulti-pageの複合Flag
```

内部では文字列全体を1つのClassとして扱わず、少なくとも次へ分ける。

```text
is_unanswerable = no_reason == "0"
is_answerable   = no_reason != "0"
is_multi_page   = "2" in no_reason.split(",")
```

`2`単独も本研究ではAnswerableなMulti-page例として扱う。ただしRaw値を必ず残し、将来の
解釈変更に対応できるようにする。

現行AnnotationのSplit別内訳:

| Split | `0` | `1` | `2` | `1,2` |
|---|---:|---:|---:|---:|
| Train | 1,450 | 7,025 | 689 | 126 |
| Validation | 196 | 845 | 82 | 11 |
| Test | 145 | 939 | 77 | 15 |

## 5.3 `type_of_image`

| Raw値 | 意味 | 現行AnnotationのRecord数 |
|---|---|---:|
| 空文字 | null/未記録 | 1,276 |
| `1` | Table | 2,989 |
| `2` | Bar chart | 838 |
| `3` | Line chart | 284 |
| `4` | Pie chart | 421 |
| `5` | Map | 288 |
| `6` | Other figures | 1,710 |
| `7` | 縦書き・横書き混在 | 74 |
| `8` | Drawings | 366 |
| `9` | Others | 3,350 |
| 複合値 | `2,3`、`1,4`、`2,4` | 4 |

複数種別は`2,3`のようにComma区切りとなる。公式説明でもLabel欠損があると明記されている。
そのため、空文字を「視覚情報なし」と断定してはならず、非空を「視覚推論必須」と断定しても
ならない。本文の横に表があるだけで、質問の答え自体は本文にある場合があるためである。

## 5.4 質問Field

`original_question`は元の質問である。`question`には、質問形式に応じて「はい/いいえで答える」
「数量のみ」「自由記述」などの回答形式指示が追加されている。現行Annotationでは11,600件すべてで
両者が異なる。

本研究では次のように分離する。

- `question_text`: `original_question`を基本とする意味内容。
- `answer_instruction`: 期待する回答形式。
- `model_question`: 実験時に両者をTemplateで組み立てた入力。

これにより、質問内容とFormatting指示を混同せず、3方式で同一Templateを使える。

## 5.5 回答Fieldと正規化上の注意

`original_answer`、`answer`、`normalized_answer`は同じ意味の異なる加工段階である。
`normalized_answer`は常に単純なScalar文字列ではない。FactoidとNumericalを中心に、
例えば`['1', '950円']`のような**Python List表現に見える文字列**が含まれる。

現行Annotationで`normalized_answer`が`[`から始まるRecord数:

| Split | 件数 |
|---|---:|
| Train | 2,790 |
| Validation | 333 |
| Test | 350 |

実装時の規則:

1. Raw文字列を`normalized_answer_raw`へ保存する。
2. List形式候補だけを`ast.literal_eval`など安全な方法でParseする。
3. Pythonの`eval`は絶対に使用しない。
4. Parse結果が文字列ListでなければValidation Errorにする。
5. Scalarの場合も含め、内部では`reference_answers: list[str]`へ統一する。
6. `original_answer`と`answer`も失わず、監査可能にする。

Unanswerableの`answer`は、監査した全Splitで全件`本文中に記載がありません`だった。

## 5.6 Unique ID

`question_number`は単独でも`pdf_name`との組合せでも完全なUnique Keyではない。実際にTrainで
`pdf_name + question_number`の重複が3件あった。

固定Revision内のStable IDは次の形式とする。

```text
jdocqa:{revision_short}:{split}:{zero_based_line_index:05d}
```

加えて`pdf_name`、`question_number_raw`、Raw RecordのSHA-256を保存する。Revisionが変わったら
同じLine番号を同一Recordと仮定せず、Record Hashと内容を照合する。

---

# 6. 4つのText Fieldをどう理解するか

JDocQAには`original_context`、`context`、`text_from_pdf`、`text_from_ocr_pdf`がある。
これらは4つの独立した根拠文書ではない。

```text
質問に対応付けられたPDF Page
├─ PDF埋め込みText抽出 ───────────────> text_from_pdf
├─ Page画像へのOCR ──────────────────> text_from_ocr_pdf
└─ Annotation側で選んだContext
   ├─ 抽出時点のText ─────────────────> original_context
   └─ 公式説明上のNoise除去後Text ────> context
```

## 6.1 `context`は正解に関係するか

Answerable QAでは、質問と対応付けられたPageの内容であり、通常は答えの手掛かりに関係する。
しかし、これはPDF全文ではなく、質問作成時に対応付けられた質問単位のContextである。

Unanswerable QAでは、文書中に正解根拠が存在しないため、`context`に文章があっても答えの根拠では
ない。TestのUnanswerable 145件中144件には非空の`context`がある。したがって、
「Contextが存在する = Answerable」ではない。

## 6.2 現行Annotationの実測結果

| Split | QA数 | `context`非空 | `text_from_pdf`非空 | `text_from_ocr_pdf`非空 | PDF/OCR両方空 |
|---|---:|---:|---:|---:|---:|
| Train | 9,290 | 9,142 | 2,606 | 9,214 | 76 |
| Validation | 1,134 | 1,125 | 358 | 1,130 | 4 |
| Test | 1,176 | 1,159 | 310 | 1,165 | 11 |
| 合計 | 11,600 | 11,426 | 3,274 | 11,509 | 91 |

さらに、固定Revisionでは次を確認した。

- `context == original_context`: 11,600件すべて。
- 非空の`context == text_from_pdf`: 3,270件。
- 非空の`context == text_from_ocr_pdf`: 8,156件。
- PDF TextとOCR Textが両方非空で完全一致: 0件。

公式説明では`context`は`original_context`からNoiseを除いたものだが、現行Fileでは全件完全一致する。
また、PDF TextとOCR Textの不一致は、空白、改行、文字認識差を含むため、直ちにどちらかが誤りとは
断定しない。

Test Unanswerable 145件のText状況:

| 条件 | 件数 |
|---|---:|
| `context`非空 | 144 |
| `text_from_pdf`非空 | 39 |
| `text_from_ocr_pdf`非空 | 144 |
| PDF TextとOCR Textが両方空 | 1 |

## 6.3 なぜ`context`をRAGへ直接渡してはいけないか

`context`は質問ごとに対応付けられたPage由来である。これをGeneratorへ直接渡すと、Retrieverが
全文書から根拠を探す工程を飛ばし、検索性能やRetrieval Failureを正しく評価できない。

本研究で禁止する処理:

```text
question + JDocQA context -> Generator
```

本研究で行う処理:

```text
対象Splitの全PDF・全Page
-> Text抽出/OCR Fallback
-> Chunk化・Index化
-> questionで検索
-> 取得ChunkだけをGeneratorへ渡す
```

`context`は、Corpus Textが正しく抽出できたか、質問が文章だけで回答可能かを確認するための
Audit用Referenceとして利用する。

## 6.4 `question_page_number`の注意

公式説明では「Annotatorが質問の答えを見つけたPage」とされるが、Unanswerableにも全件値があり、
Test Unanswerableの一部にはBounding Box IDもある。Unanswerableでは答えのPageではなく、
質問作成時に対応付けられたPageと解釈するのが安全である。

Page番号の区切りやPDF内部Indexとの対応を決め打ちせず、実装時に実PDFを表示して1-origin/0-origin、
印刷Page番号、PDF Page Indexの関係を検証する。検証完了まではRaw文字列を保持する。

---

# 7. 本研究におけるText-onlyの定義

## 7.1 主実験の対象

本研究のText-only適格例とは、**RAGにPDF画像、表構造、Graph、地図、色、位置、形状、
Bounding Box、Layout座標を与えず、通常の文章として抽出されたTextだけから回答または回答拒否を
判断できる例**である。

ここで「文章」には本文、見出し、Caption、箇条書きを含めてよい。ただし、次は除外する。

- 表の行と列の交点を読む必要がある。
- Bar/Line/Pie chartの値や傾向を読む必要がある。
- 地図上の位置関係を読む必要がある。
- 色、形、大きさ、矢印、配置を解釈する必要がある。
- OCRで文字列化されても、元の2次元Layoutなしでは意味を復元できない。
- 答えの手掛かりが画像内にしかなく、文章として独立して記載されていない。

## 7.2 含める例

- 本文の一文にFactが明記されているFactoid。
- 本文中に日付・人数・金額が文章として書かれているNumerical。
- 複数Pageの本文を組み合わせれば答えられるOpen-ended。
- Pageに表が存在していても、答えの根拠は表外の本文に完結している質問。
- 図のCaptionだけで回答でき、図の形状や値を読む必要がない質問。
- 箇条書きの順番を通常の読み順でText化すれば答えられる質問。

## 7.3 除外する例

- 「表の3列目で最も大きい値」のような表構造依存。
- 「赤い線が示す年度」のような色・Graph依存。
- 「右側の図」「矢印の先」のような位置依存。
- OCR結果に単語は含まれるが、行列関係を失うと答えが変わる質問。
- 正解根拠の本文が抽出失敗し、画像を見なければ復元できない質問。
- 質問そのものが「この図」「次の表」など、視覚対象なしでは指示対象を特定できない質問。

## 7.4 判断が分かれやすい例

| 状況 | 判定 |
|---|---|
| Pageに表があるが、同じ値が本文にも明記される | 本文根拠を特定できれば採用 |
| OCRで表がきれいに1行化される | 主実験では原則除外。表構造利用になるため |
| 箇条書き | 読み順が一意でLayout推論不要なら採用 |
| Caption | Caption単独で根拠が完結すれば採用 |
| 複数Page | 全根拠が文章なら採用 |
| 数値計算 | 必要な数値と条件が文章にあれば採用 |
| Pageに画像Labelがない | 自動採用しない。Label欠損があるため内容を確認 |
| Pageに画像Labelがある | 自動除外しない。答えが本文にある場合があるため |

---

# 8. Text-only適格性の選別手順

## 8.1 基準を固定する順序

1. TrainからAnswer Type、Category、`type_of_image`を分散させたPilot標本を抽出する。
2. 2名または主担当＋再確認担当で独立判定し、不一致理由を収集する。
3. 判定Ruleと除外理由Enumを修正する。
4. Validationへ適用し、曖昧例を解消する。
5. Testを見る前にRule Versionを固定する。
6. TestではModel性能を見ず、固定Ruleだけで判定する。
7. 採用・除外を全件Manifestへ保存する。

## 8.2 自動Prefilter

自動判定だけで最終確定しない。人手確認対象を絞るため、次をFlag化する。

- `context`、PDF Text、OCR Textのすべてが空。
- `type_of_image`にTable/Chart/Mapが含まれる。
- 質問に「表」「図」「Graph」「地図」「色」「線」「右」「左」「上」「下」などが現れる。
- OCR品質が基準未満。
- `question_page_number`が複数Pageを示す。
- `reason_of_answer_bbox`が存在する。
- Gold Answerが抽出文章に見つからない。

最後の条件は除外条件ではなく、表記揺れ、要約回答、推論、抽出失敗を人が確認するためのFlagである。

## 8.3 人手判定Question

Answerable QAでは次を順に確認する。

1. 質問は画像なしでも意味が一意か。
2. 必要な根拠は通常の文章に存在するか。
3. 表・図・Layoutを使わず答えを導けるか。
4. その文章は本研究のCorpus抽出Pipelineで十分に取得できるか。
5. 正解と文章根拠に矛盾がないか。

Unanswerable QAでは次を確認する。

1. 質問は画像なしでも意味が一意か。
2. 文書のText抽出が十分で、「抽出失敗」を「答えなし」と誤認する条件ではないか。
3. 視覚情報を見れば答えられるのに、Text-onlyだから答えられない例ではないか。
4. 正しい期待動作が、根拠のない回答生成ではなく回答拒否であるか。

## 8.4 判定Label

```text
eligibility:
  eligible
  ineligible
  needs_adjudication

exclusion_reason:
  null
  no_usable_text
  ocr_corrupted
  table_structure_required
  chart_reasoning_required
  map_spatial_reasoning_required
  visual_attribute_required
  layout_required
  image_only_evidence
  deictic_question_without_visual
  answer_label_inconsistent
  source_pdf_missing
  ambiguous_other
```

複数理由がある場合は`exclusion_reasons: list[str]`へすべて保存し、最初の理由だけを残さない。

## 8.5 判定Manifest例

```json
{
  "record_id": "jdocqa:e65c6c7:test:00000",
  "rule_version": "text_only_v1",
  "eligibility": "eligible",
  "exclusion_reasons": [],
  "evidence_mode": "prose",
  "text_sources_checked": ["embedded", "ocr"],
  "question_is_self_contained": true,
  "layout_required": false,
  "extraction_quality": "pass",
  "reviewer_1": "reviewer_id",
  "reviewer_2": null,
  "adjudication_note": "本文の記述だけで回答可能",
  "reviewed_at": "YYYY-MM-DD"
}
```

個人名を公開Manifestへ出さない場合は、研究内の匿名Reviewer IDを使用する。

## 8.6 判定品質

- Pilotの少なくとも一部は2名で独立判定する。
- 一致率とCohen's kappaなどを記録する。
- 不一致が多い理由はRuleを具体化してから全件判定する。
- Testの境界例は単独判断で無理に採用せず、`needs_adjudication`として再確認する。
- 最終評価Manifestには未決着例を含めない。

---

# 9. 検索Corpusの作り方

## 9.1 最重要原則

質問に対応する`context`や`question_page_number`だけでCorpusを作らない。対象Splitに属する
**全PDFの全Page**を検索候補にする。Gold情報はCorpus構築から分離する。

## 9.2 Page単位Text抽出

各Pageに対して次を行う。

1. PDF埋め込みTextを抽出する。
2. Text品質を計測する。
3. 品質が十分なら`embedded`を採用する。
4. 空または品質不足ならPage画像へOCRを実行する。
5. OCR品質も不足ならPageを`unusable`として記録する。
6. 採用Textを正規化するが、Raw抽出結果も再現用に保持する。

初期品質Check候補は次のとおりで、Validationで固定する。

- 非空白文字数。
- Unicode置換文字や制御文字の割合。
- 日本語文字、英数字、一般記号以外の異常文字率。
- 同一文字やHeader/Footerの過剰反復。
- JDocQA提供Textとの文字類似度。
- 人手Sampleでの可読性。

単一の文字数閾値だけで判定しない。短いが有効なPageを誤除外するためである。

## 9.3 Text正規化

意味を変えない範囲で次を行う。

- Unicode正規化方式を固定する。
- 改行、連続空白、Soft Hyphenなどを規則化する。
- Page Header/Footerの反復除去はRuleと検出結果を保存する。
- 数字、単位、記号を不用意に削除しない。
- OCR誤りをGold Answerに合わせて手作業修正しない。

Gold Answerを見てCorpus Textを直すとData Leakageになる。修正する場合は、質問非依存の一般Ruleとして
Train/Validationで決め、全Pageに同じRuleを適用する。

## 9.4 Chunk分割

初期候補は次のとおりとし、Validationで変更可能とする。

```text
chunk_size_chars: 800
chunk_overlap_chars: 120
cross_page_chunk: false
sentence_boundary_preferred: true
```

Page境界を越えてChunk化しないことを初期方針とする。Multi-page質問は複数Chunkを検索して扱う。
Parameter変更時はConfig、Corpus Revision、Index、結果をすべて別Versionにする。

## 9.5 Document Schema

```json
{
  "document_id": "sha256-of-pdf",
  "chunk_id": "test:pdfhash:p0008:c003:texthash",
  "source_dataset": "JDocQA",
  "source_revision": "e65c6c7d4a3ac869b48641eb94ed1f8b0ddf886a",
  "split": "test",
  "pdf_name": "example.pdf",
  "pdf_sha256": "...",
  "page_index": 7,
  "page_number_display": null,
  "chunk_index": 3,
  "text": "...",
  "text_sha256": "...",
  "text_source": "embedded",
  "extraction_status": "pass",
  "extractor_name": "...",
  "extractor_version": "...",
  "ocr_engine": null,
  "ocr_version": null,
  "normalization_version": "text_norm_v1",
  "chunking_version": "chunk_v1"
}
```

## 9.6 Gold情報との分離

次の情報をRetriever、Generator、Query RewriteのStateへ含めない。

- `reference_answers`
- `question_page_number`
- `reason_of_answer_bbox`
- Gold Document/Chunk ID
- `context`
- `original_context`
- `dataset_type`から答えの有無を直接示すLabel
- 正解に基づいて作った説明文

評価器は生成完了後にGold情報へAccessできる。実装では`InferenceRecord`と`EvaluationRecord`を
別の型または別Objectにし、誤ってPromptへSerializeされないようTestする。

---

# 10. JDocQAから作る本研究用Dataset

JDocQAのRaw Labelだけでは、Normal、Retrieval Failure、Distractorの比較条件は完成しない。
本研究用の固定Datasetを新たに作成する必要がある。

## 10.1 共通ルール

- 最終評価用のBase QAはTest Splitから選ぶ。
- すべてText-only適格性監査を通す。
- Normal、Retrieval Failure、DistractorのBase QA IDは原則として重複させない。
- 同じQAを意図的にPair比較する場合は、全体平均へ重複計上せず、Pair分析として別集計する。
- Seed、抽出母集団、層別条件、候補順序、採否理由を保存する。
- 3方式で同じDataset、Corpus、Retriever、Generator、Prompt、Seedを使う。
- 比較方式間で変えるのはRecovery制御だけとする。

## 10.2 Normal QA

目的は、入力を意図的に難化していない通常条件での性能測定である。

構築手順:

1. TestのText-only適格なAnswerable QAを母集団にする。
2. Answer Type、PDF Category、Multi-page、Text Sourceの分布を取得する。
3. Seed 42で層別抽出し、初期目標150件とする。
4. 特定PDFへの偏りを避けるため、可能なら1 Subset内の同一PDF件数に上限を設ける。
5. Modelの正答・誤答を採否条件にしない。

Normalは「必ずBaselineが成功する例」という意味ではない。自然条件のDatasetであり、実行後に
観測されたFailureは別Fieldへ記録する。

## 10.3 Unanswerable QA

目的は、文書に答えがないときにHallucinationせず回答拒否できるかを評価することである。

構築手順:

1. Testで`no_reason == "0"`の145件を候補とする。
2. 固定したText-only Ruleで全件監査する。
3. `eligible`を全件採用し、150件へ固定しない。
4. `ineligible`と`needs_adjudication`は採用せず、理由をManifestへ残す。
5. 145件、採用件数、理由別除外件数をすべて報告する。

Unanswerableの正解文字列は`本文中に記載がありません`である。Primary指標では正規化後の
Canonical回答一致を測る。Secondary指標では、事前に固定した回答拒否表現も認めるが、
拒否文と同時に根拠のない具体的事実を述べた回答は成功としない。

## 10.4 Retrieval Failure

目的は、初回検索でGold根拠を取得できない条件において、Query Rewriteが回復に寄与するかを
測ることである。

「Retrieval Failure」はJDocQAのNative Labelではなく、固定Retrieverと派生条件に依存する。

構築手順:

1. Text-only適格なAnswerable QAから、Normal/Distractorと重複しない候補を取る。
2. 元質問と意味・正解を変えず、検索Keywordを減らす、参照表現を一般化する、表記を変えるなどの
   検索困難化を決定的なRuleまたは固定Model/Promptで行う。
3. 人手または検証Ruleで、派生質問が元質問と意味的に同値か確認する。
4. 固定Corpusと固定Retrieverで派生質問を検索する。
5. Gold Pageに由来するChunkがTop-kにない例をRetrieval Failure候補とする。
6. Query Rewrite後の成功は採用条件にしない。成功例だけを選ぶとRSRを過大評価するためである。
7. Answer Type等を層別し、初期目標150件を固定Manifestへ保存する。

保存項目:

```text
base_record_id
original_question
derived_question
transformation_type
derivation_prompt_hash
derivation_model_revision
seed
retriever_config_hash
top_k
initial_retrieved_chunk_ids
gold_chunk_in_initial_top_k
human_equivalence_check
```

Gold PageがTop-kにないことはOffline Dataset構築時だけ判定し、本番のFailure DiagnosisへGold情報を
渡さない。実行時のR Scoreによる診断と、Goldに基づく事後評価を分離する。

## 10.5 Distractor

目的は、正解に似ているが根拠として不適切なChunkが取得Contextにある場合の耐性を測ることである。

構築手順:

1. Text-only適格なAnswerable QAから、他Subsetと重複しない候補を取る。
2. 同じSplitの異なるPDFから、BM25またはEmbedding類似度が高いChunkをHard Negative候補にする。
3. Gold Answer文字列を含むChunkを機械的に除き、残りを人手またはRuleで「正解根拠ではない」と確認する。
4. 固有名詞、年度、地域、制度名が似ているが異なるChunkを優先する。
5. 候補PoolへDistractorを追加し、通常と同じFusion/Rerankを適用する。
6. 最終Top-kに少なくとも1 Distractorと1 Gold根拠Chunkが残る例をDistractor条件とする。
7. Gold Chunkが落ちた場合はDistractorではなくRetrieval Failureとして分離する。
8. 初期目標150件を固定する。

Distractorを最終順位へ無条件に差し込む場合は、その挿入位置と個数を明記する。方式比較ごとに
異なるDistractorを使ってはならない。

保存項目:

```text
base_record_id
distractor_chunk_ids
distractor_pdf_names
selection_method
similarity_scores
negative_validation_method
seed
candidate_pool_position
final_rank
gold_chunk_ids
```

## 10.6 Dataset条件と実際のFailureを分ける

`dataset_type`は実験条件であり、Modelが実際にどのFailureを起こしたかとは別である。

```text
dataset_type:
  normal
  unanswerable
  retrieval_failure
  distractor

observed_failure_type:
  none
  retrieval_failure
  generation_failure
  answer_relevance_failure
```

例えばDistractor条件でも検索自体が失敗する場合がある。この2 Fieldを混同すると、
Failure Detection F1の正解Labelが循環的になる。

---

# 11. 本研究用QA Schema

```json
{
  "record_id": "jdocqa:e65c6c7:test:00000",
  "source_dataset": "JDocQA",
  "source_revision": "e65c6c7d4a3ac869b48641eb94ed1f8b0ddf886a",
  "source_record_sha256": "...",
  "split": "test",
  "source_line_index": 0,
  "pdf_name": "example.pdf",
  "question_number_raw": "2-378-1-5",
  "question_text": "...",
  "answer_instruction": "open_ended",
  "reference_answers": ["..."],
  "answer_type": "open_ended",
  "is_answerable": true,
  "is_unanswerable": false,
  "is_multi_page": false,
  "no_reason_raw": "1",
  "reference_pages_raw": "8",
  "reason_of_answer_bbox_raw": "",
  "text_only": {
    "rule_version": "text_only_v1",
    "eligibility": "eligible",
    "exclusion_reasons": [],
    "evidence_mode": "prose"
  },
  "dataset_type": "normal",
  "derived_from_id": null,
  "derivation": null
}
```

公開・推論用Viewからは`reference_answers`、Reference Page、BBox、`dataset_type`などを除去する。

---

# 12. ManifestとDirectory

実装予定の配置:

```text
data/
├─ raw/jdocqa/                         # PDF・元Annotation、Git対象外
├─ processed/jdocqa/{revision}/
│  ├─ train/documents.jsonl
│  ├─ validation/documents.jsonl
│  └─ test/documents.jsonl
└─ manifests/
   ├─ jdocqa_source_manifest.json
   ├─ jdocqa_text_only_train.jsonl
   ├─ jdocqa_text_only_validation.jsonl
   ├─ jdocqa_text_only_test.jsonl
   ├─ jdocqa_eval_normal.jsonl
   ├─ jdocqa_eval_unanswerable.jsonl
   ├─ jdocqa_eval_retrieval_failure.jsonl
   └─ jdocqa_eval_distractor.jsonl
```

Source Manifestに最低限保存するもの:

```json
{
  "dataset": "JDocQA",
  "official_repository": "https://github.com/mizuumi/JDocQA",
  "revision": "e65c6c7d4a3ac869b48641eb94ed1f8b0ddf886a",
  "retrieved_at": "2026-08-25",
  "annotation_license": "CC BY-SA 4.0",
  "files": {
    "train": {"rows": 9290, "sha256": "..."},
    "validation": {"rows": 1134, "sha256": "..."},
    "test": {"rows": 1176, "sha256": "..."}
  },
  "pdf_expected": 5504,
  "pdf_found": 5504,
  "missing_pdf_names": [],
  "pipeline_git_commit": "...",
  "config_hash": "..."
}
```

Manifest自体を更新した場合は上書きだけで履歴を消さず、Versionまたは作成日時を変える。

---

# 13. 再現性に必要な固定情報

次を固定しなければ「同じDataset」とみなさない。

- JDocQA Repository/Hugging Face DatasetのRevision。
- AnnotationとPDFのSHA-256。
- 欠損・破損PDF一覧。
- Text抽出Library、Version、Option。
- OCR Engine、言語Model、Version、解像度、前処理。
- Text正規化Rule Version。
- Chunk長、Overlap、境界Rule。
- BM25 Tokenizerと辞書Version。
- Embedding Model名とRevision。
- Vector Index設定。
- Text-only選別Rule VersionとReviewer判定。
- 派生質問/Distractorの生成Prompt、Model Revision、Seed。
- `top_k`、RRF Parameter、Reranker設定。
- 実験Config、Prompt Hash、CodeのGit Commit。

研究室PCとLocal PCで同一Manifestを読み、Hash照合後に実験を開始する。

---

# 14. Validationと自動Test

Dataset Pipelineでは少なくとも次を自動検証する。

## 14.1 Source検証

- Split件数が9,290/1,134/1,176である。
- 合計が11,600件である。
- 異なるPDF数が4,403/550/551、合計5,504件である。
- Split間の`pdf_name`重複が0件である。
- File HashがManifestと一致する。
- 19 Raw Fieldが存在する。
- 不明な`answer_type`、`no_reason`、`type_of_image`を黙って受理しない。

## 14.2 正規化検証

- 全RecordにStable IDとRaw Record Hashがある。
- `reference_answers`が空でない文字列Listである。
- List風`normalized_answer`を安全にParseできる。
- `no_reason`から3 Booleanへ期待どおり変換できる。
- Raw Fieldを失わず再監査できる。

## 14.3 Corpus検証

- 全PDF、全Pageを処理したか記録される。
- 各ChunkにSplit、PDF、Page、Text Source、Hashがある。
- Corpus構築処理がGold Page/BBox/Answerを参照しない。
- 埋め込みTextが品質不足ならOCRへFallbackする。
- 同じConfigとInputから同じChunk IDを再生成できる。

## 14.4 Subset検証

- 全採用例が`eligibility == eligible`である。
- UnanswerableはTestの適格な`no_reason == "0"`を全件含む。
- Unanswerableを150件へ固定していない。
- Normal/Retrieval Failure/DistractorのBase ID重複がない。
- 派生例に元ID、Seed、生成条件がある。
- Distractorが異なるPDF由来で、Gold根拠と区別されている。
- 3比較方式でManifest Hashが一致する。

## 14.5 Leakage検証

- Inference PromptにGold Answer、Gold Page、BBoxが含まれない。
- `context`をGeneratorへ直接渡していない。
- Test由来の質問がPrompt例やFew-shot例に含まれない。
- Test結果によるParameter変更が別Experiment IDとして記録される。

---

# 15. 評価時の注意

JDocQA原論文では、Yes/No、Factoid、Numericalに軽微な表記差を除去したExact Match、
Open-endedにMeCabでTokenizeしたBLEUを使用している。本研究の主要指標にはAnswer F1、
Faithfulness、Hallucination Rate、Failure Detection F1、Recovery Success Rate、ECEなどを使うが、
原論文との比較用Metricと本研究のMetricを混同しない。

Dataset別に最低限報告するもの:

- 採用件数と除外件数。
- Answer Type、Category、Multi-page、Text Sourceの分布。
- Retrieval Recall@kまたはGold Page/Chunk到達率。
- Answer正確性。
- Unanswerableの回答拒否率とHallucination率。
- Failure DetectionのConfusion Matrix。
- Recovery前後の品質とRecovery Success Rate。
- LLM Call数、Latency、失敗・Timeout件数。
- 抽出不能/OCR品質不足による除外件数。

Gold Page到達率を測るときは、Page番号対応の検証が済んでいること、複数Page QAで必要Pageを
何件取得すれば成功とするかを事前に定義することが必要である。

---

# 16. 既知のRiskとLimitations

- 元DatasetはMultimodalであり、Text-only選別によって母集団が変わる。
- 選別により簡単な質問へ偏る可能性があるため、採用前後の分布比較が必要である。
- `type_of_image`には欠損があり、自動Filterだけでは正確に選べない。
- OCR誤りはRAGの検索失敗と区別しにくい。抽出品質Labelを別に持つ必要がある。
- JDocQA提供の質問単位Textは全文Corpusではない。
- `context`と`original_context`が現行Revisionで全件同一であり、公式説明上のNoise除去差を
  実データから確認できない。
- 論文集計と現行Annotationには数件の差がある。
- `pdf_category`が同一PDF内で矛盾するRecordがある。
- UnanswerableにもPage番号や一部BBox IDがあるため、それらをGold根拠とみなせない。
- Retrieval Failureは固定Retriever依存、Distractorは生成手順依存であり、JDocQA Native Labelではない。
- Test Splitだけで対象数が不足する場合、件数を無理に揃えると分布や公平性を損なう。
- 元PDFの利用条件と配布可否は文書ごとに異なり得る。

これらは欠点を隠すのではなく、卒業論文のDataset節とLimitations節に明記する。

---

# 17. よくある質問

## Q1. `context`、`text_from_pdf`、`text_from_ocr_pdf`は全部、答えに関係する別文書か

違う。同じ質問対応Pageの内容を異なる方法・加工段階で表したものに近い。Answerableでは通常
答えの手掛かりに関係するが、Unanswerableでは文章が存在しても答えはない。

## Q2. `context`をそのままRetrieverの文書にできるか

できない。質問ごとに対応付けられたContextであり、検索対象を事前に絞った状態になる。
対象Splitの全PDF・全Pageから質問非依存にCorpusを作る。

## Q3. OCRを使うとMultimodal研究になるか

本研究ではならない。OCRはPDFから文字を取得する前処理としてのみ使い、RAGへ渡すのは文字列だけで
ある。ただしOCR性能自体は研究対象外なので、抽出品質を記録して交絡を管理する。

## Q4. 表をOCRして文字にすれば対象にできるか

主実験では原則できない。本研究は「文章だけで回答できる例」を対象とし、表の行列構造に依存する
質問を除外する。本文に同じ根拠が独立して書かれている場合だけ採用できる。

## Q5. `type_of_image`が空なら自動的に採用できるか

できない。公式にLabel欠損がある。質問と根拠を確認する必要がある。

## Q6. Test Unanswerableは145件すべて使うか

145件すべてを候補にし、Text-only適格なものをすべて使う。視覚依存、抽出不能、Source PDF欠損などは
理由を残して除外するため、最終件数は145件以下になる。

## Q7. なぜ150件へ揃えないのか

UnanswerableはJDocQAのNative Labelであり、Test内の利用可能な全例を使う方が恣意的なSamplingを
減らせるからである。Dataset間の件数差は、各Dataset別MetricとMacro平均で扱う。

## Q8. Multi-page質問は除外するか

除外しない。必要な根拠がすべて文章で抽出できれば対象となる。複数Chunk取得が必要なため、
Single-pageと分けて結果を報告する。

## Q9. 正解PageとBBoxをRetrieverへ渡してよいか

不可。評価時のGold Labelとしてだけ使用する。渡すとRetrieval Failureを評価できない。

## Q10. Unanswerableの`context`が空だから答えられないのか

多くは違う。Testの145件中144件には非空の`context`がある。Unanswerableは「文書に質問への答えが
ない」Labelであり、単なるEmpty Contextではない。

## Q11. `normalized_answer`をそのまま正解文字列にしてよいか

不可。一部がList風文字列なので、安全にParseして`reference_answers`へ正規化する必要がある。

## Q12. Retrieval FailureとDistractorはJDocQAにもともと含まれるか

含まれない。本研究がJDocQAのText-only適格なAnswerable QAを基に、固定手順で作る派生条件である。

## Q13. 研究室PCへ何をCopyすれば同じDatasetになるか

GitHubからCode、Config、Manifestを取得し、別途同じRevisionのJDocQA PDF/Annotationを用意する。
File Hash、抽出Tool Version、OCR、Chunk、Index設定まで一致させる。

## Q14. Raw DatasetをGitHubへ置いてよいか

原則置かない。容量、元PDFごとの利用条件、再配布条件があるため、取得ScriptとManifestで再現する。

---

# 18. 実装開始前Checklist

- [ ] 公式の方法でPDFを取得した。
- [ ] Annotation Revisionと3 FileのSHA-256をManifestへ保存した。
- [ ] 5,504 PDFの存在とHashを確認した。
- [ ] Raw JSONL Loaderが19 Fieldを保持する。
- [ ] Stable IDとRaw Record Hashを生成する。
- [ ] `normalized_answer`のList風文字列を安全にParseする。
- [ ] TrainでText-only選別Pilotを実施する。
- [ ] Validationで選別Ruleと抽出品質Ruleを固定する。
- [ ] 全PDF・全PageからSplit別Corpusを作る。
- [ ] Gold Answer/Page/BBoxをInference Stateから分離する。
- [ ] Test Unanswerable 145候補を全件監査する。
- [ ] 4種類の評価Manifestを固定する。
- [ ] 3比較方式でDataset/Corpus/Model設定が同一かTestする。
- [ ] 卒業論文用のDataset統計と除外理由表を自動出力する。

---

# 19. 変更時に更新する場所

| 変更内容 | 更新対象 |
|---|---|
| Text-only定義・除外理由 | 本書、選別Script、Test、Manifest Rule Version |
| 対象件数・Sampling | 本書、研究計画書、Dataset Manifest |
| Text抽出/OCR | 本書、実装計画書、Corpus Config、Manifest |
| Chunk/検索Parameter | 実装計画書、Config、Corpus/Index Revision |
| Failure派生方法 | 本書、研究計画書、生成Script、Manifest |
| 評価Metric | 研究計画書、本書、評価実装、結果Schema |
| JDocQA Revision | 本書、Source Manifest、Hash、全派生物 |

---

# 20. Citation

```bibtex
@inproceedings{onami-etal-2024-jdocqa,
  title = "{JD}oc{QA}: {J}apanese Document Question Answering Dataset for Generative Language Models",
  author = "Onami, Eri and Kurita, Shuhei and Miyanishi, Taiki and Watanabe, Taro",
  booktitle = "Proceedings of the 2024 Joint International Conference on Computational Linguistics, Language Resources and Evaluation (LREC-COLING 2024)",
  month = may,
  year = "2024",
  publisher = "ELRA and ICCL",
  url = "https://aclanthology.org/2024.lrec-main.830/",
  pages = "9503--9514"
}
```

本研究の卒業論文では、JDocQAを基盤Datasetとして用いたこと、Text-only Subsetへ選別したこと、
Retrieval Failure/Distractorを派生生成したこと、公式Datasetからの変更点を明記する。
