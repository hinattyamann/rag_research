# CLAPNQデータセット理解・Text-based RAG利用仕様書

## Version 1.3

最終確認日: 2026-08-26

本書は、CLAPNQそのものの仕様と、本研究「評価駆動型自己制御RAGによる回答信頼性向上手法」
での利用方法を一か所に集約したDataset仕様書である。CLAPNQの取得、研究用Split、検索Corpus、
派生評価条件、評価指標、License、論文での引用・表示方法について疑問が生じた場合は、まず本書を
参照する。

本書では、情報の性質を次の4種類に分ける。

- **公式情報**: CLAPNQ論文、公式Repository、公式Dataset Cardに明記された内容。
- **実データ監査結果**: 2026-08-26に固定Revisionの公開Fileを取得・再集計した結果。
- **研究上の決定**: 本研究の目的に合わせて採用する運用。
- **未確定**: PilotまたはCalibration Splitで検証後に固定する値。

研究方針や実装を変更した場合は、本書、`rag_research_plan.md`、
`rag_implementation_plan.md`、実装、Test、Dataset Manifestを同時に更新する。

---

# 1. 最初に確認する結論

## 1.1 CLAPNQは本研究に利用できるか

CLAPNQは、本研究の基盤Datasetとして利用できる。むしろ、Text-only選別、PDF取得、Text抽出、
OCRといったJDocQA固有の前処理を必要とせず、次を公式に備えるため、本研究が対象とする
**Text-basedのFull RAG Pipeline**へ直接適用できる。

- 自然な質問。
- 人手で作成された長文Reference Answer。
- 回答を根拠付けるGold Passage。
- 回答作成に使用されたSelected Sentences。
- 約17.9万Passageの検索Corpus。
- 質問とGold Passage IDの対応。
- AnswerableとUnanswerableの両方。

CLAPNQの導入によって、OCR品質や視覚情報依存がRetrieval Failureへ混入する問題を除き、
自己評価、Failure Diagnosis、Adaptive Recoveryそのものへ研究範囲を集中できる。

ただし、次の制約があるため、公式Fileをそのまま最終評価へ流用しない。

1. 公式Test Answerは非公開である。
2. 公開TrainとDevはWikipedia Title単位で完全には分離されていない。
3. UnanswerableはCorpus全体での回答不能を保証しない。
4. 長文回答であるため、短答向けExact MatchやAnswer F1だけでは評価できない。
5. 英語Wikipediaのみであり、言語非依存性や他Domainへの一般化を直接実証するものではない。

## 1.2 本研究で使うもの・使わないもの

| 対象 | 方針 |
|---|---|
| 公開Train/Devの最終Round Annotation | 主Datasetとして使用する |
| `input` | 質問本文として使用する |
| `passages[].text` | Gold Passageの評価・Generation Oracle条件に使用する |
| `output[].answer` | Reference Answerとして評価に使用する |
| `output[].selected_sentences` | Gold EvidenceとしてFaithfulness評価に使用する |
| `retrieval/passages.tsv.zip` | Full RAGの検索Corpusとして使用する |
| Retrieval Query TSVのGold Passage ID | Retrieval評価にのみ使用し、Inferenceへ渡さない |
| Original NQ Document | Dataset監査に使用し、主Retrieval Corpusには直接追加しない |
| 公式Test | Answerが非公開のため、著者から正式に取得しない限り主実験では使用しない |
| CLAPNQ-R1 | 品質条件が異なる補助Train Dataであるため、主実験には使用しない |

## 1.3 本研究で固定する評価条件

| 種類 | 初期目標 | 用途 |
|---|---:|---|
| Normal QA | 150件 | 通常検索・生成条件の性能評価 |
| Unanswerable QA | 監査済み150件 | 回答拒否、Hallucination、誤Recoveryの評価 |
| Retrieval Failure | 150件以下 | Query Rewriteによる検索Recovery評価 |
| Distractor | 150件 | 類似する誤根拠への耐性評価 |

Normal、Retrieval Failure、DistractorのBase QAは重複させない。Retrieval Failureは固定Retrieverで
条件を満たす例の実数が150件未満なら、水増しせず実数を報告する。件数を増やすために派生質問を
作る場合は、自然発生したFailureと派生Failureを別集計する。

Unanswerableは、事前に固定した候補順からCorpus-level監査を通過した150件を採用する。監査で
除外した例は、Model結果を見ず、同じ固定順の次候補で補充する。

---

# 2. CLAPNQの概要

## 2.1 基本情報

CLAPNQは、Rosenthal et al.がTransactions of the Association for Computational Linguistics
（TACL）Volume 13で発表した、Full RAG Pipeline向けの英語Long-form Question Answering
Datasetである。

| 項目 | 内容 |
|---|---|
| 元Dataset | Natural Questions（NQ） |
| 言語 | 英語 |
| Domain | Wikipedia |
| 質問 | 実際のGoogle検索Queryに由来するNQ質問 |
| 回答 | 人手で作成された簡潔で根拠付きの長文回答 |
| Gold Evidence | 1つを基本とするGold PassageとSelected Sentences |
| Answerability | AnswerableとUnanswerable |
| Retrieval Corpus | 4,293文書、178,890 Passage Records |
| 主用途 | Retrieval、Gold Passage Generation、Full RAG |

