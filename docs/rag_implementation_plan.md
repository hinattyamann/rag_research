# 自己制御型RAG実装計画書

## Version 7.5

## 外部実装依頼用 最終実装仕様書

本書はVersion 7.4を基礎とし、Annotation Loader、Reference正規化、Raw Record Hashの計算規則を
具体化した版である。
CLAPNQの取得、研究用Split、Corpus、Unanswerable監査、派生Dataset、Licenseおよび引用方法は
`docs/clapnq_dataset_guide.md`を正本とする。

------------------------------------------------------------------------

# 1. システム構成

    main.py

     ↓

    LangGraph Workflow

     ↓

    Retrieval
     ↓
    Generation
     ↓
    Evaluation
     ↓
    Confidence
     ↓
    Decision
     ↓
    Recovery


LangGraph Workflowとは、LLMアプリケーションの処理を、ノードとエッジで表現するフレームワークのこと。
ノードが、RetrievalからRecoveryまでとなる。エッジは処理の流れを指す。

------------------------------------------------------------------------

# 2. Directory Structure

    src/
    ├ graph/
    ├ retrieval/
    ├ generation/
    ├ evaluation/
    ├ recovery/
    | ├ diagnosis.py
    | ├ router.py
    | ├ query_rewrite.py
    | ├ constrained_generation.py
    | └ answer_rewrite.py
    ├ utils/

    configs/
    ├ config.yaml
    └ prompts.yaml

    data/
    ├ raw/clapnq/          # 公式配布物、Git管理対象外
    ├ processed/clapnq/    # 再生成可能な正規化Dataと研究用Split
    └ manifests/           # Dataset revision、License、件数、hash、生成条件

    scripts/
    ├ prepare_clapnq.py
    ├ inspect_clapnq.py
    ├ split_clapnq.py
    └ audit_unanswerable.py

    experiments/
    ├ baseline.py
    ├ always_rewrite.py
    └ adaptive.py

    docs/
    ├ rag_research_plan.md
    ├ rag_implementation_plan.md
    └ clapnq_dataset_guide.md

    tests/
    logs/
    results/

------------------------------------------------------------------------

# 3. API仕様

## Retriever

``` python
retrieve(question:str)->list
```

責務: 関連文書取得。

------------------------------------------------------------------------

## Generator

``` python
generate(question:str, context:list)->str
```

責務: 回答生成。

------------------------------------------------------------------------

## Evaluator

``` python
evaluate(answer:str, documents:list)->dict
```

返却:

``` json
{
"R":0.0,
"F":0.0,
"A":0.0
}
```

------------------------------------------------------------------------

## Confidence

``` python
calculate_confidence(R,F,A)->float
```

## Confidence Controller

Confidence ScoreはDecision Nodeへの入力として利用する。

役割:

- 回答採用判断
- Recovery起動判断

を担当する。


------------------------------------------------------------------------

## Recovery

``` python
recover(failure_type,state)
```

------------------------------------------------------------------------

## RecoveryManager

Failure Typeに応じて適切なRecovery処理を選択する。


API:

recover(
    failure_type,
    state
)


Input:

failure_type:
    Retrieval Failure
    Generation Failure
    Answer Relevance Failure


state:
    question
    documents
    answer


Output:

recovered_state


内部処理:

if failure_type == "Retrieval Failure":

    query_rewrite()


elif failure_type == "Generation Failure":

    constrained_generation()


elif failure_type == "Answer Relevance Failure":

    answer_rewrite()

------------------------------------------------------------------------

# 4. Config仕様

config.yaml:

``` yaml
model:
  generator: qwen2.5-14b
  evaluator: qwen2.5-7b

retrieval:
  top_k: 5

confidence:
  threshold: 0.7

dataset:
  name: CLAPNQ
  source_repository: https://github.com/primeqa/clapnq
  source_revision: c508d78d8c5c2eecbf172fcf5f789004206e11fb
  annotation_source: PrimeQA/clapnq
  corpus_source: PrimeQA/clapnq_passages
  research_split: development
  split_group_key: source_title
  split_ratios: [0.65, 0.10, 0.25]
  seed: 42
```
------------------------------------------------------------------------

## Failure Threshold設定

config.yamlでFailure判定閾値を管理する。

例:

confidence:
  threshold:0.7

failure:
  retrieval_threshold:0.5
  faithfulness_threshold:0.5
  relevance_threshold:0.5

各評価値が対応する閾値を下回った場合、Failure Diagnosisを実行する。

