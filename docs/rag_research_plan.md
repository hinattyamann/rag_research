# 自己制御型RAG研究計画書

## Version 6.10

## 外部実装依頼用 最終研究仕様書

本書はVersion 6.9を基礎とし、先行研究との関係、貢献候補、有用性および主張の限界を追記した版である。
Phase 5のノートPC用Generatorと開発用Baseline条件を維持する。
公開Train/Devだけで研究を継続する方針を維持し、2026年10月6日にユーザーが
承認したConfidenceとFailure判定の接続、Always Rewrite、独立品質評価およびRecovery成功の定義を
維持する。制御・評価Module、Calibration、比較実験は未実施である。
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

## 先行研究との関係・研究の立ち位置

自己評価を伴うRAG、Adaptiveな検索、失敗原因に応じた修復には、Self-RAG、CRAG、Adaptive-RAG、
Doctor-RAGなどの先行研究がある。R/F/Aに対応する評価観点もARESなどで扱われている。
本研究はこれらの考え方を初めて提案したとは主張しない。
原論文への参照と比較の詳細は[先行研究との関係・本研究の立ち位置と有用性](related_research_positioning.md)に示す。

貢献候補は、固定Corpusと最大1回のRecoveryという制約下で、明示的なR/F/AとRuleによる
起動・修正選択が、独立に評価した回答品質と自己評価を含む総推論コストに与える効果・限界を示すことにある。
失敗種別、診断の誤り、修復成功、正しい回答への不要な修正と悪化も分析する。
R/F/Aによる分類は原因の代理指標であり、真の原因を特定できると保証された診断ではない。

有用性は、限られた計算資源で「再検索が必要か」「取得済み根拠からの修正で足りるか」を判断するための
実証的な知見を得ることである。小型LLM・ノートPCの採用、評価の独立性、実験条件の違いだけを
新規性とはしない。効果が出ない場合も、その条件と誤判断の分析を示す。
Phase 5時点でH1/H2/H3は未検証であり、新規性・先行手法への優位性・一般的な性能向上は未確立である。

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
    修正後の回答（Answer Rewriteも回答生成1回に含む）
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

初期の採用閾値は0.7とする。ただし、Confidenceだけでは採用せず、R/F/Aの各値が個別Failure閾値
以上であることも必要とする。重み付きScoreは校正済みの正解確率ではなく、確率的な品質との対応は
独立品質Labelを使うECEで検証する。

------------------------------------------------------------------------

# 6. Failure判定仕様

Failure判定優先順位:

1.  Retrieval Failure
2.  Generation Failure
3.  Answer Relevance Failure

判定:

    R < threshold
    → Retrieval Failure

    F < threshold
    → Generation Failure

    A < threshold
    → Answer Relevance Failure

## Failure判定閾値

初期実験では、Failure判定閾値を0.5として固定する。

判定:

R < 0.5

→ Retrieval Failure


F < 0.5

→ Generation Failure


A < 0.5

→ Answer Relevance Failure


比較演算は厳密な`<`とし、0.5は個別Failureに含めない。閾値の調整はDevelopment/Calibrationで
行い、最終Evaluation前に固定する。Sensitivity Analysisは条件を明示した追加分析として扱い、
Evaluation結果を見た変更を同じ最終評価へ混在させない。

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

## ConfidenceとFailure判定を接続するDecision Rule

以下を上から順に適用する。加重平均によって個別の低評価が隠れることを防ぐため、Cが採用閾値以上
でも個別Failureを優先する。R/F/Aは0以上1以下の制御用Scoreを前提とする。

| 優先順位 | 条件 | `failure_type` | `recovery_action` |
|---|---|---|---|
| 1 | R < 0.5 | `retrieval_failure` | `query_rewrite` |
| 2 | 1に該当せずF < 0.5 | `generation_failure` | `constrained_generation` |
| 3 | 1・2に該当せずA < 0.5 | `answer_relevance_failure` | `answer_rewrite` |
| 4 | 個別Failureなし、C < 0.7 | `low_confidence` | 下記の補助Ruleで選択 |
| 5 | 個別Failureなし、C >= 0.7 | `none` | `none`（Accept） |

`low_confidence`は原因を断定できない状態であり、3種類のFailureのいずれかを正しく診断したという
意味を持たない。修正方法は、採用閾値までの不足分にConfidence重みを掛けた値が最大の項目から選ぶ。

```text
dR = 0.25 * max(0, 0.7 - R)
dF = 0.50 * max(0, 0.7 - F)
dA = 0.25 * max(0, 0.7 - A)

最大項目R → query_rewrite
最大項目F → constrained_generation
最大項目A → answer_rewrite
同点の優先順位: R → F → A
```