CLAPNQは、NQのうちLong AnswerはあるがShort Answerがなく、表・Listを除き、Passageが5文より長い
質問を基に作られた。回答は平均約56.8語、2.3文、Gold Passageは平均約156語であり、回答は
Passage全体の約3分の1である。複数の非連続な根拠文を自然につなぐCohesive Answerが中心である。

## 2.2 公式Split

| Split | Answerable | Unanswerable | 合計 | 公開状態 |
|---|---:|---:|---:|---|
| Train | 1,954 | 1,791 | 3,745 | 公開 |
| Dev | 300 | 300 | 600 | 公開 |
| Test | 301 | 300 | 601 | Answer非公開 |
| 合計 | 2,555 | 2,391 | 4,946 | 一部非公開 |

研究で直ちに利用できる公開範囲はTrainとDevの4,345件で、Answerable 2,254件、
Unanswerable 2,091件である。公式Testを利用する必要がある場合は、公式READMEに従って著者へ
研究目的と利用理由を連絡し、許可されたFile、利用条件、取得日をManifestへ記録する。

## 2.3 Annotation品質

CLAPNQは7名の熟練Annotatorによって作られた。Round 1で根拠文の選択と回答作成を行い、
非連続な複数文を使用した回答は別AnnotatorによるRound 2を行った。最終Datasetは複数人が確認した
例から構成され、複数Reference間のROUGE-LによるInter-Annotator Agreementは0.67と報告される。

Reference Answerは抽象生成だけではなく、Gold Passageの表現を多く保持する。そのため、
ROUGE-LやToken F1が利用できる一方、単純な文字列一致だけで回答品質を断定しない。

---

# 3. 一次資料、配布物、取得方法

## 3.1 一次資料

- CLAPNQ論文: <https://aclanthology.org/2025.tacl-1.3/>
- DOI: <https://doi.org/10.1162/tacl_a_00729>
- 公式Repository: <https://github.com/primeqa/clapnq>
- Hugging Face Annotation: <https://huggingface.co/datasets/PrimeQA/clapnq>
- Hugging Face Retrieval Corpus: <https://huggingface.co/datasets/PrimeQA/clapnq_passages>
- Natural Questions公式配布ページ: <https://ai.google.com/research/NaturalQuestions/download>
- Natural Questions論文: <https://aclanthology.org/Q19-1026/>

Datasetの仕様と件数はCLAPNQ論文および公式Repositoryを一次資料とする。Hugging Faceは
取得を簡便にする配布Channelとして扱い、Dataset Cardだけで元Fieldの意味を変更しない。

## 3.2 本書で監査したRevision

2026-08-26時点で次の公式Repository Commitを固定して公開Dataを監査した。

```text
c508d78d8c5c2eecbf172fcf5f789004206e11fb
```

実験開始時はこのRevisionを初期基準とする。将来別Revisionへ更新する場合は、File Hash、件数、
Schema、結果差を確認し、Source Manifestと本書を同時に更新する。可変の`main`だけを記録しては
ならない。

## 3.3 主な配布File

```text
annotated_data/
├─ train/clapnq_train_answerable.jsonl
├─ train/clapnq_train_unanswerable.jsonl
├─ train/clapnq_train_single_answerable.jsonl
├─ dev/clapnq_dev_answerable.jsonl
└─ dev/clapnq_dev_unanswerable.jsonl

original_documents/
├─ train/*_orig.jsonl
└─ dev/*_orig.jsonl

retrieval/
├─ passages.tsv.zip
├─ train/question_train_answerable.tsv
├─ train/question_train_unanswerable.tsv
├─ dev/question_dev_answerable.tsv
└─ dev/question_dev_unanswerable.tsv
```

主実験では最終Roundの4 Annotation File、`passages.tsv.zip`、4 Retrieval Query TSVを使用する。
`clapnq_train_single_answerable.jsonl`はRound 1の補助Train Dataであり、主評価Dataへ混ぜない。

## 3.4 取得方法

初期実装では公式Git Repositoryを固定CommitでCloneして取得する。Hugging Faceから取得する場合も、
Dataset Revisionを指定し、取得Channelが異なってもRecord IDとHashが対応することを確認する。

```text
data/raw/clapnq/{revision}/
├─ annotated_data/
├─ original_documents/
├─ retrieval/
├─ LICENSE
└─ SOURCE_MANIFEST.json
```

Raw DataはGit管理対象外とし、取得Script、Revision、URL、Hash、件数、License情報だけを本Repositoryで
管理する。監査時の展開済みDataは約300 MiB、Retrieval CorpusのZipは約40 MiBだったため、通常の
研究用PCで扱える規模である。

---

# 4. AnnotationとRetrieval Fileの実構造

## 4.1 Annotation JSONL

各行は次の構造を持つ。

```json
{
  "id": "8045984229282682032",
  "input": "who sang love the one you're with first",
  "passages": [
    {
      "title": "Love the One You're With",
      "text": "...",
      "sentences": ["...", "..."]
    }
  ],
  "output": [
    {
      "answer": "...",
      "selected_sentences": ["...", "..."],
      "meta": {
        "annotator": [47200615, 46373812],
        "has_minimal_answer": false,
        "non_consecutive": true,
        "round": 2,
        "skip": false
      }
    }
  ]
}
```