------------------------------------------------------------------------

## Hybrid Retrieval実装仕様

Retrieval Moduleでは以下の2種類の検索を実行する。

### Keyword Retrieval

方式:
BM25

役割:
- 固有名詞検索
- 数値情報検索
- 完全一致検索


### Embedding Retrieval

方式:
Vector Similarity Search

役割:
- 言い換え対応
- 意味的類似検索


### Fusion

両検索結果はRRFにより統合する。

RRFにより、片方の検索方式のみで高順位となった文書も評価対象とする。


------------------------------------------------------------------------

# Adaptive Recovery詳細設計

Adaptive Recoveryでは、Failure Diagnosis結果に基づき、
異なるRecovery Moduleを呼び出す。

処理フロー:

Evaluation

↓

Failure Diagnosis

↓

Recovery Router

↓

Failure Type別Recovery

↓

Re-Generation

↓

Re-Evaluation


## Retrieval Failure Recovery

### 判定条件

Retrieval Quality Score(R)が閾値以下の場合。

### 処理

Query Rewriteを実行する。

Flow:

Question

↓

Query Rewrite

↓

再Retrieval

↓

Generation


目的:

検索されやすい質問表現へ変換し、
適切な根拠文書取得を目指す。


---

## Generation Failure Recovery

### 判定条件

Faithfulness Score(F)が閾値以下の場合。

### 処理

制約付き再生成を実行する。

追加制約例:

- Retrieved Documentsのみを根拠として利用する
- 根拠が存在しない情報を生成しない
- 不明な場合は不明と回答する


Flow:

Documents

↓

Constraint Prompt

↓

Regeneration


---

## Answer Relevance Failure Recovery

### 判定条件

Answer Relevance Score(A)が閾値以下の場合。

### 処理

Answer Rewriteを実行する。

Flow:

Original Answer

↓

Question Alignment

↓

Answer Refinement


目的:

質問意図に適合した回答へ修正する。
------------------------------------------------------------------------


# 5. Prompt仕様

管理:

-   generation_prompt(回答生成用)
-   faithfulness_prompt(忠実性評価用)
-   relevance_prompt(回答関連性評価用)
-   rewrite_prompt(Recovery処理の修正用)

------------------------------------------------------------------------

## Faithfulness Prompt

Input:

-   Context
-   Answer

Output:

``` json
{
"claims":[],
"score":0.0
}
```

------------------------------------------------------------------------

# 6. Data Schema

## CLAPNQ取得元

CLAPNQは以下を参照して取得する。

- 公式Repository: https://github.com/primeqa/clapnq
- Hugging Face Annotation: `PrimeQA/clapnq`
- Hugging Face Retrieval Corpus: `PrimeQA/clapnq_passages`
- 論文: https://aclanthology.org/2025.tacl-1.3/
- Natural Questions配布ページ: https://ai.google.com/research/NaturalQuestions/download
- Dataset詳細仕様: `docs/clapnq_dataset_guide.md`

初期基準Revisionは`c508d78d8c5c2eecbf172fcf5f789004206e11fb`とする。Dataset取得時には、
取得日、GitまたはHugging Face Revision、Split別件数、File Hash、License LineageをManifestへ
記録する。`main`のような可変Revisionだけに依存しない。

CLAPNQはApache License 2.0として公開され、元Natural Questions DataはCC BY-SA 3.0で公開される。
本研究では両方のLicense情報を保持し、CLAPNQ論文とNQ論文の両方を引用する。Raw Dataは
`data/raw/clapnq/{revision}/`へ保存してGit管理対象外とする。公開時の詳細はDataset Guideに従う。

## CLAPNQ前処理

公開Source SplitをRaw Metadataとして保持する。

| Source Split | Answerable | Unanswerable | 合計 |
|---|---:|---:|---:|
| Train | 1,954 | 1,791 | 3,745 |
| Dev | 300 | 300 | 600 |

公式Test 601件はAnswerが非公開であるため、著者から正式に取得しない限り処理対象にしない。

処理フロー:

CLAPNQ取得・Revision固定

↓

File Hash、Schema、件数、License Lineage検証

↓

Annotation JSONLとRetrieval TSVのLoad

↓

無効Reference除外・内部Schema正規化

↓

Gold Passage IDと固定配布物の178,890 Passage Recordsの対応検証

↓

Wikipedia Title単位のGroup-aware研究用Split生成

↓

DevelopmentでPipeline開発