R/F/Aがすべて0.6ならC=0.6、dR=0.025、dF=0.050、dA=0.025となり、根拠制約付き再生成を選ぶ。
この補助RuleはFaithfulnessを重視する設計上のHeuristicであり、原因診断の正しさは未実証である。
Calibrationで挙動を確認し、最終Evaluation前に固定する。閾値・重みを変更する場合は式にも同じ
設定値を使い、仕様・Config・Test・実験条件を合わせて更新する。

------------------------------------------------------------------------

# 7. Adaptive Recovery

制約:

-   Recovery最大1回
-   最終回答候補を作る生成は最大2回（初回回答と修正後回答）

Query Rewrite、Claim抽出、根拠検証等の補助LLM呼び出しは、この回答生成回数とは区別し、LLM Callsに
別途計上する。Answer Rewrite自体を2回目の回答生成と数え、その後に別の再生成を追加しない。

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

Query Rewriteの入力は元の質問だけとし、自己評価結果、Reference、Gold情報を渡さない。
Rewriteした質問は検索にだけ使い、回答生成とAnswer Relevance評価には元の質問を使う。
再検索は共通Corpus・Retriever・top-kを使い、初回Contextとの結合は行わない。
制約付き再生成は同じ検索結果を使い、Answer Rewriteは元の質問・取得Context・初回回答を使う。

Phase 5の初回Promptは既に根拠限定・根拠外情報の禁止・情報不足時の回答抑制を含むため、
上記の制約例を繰り返すだけではGeneration Failure Recoveryの追加介入が十分に具体化されない。
実装前に初回生成から変更するPrompt・生成条件を固定する。現行の入力は元の質問と同じContextであり、
初回回答や診断Feedbackを追加する場合は別途仕様変更として理由・比較条件を文書へ反映する。
現時点でその入力変更を決定・実装したものではない。

Recoveryした場合は修正後の回答を最終回答とし、再評価して終了する。初回回答との選別は行わない。
修正後も採用条件を満たさない場合は`unresolved=true`として記録するが、追加Recoveryや閾値だけに
よる強制拒否は行わない。拒否の妥当性も独立品質評価の対象とする。Acceptなら初回回答を返す。

------------------------------------------------------------------------

# 8. Recovery Success Rate

Recovery成功は制御用ConfidenceやR/F/Aの上昇だけでは判断しない。第11節およびDataset Guide
第10節の独立品質Label Yを使い、信頼できない初回回答を信頼できる回答へ修復できたかを測る。

## Recovery Success Rateの具体的定義

```text
RSR = Recoveryした例のうち初回Y=0かつ修正後Y=1となった件数 / Recovery実行件数
```

Recoveryが0件なら適用対象外とする。初回Y=1を維持した例は修復成功に数えず、維持と悪化を
別途報告する。判定不能の除外方法・件数はDataset Guide第10.6節に従う。

Version 6.5の「Faithfulness上昇、Answer Relevance非低下、Hallucination非増加」という条件は
Faithfulness改善の補助分析として残し、主RSRと区別する。その判定にも制御用Scoreを流用せず、
独立評価値を使う。主定義を変更する理由は、Faithfulnessが満点でも検索・質問適合性の改善を
修復成功として評価できるようにするためである。

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

### Phase 3の固定結果（2026-10-06、Gate 3通過）

Title Group Keyは`source_title`をcasefold後にUnicode NFCへ正規化した文字列とする。原文のTitleは
QAへ保持する。原文Titleは3,799種類だが、`The Dragon (Beowulf)`と`The dragon (Beowulf)`を同じ
Groupへ置くため、正規化後は3,798 Groupである。これは表記差による漏洩を安全側で防ぐための具体化で、
質問・正解・Answerabilityの変更やQAの除外は行わない。表記の正規化は異なるTitleを保守的に同一Groupへ
まとめ得るため、このRuleを全方式共通のDataset条件として記録する。

| Split | QA数 | 実比率 | Answerable | Unanswerable | Group数 |
|---|---:|---:|---:|---:|---:|
| Development | 2,824 | 64.99% | 1,465 | 1,359 | 2,277 |
| Calibration | 434 | 9.99% | 225 | 209 | 434 |
| Evaluation | 1,087 | 25.02% | 564 | 523 | 1,087 |

Dataset Versionは`c508d78-split-v1`、Algorithm Versionは
`title-nfc-casefold-stratified-greedy-sha256-v1`とする。Group内件数の大きい順に処理し、同じSizeの順序を
Seed付きSHA-256で固定する。総件数・Answerable件数・Unanswerable件数の目標からの二乗誤差を
減らすSplitへGroupを割り当てる。詳細な目的関数・同点RuleはDataset Guide第6.2節を正本とする。

