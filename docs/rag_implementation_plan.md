# 自己制御型RAG実装計画書

## Version 7.15

## 外部実装依頼用 最終実装仕様書

本書はVersion 7.14の制御・比較・独立品質評価仕様を維持し、Phase 6のHybrid検索と検索Calibrationの
選定結果を反映した版である。Phase 5のGenerator条件を維持する。
Decision Rule、
Always Rewrite、独立品質評価等のModule・Config・Test・比較実験はまだ実装・実施していない。
CLAPNQの取得、研究用Split、Corpus、Unanswerable監査、派生Dataset、Licenseおよび引用方法は
`docs/clapnq_dataset_guide.md`を正本とする。

研究の立ち位置・貢献候補・有用性・関連論文は
[先行研究との関係・本研究の立ち位置と有用性](related_research_positioning.md)を参照する。
原因別修復やR/F/Aの評価観点自体を新規性とはせず、独立品質と総推論コストによって制御の効果・限界を検証する。

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
evaluate(question:str, answer:str, documents:list)->dict
```

ここでのEvaluatorは制御用の自己評価であり、Reference、Gold、Answerability Labelを入力しない。
元の質問を必須とし、Query Rewrite後もAnswer Relevanceは元の質問との適合性を評価する。
実験後の独立品質評価は別の処理・保存先とし、Dataset Guide第10.6〜10.10節に従う。

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
    low_confidence


state:
    question
    search_query
    documents
    answer
    recovery_action


Output:

recovered_state


内部処理:

if failure_type == "Retrieval Failure":

    query_rewrite()


elif failure_type == "Generation Failure":

    constrained_generation()


elif failure_type == "Answer Relevance Failure":

    answer_rewrite()

elif failure_type == "low_confidence":

    # 原因Labelを変更せず、Decision Ruleが選択したrecovery_actionを実行する
    execute_selected_recovery_action()

------------------------------------------------------------------------

# 4. Config仕様

以下は後続Phaseを含む構成例で、全項目の実装済みを意味しない。例示の14B/7Bは最終Modelの決定ではない。
現行Phase 5は`configs/phase5.yaml`、`configs/prompts.yaml`、
`data/manifests/phase5_generation_manifest.json`の条件を使う。

config.yaml（将来構成の例）:

``` yaml
model:
  generator: qwen2.5-14b
  evaluator: qwen2.5-7b

retrieval:
  top_k: 5

confidence:
  weights: [0.25, 0.50, 0.25]  # R, F, A
  threshold: 0.7

failure:
  retrieval_threshold: 0.5
  faithfulness_threshold: 0.5
  relevance_threshold: 0.5

recovery:
  max_recoveries: 1
  max_answer_generations: 2
  low_confidence_policy: weighted_deficit
  tie_break_order: [retrieval, generation, answer_relevance]

dataset:
  name: CLAPNQ
  source_repository: https://github.com/primeqa/clapnq
  source_revision: c508d78d8c5c2eecbf172fcf5f789004206e11fb
  annotation_source: PrimeQA/clapnq
  corpus_source: PrimeQA/clapnq_passages
  source_splits: [train, dev]
  official_test_policy: excluded_no_access
  research_split: development
  split_group_key: source_title
  split_ratios: [0.65, 0.10, 0.25]
  seed: 42
```

上記は将来作成するConfigの例であり、現時点ではConfig Fileと推論基盤は未実装である。
重み、採用閾値0.7、個別閾値0.5、Recovery上限は承認済みの初期条件とする。Model名とtop-kは
導入済み・Calibration済みの条件を意味しない。変更時には仕様・Config・Test・実験条件を更新する。
------------------------------------------------------------------------

## Failure Threshold設定

config.yamlでFailure判定閾値を管理する。

例:

confidence:
  threshold: 0.7

failure:
  retrieval_threshold: 0.5
  faithfulness_threshold: 0.5
  relevance_threshold: 0.5

個別Failureは厳密な`<`で判定する。0.5はFailureに含めず、C=0.7は個別Failureがなければ採用する。

## Decision Ruleと低Confidence時のRouting

R/F/Aは0〜1の制御用Scoreとし、C = wR*R + wF*F + wA*Aを計算する。
以下の疑似Codeの順序で判断する。実行Codeはまだ存在しない。

```text
if R < retrieval_threshold:
    failure_type = retrieval_failure
    recovery_action = query_rewrite