↓

CalibrationでRetriever・Prompt・閾値固定

↓

Evaluation QAとFailure評価用派生Record生成

Annotation内の`passages`はAnswerableではGold Passage、UnanswerableではRandom Provided Passageである。
Full RAG主実験では、いずれもGeneratorへ直接渡さず、公式CorpusからRetrieverが取得したTop-kだけを
Contextにする。Gold Passageを直接与える実験は`oracle_generation`として分離する。

### Annotation Fieldの役割

- `id`: 元Natural Questions ID。Source IDとして保持する。
- `input`: 質問本文。内部`question`へ変換する。
- `passages[].title`: Wikipedia Title。Group-aware Splitに使用する。
- `passages[].text`: AnswerableではGold Passage、UnanswerableではRandom Provided Passage。
- `passages[].sentences`: Passageの文分割。
- `output[].answer`: 人手作成Reference Answer。
- `output[].selected_sentences`: Reference作成に使われたGold Evidence。
- `output[].meta`: Annotation Round、Annotator、`skip`等の監査情報。

Answerableの`output`には複数Referenceや`skip=true`の空Answer、Devには`NA`が含まれる。
Loaderは無効Referenceを除外するがRaw値を保持し、Answerableの各Recordに少なくとも1つ有効Referenceが
残ることを検証する。Unanswerableの`null`または空文字Answerは内部で空Listへ統一する。

## 内部Dataset Schema

CLAPNQの元Fieldを正規化し、以下の内部Schemaへ変換する。

``` json
{
  "record_id":"clapnq:c508d78:train:source-id:answerable",
  "source_dataset":"CLAPNQ",
  "source_revision":"c508d78d8c5c2eecbf172fcf5f789004206e11fb",
  "source_split":"train|dev",
  "research_split":"development|calibration|evaluation",
  "source_id":"",
  "source_line_index":0,
  "source_record_sha256":"",
  "source_title":"",
  "question":"",
  "reference_answers":[],
  "selected_sentences_by_reference":[],
  "is_answerable":true,
  "gold_passage_ids":[],
  "provided_passage":null,
  "dataset_type":"normal|unanswerable|retrieval_failure|distractor",
  "derived_from_id":null,
  "derivation":null
}
```

Retrieval用Document Schema:

``` json
{
  "passage_id":"",
  "source_dataset":"CLAPNQ",
  "source_revision":"c508d78d8c5c2eecbf172fcf5f789004206e11fb",
  "title":"",
  "text":"",
  "text_sha256":""
}
```

元Fieldとの主な対応:

- `id` → `source_id`。
- `input` → `question`。
- `passages[0].title` → `source_title`。
- 有効な`output[].answer` → `reference_answers`。
- 各`output[].selected_sentences` → 対応を保った`selected_sentences_by_reference`。
- Retrieval Query TSVの`doc-id-list` → Answerableの`gold_passage_ids`。
- Unanswerableの`passages[0]` → `provided_passage`。Goldとは扱わない。

無効Referenceは`skip=true`、`null`、空文字、`NA`とする。Raw `output`を失わず保持し、評価用Viewで
除外する。複数Referenceへの文字列Metricは最大Scoreを用いる。

Stable IDはDataset Revision、Source Split、NQ ID、Answerabilityを組み合わせて生成し、Line番号と
Raw Record Hashも保存する。Line番号は各Source File内の0始まりIndexとし、Raw Record HashはJSONLの
行末を除いたUTF-8 JSON BytesからSHA-256で生成する。Research Splitを作り直してもSource Record IDは
変えず、Split ManifestのVersionを変更する。

## 正解情報の分離

以下のFieldは評価およびDataset監査でのみ使用し、Retriever、Generator、Query Rewriteへ渡す
Inference Stateには含めない。

- `reference_answers`
- `selected_sentences_by_reference`
- `gold_passage_ids`
- `is_answerable`
- `dataset_type`
- `derived_from_id`
- Unanswerable監査Label

これにより、Gold Passage、Answerability、派生条件をPromptへ漏洩させない。

## Failure Dataset Metadata

Failure原因評価のため、`dataset_type` と派生元情報を保持する。

- Normal QA: Evaluation SplitのAnswerableからSeed 42で150件を抽出
- Unanswerable QA: Evaluation SplitからCorpus-level監査を通過した150件を抽出
- Retrieval Failure: 固定RetrieverのTop-kにGold PassageがないAnswerableから最大150件を抽出
- Distractor: Gold Passageと検証済みHard Negativeを共存させた150件を抽出

