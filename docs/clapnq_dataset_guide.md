# CLAPNQデータセット理解・Text-based RAG利用仕様書

## Version 2.0 — 2026年10月18日

[研究計画7.0](rag_research_plan.md)の正式テーマ変更に対応するDataset仕様書。
Source、License、Loader、内部Schema、Title単位Split、CorpusとPhase 6までの条件は維持する。
主実験はAnswerable QAの固定回答に対する評価順序と修復判断の比較へ変更する。
[旧Version 1.10](archive/clapnq_dataset_guide_v1_10.md)の四種類Failure Dataset、全R/F/A、原因分類、ECE中心の比較は必須工程から外す。

本書の第2〜8節は公式情報・実監査・Source/Schema運用の正本。研究目的と指標の最終的な定義は
[研究計画](rag_research_plan.md)、実装契約は[実装計画](rag_implementation_plan.md)、工程は[ロードマップ](research_roadmap.md)へそろえる。
新しい評価用Manifest、評価器、書換え、品質採点は未作成・未実装・未実施である。
公式情報と研究上の決定、実監査結果、未確定値を区別し、推論へ正解情報を渡さない。

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
| 公式Test | Access依頼への返信・Data提供がないため、本研究では使用しない |
| CLAPNQ-R1 | 品質条件が異なる補助Train Dataであるため、主実験には使用しない |

2026年8月26日に公式README記載の著者連絡先へTest Accessを依頼したが、2026年9月10日時点で返信も
Data提供もない。そのため、非公開Testの取得を待たず、公開Train/Dev 4,345件だけで研究を継続する。
この決定後に返信があった場合も、現行主実験のDatasetへ途中追加しない。利用を検討する場合は、現行結果と
混在させず、別Dataset Version・別実験として利用条件と評価目的を記録する。

## 1.3 新テーマで使用する対象

| Split | 用途 | 対象候補 |
|---|---|---|
| Development | 実装・採点基準作成・20〜30問のPilot | Answerable 1,465件 |
| Calibration | Judge/閾値/予算/最終Protocolの確認 | Answerable 225件。検索調整へ既に使用した履歴を保持 |
| 内部Evaluation | 凍結後の最終比較 | Answerable 564件から事前選定。公式Testではない |

本実験100〜200問程度は作業量の候補で、必要件数を保証しない。Pilotの発生率・推定精度・負担から確定する。
Unanswerable、検索失敗・Distractor専用Subsetは今回の必須対象から外す。既存QAやLabelは削除・書換えしない。
検索に自然発生するGold未取得を除かず、Gold未取得だけで回答不能と決めない。
主実験のAnswerabilityは対象選定だけに使い、Generator/Judge/修復Promptへ渡さない。

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

本研究で利用する範囲は公開TrainとDevの4,345件で、Answerable 2,254件、Unanswerable 2,091件である。
公式Testは使用しない。公開Train/Devから作る研究用Evaluation Splitは内部評価用であり、公式Testまたは
公式Leaderboard相当の評価とは区別する。

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

固定Corpus LoaderはZIPを展開せず`passages.tsv`をStreamingで読み、ZIP Entry、Header、列数、UTF-8、
空Field、Passage ID重複、期待件数を検証する。固定Dataでは全178,890件が1物理行のLogical Recordで、
空ID、空本文、空Titleは0件だった。Loaderは引用符付き改行を含む将来のTSVにも対応する。

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
- 非公開TestへのAccess。料金は記載されていないが著者への申請が必要であり、本研究ではAccess未取得のため
  使用対象外とする。
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

公式Test Answerは非公開であり、実データ監査では公開TrainとDevの間に同じWikipedia Titleが91件存在した。
開発・Calibration・最終評価をTitle単位で分離するため、固定した内部Splitを使用する。
旧四条件各150件の構築はテーマ変更後の分割理由や必須条件として扱わない。

したがって、公開Train/DevのSource Splitを保持したまま、研究用Splitを別Fieldとして作る。

## 6.2 Group-aware Split

公開4,345件を結合し、元の`passages[0].title`を保持する内部`source_title`をcasefold後にUnicode NFCへ
正規化した文字列をGroup Keyとして、同一Groupの全Recordを同じ研究用Splitへ配置する。
Answerable/Unanswerable比を可能な限り維持し、Seed 42で次を目標に分割する。

