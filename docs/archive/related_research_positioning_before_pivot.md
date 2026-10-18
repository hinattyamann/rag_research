> 2026年10月18日のテーマ変更前の保存版。今後の作業指示には使わない。現行の正本は[研究計画](../rag_research_plan.md)、[実装計画](../rag_implementation_plan.md)、[進捗とフェーズ](../research_roadmap.md)を参照する。

# 先行研究との関係・本研究の立ち位置と有用性

文献確認日・作成日: 2026年10月6日。
対象: 学士卒業研究「評価駆動型自己制御RAGによる回答信頼性向上手法の提案」。
研究仕様は[研究計画書](../rag_research_plan.md)、工程と実装仕様は[実装計画書](../rag_implementation_plan.md)、
Datasetと独立品質評価の詳細は[Dataset Guide](../clapnq_dataset_guide.md)を正本とする。

本書は論文・発表に向けた関連研究と貢献の整理であり、網羅的な文献調査や新規性の確定ではない。
現在はPhase 6の固定Hybrid検索を使うBaselineまで実装済みで、自己評価・Recovery・比較実験は未実施である。
検索CalibrationではHybridの精度改善を確認できていない。全結果と条件は[Phase 6記録](../phase6_hybrid.md)による。
以下の「貢献候補」は、実験で確認できた範囲に絞って最終的な論文の主張へ更新する。

## 1. 本研究の立ち位置

本研究は、検索品質(R)、回答の根拠性(F)、質問への適合性(A)を評価し、最大1回のRecoveryという
制約の中で、いつ・どの処理を修正すべきかを判断する。その制御が、回答品質と総推論コストに
与える効果と限界を、固定条件の比較実験と誤り分析で検証する研究である。

対象はCLAPNQの英語質問・Wikipediaの固定Corpusを用いたLong-form回答である。
公開Train/DevをTitle単位で分割した内部Evaluationを使い、公式TestやLeaderboardとは区別する。
開発用にはノートPCで動作する小型・量子化LLMを採用しているが、最終Generator/Evaluatorは未確定である。
小型LLMやノートPCの採用自体を、新しいRAG手法の新規性とはしない。

「自分で回答を評価する」「必要時だけ検索する」「失敗に応じて修復する」という考え方には
既に先行研究がある。本研究は、それらを初めて提案したとは主張しない。
狙うのは、限定した処理予算の下で明示的な評価・制御Ruleを用い、その有効な条件と限界を
再現可能な形で明らかにする実証的な貢献である。

## 2. 主要な先行研究との関係

以下は原論文・公式掲載情報に基づく比較である。各論文の結果を、本研究のDataset・Modelで
再現したわけではない。異なる実験条件の数値から直接優劣を主張しない。