elif F < faithfulness_threshold:
    failure_type = generation_failure
    recovery_action = constrained_generation
elif A < relevance_threshold:
    failure_type = answer_relevance_failure
    recovery_action = answer_rewrite
elif C < confidence_threshold:
    failure_type = low_confidence
    deficits = [wR*max(0, confidence_threshold-R),
                wF*max(0, confidence_threshold-F),
                wA*max(0, confidence_threshold-A)]
    recovery_action = 最大のdeficitに対応する処理（同点はR → F → A）
else:
    failure_type = none
    recovery_action = none
```

低Confidenceの原因を3種類のFailureへ読み替えず、`failure_type`と`recovery_action`を別々に保存する。
R=F=A=0.6ではC=0.6となり、重み付き不足分0.025/0.050/0.025から`constrained_generation`を選ぶ。
Cが0.7以上でも個別FailureがあればRecoveryを起動する。補助Ruleは原因を保証する診断ではなく、
Calibrationで挙動を確認して最終Evaluation前に固定するHeuristicである。

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

選択したRecovery処理（回答候補を1つ作る）

↓

修正後回答

↓

Re-Evaluation

Acceptなら初回回答を返し、Recoveryした場合は修正後回答を返す。初回・修正後の選別はしない。
再評価後に同じ採用条件を満たさなければ`unresolved=true`として記録して終了する。Recoveryは
最大1回で、閾値だけを理由とする強制拒否や追加Recoveryは行わない。


## Retrieval Failure Recovery

### 判定条件

Retrieval Quality Score(R)が閾値未満の場合。または低Confidence Ruleがこの処理を選んだ場合。

### 処理

Query Rewriteを実行する。

Rewriteの入力は元の質問だけとし、自己評価結果、初回回答、Reference、Gold情報を渡さない。
`question`は元のまま保持し、`search_query`だけをRewrite結果へ変更する。再検索は同じCorpus・
Retriever・top-kを使い、初回Contextと結合せず、新しい検索結果から元の質問への回答を生成する。

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

上流の個別Failureがなく、Faithfulness Score(F)が閾値未満の場合。
または低Confidence Ruleがこの処理を選んだ場合。

### 処理

制約付き再生成を実行する。

元の質問と初回と同じ取得Contextを使う。検索結果は変更しない。

追加制約例:

- Retrieved Documentsのみを根拠として利用する
- 根拠が存在しない情報を生成しない
- 不明な場合は不明と回答する

### 実装前に具体化する事項（未決定）

Phase 5のBaseline Promptは既に上記の制約を含む。そのため、追加制約を同じ文言で繰り返すだけでは
初回生成との違いを十分に説明できない。Recovery実装前に、初回から変更するPrompt・生成設定を
固定し、通常の再生成との差と測定したい効果を文書化する。
現在の入力は元の質問と同じContextである。初回回答・診断Feedbackの追加は候補であり、
採用する場合は理由と影響を明示し、研究計画・入出力仕様・共通Prompt・比較条件を同時に更新する。
この追記では入力仕様を変更せず、Recoveryを実装済みとも扱わない。


Flow:

Documents

↓

Constraint Prompt

↓

Regeneration


---

## Answer Relevance Failure Recovery

### 判定条件

上流の個別Failureがなく、Answer Relevance Score(A)が閾値未満の場合。
または低Confidence Ruleがこの処理を選んだ場合。

### 処理

Answer Rewriteを実行する。

入力は元の質問・取得Context・初回回答とする。この呼び出し自体が2回目の回答生成であり、
後段に別の再生成を追加しない。Query Rewrite等の補助呼び出しは回答生成回数とは別に数える。

Flow:

Original Answer

↓

Question Alignment

↓

Answer Refinement


目的:

質問意図に適合した回答へ修正する。

## Always Rewriteの実行仕様

全方式で共通の初回検索・初回回答を作った後、Always Rewriteは制御用Scoreに関係なく
Query Rewrite → 再検索 → 再生成を1回実行する。2回目の回答を最終回答とし、初回との選別はしない。
Adaptiveの検索Recoveryと同じQuery Rewrite Module、Model、Prompt、生成設定を使う。
元の質問の保持、検索Contextの置換、Gold情報の分離も同じ仕様とする。

Baselineは初回回答を返す。Adaptiveだけが制御用自己評価から起動の有無・修正方法を選ぶ。
初回結果を共有・再利用する場合も、各方式の推論コストには初回処理を1回ずつ含める。

## 推論コストとOffline評価

推論に必要なLLM呼び出し・Token・Latencyを集計する。Adaptiveの自己評価、Query Rewrite、Claim抽出、
根拠検証等も含め、実際の呼び出し回数を保存する。回答生成2回という上限を総LLM Callsの上限と
解釈しない。全方式の独立品質採点はOffline評価として別集計する。

Baseline・AlwaysのCをECE用に取得する自己評価も、制御には使わずOffline評価に含める。
Adaptiveの制御用Scoreをそのまま初回/最終ECEへ使用し、同じ条件の評価を他方式にも適用する。
推論とOffline評価の区分・実行条件を実験ConfigとLogへ保存する。
------------------------------------------------------------------------


# 5. Prompt仕様

管理:

-   generation_prompt(回答生成用)
-   faithfulness_prompt(忠実性評価用)
-   relevance_prompt(回答関連性評価用)
-   rewrite_prompt(Recovery処理の修正用)

Query Rewrite、制約付き再生成、Answer RewriteのPromptは区別して管理する。Query Rewrite Promptは
AlwaysとAdaptiveで共通にする。共通資産のHashと各方式が実際に呼び出したPromptの履歴を記録する。
独立評価用の判定基準・Promptは制御用Promptと分離し、主Labelは人手確認で確定する。

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

公式Test 601件は非公開Dataを必要とし、2026年8月26日のAccess問い合わせに対して2026年9月10日時点で
返信およびData提供がないため、本実装の処理対象から除外する。Loader、Manifest、Split処理、実験Configは
公開Train/Dev 4,345件だけを入力とし、Test Accessを実装開始または最終実験の前提にしない。将来Dataを
受領した場合も現行Dataset Versionへ追加せず、別Versionの追加実験として実装・利用条件を再定義する。

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
  "research_split":null,
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

Phase 2のBase QA生成時点では、`research_split`は未割当のため`null`とする。Phase 3でTitle単位の
Group-aware Splitを固定した後に`development|calibration|evaluation`を設定する。Base QAの
`dataset_type`はAnswerableを`normal`、Unanswerableを`unanswerable`とする。ただし、後者は
Corpus-level Unanswerable監査の通過を意味しない。`retrieval_failure`と`distractor`は固定Retrieverと
派生条件を確定する後続工程でのみ設定する。

Unanswerableの`provided_passage`は次の構造で、公式Annotationの値を保持する。

``` json
{
  "title":"",
  "text":"",
  "sentences":[]
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

`passages.tsv.zip`はDiskへ展開せず、ZIP Entry `passages.tsv`をCSV/TSV ParserでLogical Record単位に
Streaming Loadする。ZIP内のFile構成、Header、列数、UTF-8、空ID・本文・Title、Passage ID重複、件数を
検証する。`text_sha256`はTSV Parse後の`text`をUTF-8へEncodeしたByte列から計算し、Retrieverへ渡す
本文とHash対象を一致させる。

DocumentはUTF-8、Key辞書順、不要な空白なし、LF終端で
`data/processed/clapnq/c508d78-base-v1/passages.jsonl`へStreaming Serializeする。一時Fileへの書き込みが
完了し、2,074 Unique Gold Passage IDの全件存在を確認した後だけ出力先を置換する。

元Fieldとの主な対応:

- `id` → `source_id`。
- `input` → `question`。
- `passages[0].title` → `source_title`。
- 有効な`output[].answer` → `reference_answers`。
- 各`output[].selected_sentences` → 対応を保った`selected_sentences_by_reference`。
- Retrieval Query TSVの`doc-id-list` → Answerableの`gold_passage_ids`。
- Unanswerableの`passages[0]` → `provided_passage`。Goldとは扱わない。

Retrieval Query TSVは`answers`内の引用符付き改行を含むため、物理行ではなくCSV Parserが返すLogical
Record単位でLoadする。QueryのLine IndexはHeaderを除くLogical Recordの0始まりとする。Annotationとは
`source_split`、`is_answerable`、`source_id`で1対1に結合し、質問文も完全一致することを検証する。
AnswerableはGold Passage ID 1件、Unanswerableは空Listとする。

無効Referenceは`skip=true`、`null`、空文字、`NA`とする。Raw `output`を失わず保持し、評価用Viewで
除外する。複数Referenceへの文字列Metricは最大Scoreを用いる。

Stable IDはDataset Revision、Source Split、NQ ID、Answerabilityを組み合わせて生成し、Line番号と
Raw Record Hashも保存する。Line番号は各Source File内の0始まりIndexとし、Raw Record HashはJSONLの
行末を除いたUTF-8 JSON BytesからSHA-256で生成する。Research Splitを作り直してもSource Record IDは
変えず、Split ManifestのVersionを変更する。

Base QAのStable ID形式は
`clapnq:{revision先頭7文字}:{source_split}:{source_id}:{answerable|unanswerable}`とする。内部Recordは
UTF-8、Key辞書順、不要な空白なし、LF終端のJSONLへ決定的にSerializeし、Base Dataset Version
`c508d78-base-v1`の`qa.jsonl`として生成する。

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
- 独立品質Label Y、独立Failure Label、Claim判定、評価理由

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
  "recovery_action":"none",
  "recovery_count":0,
  "search_query":"",
  "answer_generation_count":1,
  "unresolved":false,
  "model_name":"",
  "config_hash":"",
  "latency_seconds":0.0,
  "llm_calls":0
}
```

上記は将来のLog例であり、現行実装の出力ではない。初回・修正後を区別して、質問、検索Query、
取得文書ID、回答、R/F/A、C、採用条件の成立、処理履歴を保存する。未計測Scoreは0で埋めず未計測と
区別する。方式ごとの推論LLM Calls・Token・LatencyとOffline評価コストも分離する。

独立評価RecordはInference Stateと別に保存し、Run/QA/回答段階のID、Y、複数Failure Label、代表原因、
Gold取得の有無、Context根拠充足、Claim本文・判定・根拠箇所、判定理由、判定不能理由、評価基準の
Versionを保持する。元質問・回答・Contextが同一なら評価を再利用し、比較時のQA対応は失わない。

------------------------------------------------------------------------

# 7. Test仕様

## Phase 3の実装と成果物

Moduleは`src/rag_research/data/clapnq_split.py`、CLIは`scripts/split_clapnq.py`である。
Phase 2の`c508d78-base-v1/qa.jsonl`だけを入力とし、Raw再取得・GPU・追加依存Libraryを必要としない。

```powershell
uv run python scripts/split_clapnq.py
```

原文Titleを保持し、casefold後にUnicode NFCへ正規化したTitleをGroup Keyとする。
固定Algorithmの目的関数と同点RuleはDataset Guide第6.2節、Manifestの内容は第7.7節に従う。
割当はTitle・Group内Answerability数・Seedだけで決まり、質問・回答・Gold・Model成績を参照しない。

出力Directoryは`data/processed/clapnq/c508d78-split-v1/`で、全件の`qa.jsonl`、各Split名のJSONL、
`split_report.json`を生成する。全QAをStable ID順でSerializeし、`research_split`以外のFieldを変更しない。
`data/manifests/clapnq_split_manifest.json`へ入力・出力Hash、条件、割当、実数、Validationを記録する。
JSON/JSONLはUTF-8・Key辞書順・LF終端とし、Manifestの改行は`.gitattributes`でも固定する。

公開Train/Devの4区分件数、固定Revision、Stable ID、Base QA状態を検証してから分割する。
出力前に欠損・重複・Title/GroupのSplit間重複と全Metadata保持を検証する。
全出力の競合を事前確認し、同じByte列なら再利用、異なる場合は上書きせず停止する。
各Fileは同じDirectory内の一時Fileへ書き終えてからHard Linkで原子的に公開し、Manifestは最後に公開する。
出力一式全体を1つのTransactionとしては扱わない。途中でI/O障害が起きた場合は同じ条件で再実行し、
全出力の存在・HashとManifestを確認して完了判定する。

Seed等を変える分割は新しいDataset Versionと出力先・Manifestを使う。
CLIは`--input`、`--output-dir`、`--manifest`、`--seed`、`--dataset-version`を受け付ける。
Seed 42以外を`c508d78-split-v1`として生成することは拒否する。CLIは公開4,345件の件数検証を省略できない。

実測はDevelopment 2,824件、Calibration 434件、Evaluation 1,087件で、正規化Group重複0である。
別出力先での再生成もByte単位で一致した。`tests/data/test_clapnq_split.py`に、混在・不均等Group、
表記差、入力順非依存、回答内容非依存、異常入力、欠損・重複・漏洩・Metadata改変、出力保護、
再生成・実データを確認する18 Testsを追加した。Phase 3完了時点で全体61 Tests成功・Skipなし、ruff問題なし。

## Phase 4の実装と固定条件

実装・CLI・再開条件・実測結果は[`phase4_retrieval.md`](phase4_retrieval.md)に記録する。
Index Versionは`c508d78-retrieval-v1`、共通Corpusは全178,890件である。本文のみを検索対象とし、
QAのGold・Reference・Answerability等は検索入力へ渡さない。Return値はPassage ID・Title・本文・
Source Revision・Score・Rankで、ScoreはConfidenceや正解確率ではない。

BM25はbm25sのLucene方式、k1=1.2、b=0.75、lower、Unicode単語Token、Stopword/Stemmerなし。
Embeddingは`sentence-transformers/all-MiniLM-L6-v2`の固定Revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`、公式quint8 AVX2 ONNX、CPU 6 Threads・Batch 1、
最大256 Token、Attention Mask Mean Pooling、L2正規化、384次元float32である。
NumPyのmmapとBlock内積で全件Cosine検索し、同ScoreはCanonical Corpus順に返す。
Token切詰め・量子化の影響を実験条件として扱い、3方式で同じ確定Retrieverを共有する。

