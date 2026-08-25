# 自己制御型RAG研究計画書

## Version 6.2

## 外部実装依頼用 最終研究仕様書

本書はVersion
6.1を基礎とし、JDocQA論文と現行Annotationの再監査結果を反映した版である。
JDocQAのField、Text-only選別、Corpus構築および派生Datasetの詳細は
`docs/jdocqa_dataset_guide.md`を正本とする。

------------------------------------------------------------------------

# 1. 研究概要

## 研究テーマ

評価駆動型自己制御RAGによる回答信頼性向上手法の提案
(Proposal of an Evaluation-Driven Self-Controlled RAG Method for Improving Answer Reliability)

本研究では、RAG自身が生成回答を評価し、失敗原因を判断し、必要な場合のみRecoveryを実行する自己制御型RAGを構築する。

つまり、全体的なフローとしては、
普通のRAGが、質問→検索→回答生成→終了なのに対して、
本研究の目的とするRAGは、質問→検索→回答生成→自分で回答を評価→失敗原因を判断→必要であれば修正処理→再評価→最終回答
となる。

そもそもRAGというのは、検索拡張生成と呼ばれるものであり、LLMが持っている知識だけで回答するのではなく、外部文書を検索して、その情報を根拠として回答する仕組みのことである。
これによりハルシネーションを減らすという目的がある。

普通のRAGでは不十分な理由としては、検索失敗、生成失敗、回答失敗がある。
<span style='color: #ff0000;'>検索失敗→Retrieval Failure、生成失敗(ハルシネーション)→Generation Failure、回答失敗→Answer Failure</span>とする。

それらを評価指標によって判断し、失敗原因ごとに異なるRecoveryを行うという取り組みである。

------------------------------------------------------------------------

# 2. 研究目的

目的: 以下に構造化した研究目的を示す。

最終目的
│
├── 回答品質向上
│
├── そのための仕組み
│   ├── RAG自身による評価
│   ├── Confidence Scoreによる判断
│   └── Failure原因別Recovery
│
└── 実用上の制約
    └── 計算コスト削減

第一の目的として、回答信頼性の向上がある。
実用上の制約とは、何度も生成して回答の品質を向上させるのではなく、必要な場合に的確な方法でRecoveryするという手段をとるということです。

------------------------------------------------------------------------

# 3. 提案手法

Question
 ↓
Hybrid Retrieval
 ↓
Generation
 ↓
R/F/A Self Evaluation
 ↓
Confidence Calculation
 ↓
Decision
 ├─ Accept → Final Answer
 │
 └─ Reject
       ↓
    Failure Diagnosis
       ↓
    Adaptive Recovery
       ↓
    Re-Generation
       ↓
    Re-Evaluation
       ↓
    Final Answer


## Hybrid Retrieval詳細仕様

本研究では、Keyword RetrievalとEmbedding Retrievalを統合したHybrid Retrievalを採用する。

Keyword RetrievalにはBM25を利用し、語句一致や固有表現検索における精度を確保する。

一方、Embedding Retrievalでは文章の意味的類似性を利用し、質問文と表現が異なる文書も取得可能にする。

両者の検索結果はReciprocal Rank Fusion(RRF)によって統合する。

処理フロー:

Question

↓

BM25 Retrieval

+

Embedding Retrieval

↓

RRF Fusion

↓

Top-k Documents

↓

Generation


Hybrid Retrievalにより、語句一致能力と意味的検索能力を両立し、適切な根拠文書取得によるFaithfulness向上および回答信頼性改善を図る。

------------------------------------------------------------------------

# 4. 評価設計

## Retrieval Quality(R)

Embeddingベース数値評価。
つまり、取得した文書が質問に対して、どれだけ関連しているかの指標。

目的: 検索品質評価。

------------------------------------------------------------------------

## Faithfulness(F)

Claim分解型LLM評価。
Claim分解型LLM評価とは、LLMの回答を主張単位に分解し、それぞれについて、根拠があるかを確認する手法。

例): 商品Aは国内工場で製造され、賞味期限は30日で、保存料を使用していません。
Claim 1:
商品Aは国内工場で製造される

Claim 2:
賞味期限は30日

Claim 3:
保存料を使用していない

