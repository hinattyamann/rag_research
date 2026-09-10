# 自己制御型RAG研究計画書

## Version 6.5

## 外部実装依頼用 最終研究仕様書

本書はVersion 6.4を基礎とし、非公開Test Dataを使用せず、公開Train/Devだけで研究を継続する
評価条件を固定した版である。
CLAPNQのField、研究用Split、Corpus、Unanswerable監査、派生Dataset、Licenseおよび引用方法の
詳細は`docs/clapnq_dataset_guide.md`を正本とする。

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

## 基盤Dataset: CLAPNQ

本研究では、基盤DatasetとしてCLAPNQ（Cohesive Long-form Answers from Passages in
Natural Questions）を使用する。

CLAPNQはNatural Questionsの英語質問とWikipedia Passageから構築された、Long-form QAおよび
Full RAG Pipeline向けDatasetである。人手作成のReference Answer、Gold Passage、回答作成に使われた
Selected Sentences、検索Corpusを備え、Retrieval、Gold Passage Generation、Full RAGを分離して
評価できる。

公式Datasetの構成は次のとおりである。

| Split | Answerable | Unanswerable | 合計 | 公開状態 |
|---|---:|---:|---:|---|
| Train | 1,954 | 1,791 | 3,745 | 公開 |
| Dev | 300 | 300 | 600 | 公開 |
| Test | 301 | 300 | 601 | Answer非公開 |
| 合計 | 2,555 | 2,391 | 4,946 | 一部非公開 |

Retrieval Corpusは4,293 Wikipedia Documentsから作られた178,890 Passage Recordsで構成される。
CLAPNQ論文は178,891 Passagesと報告するが、固定Git配布TSVはHeader込み178,891物理行、Data部分
178,890 Recordsであり、公式Hugging Face配布の`num_examples`も178,890件である。本研究では実際に
Retrieverへ投入するData Record数178,890件をCorpus件数として使用する。
回答は平均約56.8語、2.3文で、平均約156語のGold Passage内にある複数の非連続な根拠文を統合する
例が中心である。この性質は、回答のCorrectnessだけでなくFaithfulness、Completeness、Concisenessを
評価する本研究と整合する。

主な参照先:

- CLAPNQ論文: https://aclanthology.org/2025.tacl-1.3/
- 公式Repository: https://github.com/primeqa/clapnq
- Hugging Face Annotation: https://huggingface.co/datasets/PrimeQA/clapnq
- Hugging Face Retrieval Corpus: https://huggingface.co/datasets/PrimeQA/clapnq_passages
- Natural Questions公式配布ページ: https://ai.google.com/research/NaturalQuestions/download
- Dataset詳細仕様: `docs/clapnq_dataset_guide.md`

本研究では、CLAPNQ公式Repository Revision
`c508d78d8c5c2eecbf172fcf5f789004206e11fb`を初期基準とし、取得日、File Hash、件数、Schema、
LicenseをSource Manifestへ保存する。

CLAPNQはApache License 2.0として公開される。一方、元Natural Questions DataはGoogle公式ページで
CC BY-SA 3.0とされるため、本研究では両方をLicense Lineageとして記録し、CLAPNQ論文とNQ論文の
両方を引用する。Raw Dataは本Repositoryへ直接格納せず、取得・変換ScriptとManifestで再現する。

## 本研究におけるCLAPNQの利用範囲

- 公開Train/Devの最終Round Annotationを使用する。
- 固定配布物の178,890 Passage Recordsを共通の検索Corpusとして使用する。
- Annotation内のGold PassageをGeneratorへ直接与える処理はOracle Generationとして分離する。
- Full RAG主実験では、Retrieverが取得したTop-k PassageだけをGeneratorへ渡す。
- Gold Passage ID、Reference Answer、Selected Sentences、Answerability Labelは評価専用とし、
  Retriever、Generator、Query Rewriteへ渡さない。
- Optional CLAPNQ-R1はAnnotation品質条件が異なるため、主実験には使用しない。
- 公式Test 601件は非公開Dataを必要とするため、本研究の主実験には使用しない。

2026年8月26日に著者へTest Accessを問い合わせたが、2026年9月10日時点で返信およびData提供を
受けていない。このため、Test Accessを研究進行上の前提から外し、公開Train/Dev 4,345件だけで
Development、Calibration、Evaluationを構成する。今後返信またはData提供があっても、現行の主実験へ
途中追加せず、利用する場合は別Versionの追加実験として目的、利用条件、Data Versionを改めて固定する。

これにより、OCR、PDF Layout、図表理解などを研究対象から除外し、Text-based RAGの自己評価、
Failure Diagnosis、Adaptive Recoveryへ焦点を維持する。