4,345件の欠損・重複0、原文Titleおよび正規化GroupのSplit間重複0、Split以外の全QA Metadata保持を
検証済みである。別出力先でQA・レポート・ManifestがByte単位で一致した。Base Datasetは保持し、
Git管理する`data/manifests/clapnq_split_manifest.json`に割当・実数・Hash・条件を固定した。

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
全質問に、初回回答の後でQuery Rewrite・再検索・再生成を1回適用

Adaptive Recovery:
個別Failureまたは低Confidence時だけ、定義したRuleに従ってRecovery適用

3方式の具体的な共通条件と比較の解釈は第11節に従う。

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
-   原因分類Macro-F1
-   Recovery Success Rate
-   ECE
-   Average LLM Calls
-   Latency

Token-level Answer F1、ROUGE-L F1、ROUGE-1 Recallは、複数表現を許すCLAPNQの長文回答について、
語の一致、まとまり、必要情報の網羅性を補完的に測る。複数Referenceには最大Scoreを用いる。
Retrieval Recall@kとnDCG@10はGold Passage取得性能、Answerability F1は回答すべき質問と拒否すべき
質問の識別性能を見る。
Faithfulnessは取得Contextに対するClaimの裏付けを独立評価する。Hallucination Rateの主単位は回答
であり、根拠のないClaimが1つ以上ある回答の割合とする。Claim単位の割合は補助指標とする。
Failure Detection F1は初回Y=0をRecovery起動判断が検出したか、原因分類Macro-F1は独立Labelの
代表原因と自己診断が一致したかを測る。RSRは第8節、ECEは下記の定義に従う。

## 制御用自己評価と独立品質評価の分離

制御用R/F/AはInference時に使う。主評価のLabelは、質問、Reference、Gold根拠、取得Context、回答を
使って実験後に人手確認で確定する。LLMによる独立評価は下書きの補助に限定する。評価結果を生成や
Recoveryへ戻してはならない。判定時には方式名、Confidence、制御用R/F/Aを隠し、初回・修正後の
順序を入れ替えて個別に評価する。根拠箇所と判定理由を保存する。

AnswerableのY=1は、必須要点を満たし、重大な事実誤りがなく、事実主張が取得Contextで裏付けられる
回答とする。監査済みUnanswerableのY=1は、回答不能を明確に伝え、回答を捏造しない応答とする。
それ以外はY=0、判定不能は別Labelとする。Referenceとの表現一致は必須にしない。

Dataset種類をFailureの正解Labelに流用しない。Retrieved Contextの根拠不足、回答Claimの裏付け
不足、質問への意味的な誤答・不完全さ等を実際の検索・回答から判定する。複数Labelを保存し、
代表原因はRetrieval → Generation → Answer Relevanceの順とする。Gold未取得と根拠不足は区別し、
監査済みUnanswerableにはRetrieval Failureを適用しない。詳細はDataset Guide第10.7節による。

## ECEとHallucinationの集計

ECEは独立Label YとCを使い、[0,1]を10個の等幅区間に分けて計算する。区間は左端を含み右端を
含まないが、最後だけ1を含む。空区間の寄与は0とする。

```text
ECE = sum((区間件数 / 全判定可能件数) * abs(区間平均C - 区間内のY=1の割合))
```