つまり、生成された回答が、取得した根拠文書に忠実であるかの指標。
ハルシネーション問題を検出するための指標となる。

処理:

    Answer
     ↓
    Claim Extraction
     ↓
    Evidence Verification
     ↓
    Supported Claim Ratio

------------------------------------------------------------------------

## Answer Relevance(A)

LLM評価。
つまり、質問意図と回答内容との一致度を示す評価指標。

目的: 質問意図との一致評価。

------------------------------------------------------------------------

# 5. Confidence Score

式:

C = 0.25R + 0.50F + 0.25A

理由:

Faithfulnessは根拠性およびHallucination抑制に最重要であるため最大重みとする。
つまり、見た目はいいが、危険な回答を抑制したいという、RAGへの研究目的を反映させている。

## Confidence Scoreの役割

Confidence Scoreは単なる評価指標ではなく、Recovery制御を行うためのDecision Signalとして利用する。

処理:

R/F/A Evaluation

↓

Confidence Calculation

↓

Accept / Recovery Decision

↓

必要時のみRecovery


したがって、本研究ではConfidence Scoreを回答品質評価と制御判断を接続する中間層として位置付ける。

------------------------------------------------------------------------

# 6. Failure判定仕様

Failure判定優先順位:

1.  Retrieval Failure
2.  Generation Failure
3.  Answer Failure

判定:

    R < threshold
    → Retrieval Failure

    F < threshold
    → Generation Failure

    A < threshold
    → Answer Failure

## Failure判定閾値

初期実験では、Failure判定閾値を0.5として固定する。

判定:

R < 0.5

→ Retrieval Failure


F < 0.5

→ Generation Failure


A < 0.5

→ Answer Relevance Failure


なお、閾値については実験結果に基づきSensitivity Analysisによる検討を行う。

## Failure Diagnosis優先順位

Failure判定では、上流工程の失敗を優先的に確認する。

優先順位:

1. Retrieval Failure
2. Generation Failure
3. Answer Relevance Failure


理由:

RAGではRetrievalがGenerationの入力情報を決定するため、
検索失敗を修正せずにGenerationのみ改善しても根本的な品質改善にはならない。

そのため、処理パイプライン上流から順番にFailure原因を診断する。

------------------------------------------------------------------------

# 7. Adaptive Recovery

制約:

-   Recovery最大1回
-   最大生成試行2回

理由:

-   計算コスト制御
-   無限ループ防止
-   比較実験公平性確保


## Failure原因別Adaptive Recovery戦略

本研究では、Failure発生時に単純な再生成を行うのではなく、
Failure原因を分類し、その原因に応じたRecovery処理を選択するAdaptive Recoveryを採用する。

Failure TypeごとのRecovery戦略を以下に示す。
Query Rewriteとは、検索されやすい質問表現へ変換すること。
制約付き再生成の制約とは、Retrieved Documentsのみを根拠として利用する、根拠がない情報を生成しない、不明な場合は不明と回答するなどである。
Answer Rewriteとは、LLMの回答を修正すること。

| Failure Type | 主な原因 | Recovery方法 |
|---|---|---|
| Retrieval Failure | 質問に対して適切な文書取得ができていない | Query Rewriteによる質問再構成後、再Retrievalを実行 |
| Generation Failure | 取得文書は適切だが回答生成時に根拠利用が不十分 | 制約付き再生成を実行 |
| Answer Relevance Failure | 回答内容が質問意図と一致していない | Answer Rewriteによる回答修正を実行 |

このように、本研究のRecoveryは生成結果の単純な再生成ではなく、
失敗原因に応じて異なる修正戦略を適用する点に特徴がある。

------------------------------------------------------------------------

# 8. Recovery Success Rate

Recovery成功はConfidence上昇のみでは判断しない。
Confidence Scoreはあくまで、R/F/Aの統合結果であるため。
内部的な評価値が向上しただけで、本当に良い回答になったとは限らないから。

成功条件:

-   Answer品質向上
-   Faithfulness向上
-   Hallucination低減

Confidence ScoreはRecovery判断に利用するが、Recovery成功評価では最終回答品質を基準とする。

## Recovery Success Rateの具体的定義

Recovery Success Rate（RSR）は、Recoveryによって回答品質が改善した割合を示す。

RSR:

RSR = Recovery Success数 / Recovery実行数