## 研究用Split

公開Train/Devには同じWikipedia Titleが含まれるため、Source Splitを保持したうえで、公開4,345件を
Title単位で再分割する。同一Titleの全QAを同じ研究用Splitへ配置し、Answerability比を可能な限り
維持する。Seedは42とし、目標比率は次とする。

| 研究用Split | 目標比率 | 用途 |
|---|---:|---|
| Development | 65% | Pipeline、Prompt、Retrieverの開発 |
| Calibration | 10% | Confidence重み、閾値、検索Parameterの固定 |
| Evaluation | 25% | 設計固定後の最終評価 |

Group Sizeにより比率は厳密には一致しないため、実数をSplit Manifestへ記録する。Evaluation結果を
確認してからPrompt、閾値、Weight、`top_k`等を調整し、同じ結果を最終評価として再利用しない。

ここでいうEvaluationは公開Train/Devから作る本研究独自の内部評価Splitであり、CLAPNQ公式Testや
公式Leaderboard相当のHeld-out評価ではない。この制約を結果、考察、Limitationsで明記する。

研究用Splitが分離するのはQA Annotation、Gold Label、Few-shot例である。Full RAGでは全方式が同じ
公式Corpusを検索し、Evaluation質問のGold Passageも検索候補に含める。ただし、EvaluationのQrelや
Reference AnswerをRetrieverの学習・Parameter調整に使用しない。

## Failure評価用Dataset

本研究Datasetは単純なQA性能評価だけを目的としない。

CLAPNQを基盤として、Failure Diagnosis能力およびAdaptive Recovery能力を評価するため、
以下の条件を持つ固定Subsetを構築する。

| 種類 | 目標件数 | CLAPNQからの構築方針 |
|---|---:|---|
| Normal QA | 150 | EvaluationのAnswerableを通常条件で使用 |
| Unanswerable QA | 監査済み150 | EvaluationのUnanswerableをCorpus-levelで監査して使用 |
| Retrieval Failure | 150以下 | 固定RetrieverのTop-kにGold PassageがないAnswerable |
| Distractor | 150 | 異なるTitleの高類似度非Gold Passageを混入したAnswerable |

Normal QA、Retrieval Failure、Distractorは各150件を初期目標とし、Base QAは重複させない。
Retrieval Failureの自然発生例が150件未満なら水増しせず、実数を報告する。検索困難化した派生質問を
補助分析に使う場合は、自然発生Failureと分けて集計する。

Unanswerableは、NQで提示されたDocumentに回答がないLabelであり、検索Corpus全体での回答不能を
保証しない。固定Retrieverの上位PassageとProvided Passageを監査し、`corpus_unanswerable`と確認した
150件を主評価へ採用する。回答根拠を発見した例、曖昧例、時点依存例は除外理由とともに報告する。

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

-   Token-level Answer F1
-   ROUGE-L F1
-   ROUGE-1 Recall
-   Retrieval Recall@k / nDCG@10
-   Answerability F1
-   Faithfulness
-   Hallucination Rate
-   Failure Detection F1
-   Recovery Success Rate
-   ECE
-   Average LLM Calls
-   Latency

Token-level Answer F1、ROUGE-L F1、ROUGE-1 Recallは、複数表現を許すCLAPNQの長文回答について、
語の一致、まとまり、必要情報の網羅性を補完的に測る。複数Referenceには最大Scoreを用いる。
Retrieval Recall@kとnDCG@10はGold Passage取得性能、Answerability F1は回答すべき質問と拒否すべき
質問の識別性能を見る。
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

CLAPNQの英語質問と公式Wikipedia Passage Corpusを用いるText-based RAG。
本研究の中心は、特定言語の処理性能ではなく、Retrieval、Generation、Answer Relevanceの失敗を
自己評価し、Failure原因に対応したRecoveryを選択する制御機構の有効性である。

対象外:

-   PDF/OCR、Page画像、図表、Layoutを入力する処理
-   Multimodal Modelによる回答生成
-   複数文書の情報を必須とするMulti-document Synthesis
-   日本語を含む言語横断性能の実証

理由:

CLAPNQは1 Gold Passageを基本とするText Datasetであり、視覚処理や複数文書統合を導入すると
研究目的が自己制御機構評価から逸れるため。

CLAPNQだけを用いた結果から「提案手法が言語に依存しないことを実証した」とは主張しない。
主張できる範囲は、英語Wikipediaを対象とするText-based RAGにおいて、提案する制御機構が
日本語固有のPDF/OCR処理を前提とせず機能したかどうかである。