Index File Hash、Model File Hash、Library Version、Corpus/ID順HashをManifestへ保存し、
完成済みIndexは上書きしない。Embeddingは条件・完了Vector領域Hashが一致するcheckpointだけから
再開する。Developmentの固定Answerable 50問をSmoke検証に使い、Calibration/Evaluationの性能は
ここで測定しない。最終Parameterの調整・固定とRRFはPhase 6で行う。

2026-10-06にノートPCで両Indexを全件生成し、Gold欠損0、同じDevelopment 50問での検索と
共通Manifest固定を検証した。BM25は別Directoryで全FileのByte再現を確認し、Embeddingは
60,349件から実Corpusで再開して完了した。Gate 4通過。回答生成の条件は次節を参照する。

## Phase 5の開発用Baseline条件

元質問→固定Embedding Top-5→ローカルLLM生成1回をLangGraphの2ノードで実装した。
Stateは元質問、取得文書、時間、生成記録だけを持ち、正解情報は外のOffline確認へ分離する。
GeneratorはQwen2.5-3B-Instruct-GGUF Q4_K_M、固定Revision、llama.cpp b11433 Windows CPU。
合計4,096/出力512/本文各512 Token、6 Threads、Temperature 0/Seed 42、Batch 128、重み再配置なし。
実GGUF TokenizerとChat Templateで入力予算を確認し、数えたToken IDsで生成を要求する。