| 先行研究 | 主な取り組み・本研究との重なり | 本研究で扱う違いと注意点 |
|---|---|---|
| [Self-RAG](https://arxiv.org/abs/2310.11511)（ICLR 2024） | Reflection Tokenを用いた学習により、検索の必要性や取得文書・生成内容の評価を生成過程へ組み込む。自己評価を伴うRAGという考え方が重なる。 | 本研究は専用Reflection Tokenの学習を前提とせず、明示的なR/F/A ScoreとRuleで初回回答後の修正を制御する。自己評価すること自体を新規性とはしない。 |
| [Corrective Retrieval Augmented Generation（CRAG）](https://arxiv.org/abs/2401.15884)（2024、arXiv） | 検索文書の品質評価を基に処理を切り替え、文書の精緻化やWeb検索を使う。検索失敗への対応が重なる。 | 本研究は固定Corpusで検索し、生成回答の根拠性・適合性も修正選択に用いる。Web検索拡張を採用した性能との直接比較はしない。 |
| [Adaptive-RAG](https://aclanthology.org/2024.naacl-long.389/)（NAACL 2024） | 質問の複雑さを分類し、検索なし・単回検索・反復検索を選択する。必要に応じた処理と効率化が重なる。 | 本研究は初回検索・回答を行った後の品質評価を基にRecoveryを選ぶ。質問の複雑さだけで処理を選ぶ設計とは判断時点・入力が異なる。 |
| [Doctor-RAG](https://arxiv.org/html/2604.00865v2)（2026、arXivプレプリント） | Agentic RAGの失敗履歴について、根拠の十分性・失敗種別・最初の誤り位置を診断し、正常な履歴を再利用して局所修復する。原因に応じた修復という点で特に近い。 | 本研究は長いAgent軌跡の局所修復ではなく、初回検索・回答に対するR/F/Aと最大1回の明示的な修正Ruleを対象とする。正しい初回回答も含めて起動判断の誤りを評価する。原因別修復自体が本研究固有とは主張しない。 |
| [ARES](https://aclanthology.org/2024.naacl-long.20/)（NAACL 2024） | Context Relevance、Answer Faithfulness、Answer Relevanceを評価し、学習したJudgeと人手Annotationを活用する。評価する観点が重なる。 | R/F/Aの観点自体は新しいものではない。本研究ではこれらを制御用Scoreとし、最終的な品質の判定は独立したLabelで行う。人手評価の導入自体も新規性とはしない。 |
| [RAGVUE](https://aclanthology.org/2026.eacl-demo.35/)（EACL 2026 System Demonstrations） | Retrieval品質、回答の関連性・完全性、Claimの根拠性を診断的に評価し、JudgeのCalibrationを扱う。診断・根拠性評価が重なる。 | 本研究の中心は評価ツールそのものの提案ではなく、その評価をRecoveryの起動・選択に接続したときの品質・コスト・誤判断の検証である。 |
| [Adaptive Retrieval Without Self-Knowledge? Bringing Uncertainty Back Home](https://aclanthology.org/2025.acl-long.319/)（ACL 2025） | 多数のAdaptive Retrieval手法を、回答品質・自己認識・効率などの観点で比較する。品質と計算量を併せて評価する必要性に関係する。 | 本研究も修正回数だけでなく、自己評価を含めた総推論コストを測る。ただし、この評価観点や「Adaptiveなら効率的」という結論を新規に確立済みとはしない。 |

Doctor-RAGについては2026年6月12日版（v2）を参照した。文献確認時点でarXiv上の
プレプリントとして扱い、査読済みの採択論文と同一視しない。論文・発表前に版と掲載状況を再確認する。
その他の文献も、本文で使う主張・引用箇所に対応した書誌情報を最終的に整える。

## 3. 差別化と貢献の候補

### 3.1 限定した修正予算で、原因に合った処理を選ぶ効果と限界

最大1回のRecovery、回答生成は初回を含め最大2回という条件で、再検索、同じContextからの
再生成、回答Rewriteを選ぶ。この条件下で、どの失敗ではどの修正が役立ち、どの失敗では
修正しても改善しないかを調べる。補助LLM呼び出しはこの回答生成回数と別に計上する。

例えば、根拠が取得できているのに回答へ根拠外の情報を追加した場合、再検索より同じContextからの
修正が有効かを検討する。ただしこれは検証対象の例であり、現時点で効果を確認した事実ではない。
実験条件の違いだけでは貢献として弱いため、失敗種別・診断誤り・修復成功・悪化の関係まで分析する。

R/F/Aは失敗原因の代理指標であり、閾値による分類が真の原因を特定したとは限らない。
複数Failureが同時に起きる可能性もある。Ruleの優先順位や低Confidence時の選択は設計上の
ヒューリスティックであって、因果的な診断の正しさが保証されたものではない。
独立したFailure正解Labelとの照合が必要である。

### 3.2 制御用の自己評価と、成果を測る独立品質評価を分ける

ConfidenceやR/F/Aが上昇しても、実際の回答が正しくなったとは限らない。
方式名・制御Scoreを伏せた独立評価で、品質Label Y、Failure Label、根拠外Claimを判定し、
自己評価の改善と実品質の改善が一致するかを確認する。LLMのLabel案は人手確認の代替とはしない。

高Confidenceの誤答、正しい回答への不要なRecovery、修正による悪化も報告する。
Hallucination率の主集計は「事実Claimに1つでも根拠外Claimを含む回答」の回答単位、
ECEは独立品質Label Yに対するraw Confidenceの10 Bin評価とし、初回・最終を分ける。
Label、監査、判定不能の処理などの詳細はDataset Guideの承認済み定義に従う。

これらは妥当な実験のための要件であり、独立評価自体を世界初の手法とは位置づけない。
本研究の制御がどの程度誤るかを説明するための証拠として使う。

### 3.3 自己評価の費用を含めた品質と総推論コストの関係

Adaptiveは修正回数が少なくても、R/F/Aの評価、Claim抽出、根拠確認などに費用がかかる。
Always Rewriteより総LLM Calls・Token・Latencyが増える可能性がある。
したがって、修正回数の減少だけでH2を支持せず、実行に必要な自己評価・補助処理を含めて比較する。
全方式を採点するOffline評価は制御に使う推論とは分けて記録する。

品質と費用を併記し、どの条件で改善と費用が見合うかを調べる。
品質が下がった方式を単に「効率的」と結論づけない。一定品質を維持した効率改善を主張する場合は、
品質維持の判定基準をEvaluation前に固定し、結果を見て基準を変えない。

## 4. 本研究の有用性

実用上の有用性は、限られた計算資源で信頼できる回答を得るための処理選択に根拠を与えることである。
具体的には次の問いに答えることを目指す。

- 根拠不足のときと、根拠の利用を誤ったときで、必要な修正処理は変わるか。
- 常時修正と比べて、自己評価を含む総費用を抑えつつ回答品質を維持・改善できるか。
- Confidenceが高いのに誤っている回答を、どの程度見逃すか。
- どの失敗で修復でき、どの状況で正しい回答まで悪化させるか。

学術上は、明示的な制御Ruleを固定条件で評価し、その有効条件と失敗例を再現可能な形で示すことに
価値がある。例えば小型Evaluatorの誤診でRecoveryが逆効果になる場合、その割合や原因を示す結果は
設計の限界を説明する。ただし、単に「改善しなかった」と述べるだけでなく、比較の妥当性と分析が必要である。

学士卒業研究としては、範囲を限定した研究質問、関連研究との関係、公平な比較、独立評価、結果に
基づく考察を揃えることを目指す。採択や卒業要件の充足を保証する記述ではなく、最終的な評価は
所属機関の基準・指導教員の判断による。

## 5. 論文の主張に関係する設計上の未解決事項

### 5.1 BaselineとGeneration Failure Recoveryの差を具体化する

Phase 5の初回生成Promptは、既に「取得Passageだけを根拠とする」「根拠外の情報を追加しない」
「情報不足なら回答を控える」という制約を含む。
現在のRecoveryの追加制約例はこれらと重なっており、同じ制約を列挙するだけでは、
何を変更する処理なのか、通常の再生成との差が十分に定義されていない。

Recovery実装前に、初回生成から追加・変更するPrompt、入出力、生成設定を固定し、
どの変更の効果を調べるのかを説明する。現在の承認済み入力は「元の質問＋初回と同じContext」である。
初回回答や自己評価の診断を渡す方法は設計候補であり、現時点の入力仕様や実装済み機能ではない。
入力を変更する場合は理由・影響を明記し、研究計画・実装計画・共通Prompt・比較条件を整合させる。
この文書追記によって、その入力変更を決定したとは扱わない。

### 5.2 起動判断と修正方法の選択を区別する

承認済みの主比較はBaseline、Always Query Rewrite、Adaptiveの3方式である。
AlwaysとAdaptiveでは、Recoveryの起動と修正方法の両方が異なる。
主比較の差は仕組み全体の効果であり、片方だけの効果に帰属させない。

| 比較・分析 | 調べられる内容 | 現在の扱い |
|---|---|---|
| Baseline / Always / Adaptive | 修正なし・常時修正・評価に応じた修正という仕組み全体の品質と費用 | 承認済みの主比較。未実施。 |
| 常時Query Rewrite / Adaptiveの起動条件でQuery Rewrite | 修正方法を揃えたときの起動判断の効果 | 既存計画にある補助実験。未実施。 |
| 同じAdaptive起動条件で固定の修正 / 原因に応じた修正 | 起動判断を揃えたときの修正方法選択の効果 | 追加の設計候補。固定修正の内容などは未確定、未実施。 |

原因に応じた選択自体の有効性を論文で主張するなら、最後の比較などで切り分ける必要がある。
追加実験を採用する場合は、初回結果・起動条件・共通Module・Model・最大Recovery予算を揃え、
Evaluation前に具体的な条件を固定する。実行コストは修正方法ごとに実測し、同額とは仮定しない。
追加実験を行わない場合は、主張を仕組み全体の効果と観察した失敗別の傾向に限定する。
先行手法の実装・同条件比較もまだ行っておらず、Self-RAGやDoctor-RAGに優れるとは主張しない。

### 5.3 仮説と必要な証拠

| 仮説・主張 | 必要な証拠・注意点 |
|---|---|
| H1: 通常RAGより信頼性が向上する | 独立品質Y・Hallucination・修復/悪化の比較。制御Scoreの上昇だけで判断しない。主比較では自己評価とRecoveryを含む仕組み全体の効果を検証する。 |
| H2: AdaptiveはAlwaysより効率的である | 自己評価を含む総LLM Calls・Token・Latencyと品質の併記。費用増加や品質低下の可能性も検証する。 |
| H3: Confidenceは実品質と相関する | 独立品質Yとの関係、ECE、高Confidence誤答の分析。相関だけで採用閾値の妥当性や確率としてのCalibrationを保証しない。 |
| 原因に合った修正選択が役立つ | 独立Failure Label・診断の誤り・修復/悪化の分析。選択の個別効果を主張するなら、起動条件を揃えた追加比較が必要。 |

## 6. 論文・発表時の主張範囲と記載事項

- 自己評価、Adaptiveな検索、Failure別修復、R/F/Aの評価観点は既存研究と重なることを示す。
  差別化は対象・処理予算・制御方法と、実験で得られた知見を組み合わせて説明する。
- 現時点では「世界初」「先行研究に優れる」「信頼性や効率が向上した」「Confidenceが正確な確率」
  とは記載しない。新規性の最終判断には文献調査の更新が必要である。
- 実験結果は、固定したCorpus、内部Split、Model、Prompt、Runtime、言語・質問形式の範囲で解釈する。
  他Model、日本語、外部Web検索、別Dataset、長いAgent軌跡への一般化は別の検証が必要である。
- Datasetの出典・License、SplitとManifest、Model/RuntimeのRevision、Prompt、閾値、推論予算、
  独立Labelの基準、評価者の一致と判定不能例、共通条件、全推論費用、実施/未実施を記載する。
- 事前に固定したEvaluationで仮説を検証し、推定値に加えて不確実性を示す方法を事前に決める。
  少数のDevelopment例や動作確認を、最終的な性能比較と混同しない。
- 論文・発表前に本書の関連研究を更新し、貢献候補を実験結果で支持できる主張へ書き換える。
  改善しなかった点、診断誤り、悪化、限界も示す。

現時点の要約は、「自己修正RAGの原理の新規提案」ではなく、
「1回のRecovery予算に制約した評価駆動の制御について、回答品質・総費用・失敗例を検証する卒業研究」
である。これは研究の位置づけであり、性能や新規性を検証済みという意味ではない。

## 7. 参照文献

以下は本書の比較に用いた文献であり、卒業論文では指定の引用形式に整える。

- Asai, A., et al. (2024). [Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection](https://arxiv.org/abs/2310.11511). ICLR 2024.
- Yan, S.-Q., et al. (2024). [Corrective Retrieval Augmented Generation](https://arxiv.org/abs/2401.15884). arXiv:2401.15884.
- Jeong, S., et al. (2024). [Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity](https://aclanthology.org/2024.naacl-long.389/). NAACL 2024.
- Jiao, S., et al. (2026). [Doctor-RAG: A Failure-Aware Repair Framework for Agentic Retrieval-Augmented Generation](https://arxiv.org/abs/2604.00865). arXiv:2604.00865, v2（2026年6月12日）.
- Saad-Falcon, J., et al. (2024). [ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems](https://aclanthology.org/2024.naacl-long.20/). NAACL 2024.
- Murugaraj, K., et al. (2026). [RAGVUE: A Diagnostic View for Explainable and Automated Evaluation of Retrieval-Augmented Generation](https://aclanthology.org/2026.eacl-demo.35/). EACL 2026 System Demonstrations.
- Moskvoretskii, V., et al. (2025). [Adaptive Retrieval Without Self-Knowledge? Bringing Uncertainty Back Home](https://aclanthology.org/2025.acl-long.319/). ACL 2025.