| 研究用Split | 目標比率 | 用途 |
|---|---:|---|
| Development | 65% | Loader、Prompt、Retriever、Pipeline開発 |
| Calibration | 10% | 検索条件（実施済み）と評価器・閾値・Protocolの確認 |
| Evaluation | 25% | 設定固定後の最終比較 |

Group Sizeのため厳密な比率にはならない。実数はManifestで報告する。Split作成Algorithmは、Recordの
内容やModel成績を見ず、Title、Answerability、Seedだけで決定する。

### 正規化と決定的Algorithm（Phase 3実装済み）

正規化は`unicodedata.normalize("NFC", source_title.casefold())`とする。原文Titleは変更しない。
原文Titleは3,799種類、正規化Groupは3,798件である。差は`The Dragon (Beowulf)`と
`The dragon (Beowulf)`で、同一Groupへ置く。以前のPowerShell集計では大小文字を区別せず3,798件と
数えていたため、原文Title数とGroup数を区別して記録する。大小文字差で別Titleを保守的にまとめる
可能性はあるが、QAやLabelは除外・変更せず、全方式に同じ条件を適用する。

Algorithm Versionは`title-nfc-casefold-stratified-greedy-sha256-v1`とする。

1. 正規化TitleでGroup化し、各Groupの総件数・Answerable件数・Unanswerable件数だけを数える。
2. Group総件数の降順で処理する。同じSizeでは`[seed, 正規化Title]`をUTF-8・Key辞書順・Compact JSON・
   LF終端でSerializeしたByte列のSHA-256昇順、さらに同点なら正規化TitleのUnicode辞書順とする。
3. Groupを追加したときに下記Jが最も減るSplitへ割り当てる。同点はDevelopment → Calibration →
   Evaluationの順とする。判断はFractionによる有理数演算とし、浮動小数点の丸めに依存しない。
4. Stable ID順に出力し、`research_split`だけを設定する。入力順や質問・回答・Goldの内容を割当判断に
   使わない。全割当をValidationしてから成果物を出力する。

```text
J = sum_s sum_d ((n[s,d] - ratio[s] * N[d]) / N[d]) ** 2
s: development / calibration / evaluation
d: 総件数 / Answerable件数 / Unanswerable件数
N[d]: 入力全体の件数。N[d]=0の次元は計算から除く
n[s,d]: 現在そのSplitに割り当てた件数
ratio[s]: 65/100、10/100、25/100
```

これはGroupを分割しないGreedy近似であり、比率の完全一致や大域的最適性は保証しない。
固定公開Dataの実数は次のとおりで、欠損・重複・原文Title/正規化GroupのSplit間重複は0である。

| Split | QA | 実比率 | Answerable | Unanswerable | 原文Title数 | Group数 |
|---|---:|---:|---:|---:|---:|---:|
| Development | 2,824 | 64.99% | 1,465 | 1,359 | 2,278 | 2,277 |
| Calibration | 434 | 9.99% | 225 | 209 | 434 | 434 |
| Evaluation | 1,087 | 25.02% | 564 | 523 | 1,087 | 1,087 |

Title Groupingを適用しても、LLMがNQ質問・Wikipedia本文を事前学習で見ている可能性は残る。
これはLimitationsに明記し、絶対性能よりも同じQAに対する3方式の相対差を主要な解釈対象とする。

## 6.3 Leakage防止

- 研究用SplitはQA Annotation、Gold Label、Few-shot例を分離するためのものである。Full RAGでは全方式が
  同じ固定配布物の178,890 Passage Recordsを検索し、Evaluation質問のGold Passageも検索候補に含める。これは
  Retrieval Taskの要件でありLeakageではない。ただし、EvaluationのQrelやReferenceをRetrieverの
  学習・Parameter調整へ使用してはならない。
- `source_split`と`research_split`を別々に保存する。
- 同じTitleを複数の研究用Splitへ入れない。
- 原文Titleだけでなく、casefold・NFC正規化したGroupのSplit間重複も0にする。
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
  "research_split": null,
  "source_id": "8045984229282682032",
  "source_line_index": 0,
  "source_record_sha256": "...",
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