CLIは`scripts/prepare_generation.py`と`scripts/run_baseline.py`。Model/Runtimeは公式Hashで検証し、
既存Runを上書きしない。取得全文/使用Context、Prompt/Hash、回答、Token、生成要求数、Latency、
100ms間隔のPython/Server RSSを保存する。Timeout、空回答、予期しない切詰め、出力上限到達はErrorにし、
暗黙に再試行しない。`status=ok`は実行成功であり、回答の正しさを意味しない。

固定Development Answerable 3問/Unanswerable 2問のEnd-to-Endが完了し、Gate 5を通過した。
Gold/Reference確認は生成後に別保存する。Phase 5時点ではCalibration/Evaluation、独立品質Y/Failureの正解付け、
ECE/Hallucination集計、自己評価/Recoveryは未実施。詳細は[`phase5_baseline.md`](phase5_baseline.md)による。

## Phase 6のHybrid検索と固定条件

`retrieval/hybrid.py`に等重みRRFを実装し、`calibration.py`と`scripts/calibrate_retrieval.py`で
固定Calibration全件のHash・Record IDを確認して検索条件を選定した。自己評価・回答品質の調整ではない。
候補50件/方式、RRF定数20、top-k=10。Missing Rankは寄与0、重複はPassage IDでまとめ、同点はCorpus行順とする。
Calibrationの候補・選定基準は測定前に`configs/phase6_calibration.yaml`へ固定した。