| Field | 意味 | 本研究での扱い |
|---|---|---|
| `id` | 元NQ Example ID | Source IDとして保持する |
| `input` | 質問 | `question`へ正規化する |
| `passages[].title` | Goldまたは関連Wikipedia Title | Group Splitと監査に使用する |
| `passages[].text` | Gold Passage、UnanswerableではRandom Passage | Answerabilityに応じて役割を分ける |
| `passages[].sentences` | Passageの文分割 | Evidence対応確認に使う |
| `output[].answer` | Reference Answer | 複数Referenceをすべて保持する |
| `selected_sentences` | 回答作成に使った根拠文 | Gold Evidenceとして保持する |
| `meta` | Annotation Round等 | 品質監査用に保持する |

Answerableでは通常1つのGold Passageを持つ。論文ではNQ Dev由来の14問に2つのGold Passageがあるが、
回答Annotationは頻度の高い1 Passageに対してのみ付与されると説明されている。

UnanswerableにはGold Passageが存在しない。Annotationに含まれるPassageは元Wikipedia文書から
ランダムに選ばれたものであり、`gold_passage`と呼ばず`provided_unanswerable_passage`として保持する。

## 4.2 公開Dataの実監査で確認した注意点

- Train Answerable 1,954行、Dev Answerable 300行は、無効Referenceを除外しても全行に1つ以上の
  有効Answerが残る。
- Train Answerableには`skip=true`の空Answerが76 Reference、Devには空Answerが10 Referenceある。
- Devには文字列`NA`のReferenceが10件ある。空文字、`NA`、`skip=true`を評価Referenceから除外する。
- Unanswerableの公開実Fileでは、README例の`null`ではなく空文字Answerが格納される。Loaderは
  `null`と空文字の両方を受理し、内部ではReference Answerを空Listへ統一する。
- Answerableには1～2 Referenceが中心だが、Pilot由来の少数例には4～7 Referenceがある。
- 正規化後の有効ReferenceはTrain Answerable 2,667件、Dev Answerable 475件、合計3,142件である。
- 同一Record内で同じ有効Answerが重複する例が2件ある。Raw Annotationの順序を維持して両方を残し、
  元`output` Indexを保持する。最大Score方式では重複によってScoreは変わらない。
- 有効Answerだが`selected_sentences=[]`のReferenceが2件ある。Answerを無効化せず、空Evidenceとの対応を
  保持してEvidence監査時に識別する。
- Optional R1 FileはREADME表の12,657件に対して実Fileが12,039行だった。主実験では使用せず、
  使用する場合は別Dataset Revisionとして件数差を明記する。

## 4.3 Retrieval Corpus

`passages.tsv.zip`内のTSVは次のFieldを持つ。

```text
id    text    title
```

- `id`: Corpus内で一意なPassage ID。
- `text`: Retrieverへ投入する本文。
- `title`: Wikipedia Article Title。

公式論文では178,891 Passages、4,293 Documentsと報告される。一方、固定Revisionの
`retrieval/passages.tsv.zip`を実監査すると、`passages.tsv`はHeader込み178,891物理行であり、
Data Recordは178,890件だった。Passage IDは178,890件すべて一意で、公式Hugging Face配布の
`num_examples`も178,890件である。このため、本研究では実際にRetrieverへ投入する178,890 Recordsを
Corpus件数の正本とし、論文記載値との差をSource Manifestと論文のDataset説明に注記する。

極端に長い3,000語超または短い15語未満の非Gold Passageは除かれている。Gold Answerable Passageは
Corpusに含まれる。

本研究では公式PassageをCanonical Retrieval Unitとし、最初の主実験では再Chunkしない。再Chunkを
試す場合は追加実験として、元Passage ID、Chunk Rule、Gold Mappingの再構築方法を別Versionで保存する。

## 4.4 Retrieval Query TSV

```text
id    question    doc-id-list    answers
```

`doc-id-list`はAnswerableのGold Passage IDである。Unanswerableでは空である。Gold Passage IDと
Reference AnswerはRetriever、Generator、Query Rewriteへ渡さず、評価処理だけが参照する。

固定公開Dataでは、Answerable 2,254件の`doc-id-list`は全てGold Passage ID 1件、Unanswerable 2,091件は
全て空である。Unique Gold Passage IDは2,074件で、全てCanonical Corpusに存在する。Annotationとの結合は
`source_split`、`is_answerable`、`source_id`の3要素をKeyとし、質問文の完全一致も検証する。4,345件で
欠損、余剰、重複、不一致は0件である。

`answers`列には引用符内の改行によって複数物理行にまたがるLogical TSV Recordが200件ある。そのため、
物理行ごとの`split("\t")`ではなく、引用符と改行を扱えるCSV/TSV Parserで読み込む。Queryの
`source_line_index`はHeaderを除くLogical Recordの0始まりIndexとする。出所の同一性はSource Manifestの
TSV File SHA-256とLogical Indexで追跡し、物理行単位のRow Hashは作らない。

---

# 5. License、無料利用、表示保持

## 5.1 無料利用の意味

CLAPNQ RepositoryとHugging Face上の公開Dataは、Dataset利用料なしで取得できる。公式Repositoryは
Apache License 2.0を掲示し、利用、複製、変更、配布を無償・Royalty-freeで許諾している。

ただし、次は別である。

- LLM API、GPU、Storage、通信などの実験費用。
- 非公開TestへのAccess。料金は記載されていないが、著者への申請が必要である。
- 元となるNatural QuestionsおよびWikipedia由来ContentのLicense条件。

「無料で利用できる」と「出典やLicense表示なしで再配布できる」は同義ではない。

## 5.2 適用Licenseの整理

