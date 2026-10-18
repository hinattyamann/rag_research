# RAG研究のテーマ変更候補と文献調査メモ

調査日: 2026年10月9日。対象期間: 同日までに公開された原論文・著者公開資料。
状態: **検討用の提案。テーマ変更、仕様変更、実験実施を決定した文書ではない。**
ユーザーから共有された実装・実験期間: 3〜4か月程度。

2026年10月18日追記: 投稿先としてICIAE 2027が共有されたため、
[新規性の再調査とICIAE向け三案・日程](iciae2027_research_direction_review.md)を作成した。
公式の通常初回フルペーパー締切は2026年11月20日、2027年1月8日は最終原稿締切である。
追加調査でD2R-RAG・GroundedCache等との重なりを確認し、本書の候補Aの優先度を下げた。
以下は10月9日時点の候補記録として保持し、現在の優先度は新メモを参照する。

現行仕様は[研究計画Version 6.11](rag_research_plan.md)、
[実装計画Version 7.15](rag_implementation_plan.md)による。
従来テーマの位置づけは[関連研究の整理](related_research_positioning.md)を参照する。

## 1. 調査の目的・確認の範囲

目的は、原因別Recoveryの組合せにとどまらず、既存Baselineを使って検証できる新しい研究質問を探すことである。
原論文のAbstract・公式掲載情報を広く確認し、近接する論文では方法・指標・限界の該当本文も確認した。
全論文を全文精読した体系的レビューではない。以下の差別化・優先度は文献に基づく判断であり、
未調査の類似研究が存在しないことや、新規性が確立したことを意味しない。
arXivの公開だけで査読済みとは扱わず、採録が公式ページで確認できた場合のみ掲載先を記す。

現状はPhase 6/Gate 6まで完了。CLAPNQのQA 4,345件、Corpus 178,890件、Title単位の研究用Split、
BM25/Embedding/Hybrid、ローカル生成、入出力・Token・時間・Hashの保存を再利用できる。
Generatorは開発用Qwen2.5-3B-Instruct GGUF Q4_K_M、CPU実行、Context 4,096 Token。
自己評価・Recovery・人手による独立品質の成績測定は未実装/未実施。
研究室Ubuntu PCのGPU詳細と最終Generator/Evaluatorは未確定である。

## 2. 文献から分かった重なり