派生Datasetは、同一入力とSeedから再生成できることを要件とする。

Retrieval Failureが150件未満なら実数を採用する。派生した検索困難化質問を使う場合は、自然発生例と
別Manifest・別集計にする。Unanswerableは固定候補順で監査し、回答根拠を発見した例、曖昧例、
時点依存例を除外して理由を記録する。

Log:

``` json
{
  "dataset_id":"",
  "split":"",
  "question":"",
  "answer":"",
  "retrieved_document_ids":[],
  "R":0.0,
  "F":0.0,
  "A":0.0,
  "confidence":0.0,
  "failure_type":"",
  "recovery_count":0,
  "model_name":"",
  "config_hash":"",
  "latency_seconds":0.0,
  "llm_calls":0
}
```

------------------------------------------------------------------------

# 7. Test仕様

## Unit Test

対象:

-   CLAPNQ Annotation/Corpus Loader
-   Dataset Schema変換
-   Reference正規化
-   Title Group-aware Split
-   Retrieval
-   Evaluation
-   Confidence

CLAPNQ関連Test条件:

-   公開Source件数がTrain 3,745、Dev 600である
-   Answerable/Unanswerable件数がTrain 1,954/1,791、Dev 300/300である
-   AnswerableのGold Passage IDが公式Corpusに存在する
-   無効Reference除外後も各Answerableに有効Answerが残る
-   正規化後の有効Reference数がTrain Answerable 2,667件、Dev Answerable 475件である
-   重複する有効Answerと空Selected Sentencesを順序どおり保持できる
-   UnanswerableのReference AnswerとGold Passage IDが空である
-   同一Wikipedia Titleが複数の研究用Splitに出現しない
-   同一Seedから同一のSplitとFailure評価用Subsetを再生成できる
-   RetrieverおよびGeneratorへGold情報、Answerability、Dataset Typeが渡らない
-   Unanswerable監査結果と除外理由が記録される

## Integration Test

対象:

-   LangGraph workflow
-   CLAPNQ取得からCorpus Load、Research Split、Retrieval、GenerationまでのPipeline

## Experiment Test

対象:

-   Baseline
-   Always Rewrite
-   Adaptive

3方式ではRetriever、Generator、Datasetを固定する。

変更する要素はRecovery制御のみとする。

これにより、Adaptive Recovery機構そのものの効果を評価する。

Evaluation Splitを用いた最終実験では、事前に固定したDataset Manifest、Config、Prompt、
Model Revisionを使用する。Evaluation結果を確認した後の設定変更は別実験として記録する。

------------------------------------------------------------------------

# 8. Error Handling

対象:

-   Empty Context
-   Retrieval Failure
-   LLM Timeout
-   JSON Parse Error

方針:

-   Retry
-   Error Log保存
-   実験継続可能性確保

------------------------------------------------------------------------

# 9. 実装計画

【完了済み】
研究テーマ・仮説・実装計画の作成
GitHub・uv・Codex環境の整備
CLAPNQの調査と詳細仕様書の作成
        ↓
────────────────────────────
【Phase 1】CLAPNQを取得・検証する
        ↓
公式Repositoryを固定Revisionで取得
Annotation・Retrieval Corpus・Query TSVをLoad
件数・Hash・Schema・License Lineageを検証
        ↓
【Gate 1】
使用したSourceを完全に再現できる
        ↓
────────────────────────────
【Phase 2】CLAPNQ Loaderと内部Schemaを実装する
        ↓
Annotation Loader
Retrieval Corpus Loader
無効Reference除外
Source Manifest
Stable ID
        ↓
【Gate 2】
QA、Reference、Gold Passage、Corpusの対応を検証できる
        ↓
────────────────────────────
【Phase 3】研究用Splitを固定する
        ↓
公開Train/Devを結合
        ↓
Wikipedia Title単位でGroup化
        ↓
Answerabilityを層別しSeed 42で
Development/Calibration/Evaluationへ分割
        ↓
【Gate 3】
Title LeakageのないSplit Manifestが完成
        ↓
────────────────────────────
【Phase 4】検索CorpusとIndexを構築する
        ↓
固定配布物の178,890 Passage RecordsをCanonical CorpusとしてLoad
        ↓
BM25 IndexとEmbedding Indexを構築
        ↓
Gold Passage対応とLeakageを検証
        ↓