選定結果は`configs/phase6.yaml`、`data/manifests/phase6_calibration_report.json`と
`phase6_hybrid_manifest.json`に保存した。生成設定はPhase 5と共通で、共通Corpus/両Index/Modelを変更していない。
Inferenceは固定条件・Protocol・Report・Hybrid実装Hashを検証し、QA正解情報を読み込まない。
`scripts/run_baseline.py`の既定ConfigはPhase 6。Phase 5は`--config configs/phase5.yaml`で実行できる。
検索CLIには`--kind hybrid`を追加し、元順位・元Scoreと統合Scoreを返す。
Generation入力は元質問と取得Contextで、検索信号はPromptへ含めない。

Calibration Answerable 225件、除外Unanswerable 209件。HybridのSuccess@10=0.7822はEmbeddingと同じだが、
nDCG@10=0.5317はEmbeddingの0.5519を下回った。検索品質改善は実証していない。
選定条件の実検索225件は探索結果と一致。検索のP50/P95は0.02247/0.02535秒（読込後）。
取得成功率とGold Recallを区別し、UnanswerableのRandom Passageは検索正解Metricへ使わない。
詳細、事前基準、成果物、実行手順、End-to-End検証は[`phase6_hybrid.md`](phase6_hybrid.md)による。
固定Development 5問で生成計5回、全件保存が完了し、Gate 6を通過した。
Pipeline平均56.96秒、合計Peak RSS約2.528GiB。全135 Tests成功・Skipなし、ruff問題なし。
引用だけの回答等もあり、独立品質改善は未検証である。