| 対象 | 公式表示 | 本研究での扱い |
|---|---|---|
| CLAPNQ Repository、追加Annotation | Apache License 2.0 | LICENSE、著作権・帰属表示、変更表示を保持する |
| 元Natural Questions Data | CC BY-SA 3.0 | 出典表示とShareAlike条件を保持する |
| Wikipedia由来本文 | Wikipedia/NQ側の条件 | NQ由来であることを表示し、Raw本文の再配布を最小化する |
| CLAPNQ論文本文 | CC BY 4.0 | 論文の引用に利用し、本文・図表の転載時は帰属表示する |

CLAPNQ側はDatasetをApache 2.0として公開している一方、GoogleのNatural Questions公式配布ページは
NQ DataをCC BY-SA 3.0としている。CLAPNQはNQの質問とWikipedia Passageを含むため、本研究では
**どちらか一方だけを表示するのではなく、Apache 2.0とCC BY-SA 3.0の両方をLicense Lineageとして
記録する**。これは法的判断ではなく、Academic Useと再配布における保守的な運用方針である。

## 5.3 Local利用時に残す情報

`SOURCE_MANIFEST.json`へ最低限次を保存する。

```json
{
  "dataset": "CLAPNQ",
  "repository": "https://github.com/primeqa/clapnq",
  "revision": "c508d78d8c5c2eecbf172fcf5f789004206e11fb",
  "retrieved_at": "2026-08-26",
  "licenses": ["Apache-2.0", "CC-BY-SA-3.0"],
  "derived_from": "Natural Questions and Wikipedia",
  "files": {},
  "pipeline_git_commit": "...",
  "config_hash": "..."
}
```

FileごとにRelative Path、Byte数、SHA-256、Row数を追加する。Hugging Face経由ならDataset Revisionと
Cache上のData File Hashも保存する。

## 5.4 GitHubまたは第三者へ派生Dataを公開する場合

Raw質問、Passage、Reference Answerを含む派生Dataを公開する場合は、少なくとも次を同梱する。

```text
LICENSES/
├─ Apache-2.0.txt
└─ CC-BY-SA-3.0.txt
NOTICE_DATASET.md
DATASET_MANIFEST.json
```

`NOTICE_DATASET.md`には次を書く。

- CLAPNQとNatural Questionsから派生したこと。
- CLAPNQ論文、NQ論文、公式Repository、NQ配布ページへのLink。
- 使用Revisionと取得日。
- 本研究で行ったSplit変更、Filter、Unanswerable監査、派生質問、Distractor追加。
- 原作者が本研究結果を保証・承認しているわけではないこと。
- 元のCopyright、Attribution、NOTICEを削除していないこと。

Apache 2.0に従い、変更したFileには変更済みであることを明示する。CC BY-SA対象Contentを含む公開物は、
適切な同一条件での共有が必要になり得るため、配布前に学校の方針とLicense本文を再確認する。

Raw DataやCorpus本文を本Repositoryへ直接Commitする必要はない。再現に必要なScript、Manifest、ID、
Split Label、派生条件だけを公開し、利用者が公式配布元から取得して再生成できる方式を優先する。

## 5.5 論文・発表資料で表示する内容

卒業論文のDataset節では、最低限次を明記する。

1. CLAPNQを基盤Datasetとして使用したこと。
2. Natural QuestionsおよびWikipediaから派生した英語Datasetであること。
3. 使用した公開Split、Repository Revision、取得日。
4. 公式Test Answerは利用せず、公開Train/DevをTitle単位で再分割したこと。
5. 使用件数、除外件数、重複除去、無効Reference除外条件。
6. UnanswerableをCorpus-levelで再監査したこと。
7. Retrieval FailureとDistractorは本研究で作った派生条件であること。
8. CLAPNQとNQの両論文を引用すること。
9. Apache 2.0およびCC BY-SA 3.0の表示を残したこと。

表や図にDataset統計を載せる場合のSource例:

```text
Source: Rosenthal et al. (2025) and the official CLAPNQ repository,
revision c508d78 (accessed 2026-08-26). Counts used in this study were
recomputed from the public JSONL files.
```

日本語の表示例:

```text
本研究はCLAPNQ（Rosenthal et al., 2025）を使用した。CLAPNQはNatural Questions
（Kwiatkowski et al., 2019）およびWikipediaに由来する。CLAPNQ配布物のApache License 2.0と、
Natural Questions DataのCC BY-SA 3.0を確認し、出典・License・変更内容を表示した。
```

論文の図表や長い本文を転載する場合は、Datasetの利用とは別に論文のCC BY 4.0条件を満たす。
単に結果を要約して引用する場合は、通常の学術引用を行う。

---

# 6. 本研究用SplitとData Leakage防止

## 6.1 公式Splitをそのまま最終評価に使わない理由

公式Test Answerは非公開である。公開Devは600件のみでAnswerableが300件のため、互いに異なる
Normal、Retrieval Failure、Distractorを各150件作るには不足する。また、実データ監査では、公開Trainと
Devの間に同じWikipedia Titleが91件存在した。

したがって、公開Train/DevのSource Splitを保持したまま、研究用Splitを別Fieldとして作る。

## 6.2 Group-aware Split

公開4,345件を結合し、`passages[0].title`をGroup Keyとして、同一Titleの全Recordを同じ研究用Splitへ
配置する。Answerable/Unanswerable比を可能な限り維持し、Seed 42で次を目標に分割する。

