# 自己制御型RAG実装計画書

## Version 7.0

## 外部実装依頼用 最終実装仕様書

本書はVersion
6.0を基礎に、外部開発者が質問なく実装できる粒度まで詳細化した最終仕様書である。

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

Dataset:

``` json
{
"question":"",
"answer":"",
"documents":[],
"type":"normal"
}
```

Log:

``` json
{
"question":"",
"answer":"",
"R":0.0,
"F":0.0,
"A":0.0,
"confidence":0.0,
"failure_type":"",
"recovery_count":0
}
```

## Failure Dataset Metadata

Failure原因評価のため、DatasetにはFailure Typeを保持する。

例:

{
"question":"",
"answer":"",
"documents":[],
"type":"Retrieval Failure"
}


これにより、Failure別評価およびRecovery成功率計算を可能にする。

------------------------------------------------------------------------

# 7. Test仕様

## Unit Test

対象:

-   Retrieval
-   Evaluation
-   Confidence

## Integration Test

対象:

-   LangGraph workflow

## Experiment Test

対象:

-   Baseline
-   Always Rewrite
-   Adaptive

3方式ではRetriever、Generator、Datasetを固定する。

変更する要素はRecovery制御のみとする。

これにより、Adaptive Recovery機構そのものの効果を評価する。

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

Phase1: Baseline RAG

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