- 原因に応じた修復は[Doctor-RAG](https://arxiv.org/abs/2604.00865)で扱われる。
  原因分類を介さない処理選択も[RePAIR](https://aclanthology.org/2026.acl-short.14/)に近い。
- 現回答の正しさと修正の改善見込みを分けて学ぶ発想は
  [Return or Revise?](https://arxiv.org/abs/2609.30087)が直接扱う。
  前回提案した「修正の有効性を予測する」案は、この研究との比較なしに手法新規性を主張できない。
- 同じ失敗への根拠追加/削除は[Pair-ID](https://arxiv.org/abs/2608.08944)、
  根拠のREMOVE/REPLACE/DUPLICATEは[CUE-R](https://arxiv.org/abs/2604.05467)に近い。
- 検索指標と回答性能の違いは[eRAG](https://arxiv.org/abs/2404.13781)、
  検索有用性の予測は[ECIR 2026の研究](https://arxiv.org/abs/2601.14546)で扱われる。
- 生成側の文書順序感度は[Stable-RAG](https://aclanthology.org/2026.acl-long.1188/)、
  質問の言い換えによるAdaptive RAGの変動は
  [How You Ask Matters!](https://arxiv.org/abs/2604.10745)に近い。
- 完全性・Claim Recall・重要な内容の網羅は[RAGChecker](https://arxiv.org/abs/2408.08067)、
  [Do RAG Systems Cover What Matters?](https://aclanthology.org/2025.naacl-long.301/)などで扱われる。

「小型モデルで実行」「日本語化」「指標を追加」「閾値を変更」だけを独立した貢献とはしない。
具体的な問い、近い先行との差、公平な対照、得られた結果の説明を組にしてテーマを選ぶ。

## 3. 候補の比較

負担は現行Baselineを再利用する場合の暫定判断であり、完了期間の保証ではない。
優先度は実現性と問いの切り分けやすさによる。新規性の強さを検証済みの順位ではない。

| 候補 | 問いの転換 | 追加実装 | 主な評価負担 | 暫定優先度 |
|---|---|---|---|---|
| A 文書更新と回答再利用 | 生成直後の品質から、更新後も回答を残してよいかへ | 更新Fixture、再利用/無効化の判定 | 更新後の正解・必要な無効化の人手確認 | 高 |
| B 人工失敗から自然失敗への移行 | 修正方式の性能から、その性能評価はデータの作り方に依存するかへ | 対応する失敗生成・同じ修正の比較 | 人工/自然の条件差と独立品質の確認 | 高 |
| C 自己評価による制御の安定性 | 生成器の頑健性から、評価器の揺れが修正制御へ及ぼす影響へ | Evaluator、提示順操作、簡単な修正処理 | 固定回答の正誤と修正後品質 | 高、実装の切り分けが容易 |
| D 条件・例外の保持 | 事実の正しさから、回答が成立する適用範囲の保持へ | 対象データ、条件と本文の関係を保つ処理 | 条件・例外・適用範囲のAnnotation | 中、Dataset変更が必要な可能性 |
| E 理想修復と実行可能な再検索 | 根拠を渡せば直ることから、自力でその改善を実現できるかへ | Goldありの分析条件とGoldなし再検索 | 取得/投入/利用の失敗と長文品質 | 中、既存基盤との相性は高い |
| F 人が誤答に気づくための根拠表示 | モデルの正答率から、人の適切な採用・棄却へ | 表示UI、参加者向け評価 | 参加者募集・実験運用 | 条件付き、研究の方向は大きく変わる |

## 4. 候補A: 文書更新後の回答再利用と、引用に基づく依存管理

仮題: **文書更新下におけるRAG回答再利用の妥当性と再生成費用の分析**。

### 研究質問と具体例

引用文書が変わっていなければ、過去の回答を再利用してよいのか。
未引用の根拠更新、回答の適用条件を変える追記、新たな反証追加も含めて、
どの判定が古い回答の見逃しと不要な再生成を抑えるかを調べる。

例えば回答が文書Aを引用した後、別文書Bへ適用例外が追加される。
AのHashは同じでも、従来回答の適用範囲が過大になる場合がある。
更新によって何が正解になるかは実験側で明示する。新しい文書が常に正しいとは仮定しない。

### 最も近い先行と、狙う差分

[Correctness is not Faithfulness in RAG Attributions](https://arxiv.org/abs/2412.18004)は、
主張を支持する引用と、実際の回答生成が依存した証拠を区別する。
[FinCacheServe](https://arxiv.org/abs/2607.26076)は回答再利用をVersion/Fingerprint等で管理する。
本文第3節のDependency Freshnessは、記録された依存の整合性を対象とし、内容の正確性は別に評価する。
同手法は取得根拠Fingerprint等も使うため、「引用文書のみ変更を検知する方式」と同一視しない。
これらから、依存の記録範囲と回答の現在の妥当性の関係を比較監査する問いを導く。

Corpus変化のテスト自体は
[When Knowledge Changes](https://arxiv.org/abs/2607.26843)に近い。
本候補は、更新に対する回答の変化の検出に加え、**回答を再利用する判定の見逃し/過剰無効化と費用**を対象にする。
[ERASE](https://aclanthology.org/2025.findings-naacl.168/)は外部KBのFactを新しい文書に合わせて編集するため、
意味的な知識更新も先行研究がある。保存済み回答の無効化範囲と再生成判断へ対象を絞る。
更新テスト、Cache、依存管理の発明とは位置づけない。採用前にCache再検証の近接研究をさらに精査する。

### 実験の骨格

最初はDevelopment 30〜50問の検索結果と初回回答を固定し、別VersionのFixtureへ更新を施す。
原Corpus・Manifestを上書きしない。引用根拠の意味変更、未引用の影響ある根拠の意味変更、
新たな反証追加、意味を変えない編集を分ける。

比較する判定は、毎回再生成、引用文書変更時のみ再生成、取得文書全体の変更で再生成、
更新後に検索結果を再検証して再利用、更新差分と回答Claimの関係を確認して再生成。
最初の統制実験は検索後の文書集合を操作し、本実験でIndex更新と再検索を含める。
後者を行わない場合は検索後の根拠更新の範囲に結論を限定する。

主指標は更新後に成立しない回答の再利用率、必要な無効化の検出率、不要な無効化率、
総Token/時間/生成回数。単なるキャッシュHit率で安全性を主張しない。
初回から誤っていた回答と、更新により成立しなくなった回答を区別する。
最初の成立性確認は初回正答20〜30件と数種類の更新でもよく、全体性能をその条件だけから主張しない。
引用IDの欠損・不正や引用抽出の失敗は別カテゴリに記録し、再利用判定の効果と混同しない。
毎回再生成でも誤答は起きるため、それ自体を正解Oracleとは扱わない。
内容の採点は更新前後の根拠・正解に基づく独立評価とする。

合成更新は管理された根拠変更として明示し、可能なら少量の自然な文書更新を追加する。
予備実験の完了条件は、更新の正解を人手で確定でき、各無効化方式の差を測れることである。
全更新で同じ判定しか出ない場合は、本テーマの成立性を見直す。

## 5. 候補B: 人工的な失敗で得た修正判断は、自然な失敗に通用するか

仮題: **失敗評価データの生成方法がRAG修正方式の評価と汎化に与える影響**。

Phase 7で予定しているGold欠落・Distractor等の人工条件そのものを研究対象にする。
人工失敗で調整した判定を、BM25/Embedding/Hybridの実検索で自然に生じる失敗へ適用したとき、
修正方式の順位、改善率、悪化率、費用が変わるかを調べる。

[Pair-ID](https://arxiv.org/abs/2608.08944)は自然な失敗への根拠介入、
[RePAIR](https://aclanthology.org/2026.acl-short.14/)は修正行動の学習を扱う。
介入や自然失敗を使うこと自体は新規性としない。
狙う差分は、**同じ質問系列・同じ修正方式で、調整用失敗の生成方法だけを変えた際の移行と順位変化**である。
人工/自然のDistribution Shiftを扱う近接研究の追加調査が必要である。

予備実験ではDevelopmentの質問を先に固定し、自然な初回検索結果と対応する人工条件を作る。
採否を修正の成功/失敗で選ばない。自然失敗と人工失敗で質問の難易度、根拠量、初回品質の分布が
違う点を報告する。同じ質問でも意味・答えが変わる人工変形は別に扱う。
再検索、同じContextの再生成、回答Rewriteなど少数の修正を同じ予算で比較する。

本実験では人工のみ・自然のみ・混合で調整する条件と、常に同じ修正を使う条件を設ける。
質問とその変形群を同じSplitへまとめ、Calibrationだけで調整し、Evaluationは最終比較に固定する。
主指標は独立品質の改善/悪化、総費用、移行後の性能低下、方式順位の変化と不確実性。
ScoreやFailure Labelだけではなく、実際の修正効果を測る。

成立性を確かめる条件は、自然失敗を十分確保でき、対応する人工条件の意味・正解を監査できること。
少数例の順位逆転だけを一般的な結論にしない。現在のPhase 7へ最も接続しやすい候補である。

## 6. 候補C: 根拠提示に対する自己評価の不変性と、修正制御の安定性

仮題: **根拠提示順序に起因するRAG自己評価の揺らぎと修正判断への影響**。

回答と根拠の内容は全く同じでも、Evaluatorへ渡す文書の順序が変わると、
採否や修正方法が変わり、追加費用・正答悪化につながるかを調べる。

[Stable-RAG](https://aclanthology.org/2026.acl-long.1188/)は生成器の文書順序感度、
[ContextualJudgeBench](https://aclanthology.org/2025.acl-long.470/)は文脈付き評価の難しさを扱う。
順序Biasや評価器の不安定さの発見だけでは弱い。
狙う差分は、**Evaluator側の根拠順序の影響をGenerator側から分離し、判断反転が最終品質と費用へ伝わる過程**である。
Evaluatorの文書順序と閉じた修正Loopを直接扱う既存研究の精査が必要。

Development 30〜50問で初回回答を固定し、元順序・逆順・複数Shuffle・同一順序の反復を比較する。
引用ID対応、根拠の内容、Prompt内のToken予算、実際に使われる本文を保持する。
切詰めで見える情報が変わった例は、純粋な順序効果と分ける。
Score変動、採否反転、選択不一致を測り、分岐した場合の修正結果を独立に採点する。
本実験では生成時と評価時の順序を交差させ、影響を分離する。

改善候補は固定順序、Claimごとの根拠参照、複数順序で判定が一致した場合のみ修正する方式。
固定順序は再現性を高めても正確性を保証しない。
一致を求める方式は必要な修正を見逃す可能性があり、追加評価費用とともに測る。
全例のRecovery実装より先に、評価だけの予備実験で成立性を確認できる。

## 7. 候補D: 条件・例外を落とさない回答と、適用範囲の保持

仮題: **RAG回答における適用条件・例外の欠落分析と範囲を保持する根拠提示**。

例として、根拠「事前承認がある場合のみ利用可能」に対し、回答が「利用可能」となる問題を扱う。
一般的な事実の追加Hallucinationと、限定条件の省略による過大な一般化を分ける。
問いは、原則と例外が別Passageにある場合、検索・Context整形・生成のどこで条件が失われ、
どの対策が必要かである。

否定検索は[NevIR](https://aclanthology.org/2024.eacl-long.139/)と
[その再現・拡張](https://arxiv.org/abs/2502.13506)で扱われる。
[Disco-RAG](https://aclanthology.org/2026.acl-long.189/)は談話構造を使い、条件付き根拠の過大な一般化も問題にする。
[工学文書の研究](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1697169/full)も
複数条件の例外処理の難しさを報告する。
したがって、条件・例外の問題の発見や構造化の発想を新規とはしない。
差分を狙うなら、**原則と例外の距離・検索成否を制御して欠落の発生箇所を区別し、
適用範囲の誤りを直接測る小さなBenchmarkと対策の比較**へ限定する。

CLAPNQの条件を含む例を監査し、不足する場合は公開の利用規程やソフトウェア仕様等の別Corpusを使う。
単なるDataset変更は貢献にしない。正解は原則・適用条件・例外・対応根拠を人手で確定する。
規則が判断不能な例は分ける。研究実験の規程例を実際の判断助言として使わない。

対照は通常Top-k、周辺/参照Passageの追加、条件を明記したPrompt、原則と例外を結ぶ提示、
必要なら既存の談話構造手法の実行可能な条件とする。
評価は適用範囲の正しさ、条件保持、根拠外の条件追加、必要例外の未取得と取得済み無視、総費用。
Annotation負担は高め。予備実験で評価者間の解釈を揃えられるかが採用判断になる。

## 8. 候補E: 理想的根拠修復と、実行可能な再検索の乖離

仮題: **RAGにおける理想的根拠修復と実行可能なRecoveryの乖離分析**。

Gold根拠を渡せば直る失敗のうち、正解を見ないQuery Rewriteと実際の再検索で直せるものはどれだけか。
差が、根拠の取得、入力Contextへの投入、生成での利用のどこに残るかを調べる。

[Pair-ID](https://arxiv.org/abs/2608.08944)の本文第6節はOracle的な根拠編集の範囲を明示し、
Live Retriever、長文生成、Deployment Latencyを対象外とする。
一方、OracleとRetrievedの性能差自体は以前からある分析なので、単なる差の再測定では弱い。
**同じ自然失敗に実際の再検索行動を適用し、各段階で失われた改善余地を、長文品質と費用を含めて分ける**ことを狙う。

初回、Gold根拠を投入する分析条件、GoldなしQuery Rewrite+検索、同じContextからの再生成を比較する。
Goldは分析用の条件だけに使い、実行可能な方式や選択器へ渡さない。
同じ入出力Token予算を設定し、理想条件でも未改善、未取得、取得したが未投入、投入したが未利用を記録する。
独立採点なしに単一Gold未取得だけで回答失敗を確定しない。
制約付き再生成を使う場合は、初回Promptとの実際の差を先に定義する。

既存Data・検索・生成を最も直接再利用できる。新手法の提案よりも、実行可能な修復の限界と
ボトルネックを説明する実証研究に向く。A〜Cよりも従来テーマとの連続性が高い。

## 9. 候補F: ユーザーが誤答を見抜くための根拠表示

仮題: **RAG回答の根拠表示が、誤答の検出と採用判断に与える影響**。

モデルの回答正解率から、人が正しい回答を採用し、誤った回答を棄却できるかへ研究対象を変える。
同じ回答について、引用リンク、該当根拠の抜粋、回答が未確認の条件/論点を併記する表示を比較する。
満足度や「信頼できそう」という評定だけでなく、誤答発見率、正答棄却率、確認時間を測る。

[Citations and Trust in LLM Generated Responses](https://ojs.aaai.org/index.php/AAAI/article/view/34550)は
引用と信頼の関係、[Trust Me on This](https://arxiv.org/abs/2601.14460)は
出典・根拠・情報Coverageの説明を比較する。
[CHI 2025の研究](https://research.ibm.com/publications/exploring-trust-and-transparency-in-retrieval-augmented-generation-for-domain-experts)も
根拠の透明性とユーザーの理解を扱うため、根拠表示を追加するだけでは新規とは言えない。

差分を狙う問いは、**条件/例外の欠落を含む回答について、一定の確認時間内で誤答を見抜くことと、
正答を不要に棄却しないことを両立する表示は何か**。
表示によって判断材料の量が変わるため、通常の抜粋表示と、同程度の長さの別表示を対照にする。
参加者の事前知識、提示順、同じ問題の繰返し学習を統制する。

生成は既存Baselineで先に行い、実験時は保存済み回答を使える。
一方、参加者募集、必要人数の設計、所属機関の参加者実験手続きが必要で、3〜4か月で実施できるかは
指導教員・協力者の条件次第。モデルの新手法提案からHCI/情報行動の実証研究へ大きく変わる候補である。

## 10. 暫定的な推奨と3〜4か月の進め方

問いを大きく変えて現行基盤を使うならA、Phase 7の計画を研究対象へ変えるならB、
予備実験の切り分けを容易にするならCを上位候補とする。
Dは条件/例外のAnnotationを作る意思がある場合、Fは参加者実験の体制がある場合に検討する。
Eは従来の修復テーマを活かす実証研究として残す。
複数候補を1つの卒研へ全部組み込まず、主研究質問は1つに絞る。

1. **最初の1〜2週間**: A/B/Cのうち関心のある2案について近い2〜3論文を精読し、
   Development 20〜30問で成立性と採点時間を確認する。新しいEvaluationの成績を調整に使わない。
2. **次の1〜2週間**: 研究質問、近い先行との差、必要データ、対照、主指標、採用するModelを確定する。
   この時点で指導教員へ候補比較と予備結果を示す。選択したテーマに合わせて正式計画・Phaseを更新する。
3. **2か月目**: Data/Annotationと比較方式を実装し、Calibrationで条件を固定する。
   元Data・旧実験は保持し、変更した条件を新Version/Manifestで管理する。
4. **3か月目**: 固定Evaluationで比較・独立採点・失敗分析を行い、論文の図表と本文を作る。
5. **4か月目が使える場合**: 追加Modelまたは自然な更新例等、主張に最も必要な1軸を検証し、執筆・再現確認に充てる。

本実験の件数は「従来の各150件」を自動流用しない。
予備実験の実行/採点時間と効果のばらつきを基に決める。
同じ質問から作った変形を独立した問題数として数えず、質問またはTitle単位で不確実性を評価する。
効用・安全性の閾値や比較の基準は最終Evaluation前に固定する。
小型LLMの単一条件だけの場合は、一般的なRAG性能へ結論を拡張しない。

## 11. 参考文献と確認箇所

以下はテーマ選定に使用した主要資料。掲載状態は調査時に確認できた範囲に限定する。
「本文」は方法/指標/限界等の該当部分の確認であり、全文を精読済みという意味ではない。

| 文献 | 掲載/公開情報 | 確認箇所・本メモとの関係 |
|---|---|---|
| [Doctor-RAG](https://arxiv.org/abs/2604.00865) | arXiv、2026年4月、v2は6月 | Abstract・関連する方法。原因別修復の重なり |
| [RePAIR](https://aclanthology.org/2026.acl-short.14/) | ACL 2026 Short Papers | 公式掲載情報・Abstract。分類を介さない修正選択 |
| [Return or Revise?](https://arxiv.org/abs/2609.30087) | arXiv、2026年9月24日 | Abstract・方法概要。修正効果予測の直接の近接研究 |
| [Pair-ID / What Would Fix This RAG Failure?](https://arxiv.org/abs/2608.08944) | arXiv、2026年8月9日 | 本文の介入・限界。自然失敗とOracle根拠修復 |
| [Correctness is not Faithfulness in RAG Attributions](https://arxiv.org/abs/2412.18004) | arXiv、2024年12月 | 本文の引用依存の区別。候補A |
| [FinCacheServe](https://arxiv.org/abs/2607.26076) | arXiv、2026年7月14日、preprintと記載 | 本文第3/4/8節等。依存契約・再利用と品質の区別 |
| [When Knowledge Changes](https://arxiv.org/abs/2607.26843) | arXiv、2026年7月29日、ASE 2026と記載 | Abstract・Mutation/Scope。Corpus更新テストの近接研究 |
| [Language Modeling with Editable External Knowledge / ERASE](https://aclanthology.org/2025.findings-naacl.168/) | Findings of NAACL 2025 | 本文第3節等。新しい文書に基づく外部KBのFact更新 |
| [CUE-R](https://arxiv.org/abs/2604.05467) | arXiv、2026年4月 | 本文の根拠介入・Confidence/Utility。単純介入案の重なり |
| [DRAGged into Conflicts](https://arxiv.org/abs/2506.08500) | arXiv、2025年6月 | Abstract・矛盾の分類。一般的矛盾処理の重なり |
| [eRAG / Evaluating Retrieval Quality in RAG](https://arxiv.org/abs/2404.13781) | SIGIR 2024、著者公開論文 | 本文/掲載情報。検索品質と回答品質 |
| [Predicting Retrieval Utility and Answer Quality](https://arxiv.org/abs/2601.14546) | ECIR 2026とarXiv掲載情報に記載 | Abstract・予測対象。検索有用性予測の重なり |
| [Predicting Partial Answer Quality and Utility](https://arxiv.org/abs/2609.16453) | arXiv、2026年9月15日 | Abstract。Agentic RAGの品質/改善量の予測 |
| [How You Ask Matters!](https://arxiv.org/abs/2604.10745) | arXiv、2026年4月12日 | 本文/Abstract。質問表現・処理判断・費用の変動 |
| [Stable-RAG](https://aclanthology.org/2026.acl-long.1188/) | ACL 2026 | 本文の方法・限界。Generator順序感度 |
| [ContextualJudgeBench](https://aclanthology.org/2025.acl-long.470/) | ACL 2025 | 本文の構築/指標・Abstract。文脈評価と不完全回答 |
| [RAGChecker](https://arxiv.org/abs/2408.08067) | 著者公開論文、2024年8月 | 本文のClaim指標・人手比較。完全性/根拠性 |
| [Do RAG Systems Cover What Matters?](https://aclanthology.org/2025.naacl-long.301/) | NAACL 2025 | 本文/Abstract。重要なSub-questionのCoverage |
| [Q-CARE](https://arxiv.org/abs/2608.11238) | 著者公開論文、2026年 | Abstract。Query CoverageとClaim検証の評価 |
| [NevIR](https://aclanthology.org/2024.eacl-long.139/) | EACL 2024 | 本文/Abstract。否定に対するIRの弱さ |
| [Reproducing NevIR](https://arxiv.org/abs/2502.13506) | SIGIR 2025、公式書誌確認 | Abstract。否定理解の再現とDataset間移行 |
| [Disco-RAG](https://aclanthology.org/2026.acl-long.189/) | ACL 2026 | 本文の条件付き根拠の例・方法。候補Dの近接研究 |
| [Advancing engineering research through context-aware and KG-based RAG](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1697169/full) | Frontiers in AI、2025年 | 本文のMulti-condition exceptions。候補D |
| [Citations and Trust in LLM Generated Responses](https://ojs.aaai.org/index.php/AAAI/article/view/34550) | AAAI 2025、公式掲載情報 | Abstract。引用表示と信頼の関係 |
| [Trust Me on This](https://arxiv.org/abs/2601.14460) | arXiv、2026年1月20日 | Abstract。根拠・Coverage説明のユーザー実験 |
| [Exploring Trust and Transparency in RAG for Domain Experts](https://research.ibm.com/publications/exploring-trust-and-transparency-in-retrieval-augmented-generation-for-domain-experts) | CHI 2025、著者所属機関掲載情報 | Abstract。根拠透明性・ユーザー理解 |

## 12. 今回の実施・未実施

実施: 現行計画・実装条件の確認、原論文の調査、6候補の問い/先行との差/対照/負担の整理。
未実施: テーマの決定、正式計画の変更、Evaluator/Recovery/Cache等の実装、予備実験、性能採点。
Phase 6まで完了という実装状態と、従来の実験条件は維持している。