Recovery Success条件:

以下をすべて満たす場合、Recovery成功と判定する。

1. Faithfulness ScoreがRecovery前より向上する

2. Answer Relevance Scoreが低下しない

3. Hallucinationが増加しない


つまり、Recoveryによって根拠性を維持または向上させながら、
質問適合性を維持した回答改善が達成された場合のみ成功とする。

------------------------------------------------------------------------

# 9. Dataset設計

## 基盤Dataset: JDocQA

本研究では、基盤DatasetとしてJDocQA（Japanese Document Question Answering）を使用する。

JDocQAは、日本語の行政・公共文書を中心とするDocument Question Answering Datasetであり、
5,504件のPDF文書と11,600件の日本語QAペアから構成される。

文書形式には、Pamphlet、Slide、Report、Websiteが含まれる。

QAの質問形式は以下の4種類である。

| 質問形式 | 件数 |
|---|---:|
| Yes/No | 1,855 |
| Factoid | 2,052 |
| Numerical | 1,866 |
| Open-ended | 5,827 |

論文Table 1では、複数ページの参照を必要とするMulti-page QAが1,000件、
文書内に回答根拠が存在しないUnanswerable QAが1,788件含まれると報告されている。
2026年8月25日に固定した公式Repository RevisionのAnnotationを再集計した結果では、
Multi-pageは1,000件、Unanswerableは1,791件であり、論文値と3件の差がある。
実験ではDataset RevisionとHashを固定し、現行AnnotationのLabelを使用する。

公式分割は以下のとおりである。同一PDFが複数のSplitにまたがらないよう分割されている。

| Split | QA件数 |
|---|---:|
| Train | 9,290 |
| Validation | 1,134 |
| Test | 1,176 |

主な参照先:

- 論文: https://aclanthology.org/2024.lrec-main.830/
- 公式Repository: https://github.com/mizuumi/JDocQA
- Hugging Face Dataset: https://huggingface.co/datasets/shunk031/JDocQA
- Dataset詳細仕様: `docs/jdocqa_dataset_guide.md`

JDocQAのAnnotationはCC BY-SA 4.0で配布されている。派生Datasetや研究成果では、
JDocQA論文を引用する。元PDF文書については、それぞれの配布元が定める利用条件も確認し、
大容量の原本PDFを本Repositoryへ直接格納しない。

## 本研究におけるJDocQAの利用範囲

JDocQAは本来、テキスト情報と図表・画像などの視覚情報を組み合わせたDocument QAを
想定したDatasetである。一方、本研究の対象はText-based RAGである。

そのため、本研究では以下の方針で利用する。

- PDFに埋め込まれたテキスト、またはOCRによって抽出されたテキストを検索Corpusとして使用する。
- PDF画像、回答根拠Bounding Box、図表のLayout情報はRetrieverおよびGeneratorの入力に使用しない。
- `answer`、`normalized_answer`、`question_page_number`、`reason_of_answer_bbox` などの正解情報は、評価とDataset監査にのみ使用し、検索・回答生成時には参照しない。
- 視覚情報がなければ回答できないQAは、主実験の対象外または別の診断用Subsetとして扱う。
- Text-onlyで回答可能かを判定する選定基準はPilot調査で定義し、除外理由と件数を記録して再現可能にする。

この制限により、JDocQAを利用しつつ、本研究の焦点を自己評価、Failure Diagnosis、
Adaptive Recoveryの検証に維持する。

## Split利用方針

- Train Split: Pipeline開発、Prompt検討およびDataset構築手順の確認に使用する。
- Validation Split: Confidence重み、Failure閾値、検索パラメータなどの調整に使用する。
- Test Split: 設計とパラメータを固定した後の最終評価に使用する。
- Test Splitの結果を確認してから閾値やPromptを調整し、同じ結果を最終評価として再利用しない。

検索CorpusをSplit単位で構築する場合は、対象Splitに属する全文書を候補とし、
質問に対応する正解文書だけを直接Generatorへ与えない。これによりRetrievalそのものを評価する。

## Failure評価用Dataset

本研究Datasetは単純なQA性能評価だけを目的としない。

JDocQAを基盤として、Failure Diagnosis能力およびAdaptive Recovery能力を評価するため、
以下の条件を持つ固定Subsetを構築する。