| 研究用Split | 目標比率 | 用途 |
|---|---:|---|
| Development | 65% | Loader、Prompt、Retriever、Pipeline開発 |
| Calibration | 10% | R/F/A重み、閾値、`top_k`等の固定 |
| Evaluation | 25% | 設定固定後の最終比較 |

Group Sizeのため厳密な比率にはならない。実数はManifestで報告する。Split作成Algorithmは、Recordの
内容やModel成績を見ず、Title、Answerability、Seedだけで決定する。

Title Groupingを適用しても、LLMがNQ質問・Wikipedia本文を事前学習で見ている可能性は残る。
これはLimitationsに明記し、絶対性能よりも同じQAに対する3方式の相対差を主要な解釈対象とする。

## 6.3 Leakage防止

- 研究用SplitはQA Annotation、Gold Label、Few-shot例を分離するためのものである。Full RAGでは全方式が
  同じ固定配布物の178,890 Passage Recordsを検索し、Evaluation質問のGold Passageも検索候補に含める。これは
  Retrieval Taskの要件でありLeakageではない。ただし、EvaluationのQrelやReferenceをRetrieverの
  学習・Parameter調整へ使用してはならない。
- `source_split`と`research_split`を別々に保存する。
- 同じTitleを複数の研究用Splitへ入れない。
- Evaluationの質問、Reference Answer、Gold PassageをFew-shot Promptへ入れない。
- Evaluation結果を見てPrompt、閾値、Weight、Retriever、`top_k`を調整しない。
- Gold Passage ID、Reference Answer、Selected Sentences、Answerability LabelをInference Stateへ渡さない。
- Gold Passageを直接Generatorへ渡す実験は`oracle_generation`としてFull RAGと分離する。
- Splitを作り直した場合は新しいDataset Versionとし、以前の結果を混在させない。

---

# 7. Internal Schema

## 7.1 QA Record

```json
{
  "record_id": "clapnq:c508d78:train:8045984229282682032:answerable",
  "source_dataset": "CLAPNQ",
  "source_revision": "c508d78d8c5c2eecbf172fcf5f789004206e11fb",
  "source_split": "train",
  "research_split": "development|calibration|evaluation",
  "source_id": "8045984229282682032",
  "source_title": "Love the One You're With",
  "question": "...",
  "reference_answers": ["..."],
  "selected_sentences_by_reference": [["...", "..."]],
  "is_answerable": true,
  "gold_passage_ids": ["..."],
  "provided_passage": null,
  "dataset_type": "normal|unanswerable|retrieval_failure|distractor",
  "derived_from_id": null,
  "derivation": null
}
```

Unanswerableでは`reference_answers=[]`、`gold_passage_ids=[]`とし、公式Annotationに含まれるRandom
Passageは`provided_passage`へ保存する。空Answer文字列を正解文字列として扱わない。

## 7.2 Retrieval Document

```json
{
  "passage_id": "827849752_115-357",
  "source_dataset": "CLAPNQ",
  "source_revision": "c508d78d8c5c2eecbf172fcf5f789004206e11fb",
  "title": "...",
  "text": "...",
  "text_sha256": "..."
}
```

## 7.3 Stable ID

Source NQ IDだけでAnswerableとUnanswerableの役割を推測せず、次を組み合わせる。

```text
clapnq:{revision_short}:{source_split}:{source_id}:{answerability}
```

Raw JSONLのLine番号、Raw Record SHA-256も保存する。Revision変更時に同じNQ IDの内容が同一だと
仮定しない。`source_line_index`は各Source File内の0始まりIndexとする。Raw Record SHA-256はJSONLの
行末`LF`または`CRLF`を除いた、UTF-8 JSON Bytesに対して計算する。JSONの再Serialize結果へHashを
計算せず、元配布RecordのByte表現を識別できるようにする。

## 7.4 Reference正規化

1. `output`をすべて保持する。
2. `skip=true`を評価Referenceから除外する。
3. `answer`が`null`、空白のみ、または大文字小文字を無視して`NA`なら除外する。
4. Answerableで有効Referenceが0ならValidation Errorにする。
5. Unanswerableは有効Referenceが0であることを確認する。
6. 複数Referenceに対する自動Metricは、原則として最大Scoreを使用する。
7. Selected Sentencesは対応するReferenceとのPairを崩さない。

---

# 8. 検索CorpusとRetriever

## 8.1 Canonical Corpus

固定配布物の178,890 Passage Recordsをすべて同じIndexへ投入する。質問に対応するTitleやProvided Passageだけへ検索範囲を
制限しない。BM25、Embedding Retrieval、RRFはいずれも同じPassage集合を使用する。

## 8.2 Gold Mapping

AnswerableではRetrieval Query TSVの`doc-id-list`をGold Passage IDとして評価する。

```text
retrieval_success@k = 1 if any gold_passage_id in top_k else 0
```

複数Gold Passageがある場合は、いずれかを取得すればRecall成功とする。GenerationのReference Answerが
特定のGold Passageにのみ対応する場合は、Passage-level Retrieval成功とAnswer Evidence充足を別に記録する。

UnanswerableではGold Passage IDを作らない。Random Provided PassageをGoldとしてRetrieval評価しない。

## 8.3 Hybrid Retrieval

- Keyword Retrieval: 英語Tokenizationを用いるBM25。
- Embedding Retrieval: 固定した英語またはMultilingual Embedding Model。
- Fusion: RRF。
- Optional Reranker: Calibrationで採否を決め、最終実験前に固定する。