【Gate 4】
質問から検索可能な共通Indexが完成
        ↓
────────────────────────────
【Phase 5】開発用Baseline RAGを作る
        ↓
Question
→ Embedding Retrieval
→ Top-k Passage
→ LLMによる回答生成
        ↓
検索性能・回答性能・Leakageを確認
        ↓
【Gate 5】
検索から回答生成までEnd-to-Endで動作
        ↓
────────────────────────────
【Phase 6】Hybrid Retrievalを実装する
        ↓
BM25 Retrieval
        ＋
Embedding Retrieval
        ↓
RRFによる検索結果統合
        ↓
Calibrationでtop-k・検索設定を調整
        ↓
実験で共通使用するRetrieverを固定
        ↓
【Gate 6】
実験用Baseline RAGが完成
        ↓
────────────────────────────
【Phase 7】Failure評価用Datasetを完成させる
        ↓
Evaluation Answerableから
Normal 150件を固定
        ↓
Evaluation Unanswerableを固定順で
Corpus-level監査し150件を固定
        ↓
固定Retrieverを使って
Retrieval Failure候補を生成
        ↓
Hard Negativeによる
Distractor候補を生成
        ↓
意味・正解・誤根拠を人手確認
        ↓
4種類のDataset Manifestを固定
        ↓
Normal
Unanswerable
Retrieval Failure
Distractor
        ↓
【Gate 7】
Failure検出・Recoveryを評価できる
        ↓
────────────────────────────
【Phase 8】R/F/A自己評価を実装する
        ↓
Retrieval Quality（R）
Faithfulness（F）
Answer Relevance（A）
        ↓
C = 0.25R + 0.50F + 0.25A
        ↓
Calibrationで評価Prompt・閾値を調整
        ↓
【Gate 8】
回答品質を数値化できる
        ↓
────────────────────────────
【Phase 9】Failure Diagnosisを実装する
        ↓
Rが低い
→ Retrieval Failure
        ↓
Fが低い
→ Generation Failure
        ↓
Aが低い
→ Answer Relevance Failure
        ↓
【Gate 9】
失敗の有無と原因を分類できる
        ↓
────────────────────────────
【Phase 10】Adaptive Recoveryを実装する
        ↓
Retrieval Failure
→ Query Rewrite・再検索
        ↓
Generation Failure
→ 根拠制約付き再生成
        ↓
Answer Relevance Failure
→ Answer Rewrite
        ↓
再評価
        ↓
最終回答
        ↓
【Gate 10】
最大1回のRecoveryを含む提案手法が完成
        ↓
────────────────────────────
【Phase 11】比較実験を固定する
        ↓
使用Model・Prompt・Datasetを固定
Retriever・Generatorを固定
閾値・Seed・Configを固定
        ↓
Baseline RAG
Always Rewrite RAG
Adaptive Recovery RAG
        ↓
変更するのはRecovery制御だけ
        ↓
【Gate 11】
公平な比較実験を実行できる
        ↓
────────────────────────────
【Phase 12】最終実験を行う
        ↓
Development
→ 開発・動作確認
        ↓
Calibration
→ Parameter・閾値調整
        ↓
設定を完全に固定
        ↓
Evaluation
→ 最終評価
        ↓
Evaluation結果を見て同じ実験を再調整しない
        ↓
【Gate 12】
最終実験結果が確定
        ↓
────────────────────────────
【Phase 13】結果を分析する
        ↓
Answer F1
ROUGE-L・ROUGE-1 Recall
Retrieval Recall@k・nDCG@10
Answerability F1
Faithfulness
Hallucination Rate
Failure Detection F1
Recovery Success Rate
ECE
LLM Calls
Latency
        ↓
Dataset種類別・Question Style・Answer Length別に分析
        ↓
失敗例・Recovery成功例・悪化例を分析
        ↓
Sensitivity Analysis・必要な追加実験
        ↓
仮説H1・H2・H3を検証
        ↓
【Gate 13】
研究Questionに結論を出せる
        ↓
────────────────────────────
【Phase 14】卒業論文を完成させる
        ↓
背景・関連研究
研究目的・仮説
CLAPNQ、研究用Split、Unanswerable監査
提案手法
実装
実験条件
結果
考察
Limitations
結論
        ↓
Code・Config・Manifest・結果を整理
再現手順をREADMEへ記載
        ↓
指導教員からFeedback
        ↓
修正・最終提出
        ↓
────────────────────────────
【卒業研究完了】