| 種類 | 目標件数 | JDocQAからの構築方針 |
|---|---:|---|
| Normal QA | 150 | Text-onlyで回答可能なAnswerable QA |
| Unanswerable QA | Text-only適格例の全件 | 公式Test Splitに含まれるUnanswerable QAを監査し、適格例をすべて使用 |
| Retrieval Failure | 150 | Answerable QAを基に、検索困難な条件を再現した派生例 |
| Distractor | 150 | 正解文書に類似する別文書Chunkを混入した派生例 |

Normal QA、Retrieval Failure、Distractorは各150件を初期目標とする。
Unanswerable QAは件数を150件に固定せず、公式Test Split内でText-only適格と判定された
例をすべて使用する。公式Test Annotationには選別前のUnanswerable QAが145件含まれるため、
最終件数はText-only適格性監査後に145件以下となる。採用件数と除外理由をDataset Manifestへ記録する。

派生例の生成手順、乱数Seed、元のQA ID、正解文書ID、追加したDistractor文書IDを保存し、
同一条件を再生成できるようにする。

Dataset分類:

Normal QA:
通常性能評価。

Unanswerable QA:
文書内に答えがない問題を用いたHallucination評価。

Retrieval Failure:
必要な文書を取得しにくい状態を再現し、Query Rewriteによる検索Recoveryを評価する。

Distractor:
関係がありそうだが回答根拠として不適切な文書を混入し、誤検索耐性を評価する。


------------------------------------------------------------------------

# 10. 実験仮説

H1: 自己評価機構により通常RAGより信頼性が向上する。

H2: Adaptive RecoveryはAlways Rewriteより効率的である。

H3: Confidence Scoreは実際の品質と相関する。

## Recovery方式比較

Adaptive Recoveryの有効性を検証するため、
以下を比較する。

Baseline RAG:
Recoveryなし

Always Rewrite:
全質問にRewrite適用

Adaptive Recovery:
Failure原因に応じてRecovery適用

これにより、常時修正ではなく必要時のみ修正する方式の有効性を評価する。

------------------------------------------------------------------------

# 11. 評価指標

-   Answer F1
-   Faithfulness
-   Hallucination Rate
-   Failure Detection F1
-   Recovery Success Rate
-   ECE
-   Average LLM Calls
-   Latency

Answer F1とは、最終回答の正確性を見る指標。一般的なQA評価。
Faithfulnessとは、回答が取得した根拠文書に忠実化を見る指標。LLMが勝手に情報を追加していないか。
Hallucination Rateとは、根拠のない情報を生成した割合。
Failure Detection F1とは、RAGがこの回答は問題があると正しく判断できるかを測ります。
Recovery Success Rateは、Recoveryが実際に改善につながった割合。
ECEとは、Confidence Scoreの信頼性の指標。
Average LLM Callsとは、平均LLM呼び出し回数を測る指標。
Latencyとは、処理時間。


# 比較実験設計思想

本研究では以下3方式を比較する。

## Baseline RAG

Recovery機構を持たない通常RAG。

目的:
基本性能確認。


## Always Rewrite RAG

全質問に対してRewriteを適用する方式。

目的:
常時修正による性能変化確認。


## Adaptive Recovery RAG

Failure発生時のみRecoveryを実行する提案方式。

目的:
不要な修正を避けながら品質改善する効果を検証する。


この比較により、Adaptive Recoveryによる必要時のみの制御効果を評価する。

------------------------------------------------------------------------

# 12. 研究範囲

対象:

Text-based RAG。

JDocQAのPDF文書から抽出された埋め込みテキストまたはOCRテキストを入力とする。
OCR済みテキストの利用はText-based処理に含めるが、本研究内で画像認識モデルによる
OCR性能そのものは評価対象としない。

対象外:

-   PDFページ画像を直接入力する処理
-   図表の視覚的理解
-   Layout情報およびBounding Boxを利用した推論
-   Multimodal Modelによる回答生成

理由:

Multimodal処理を導入すると研究目的が自己制御機構評価から逸れるため。

JDocQAのうち視覚情報が不可欠なQAは、主実験から除外するか、Text-only RAGの限界を
確認する診断用Subsetとして主実験とは分離して報告する。