保存する設定:

- BM25 Library、Version、Tokenizer、Stopword、Stemmer。
- Embedding Model名、Revision、Pooling、Normalization。
- Index LibraryとMetric。
- RRF定数。
- `top_k`、Candidate数、Reranker設定。
- Corpus Revisionと全Passage IDのHash。

---

# 9. Failure評価用Dataset

## 9.1 共通Rule

- Evaluation Splitだけから最終評価例を選ぶ。
- Normal、Retrieval Failure、DistractorのBase QA IDを重複させない。
- Candidate順、Seed、採否理由をModelの最終Answerを見る前に固定する。
- Baseline、Always Rewrite、Adaptive Recoveryで同一Manifestを使用する。
- `dataset_type`と、実行後に観測した`observed_failure_type`を分ける。

## 9.2 Normal QA

1. EvaluationのAnswerableを母集団にする。
2. Question Style、Answer Length、Passage Length、Source Titleの分布を取得する。
3. Seed 42で150件を抽出する。
4. 同じTitleへの偏りを避け、原則1 Title 1件とする。
5. Baselineが成功するかどうかを採否条件にしない。

## 9.3 Unanswerable QA

CLAPNQのUnanswerableは、NQ Annotatorが提示されたWikipedia Documentで回答なしと判断した質問である。
Corpus全体のどこにも答えがないことを保証するLabelではない。また、公式AnnotationのProvided Passageは
Random Passageであり、著者自身が一部には実際の答えが存在する場合を報告している。

構築手順:

1. EvaluationのUnanswerableをSeed 42で固定順に並べる。
2. 固定RetrieverのBM25、Embedding、Hybridそれぞれで上位Passageを取得する。
3. Provided Passage、上位Retrieval Passage、必要時Original NQ Documentを確認する。
4. 質問に答える根拠がCorpus内にあるかを判定する。
5. `corpus_unanswerable`を150件採用するまで固定順に監査する。
6. 除外例と理由をすべてManifestへ残す。

監査Label:

```text
unanswerable_audit:
  corpus_unanswerable
  answer_found_in_provided_passage
  answer_found_in_retrieved_corpus
  ambiguous_or_time_sensitive
  insufficient_evidence_for_judgment
```

Primary評価では`corpus_unanswerable`だけを使用する。その他はData品質分析として別報告する。

## 9.4 Retrieval Failure

目的は、初回検索でGold Passageを取得できない条件に対するQuery Rewriteの効果を測ることである。

1. Normal/Distractorと重複しないEvaluation Answerableを検索する。
2. 固定RetrieverのTop-kにGold Passageがない例を自然発生Failure候補とする。
3. 最大150件を固定する。150件未満なら実数を主結果として報告する。
4. 補助的に検索困難化質問を作る場合は、意味と正解が変わらないことを人手確認する。
5. 自然発生Failureと派生Failureを同じ平均へ混ぜない。
6. Query Rewrite後に成功した例だけを採用しない。

GoldはOffline評価にだけ使い、本番のFailure DiagnosisはR Scoreから判断する。

## 9.5 Distractor

1. 他Subsetと重複しないEvaluation Answerableを候補とする。
2. 異なるTitleからBM25またはEmbedding類似度の高いPassageをHard Negative候補にする。
3. Gold Answer文字列や同等の回答根拠を含む候補を除外する。
4. 人手または固定Ruleで誤根拠であることを確認する。
5. 最終ContextにGold Passageと1件以上のDistractorが残るようにする。
6. GoldがTop-kから落ちた例はRetrieval Failureへ分離する。
7. 150件を固定し、挿入位置、個数、Score、Passage ID、Seedを保存する。

---

# 10. 評価指標

## 10.1 Retrieval

- Recall@k。
- nDCG@10。
- MRRまたはGold Passage Rank。
- Query Rewrite前後のGold Passage到達率。

## 10.2 Answer Correctness

- Token-level Answer F1。
- ROUGE-L F1。
- Completenessを補うROUGE-1 Recall。
- 必要に応じて固定Model/PromptによるSemantic Correctness評価。

長文回答には複数の正しい表現があるため、Exact MatchをPrimary Metricにしない。複数Referenceがある
場合は最大Scoreを採用し、Micro/Macro集計方法を固定する。

## 10.3 Faithfulness

- Retrieved Contextに対するClaim Support Ratio。
- Gold Selected Sentencesに対するEvidence Coverage。
- Unsupported Claim RatioまたはHallucination Rate。
- AnswerとRetrieved PassageのROUGE-LはExtractiveness補助指標として使用する。

Faithfulnessが高くても、誤ったDistractorへ忠実な回答は正しくない。Answer Correctness、
Faithfulness、Answer Relevanceを独立して報告する。

## 10.4 Unanswerable

- Answerability Accuracy/F1。
- Unanswerable Recall。
- Answerableを誤って拒否するFalse Refusal Rate。
- Unanswerableへ具体的事実を生成するHallucination Rate。

表現一致だけで拒否判定せず、事前に固定したCanonical Labelと判定Ruleを使用する。

## 10.5 本研究固有指標

- Failure Detection F1。
- Recovery Success Rate。
- ConfidenceのECE。
- Average LLM Calls。
- Latency。
- Recovery前後の各Metric差。

---

# 11. ManifestとDirectory