初回回答のECEを主指標、最終回答のECEを別指標とし、区間件数とDataset種類別の結果も報告する。
Cを事前に校正済み正解確率と解釈しない。標準的なECEの式は
[Guo et al. (2017)](https://proceedings.mlr.press/v70/guo17a/guo17a.pdf)に基づく。

各事実Claimは`supported`、`contradicted`、`not_supported`へ分類し、後二者を根拠のないClaimとする。
主Hallucination Rateは該当Claimを1つ以上含む回答数 / 評価回答数、補助指標は該当Claim総数 /
全Claim数とする。これは取得Contextによる裏付け不足の操作的定義であり、世界知識上の真偽や
Referenceに対するCorrectnessとは区別する。事実Claimのない適切な拒否はHallucinationなしだが、
Claim単位Faithfulnessは適用対象外とする。空回答・無関係な回答はHallucinationなしでもY=0である。


# 比較実験設計思想

本研究では以下3方式を比較する。

## Baseline RAG

Recovery機構を持たない通常RAG。

目的:
基本性能確認。


## Always Rewrite RAG

初回回答の後に、全質問へQuery Rewrite・再検索・再生成を1回適用し、2回目の回答を返す方式。

目的:
常時修正による性能変化確認。


## Adaptive Recovery RAG

個別Failureまたは低Confidence時だけ、第6節に従ってRecoveryを実行する提案方式。

目的:
不要な修正を避けながら品質改善する効果を検証する。


## 共通条件・コスト・主張できる範囲

- 3方式は同じ初回検索・初回回答から分岐し、Dataset、Corpus、Retriever、Generatorと初回生成Promptを
  共通にする。初回結果を共有する場合も各方式の推論コストへ初回処理を1回ずつ計上する。
- AlwaysとAdaptiveのQuery Rewriteは同じModel、Prompt、生成設定を使う。Rewriteの入力、元質問の
  保持、再検索Contextの扱いは第7節に従う。
- Average LLM Calls、Token、Latencyは推論に実際に必要な処理を集計し、Adaptiveの自己評価や補助
  呼び出しも含める。全方式を採点するOffline評価は別集計する。Baseline・Alwaysの初回/最終Cを
  ECE用に取得する処理も制御へ使わず、Offline評価として分離する。
- 主比較は「常時Query Rewrite」と「必要時に原因に応じて修正する仕組み全体」の品質・コスト差を
  測る。修正方法も異なるため、差のすべてをRecovery起動判断だけの効果とは解釈しない。
- 起動判断だけの効果を切り分ける補助実験では、Query Rewriteという修正方法を共通にしたまま、
  常時実行とAdaptiveの起動条件で実行する方式を比較する。主比較3方式とは別の追加分析として
  条件を事前固定し、実施状況と結果を分けて記録する。
- 修正方法の選択だけの効果を主張するには、同じAdaptive起動条件で固定の修正と原因別修正を比較する
  補助実験などが必要である。これは追加の設計候補であり、固定修正の内容・条件は未確定、未実施である。
  行わない場合は、主張を仕組み全体の効果と失敗別の観察に限定する。
- 品質と総費用を併記し、一定品質を維持した効率改善を主張する場合は、その判定基準をEvaluation前に固定する。
  先行手法の同条件比較は未実施であり、先行手法への優位性や他Model・言語・Datasetへの一般化は主張しない。

この具体化は、H2の効率評価に自己評価コストを含め、H1/H3を自己評価値だけで検証しないための
変更である。研究目的、公開Source、Split比率、初期Confidence重みは変更しない。

------------------------------------------------------------------------

# Phase 4の検索条件と研究上の扱い

2026-10-06にノートPCで両検索Indexを全件生成・検証し、Gate 4を通過した。
BM25とEmbeddingは固定Corpusの全178,890件を対象に、QAのGold・Reference・Labelを入力せず
質問文字列だけから検索する。初期EmbeddingはCPU用の公式量子化`all-MiniLM-L6-v2`を固定Revisionで
使用する。Modelの量子化、最大256 Tokenへの切詰め、Pooling/Normalization、BM25 Parameterと
Library Versionを記録する。詳細と実測結果は[`phase4_retrieval.md`](phase4_retrieval.md)による。

この選択はノートPCで検索基盤を構築するための具体化であり、研究目的・仮説・Split・3方式比較・
独立品質評価の定義は変更しない。Model変更は検索性能へ影響するため、変更時は新Index条件を記録し、
3方式に共通適用する。Developmentの50問によるSmoke結果から最終性能や提案手法の効果は主張しない。
RRFと最終RetrieverのCalibration固定はPhase 6、制御・品質比較は後続Phaseで実施する。

# Phase 5のGenerator条件と研究上の扱い

2026-10-06にユーザーがノートPC向け小型LLMを承認したため、開発用Generatorを
`Qwen/Qwen2.5-3B-Instruct-GGUF` Q4_K_M、Revision
`7dabda4d13d513e3e842b20f0d435c732f172cbe`として具体化した。
llama.cpp b11433 Windows CPU、6 Threads、重み再配置なし。固定EmbeddingのTop-5、合計4,096/出力512/
本文各512 Token、Temperature 0/Seed 42、固定英語Promptを使う。全条件とFile Hashを記録する。

これは16GiB RAMのノートPCで開発を進めるための選択であり、例示の14Bを最終実験用に固定したものではない。
Model規模・量子化・切詰め・Promptは品質へ影響するため、変更時は理由と条件を記録し、比較3方式へ
共通適用する。研究目的・仮説・Split・Confidence/Failure・Recovery・独立評価の定義は変更しない。
Gold/Reference/Answerabilityを推論へ渡さず、実行成功と品質Yを区別する。
Developmentの少数問でGate 5を通過したが、H1/H2/H3やECE/Hallucination率の改善は検証していない。
実装と実測は[`phase5_baseline.md`](phase5_baseline.md)を参照する。

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