## Unit Test

対象:

-   CLAPNQ Annotation/Corpus Loader
-   Dataset Schema変換
-   Reference正規化
-   Title Group-aware Split
-   Retrieval
-   Evaluation
-   Confidence

## Decision・Recovery・独立評価の追加Test条件（未実装）

- R/F/Aの個別閾値で`<`、Cの採用閾値で`>=`を使い、境界値を区別できる。
- Cが採用閾値以上でも、個別Failureを優先する。
- 複数個別Failureの優先順位はR → F → Aである。
- R=F=A=0.6は`low_confidence`と`constrained_generation`を別々に保存する。
- 重み付き不足分が同点ならR → F → Aの順で処理を選ぶ。
- Query Rewriteの入力は元質問のみ、再検索後の生成・A評価も元質問を使う。
- 制約付き再生成・Answer Rewriteは初回Contextを保持し、Answer Rewrite後に再生成しない。
- Recovery最大1回、回答候補の生成最大2回、補助呼び出しを含む総LLM Callsを区別する。
- 修正後も不採用なら未解決を記録して修正後回答を返し、追加Recovery・選別・強制拒否をしない。
- Alwaysは全質問でQuery Rewriteを1回実行し、Adaptiveと共通設定を使う。
- 独立LabelがInferenceへ漏れず、主RSR、10区間ECE、回答/Claim単位Hallucinationを定義どおり集計する。
- 判定不能・0 Recovery・0 Claim・空ECE区間は0点と混同せず適用対象外や件数を扱える。