```text
data/
├─ raw/clapnq/{revision}/              # 公式配布物、Git対象外
├─ processed/clapnq/{dataset_version}/
│  ├─ qa.jsonl
│  ├─ passages.jsonl
│  └─ split_report.json
└─ manifests/
   ├─ clapnq_source_manifest.json
   ├─ clapnq_split_manifest.json
   ├─ clapnq_unanswerable_audit.jsonl
   ├─ clapnq_eval_normal.jsonl
   ├─ clapnq_eval_unanswerable.jsonl
   ├─ clapnq_eval_retrieval_failure.jsonl
   └─ clapnq_eval_distractor.jsonl
```

Source ManifestにはRevision、取得日、License、File Hash、Byte数、Row数、Schemaを保存する。
Split ManifestにはGrouping Key、比率、Seed、Algorithm Version、各Split件数、Title重複検査結果を保存する。
派生ManifestにはBase ID、生成条件、Retriever Config Hash、Prompt/Model Revision、Seed、Gold/Distractor
Passage ID、監査結果を保存する。

---

# 12. 自動ValidationとTest

## 12.1 Source検証

- 公開Trainが3,745件、Devが600件である。
- Train Answerable/Unanswerableが1,954/1,791件である。
- Dev Answerable/Unanswerableが300/300件である。
- JSONL各行に`id`、`input`、`passages`、`output`がある。
- AnswerableのGold Passage IDがRetrieval Corpusに存在する。
- Corpus Passage IDが一意である。
- File HashがManifestと一致する。

## 12.2 正規化検証

- Answerableに有効Referenceが1件以上ある。
- `skip`、空Answer、`NA`を評価Referenceから除外する。
- UnanswerableのReference Answerは空Listである。
- Selected SentencesとReference Answerの対応を保持する。
- Stable IDとRaw Record Hashが全Recordにある。

## 12.3 Split検証

- 同じTitleが複数の研究用Splitに存在しない。
- Development/Calibration/Evaluation間でRecord IDが重複しない。
- Split作成が同じInput、Seed、Versionから再現できる。
- Answerability比と実数をReportできる。

## 12.4 Leakage検証

- Inference PromptにReference Answer、Gold Passage ID、Selected Sentencesが含まれない。
- Unanswerable LabelがGeneratorへ渡らない。
- Full RAGでAnnotation内Gold Passageを直接Contextへ入れない。
- Evaluation質問をFew-shot例に使用しない。
- 3比較方式でDataset、Corpus、Retriever、Generator、PromptのHashが一致する。

## 12.5 派生条件検証

- Normal/Retrieval Failure/DistractorのBase IDが重複しない。
- Retrieval Failureで初回Top-kにGold Passageがない。
- DistractorでGold Passageと検証済みHard NegativeがTop-kに共存する。
- Unanswerableは`corpus_unanswerable`監査を通過している。
- 派生例にSeed、元ID、生成条件、採否理由がある。

---

# 13. 既知のRiskとLimitations

- 英語Wikipedia Domainだけであり、日本語、行政文書、専門Domainへの一般化を直接実証しない。
- 1つのGold Passageに根拠が収まる例が中心で、Multi-document Synthesis評価には弱い。
- NQ質問とWikipedia PassageがLLMの事前学習に含まれる可能性がある。
- 公式DevはNQ Train由来であり、公式Splitだけでは独立性が十分でない。
- 公式Test Answerは非公開で、公開Dataだけでは公式Leaderboard相当の評価にならない。
- UnanswerableにAnswerが含まれる、または関連Passageが取得される例がある。
- Reference Answerは高品質だが、手動Annotationなので誤りや曖昧さを完全には排除できない。
- 回答は比較的Extractiveであり、完全にAbstractiveな回答生成を代表しない。
- Gold Answerと異なるが正しい回答が、文字列Metricで過小評価される可能性がある。
- CLAPNQのApache 2.0表示とNQ DataのCC BY-SA 3.0を併せて管理する必要がある。

本研究では、研究目的を「特定言語での有効性」ではなく「Text-based RAGにおける自己評価と
Failure別Recoveryの有効性」とする。ただし、CLAPNQだけを用いた結果から「言語に依存しないことを
実証した」とは主張しない。

---

# 14. 実装順序

1. 固定RevisionでCLAPNQ公開Dataを取得する。
2. Source ManifestとLicense Lineageを作成する。
3. Annotation LoaderとRetrieval Corpus Loaderを実装する。
4. Reference正規化とGold Passage対応を検証する。
5. Title Group-aware Splitを生成・固定する。
6. BM25、Embedding、RRFによるBaseline Retrieverを実装する。
7. CalibrationでRetriever、Prompt、R/F/A、閾値を固定する。
8. EvaluationからNormalとUnanswerable候補を固定する。
9. UnanswerableをCorpus-levelで監査する。
10. 固定RetrieverからRetrieval FailureとDistractorを構築する。
11. Baseline、Always Rewrite、Adaptive Recoveryを同じManifestで実行する。
12. Metric、Limitations、License表示を含む論文用Tableを出力する。

---

# 15. よくある質問

## Q1. Annotation内の`passages`をそのままGeneratorへ渡してよいか

Full RAG主実験では不可。Gold Passageを直接渡すとRetrievalを飛ばす。Retrieverから取得したPassageだけを
Generatorへ渡す。Gold Passageを与える実験はOracle Generationとして別に報告する。

