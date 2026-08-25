# 自己制御型RAG実装計画書

## Version 7.1

## 外部実装依頼用 最終実装仕様書

本書はVersion
7.0を基礎に、使用データセットであるJDocQAの取得、前処理、分割、Text-only利用方針を追加した版である。

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
    ├ raw/jdocqa/          # Git管理対象外
    ├ processed/jdocqa/    # 再生成可能な中間データ
    └ manifests/           # Dataset revision、件数、hash、生成条件

    scripts/
    ├ prepare_jdocqa.py
    └ inspect_jdocqa.py

    experiments/
    ├ baseline.py
    ├ always_rewrite.py
    └ adaptive.py

    docs/
    ├ rag_research_plan.md
    └ rag_implementation_plan.md

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
  name: JDocQA
  source: shunk031/JDocQA
  split: train
  text_only: true
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

## JDocQA取得元

JDocQAは以下を参照して取得する。

- 公式Repository: https://github.com/mizuumi/JDocQA
- Hugging Face Dataset: `shunk031/JDocQA`
- 論文: https://aclanthology.org/2024.lrec-main.830/

AnnotationのLicenseはCC BY-SA 4.0である。Datasetの派生物および研究成果では
原論文を引用する。元PDFは各配布元の利用条件にも従い、`data/raw/jdocqa/` に保存して
Git管理対象外とする。

Dataset取得時には、取得日、Hugging FaceまたはGit RepositoryのRevision、
Split別件数、ファイルHashをManifestへ記録する。`main` のような可変Revisionだけに
依存せず、実験で使用したDataset状態を再現可能にする。

## JDocQA前処理

JDocQAの公式Splitを保持する。

| Split | QA件数 |
|---|---:|
| Train | 9,290 |
| Validation | 1,134 |
| Test | 1,176 |

同一の `pdf_name` が複数Splitへ混入していないことを前処理時に検証する。

処理フロー:

JDocQA取得

↓

Dataset RevisionおよびLicense情報記録

↓

PDF単位・Page単位のText抽出

↓

埋め込みTextを優先し、取得できないPageはOCR Textを利用

↓

Text正規化およびChunk分割

↓

Split別Retrieval Corpus構築

↓

Text-only適格性監査

↓

QA RecordおよびFailure評価用派生Record生成

PDFページ画像、Bounding Box、Layout情報はRetrieverおよびGeneratorへ入力しない。
OCRはText取得の前処理としてのみ使用し、OCR精度そのものは本研究の評価対象外とする。

JDocQAが提供する回答根拠PageやBounding Boxのみから検索Contextを作ると、正解情報が
Retrieverへ漏洩する。そのため、Corpusは対象Splitに属する全PDFの全文Pageから構築し、
正解情報は評価処理へ分離する。

## 内部Dataset Schema

JDocQAの元Fieldを正規化し、以下の内部Schemaへ変換する。

``` json
{
  "id":"",
  "source_dataset":"JDocQA",
  "source_revision":"",
  "split":"train|validation|test",
  "question":"",
  "reference_answer":"",
  "answer_type":"yes_no|factoid|numerical|open_ended",
  "is_answerable":true,
  "is_multi_page":false,
  "pdf_name":"",
  "reference_pages":[],
  "dataset_type":"normal|unanswerable|retrieval_failure|distractor",
  "derived_from_id":null,
  "derivation_seed":null,
  "distractor_document_ids":[]
}
```

Retrieval用Document Schema:

``` json
{
  "document_id":"",
  "pdf_name":"",
  "page_number":0,
  "chunk_index":0,
  "text":"",
  "text_source":"embedded|ocr",
  "split":"train|validation|test"
}
```

元Fieldとの主な対応:

- `question` → `question`
- `normalized_answer` を優先し、必要時は `answer` または `original_answer` → `reference_answer`
- `answer_type` → 内部の4種類の `answer_type`
- `no_reason` → `is_answerable` および `is_multi_page`
- `pdf_name` → `pdf_name`
- `question_page_number` → `reference_pages`
- `text_from_pdf`、`text_from_ocr_pdf` → Text抽出結果の検証およびFallback

`no_reason` はUnanswerable、Answerable、Multi-pageの状態を表し、複合状態を含み得るため、
Loaderで正規化して2つのBooleanへ分離する。

## 正解情報の分離

以下のFieldは評価およびDataset監査でのみ使用し、Retriever、Generator、
Query Rewriteへ渡すStateには含めない。

- `reference_answer`
- `reference_pages`
- `reason_of_answer_bbox`
- `derived_from_id`
- 正解文書を直接特定できる評価用Label

これにより、正解Pageや回答根拠を検索結果として直接与えるData Leakageを防止する。

## Failure Dataset Metadata

Failure原因評価のため、`dataset_type` と派生元情報を保持する。

- Normal QA: JDocQAのText-onlyで回答可能なAnswerable QA
- Unanswerable QA: JDocQAのUnanswerable QA
- Retrieval Failure: Answerable QAから決定的手順で作成し、元QA IDとSeedを保存
- Distractor: 追加した文書ID、選択方法、Seedを保存

派生Datasetは、同一入力とSeedから再生成できることを要件とする。

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

-   JDocQA Loader
-   Dataset Schema変換
-   Text正規化およびChunk分割
-   Retrieval
-   Evaluation
-   Confidence

JDocQA関連Test条件:

-   公式Split件数がTrain 9,290、Validation 1,134、Test 1,176である
-   同一 `pdf_name` が複数Splitに出現しない
-   同一Seedから同一のFailure評価用Subsetを再生成できる
-   RetrieverおよびGeneratorへ正解情報が渡らない
-   埋め込みTextが空の場合にOCR TextへFallbackできる
-   Text-only対象外と判定した理由が記録される

## Integration Test

対象:

-   LangGraph workflow
-   JDocQA取得からCorpus構築、Retrieval、GenerationまでのPipeline

## Experiment Test

対象:

-   Baseline
-   Always Rewrite
-   Adaptive

3方式ではRetriever、Generator、Datasetを固定する。

変更する要素はRecovery制御のみとする。

これにより、Adaptive Recovery機構そのものの効果を評価する。

Test Splitを用いた最終実験では、事前に固定したDataset Manifest、Config、Prompt、
Model revisionを使用する。Test結果を確認した後の設定変更は別実験として記録する。

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

# 9. 実装Phase

Phase0: 環境構築

Phase1: JDocQA前処理およびBaseline RAG

実装内容:

- JDocQA Loader
- Dataset revisionおよびLicense Manifest
- PDF全文Text抽出とOCR Fallback
- Page単位Metadata保持とChunk分割
- Text-only適格性監査
- Split別Retrieval Corpus
- Embedding Retrievalを用いたBaseline RAG

完了条件:

JDocQAの公式Splitを保持したまま、正解情報をRetrieverへ漏洩させず、
質問から関連Chunkを検索して回答生成まで実行できる。

Phase2: Hybrid Retrieval

Phase3: Evaluation

Phase4: Confidence制御

Phase5:
Adaptive Recovery

実装内容:

- Failure Diagnosis
- Recovery Router
- Query Rewrite
- Constrainted Regeneration
- Answer Rewrite

完了条件:

Failure Typeに応じて適切なRecovery処理が実行され、
再評価まで完了できる。

Phase6: 比較実験

完了条件:

3方式比較可能。