## CLAPNQ関連Test条件

-   公開Source件数がTrain 3,745、Dev 600である
-   Answerable/Unanswerable件数がTrain 1,954/1,791、Dev 300/300である
-   AnswerableのGold Passage IDが公式Corpusに存在する
-   無効Reference除外後も各Answerableに有効Answerが残る
-   正規化後の有効Reference数がTrain Answerable 2,667件、Dev Answerable 475件である
-   重複する有効Answerと空Selected Sentencesを順序どおり保持できる
-   UnanswerableのReference AnswerとGold Passage IDが空である
-   AnnotationとRetrieval Query 4,345件が欠損・余剰・重複なく1対1で対応する
-   AnnotationとQueryの質問文が全件完全一致する
-   引用符内に改行を含む200件のQuery AnswerをLogical TSV RecordとしてLoadできる
-   Answerable 2,254件にGold Passage ID 1件、Unanswerable 2,091件に空Listを付与できる
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

初回生成Promptと各共通Moduleの設定を固定し、変更する要素はRecoveryの起動と修正方法を含む
制御方針とする。Promptの実行履歴が方式間で同じである必要はないが、共通Prompt資産は一致させる。

主比較は常時Query RewriteとAdaptiveの仕組み全体の品質・コスト差を評価するものであり、起動判断
だけの因果効果とは解釈しない。起動判断のみを調べる補助実験は、常時Query Rewriteと、Adaptiveの
起動条件でQuery Rewriteを実行する方式を比較する。条件・結果を主比較とは別に記録する。

修正方法選択の個別効果を主張する場合は、同じAdaptive起動条件で固定の修正と原因別修正を比較する
補助実験などを設計する。これは追加候補であり、固定修正の内容や具体条件は未確定、未実施である。
採用時は初回結果・起動条件・共通Module・Model・最大Recovery予算を揃え、Evaluation前に条件を固定する。
実施しない場合は、主張を仕組み全体の効果と観察した失敗別の傾向に限定する。

独立Failure Labelと診断結果を照合し、修復成功だけでなく不要な修正・悪化・高Confidence誤答も分析する。
自己評価・Claim抽出・根拠確認等を含む総推論コストと独立品質を併記する。品質維持を前提とした
効率改善を主張する場合は品質維持の基準もEvaluation前に固定する。
先行手法の同条件比較は未実施であり、先行手法への優位性を主張できる状態ではない。

Evaluation Splitを用いた最終実験では、事前に固定したDataset Manifest、Config、Prompt、
Model Revisionを使用する。Evaluation結果を確認した後の設定変更は別実験として記録する。
このEvaluation Splitは公開Train/Devから作る内部Splitであり、CLAPNQ公式Testとして扱わない。

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
（2026-10-06完了。c508d78-split-v1、Seed 42、QA 4,345件）
        ↓
公開Train/Devを結合
        ↓
Wikipedia Titleをcasefold・NFC正規化してGroup化（原文Titleは保持）
        ↓
Answerabilityを層別しSeed 42で
Development/Calibration/Evaluationへ分割
        ↓
【Gate 3】
Title LeakageのないSplit Manifestが完成
（Gate 3通過: 欠損・重複0、正規化Group重複0、別出力でByte一致）
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
（2026-10-06完了。候補50件/方式、RRF定数20、top-k=10）
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
（Gate 6通過: 検索条件固定、実検索225件一致、固定Development 5問の生成・保存完了）
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