## Q2. CLAPNQは完全なText-only Datasetか

本研究で使う最終AnnotationとRetrieval CorpusはTextで構成される。表・Listを元NQ候補から除外しており、
PDF画像やLayout解析は不要である。

## Q3. 公式DevをそのままTestとして使えるか

小規模な再現実験には使えるが、本研究の4条件を互いに異なるBase QAで各150件作るには不足する。
またTrainとのTitle重複があるため、本研究では公開Train/DevをTitle単位で再分割する。

## Q4. UnanswerableのProvided PassageはGold Passageか

違う。Gold Passageがないため元Documentからランダムに選ばれたPassageである。Retrieval RecallのGoldに
使用しない。

## Q5. 空AnswerはData破損か

Unanswerableでは期待される。Answerableでは`skip=true`等の無効Referenceが混ざるが、公開最終Dataの
各Answerable行には少なくとも1つ有効Referenceが残る。LoaderでReference単位にFilterする。

## Q6. CLAPNQを使えば言語非依存性を証明できるか

できない。英語での有効性を示せるだけである。「手法が日本語固有処理を前提としない」とは説明できるが、
言語横断性能の実証には別言語Datasetによる追加実験が必要である。

## Q7. Raw DatasetをGitHubへ置いてよいか

原則置かない。公式配布元から固定Revisionを取得するScriptとManifestを公開し、Raw本文の再配布を避ける。
再配布する場合はApache 2.0、CC BY-SA 3.0、Attribution、変更表示を確認する。

---

# 16. 論文引用

## 16.1 CLAPNQ

```bibtex
@article{rosenthal-etal-2025-clapnq,
  title = "{CLAP}nq: Cohesive Long-form Answers from Passages in Natural Questions for {RAG} systems",
  author = "Rosenthal, Sara and Sil, Avirup and Florian, Radu and Roukos, Salim",
  journal = "Transactions of the Association for Computational Linguistics",
  volume = "13",
  year = "2025",
  publisher = "MIT Press",
  url = "https://aclanthology.org/2025.tacl-1.3/",
  doi = "10.1162/tacl_a_00729",
  pages = "53--72"
}
```

## 16.2 Natural Questions

```bibtex
@article{kwiatkowski-etal-2019-natural,
  title = "Natural Questions: A Benchmark for Question Answering Research",
  author = "Kwiatkowski, Tom and Palomaki, Jennimaria and Redfield, Olivia and Collins, Michael and Parikh, Ankur and Alberti, Chris and Epstein, Danielle and Polosukhin, Illia and Devlin, Jacob and Lee, Kenton and Toutanova, Kristina and Jones, Llion and Kelcey, Matthew and Chang, Ming-Wei and Dai, Andrew M. and Uszkoreit, Jakob and Le, Quoc and Petrov, Slav",
  journal = "Transactions of the Association for Computational Linguistics",
  volume = "7",
  year = "2019",
  url = "https://aclanthology.org/Q19-1026/",
  doi = "10.1162/tacl_a_00276",
  pages = "452--466"
}
```

## 16.3 卒業論文での記述例

```text
本研究では、Full RAG Pipeline向けのLong-form QA DatasetであるCLAPNQ
（Rosenthal et al., 2025）を基盤Datasetとして使用した。CLAPNQはNatural Questions
（Kwiatkowski et al., 2019）のLong Answer質問とWikipedia Passageから構築され、
人手作成の長文回答、Gold Passage、Selected Evidence Sentences、および検索Corpusを含む。
本研究は公式Repository revision c508d78を2026年8月26日に取得し、公開Train/Devを
Wikipedia Title単位で再分割した。公式Test Answerは使用していない。
```

Method節またはAppendixには、研究用Split Seed、採用件数、Unanswerable監査、派生条件、Metric、
License表示を追記する。CLAPNQをそのまま使用したとだけ書き、再分割や派生加工を省略してはならない。

---

# 17. 実装開始前Checklist

- [x] CLAPNQを固定Revisionで取得した。
- [x] File Hash、件数、Schema、LicenseをSource Manifestへ保存した。
- [x] 公開Train 3,745件、Dev 600件を検証した。
- [x] Corpus 178,890 Passage RecordsとGold Passage対応を検証した。
- [x] 無効Referenceを除外し、Answerableに有効Answerが残ることを確認した。
- [x] Apache 2.0とCC BY-SA 3.0の表示を保存した。
- [ ] Title Group-aware SplitをSeed 42で固定した。
- [ ] Gold情報をInference Stateから分離した。
- [ ] Unanswerable候補をCorpus-levelで監査した。
- [ ] 4種類の評価Manifestを固定した。
- [ ] 3比較方式でDataset、Corpus、Model、Prompt、Seedが同一かTestした。
- [ ] 論文用Dataset統計、変更点、License、Limitationsを出力した。

---

# 18. 変更時に更新する場所

| 変更内容 | 更新対象 |
|---|---|
| Source Revision・License | 本書、Source Manifest、README、Hash |
| Split比率・Grouping | 本書、研究計画、Split Script、Test、Manifest |
| Corpus・Retriever | 本書、実装計画、Config、Index Manifest |
| Unanswerable監査 | 本書、監査Rule、Review Data、Manifest |
| Failure派生方法 | 本書、研究計画、生成Script、Manifest |
| 評価Metric | 研究計画、本書、評価実装、結果Schema |
| 引用・公開方法 | 本書、README、NOTICE、卒業論文 |