Phase 2のBase QAでは`research_split=null`とし、Phase 3のTitle単位分割後に値を設定する。
`dataset_type`はBase Answerableを`normal`、Base Unanswerableを`unanswerable`とするが、Base
Unanswerableという値だけではCorpus全体で回答不能と確認済みであることを意味しない。主評価に使う
Unanswerableは後続のCorpus-level監査を別途通過させる。

`provided_passage`は`title`、`text`、`sentences`を持つObjectである。AnswerableのAnnotation Passageは
Gold Passage本文だが、Full RAGへの誤投入を防ぐため`provided_passage`へ複製せず`null`とし、評価用の
`gold_passage_ids`だけを保持する。

Stable IDは
`clapnq:{revision先頭7文字}:{source_split}:{source_id}:{answerable|unanswerable}`で生成する。
Research Splitや出力DirectoryをIDへ含めないため、Phase 3で再分割しても元QAの識別子は変化しない。

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

`text_sha256`は、TSV Parserが返した`text`をUTF-8へEncodeしたByte列のSHA-256である。元ZIP File自体の
同一性はSource ManifestのFile SHA-256で確認し、各Retrieval Unitの本文同一性は`text_sha256`で確認する。

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

## 7.5 Base QA JSONL

次のコマンドで、固定Sourceから内部QA Schemaを決定的に再生成する。

```powershell
uv run python scripts/build_clapnq_qa.py
```

出力先は`data/processed/clapnq/c508d78-base-v1/qa.jsonl`である。JSON ObjectのKey順、区切り、UTF-8、
LF終端を固定し、同じSourceから同じByte列とSHA-256を生成する。固定Dataの実生成結果は4,345 Records、
9,954,217 Bytes、SHA-256
`233800e4cafadec8ebfdf185e28f4e7eb26efa924d68e592735b24cb8b937209`である。Processed Dataは公式Sourceから
再生成できるためGitへCommitしない。

## 7.6 Retrieval Corpus JSONL

次のコマンドで固定Corpusを内部Document Schemaへ変換する。

```powershell
uv run python scripts/build_clapnq_corpus.py
```

出力先は`data/processed/clapnq/c508d78-base-v1/passages.jsonl`である。変換はStreamingで行い、同時にQA
Recordが参照する2,074 Unique Gold Passage IDの全件存在を検証する。固定Dataの実生成結果は178,890
Records、4,293 Unique Titles、156,262,889 Bytes、SHA-256
`c847751985c2f95987628800a3a8a12aa274da37dee088310f74b6bddb1ea103`である。同じ入力から2回生成して同じ
Hashになることを確認済みである。

---

## 7.7 研究用Split JSONLとManifest

Phase 2のBase QAを入力に、GPU・追加Libraryなしで次を実行する。

```powershell
uv run python scripts/split_clapnq.py
```

出力は`data/processed/clapnq/c508d78-split-v1/`の`qa.jsonl`、`development.jsonl`、
`calibration.jsonl`、`evaluation.jsonl`、`split_report.json`である。Base QA・Corpusを上書きしない。
割当済み全件QAのSHA-256は
`6913d7a37b1938e6649c3609aa0b71e63dd2c62e8a717a470b41aaf2e912601d`である。

Git管理する`data/manifests/clapnq_split_manifest.json`にはDataset/Algorithm Version、Source Revision、
Seed、正規化Rule、目標比率、実数、入力・全出力のSHA-256とByte数、SplitごとのStable ID、原文Titleと
正規化Groupの割当、欠損・重複・漏洩・Metadata保持のValidation結果を保存する。
絶対Pathと生成日時は含めず、別Directoryでも同じInput・Seed・Versionから同じByte列を再生成する。
JSON/JSONLはUTF-8・Key辞書順・LF終端であり、Git Checkout後のManifestのLFも`.gitattributes`で固定する。

公開Train/Devの件数・Revision・Stable ID・未割当Base状態を検証してから処理する。
既存成果物はByte一致なら再利用し、不一致なら上書きせず停止する。Seed等を変更する場合は新Version・
出力Directory・Manifestを使う。途中のI/O失敗は同じ条件で再実行し、全出力Hashを確認して完了とする。
検証用の再生成例は次のとおりである。

```powershell
uv run python scripts/split_clapnq.py --output-dir data/processed/clapnq/c508d78-split-v1-verification --manifest data/processed/clapnq/clapnq_split_manifest_verification.json
```

2026-10-06に別出力先で全5 FileとManifestのByte一致を確認した。Phase 3完了時点では
61 Tests成功・Skipなし、ruff問題なしだった。Phase 4完了後の全Testは86件成功・Skipなしである。

# 8. 検索CorpusとRetriever

## 8.1 Canonical Corpus

固定配布物の178,890 Passage Recordsをすべて同じIndexへ投入する。質問に対応するTitleやProvided Passageだけへ検索範囲を
制限しない。BM25、Embedding Retrieval、RRFはいずれも同じPassage集合を使用する。

## 8.2 Gold Mapping

AnswerableではRetrieval Query TSVの`doc-id-list`をGold Passage IDとして評価する。

```text
retrieval_success@k = 1 if any gold_passage_id in top_k else 0
```

複数Gold Passageがある場合は、いずれかを取得すれば質問単位の取得成功(Success@k)とする。
取得Gold数/全Gold数を表すGold Recall@kとは区別し、両方を保存する。GenerationのReference Answerが
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

## 8.4 Phase 4の具体的な検索条件

固定条件・実行手順・実測値は[`phase4_retrieval.md`](phase4_retrieval.md)による。
BM25はbm25s 0.3.12のLucene方式、k1=1.2/b=0.75、本文のみ、lower/Unicode単語Token、
Stopword/Stemmerなし。Embeddingは`sentence-transformers/all-MiniLM-L6-v2`、Revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`の公式quint8 AVX2 ONNX、CPU 6 Threads・Batch 1、
特殊Token込み256 Tokenで切詰め、Attention Mask Mean Pooling/L2正規化、384次元float32である。
検索はNumPyで全件Cosine内積、同点は原文Corpus順とする。初期Top-kは5で、Phase 6で最終条件を
Calibration固定する。Phase 4ではRRFは対象外。Phase 6の条件は第8.5節による。切詰め数とModel File Hashを記録する。

両Indexは同じ全Passage集合・順序・Gold対応を使う。検索APIは質問文字列だけを受け取り、
Reference/Gold/Selected Sentences/Answerability/Provided Passageを受け取らない。
Development AnswerableのSeed付きHash順先頭50問で開発用Recall/MRR/nDCG・速度を確認する。
Phase 4ではCalibration/Evaluationを検索性能調整に使わない。全QAのGold ID存在確認はIndexの整合性確認だけに使う。

2026-10-06にノートPCで両Indexを全178,890件生成し、2,074 Unique Gold IDsの欠損0を確認した。
同じDevelopment Answerable 50問のRecall@5はBM25 0.40、Embedding 0.62である。最終性能ではない。
共通Manifestの固定、BM25の別Directory再生成一致、Embeddingの実Corpusでの中断再開を確認し、
Gate 4を通過した。詳細・Hash・時間・MemoryはPhase 4文書による。

## 8.5 Phase 6のHybrid検索条件とCalibration

同じ両Indexを等重みRRFで統合する。候補50件/方式、RRF定数20、最終top-k=10、Rerankerなし。
1始まりの順位に対し`sum(1/(20+rank))`、未取得の方式の寄与は0、同点はCanonical Corpus順とする。
Passage IDで重複をまとめ、元順位・元Scoreは記録用に保持する。検索入力は元質問文字列のみである。

事前規則で候補20/50/100とRRF定数20/60/100の9組を、Calibration Answerable全225件で比較した。
Unanswerable 209件はGoldを持たないため正解Metricから除外した。固定Split Manifestと入力Hash・ID集合を照合し、
Evaluationは調整に使わない。nDCG@10を主に選定し、top-k=3/5/10からSuccess@10との差が5ポイント以内の最小数を選ぶ。
選定基準の意味、同点Rule、全結果は[`phase6_hybrid.md`](phase6_hybrid.md)による。

HybridのSuccess@10=0.7822はEmbeddingと同じで、nDCG@10=0.5317はEmbeddingの0.5519を下回った。
Hybridによる精度改善の結果として扱わない。選定条件の実検索は225/225件で探索結果と一致した。
成功率とGold Recallは今回の単一Goldでは一致するが、複数Gold時は別指標である。
Phase 4の既存Reportの`recall_at_k`はGold Recallの定義を保持し、過去数値を書き換えない。

Config/Protocolと`data/manifests/phase6_calibration_report.json`、`phase6_hybrid_manifest.json`に条件を保存した。
これらと共通Corpus・Index・Hybrid実装Hashの一致を推論時に確認する。生成に使用したContextは取得Top-10と区別する。
最終Model・Embedding・Context条件等の変更時は影響を確認し、必要なCalibration/派生Datasetを新条件で再固定する。

# 9. 新テーマの実験対象と派生Record

## 9.1 選定と固定回答

対象は研究用SplitのAnswerable QA。通常の固定Hybrid検索と元順序で生成した回答を固定する。
ID選定Rule・Seedを結果を見る前に保存し、成功例・反転例だけを最終対象へ採用しない。
既存5問のSmokeは新テーマのPilotではない。Runtimeエラー、引用だけ、拒否、Claimなしを区別して記録する。
実験選定の正解Metadataと、質問・取得文書だけを含むInference入力を分離する。

## 9.2 文書順序と同一順序対照

`used_context`の本文・Title・Passage IDを固定し、配列順だけを変える。取得全文と混同しない。
本文Hash・文書集合・初回回答Hash・固定Claim Hashが全条件で同じことを検証する。
元/逆/Shuffleの順序IDと、同一順序の反復番号は別に保存する。
入力超過時は条件ごとに切詰めず、理由を記録する。最終の適格条件とFallbackはEvaluation前に固定する。

## 9.3 正解根拠と位置Label

Selected SentencesはReferenceごとの対応を保持する。代替の根拠集合を無条件に合体させない。
空Annotation・照合不能・代替支持を記録し、Goldの文字列一致と意味上の根拠充足を区別する。
根拠位置・支持分散はOfflineの条件別分析用であり、Judge/修復器へGoldの位置を教えない。

## 9.4 対象外とする旧派生条件

四種類の各150件固定、Corpus-level Unanswerable監査、人工Distractor作成、原因分類Labelは今回の主実験の必須条件ではない。
旧手順は保存版第9節に残す。将来採用するなら別VersionでSource・生成条件・監査を記録する。
Unanswerableの元LabelがCorpus全体の回答不能を保証しないという注意は維持する。

---

# 10. 評価指標と独立品質

## 10.1 検索・文字列Metric

既存のGold Success@k、Recall、nDCG等は基盤の説明用。検索改善は主研究質問にしない。
長文ReferenceとのF1/ROUGEは補助にできるが、文字列一致だけでYを決めない。

## 10.2 制御用F

初回回答だけから固定したClaimを、実使用Contextに対して検証する。
Fはsupported数/固定Claim数。Scoreは正答確率ではない。
Claimなしや失敗を満点/0点へ変換しない。独立品質の正解にも使わない。
初期τ=0.7、F>=τで採用、F<τで一回書換え。採点不能は初回保持Fallbackを別記録。

## 10.3 判断の揺れ

主指標は質問内の有効な固定ペアで採用/書換えが異なる割合を求めた質問平均と、順序群−反復群の差。
補助として少なくとも一度判断が反転した質問の割合を示す。試行数・異なる順序数への依存を明記する。
同じ質問の試行を独立QAへ水増ししない。

## 10.4 主品質Label

Y=1は、質問の必須要点、重大誤りなし、実使用Contextでの事実の支持を全て満たす回答。
Y=0は不完全・誤答・根拠外情報・不適切な拒否等。それ自体を判定できなければindeterminateと理由を記録する。
研究者本人が条件/段階/Scoreを隠した無作為順の候補を、Referenceと根拠で確認する。
自己評価のClaimや理由は品質採点の正解に流用しない。単独採点の制約を明記する。
初回Y0/書換えY1を組にして1→1、1→0、0→1、0→0を報告する。
初回誤答を全て修復可能と仮定しない。

## 10.5 品質と費用への影響

修復なし、常時Answer Rewrite、評価条件別判断は同じ初回/書換え候補から選択する。
正答悪化は全対象あたりと初回正答あたり、改善見逃しは全対象あたりと0→1例あたりを区別する。
評価器の不正出力・採点不能と、書換え失敗のFallbackを品質と費用へ反映する。
Calls/Token/Latencyには抽出・評価・補助・再試行を含める。Cacheによる実験共用を運用費用0としない。
実収集費用、方式別経路費用、Offline採点費用を分ける。

## 10.6 判定不能・統計・分母

全対象数、有効Trial、両群有効な共通QA、品質判定可能QA、エラー・不適格・判定不能の件数と理由を記録する。
品質の未知を除いた対応比較に加え、未知を良い/悪い側へ振った感度を報告する。
分母0を0%としない。元質問/Title単位の依存と、共通初回を持つ群の対応を維持して95%信頼区間を求める。
主比較と閾値・少数の条件別分析を最終評価前に固定する。詳細は研究計画第7節による。
旧原因分類Macro-F1、旧CのECE、旧Query Rewrite比較は主指標から外す。

---

# 11. Manifestと保存先

Source/Split/検索/生成の既存ManifestとRaw/Processed Dataは変更しない。
新実験用Recordは`data/runs/order_sensitivity/{study_version}/`へ分離する計画で、まだ生成していない。
Sample/固定Trace/Claim/Judge Trial/書換え候補/独立品質/分析Manifestの契約は実装計画第3節による。
全Recordを質問・候補Hash・Protocol Versionで結び、既存Manifestを上書きしない。
Raw Data、Model、Index、Runの本文をGitへ追加しない。公開範囲とLicense表示を確認して成果物を整理する。

---

# 12. ValidationとTest

Source件数・Schema・無効Reference・Gold対応・Stable ID・Split間重複0・再生成Hashの既存検証は維持する。
新実験では次を実装し、実DataのPilotと分けて確認する。

- 推論へのGold/Reference/Answerability/Y漏洩がない。
- 順序以外の文書内容と固定回答・Claimが一致し、再Packingしない。
- 既知ID・Claim対応・JSON・Label・F計算・閾値等号・採点不能Fallbackを検証する。
- 固定書換え、盲検Export/Import、四遷移、共通QA、分母0、品質未知、費用の共用補正を確認する。
- Source/既存BaselineのRegression、再開・Hash差停止を確認する。

新Testは未実装。Phase 6の135件成功を新研究のTest結果と混同しない。

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
- Fによる採用/修復の境界は設計上のRuleであり、正解確率や真の原因を保証しない。
- 固定書換え候補の比較は、その修復方式・Seedの下での起動判断の効果に限定される。
- 人手の独立評価にも主観や作業量の制約があるため、基準、理由、確認数、判定不能数を記録する。
- CLAPNQのApache 2.0表示とNQ DataのCC BY-SA 3.0を併せて管理する必要がある。

本研究の対象は、Text-based RAGの自己評価における根拠提示順序への感度と修復判断への影響である。
CLAPNQだけを用いた結果から、言語に依存しないことを実証したとは主張しない。

---

# 14. 実装順序

Phase 1〜6は完了済み。新Phase 7以降は[ロードマップ](research_roadmap.md)を正本とする。
旧四条件Datasetや全R/F/Aの実装を次工程の前提にしない。

---

# 15. よくある質問

## Q1. Annotation内の`passages`をそのままGeneratorへ渡してよいか

Full RAG主実験では不可。Gold Passageを直接渡すとRetrievalを飛ばす。Retrieverから取得したPassageだけを
Generatorへ渡す。Gold Passageを与える実験はOracle Generationとして別に報告する。

## Q2. CLAPNQは完全なText-only Datasetか

本研究で使う最終AnnotationとRetrieval CorpusはTextで構成される。表・Listを元NQ候補から除外しており、
PDF画像やLayout解析は不要である。

## Q3. 公式DevをそのままTestとして使えるか

本研究では開発用の例と最終評価を分け、Title単位で固定した内部Splitを使う。
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

# 17. 現在の確認状況

- [x] 固定Revision、Source/Schema/件数、License Lineageを検証した。
- [x] QA/Corpus/Gold ID対応とTitle単位Splitを固定した。
- [x] 共通検索・初回生成と実入力/回答保存まで動作確認した（Phase 6）。
- [x] 新テーマのData運用と研究/実装計画を更新した。
- [ ] 新しい対象選定と固定Trace/Claim/Judge TrialのManifestを作成した。
- [ ] 新評価器/修復器に正解が漏れないことを実装Testで確認した。
- [ ] 新テーマのPilotと独立品質採点を完了した。
- [ ] 最終Protocolを凍結してEvaluationを実施した。
- [ ] 論文用統計・欠測・Limitations・License表示を出力した。

Corpus-level Unanswerable監査は未実施だが、新テーマの主実験の必須Gateではない。

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
