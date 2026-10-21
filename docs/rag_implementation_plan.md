# RAG自己評価の順序感度・修復判断分析の実装計画

## Version 8.34 — 2026年10月21日 最終JSON境界の別制約と人工Runtime検証を追加

[研究計画 Version 7.31](rag_research_plan.md)の実装仕様。
[ロードマップ](research_roadmap.md)を工程・現在地の正本とする。
[旧実装計画 Version 7.15](archive/rag_implementation_plan_v7_15.md)は保存版であり、旧Phase 7以降を実装しない。
Phase 7の専用Config/Prompt・採点基準・入力検証CLIを作成した。
Phase 8の固定Trace・Claim抽出・Judge・順序/反復・判断と再開を実装した。
Phase 9の一回書換え・独立採点Export/Import・候補選択・経路費用を実装し、開発2件の書換えを実走した。
ユーザーのAI採点委任により、Gate 9をAI代行による開発確認として通過した。人手確認済みとは記録しない。
Phase 10は事前選定20問、固定Baseline、順序別Judge、一回書換え、匿名AI採点、Pilot Reportの実行層を追加した。
初回20問・書換え20件・40候補の採点と集計を完了した。[結果と修正項目](phase10_pilot.md)による。
完全比較11問、Fの順序変化1例、判断反転0例。事実本文の空Claim等の測定上の問題があり、最終凍結は未着手である。
測定系をv14へ改訂し、明確な判定15例・書換え5例・長い7主張の診断を完了した。
新規10問の内部評価36回・書換え10回・匿名20候補AI採点を完了し、両Cohortの全Label固定後に集計した。
元v14は35有効・引用ID重複による失敗1回、完全比較3問。事前Gate不通過を不変で保持する。
後処理v15は実在する同一引用IDだけを整理し、Raw出力・Boolean・理由を保持して全36出力を事後再検証した。
既存有効35出力の判定は不変で、完全比較4問となった。追加Model呼出し0、新しいModel実験とは区別する。
Astrosの順序判断反転1問と改善見逃しを元v14でも確認した。[修正後の結果](phase10_recheck_results.md)による。
既知の正しい日付結論の誤棄却は限界として残し、診断成功を一般精度100%とは扱わない。
開発3候補の[AI代行採点JSON](phase9_ai_quality_review.md)は別保存し、既存Validatorで検証した。
人手Importへは投入せず、元のModule・Schema・Run・基準Versionは変更していない。
Phase 7の入力検証CLIは引き続きCompletion 0回である。

2026年10月21日、英語CLAPNQと仕様を近づけた別の日本語Datasetを使う比較方針を採用した。
翻訳対を主実験に使わない。[選定・比較・工程の方針](english_japanese_expansion.md)に従い、
第11節の未実装事項をPhase 11で終え、両言語の条件を固定してからPhase 12へ進む。

その後、既知回帰v1は読解が配列で始まり条件付きJSON制約が未到達となって5/30条件で停止した。21 Call/他25条件未試行・再開追加0を保持。
[終了Tag境界の別候補v7](phase11_json_boundary.md)を固定し、人工Runtime検証後に同じ128 Call診断から再確認する。主Development/未使用Calibration・最終Gateは未了。

## 1. 既存実装と保存する境界

現行の任意候補`verification_mode: claimwise-v1`は`evaluation/claimwise.py`で個別Journalと集計を共用する。
原固定文をローカルc1へ写して元IDへ戻し、全分母・失敗時null・実Call/Token/時間をRawから検証する。
完了単位は再呼出しせず、未集計/結果不明/部分再開と既存Server Logを保全する。旧Configはjointのまま。
Config v4/Plan v2の最大70 Callを事前検証した。実GPUの意味診断は次工程。
その後、既知16 Call/4集計・元ID/全分母・実費/再開追加0を確認したが、Critical2/4で意味不通過と保存した。
独立に`experiments/statistics.py`でQA内ペア不一致増分、言語別QA平均/独立Group Bootstrap・日英差/95%区間を実装した。
全474 Test/Ruff成功、品質封印済み実RunへのAdapterと最終規模/条件は未了。草稿なし読解の次候補は計画のみ。
その後、`source-reading-v1`をTask/共通評価/品質Import/実費と意味診断へ実装した。読解は質問/根拠だけ、原文Quoteと全IDを検証する。
全487 Test/Ruff成功。読解58+固定文70の最大128 Call/事前上限を保存し、固定Commitの実GPU診断はこれから。
その後、v5は読解のID/Quote対応不正で1 Call停止（固定文判定0）。v6だけ`fixed_ids_exact_quotes_v2`で一意ID/原文Quoteを制約し、旧v5を保持した。全488 Test/Ruff成功、v6実走は未了。
その後、固定v6は生成0 Preflight/既知Critical4条件全一致、人工54条件実行中。`bilingual_statistics.py`とCLIで全Labelを先に検証し、Raw/Group/全選定と失敗費用から事前統計へ接続した。全493 Test/Ruff成功。現AdapterはDevelopment用で、Calibrationへの経路拡張と最終Gateは未了。
その後、v6全58条件/128 Callと再開追加0を検証し、事前意味診断基準に通過した。残るLabel下位分類/読解の誤りも保存。
共通診断Runnerに既知Trace回帰の前提Report/Model/Runtime/Core・旧Expected保持・正例基準を追加し、全502 Test/Ruff成功。Configは同じv6条件を保持し、最大114 Call/全15 QAを実走前に固定した。

現行の次工程は[意味診断の事前計画](phase11_semantic_revision.md)。`semantic_diagnostics.py`は旧Trace/Expectedの一致と
共通Task契約を確認し、既知Critical4条件の全一致後だけ人工54条件へ進む。Source/Model/Runtime/全CodeをHashへ固定し、
Expected漏洩防止・失敗/中断後の再開追加0・未試行/既試行の保存を新規7 Testで確認した。実GPU診断はこれから。
その後、固定93c3611で先行4条件を実走し、1/4一致で拡大を停止した。全450 Test/Ruffの検証に加え再開追加0を実機確認した。
Source/Expectedと実行条件を保持したPrompt改訂v2を追加し、事前契約/日英同一Judge・予算を確認した。別固定実走は次工程。
その後、v2も2/4一致で停止、失敗/再開追加0を保存した。8B公式GGUFのByte/Hashを確認し、共通Aux契約のManifestと候補v3を追加した。
全58条件の実Token/CUDA起動をCompletion0で確認するPreflight入口を用意した。8B資源/意味実走・新Fallback実装は未了。
その後、8B資源確認は成功、意味Criticalは2/4不通過と保存した。次の固定文ごとの方法候補は事前計画のみで未実装。
`decide_with_refusal`と任意の`decision.bare_refusal_policy`を追加した。裸の拒否だけnull/unscorableのまま一回書換えを要求し、
通常障害/空Claimや旧Configを変更しない。評価/品質検証/費用へ同じRuleを適用し、全459 Test/Ruffと旧保存例の事後再構成を確認した。

2026年10月21日追記: [日英共通RAG接続候補](phase11_bilingual_pipeline.md)を追加した。
`study_assets`がHash付き日英QA/Corpus/Index/親対応を検証し、Factoryは同じE5 CUDA/Subword BM25/RRFを使う。
別Development入口で既存`baseline_once`/`evaluate_traces`/`rewrite_once`を共用し、旧工程の制約は保持する。
匿名品質Packetは日本語の引用位置/人手要約/欠測の来歴と英語の親対応をOfflineで示す。
全441 Test/Ruff成功、再開追加0・中断/失敗保持・漏洩防止・匿名化とLabel固定を確認。実GPU接続・意味監査は次工程。
その後、日本語1問の初回/Judge9/書換えを固定Commitで実走した。英語生成前に判明したSource省略互換をFactoryで修正し、
日英の実Index経由Testを追加して全443 Test/Ruffに成功。旧失敗/Code/Runを保持し、Assets/英語接続Config v2で再実走する。
その後、英語v2実走・日英匿名4候補の固定とImport・全3文/27判定のAI意味確認まで完了した。
全18 Judge形式有効/入力超過0、両言語の再開追加0。既知各1問・肯定例のみで、意味採用Gateや主Pilot成功とは扱わない。

| 既存資産 | 現状と利用方法 |
|---|---|
| CLAPNQ Loader/Schema/Split | 実装済み。Source・Base Data・Split・既存Manifestを変更しない |
| BM25/Embedding/Hybrid | 実装済み。共通検索としてPhase 6条件を使用 |
| `BaselinePipeline` | retrieve/generateの2 Node。`run(question)`の既存CLIを維持 |
| `LocalGenerator.generate_record` | 実装済み。初回回答と実入力・使用Context・監査を保存 |
| `generation/context.py` | 元検索順で切詰める実装。順序変更実験のために呼び直さない |
| `configs/phase6.yaml` / `configs/prompts.yaml` | 既存Baseline用。今回の文書更新では変更しない |

Phase 6はWindows CPUでGate 6を通過した履歴である。現在は第10節の別VersionでUbuntu/CUDAを確認済み。
Runtime/Model変更は旧Manifest上書きではなく別実験Versionで記録し、必要なCalibrationをやり直す。
Phase 6の5問・135 Tests成功は当時の記録であり、新Moduleの検証実績ではない。

## 2. 新しく実装する処理

```text
QA選定（評価Metadataは別管理）
  → 既存Baselineで初回回答保存
  → 固定Traceへの正規化とHash検証
  ├→ 回答のみからClaim抽出・固定 → 根拠順序/反復ごとの検証 → 採用/修復判断
  └→ 元質問・元使用Context・初回回答 → 固定書換え候補
独立品質用の盲検化Export → 研究者の採点Import
  → 同じ候補から各方式の最終回答を再構成 → 統計・費用・図表
```

既存Baselineへの条件分岐追加ではなく、保存済み結果を読み込む実験層を加える。
評価器の操作とGeneratorの操作を分け、Gold入りQA辞書をそのまま評価器へ渡さない。

### 新規配置（Phase 10まで実装。最終実験用の拡張は後続工程）

Phase 10では`pilot/selection.py`で既知Titleを除外した結果非依存選定、`baseline.py`で初回生成のJournal、
`internal.py`で旧固定推論の実行と再開、`materials.py`で質問ごとの匿名資料出力、
`assessment.py`でAI採点の記録、`report.py`で採点固定後の条件別照合を実装した。
旧Phase 8/9のソース・設定は変更せず、`configs/phase10.yaml`と専用ProtocolでAI採点方針を定める。

| 配置 | 責務 |
|---|---|
| `src/rag_research/experiments/frozen_trace.py` | Run対応、入力/回答/使用本文のHash、既存成功Recordの固定 |
| `src/rag_research/evaluation/claims.py` | ClaimのJSON/連続ID/本文検証。実抽出と保存はtasks.py |
| `src/rag_research/evaluation/order.py` | 元/逆/Shuffle・反復、安定ID、重複順序の検出 |
| `src/rag_research/evaluation/judge.py` | Claim判定/原文引用の検証とF計算。実Prompt/呼出しはtasks.py |
| `src/rag_research/evaluation/tasks.py` | 実Model呼出し、実Prompt/Token、出力検証・費用・Checkpoint |
| `src/rag_research/experiments/protocol.py` | Phase 8設定の検証と推論入力のWhitelist |
| `src/rag_research/experiments/storage.py` | Hash付き保存・原子的Checkpoint・Run単位排他Lock |
| `src/rag_research/experiments/order_runner.py` | Development所属/元Baseline来歴確認、実行・再開、記述的集計 |
| `src/rag_research/recovery/answer_rewrite.py` | 固定1回書換え、同一予算・失敗・再開記録 |
| `src/rag_research/experiments/repair_runner.py` | Phase 8保存結果の来歴照合、質問ごとに1候補を収集 |
| `src/rag_research/experiments/decisions.py` | F閾値、採用/書換え要求/FallbackのAction。候補本文の選択はPhase 9 |
| `src/rag_research/experiments/quality.py` | 条件を隠すExport/Import、独立Yと理由、整合確認、候補選択・四遷移・経路費用 |
| `src/rag_research/experiments/quality_form.py` | 外部送信のない採点HTML、JSONの途中保存・再読込 |
| `src/rag_research/experiments/analysis.py`（後続予定） | 対応集計、信頼区間、品質遷移、費用の区別 |
| `src/rag_research/evaluation/schema.py` | JSON/原文引用候補のDecoder制約。全順序で同じSchemaを使う |
| `configs/order_phase8_v5.yaml` / `configs/order_prompts_phase8_v5.yaml` | 現在の制約付き開発用設定。初期版/v2/v3/v4は履歴として維持 |
| `scripts/run_order_evaluation.py` | 保存済みDevelopment回答の実評価CLI。Pilot選定ではない |
| `scripts/render_order_example.py` | 実出力を比較する説明用Markdown。盲検化した品質採点用ではない |

作成済みの`scripts/check_order_protocol.py`はPhase 7の検証専用で、
実ModelのChat Template/Tokenizerを使って入力を測り、Completionは0回とする。
手順と検証範囲は[Phase 7記録](phase7_order_protocol.md)を参照する。

本書の仮Pathは実装済みコマンドとしてREADMEへ掲載しない。
Python実行・依存追加はuv。実装変更時に`uv run pytest`と`uv run ruff check .`を実施する。

## 3. 新しいデータ契約

Recordを`schema_version / study_version / record_id / run_id`、Trace/Manifest Hash等で結び、以下を分離保存する。
本実験までの契約を含む表であり、Phase 8ではRun Manifest・固定Trace・Claim・Judge・判断を実装した。
未見Sample選定、書換え・独立品質・本分析は後続工程である。

| Record | 必須の内容 |
|---|---|
| Sample Manifest | Split、Title Group、選定Rule/Seed/ID、Source/Split/検索/Model/PromptのHash |
| Frozen Trace | 質問、初回回答、実使用Context・元順序・Hash。取得全文、初回Prompt/Token/費用は元Baselineファイルを参照し、元回答・来歴のHashとrecord_idで対応 |
| Fixed Claims | 初回回答Hash、抽出Prompt/Model/Seed、順序付きClaim ID/本文、抽出状態・費用 |
| Judge Trial | Trace/Claim Hash、順序ID/実表示Passage ID列、反復番号、Model/温度/Seed、実Prompt/Token Hash |
| Judge Result | ClaimごとのLabel・根拠ID/引用、F、採用/修復、エラー、処理時間・Input/Output Token/Calls |
| Rewrite Candidate | Trace Hash、元Context順序、Prompt/Model/Seed、書換え回答、状態、費用 |
| Blind Mapping | 採点用IDと元の質問/候補との対応。採点用表示とは別保存 |
| Independent Quality | 採点用ID、基準Version、Y、必須要点/誤り/支持の確認、理由・根拠、判定不能理由 |
| Analysis Manifest | 全入力Hash、主比較、分母・除外Rule、統計Seed/反復数、結果・図表のHash |

保存先は`data/runs/order_sensitivity/{run_id}/`とし、Manifestでstudy_versionとRunを対応させる。
Raw Runと採点結果はGit対象外。
小さい固定条件Manifest/集計のみ、既存のGit方針とLicense・公開範囲を確認して管理する。
全候補本文を無断で新規Git対象にしない。既存Source/Phase 6 Manifestへ研究結果を追記しない。

### 推論に入れない情報

Reference、Gold Passage ID/Selected Sentences、Answerability、品質Y、条件別分析LabelはOffline側だけに保持する。
取得した文書のPassage IDを引用識別子として使うことと、正解IDの印を渡すことは別である。
Judgeへ渡すのは元質問、固定回答/Claim、固定使用Context、評価指示のみ。
書換えへ渡すのは元質問、元順序の固定使用Context、初回回答、修正指示のみ。

## 4. Promptと入力予算

### Claim抽出

初回Pilot後の修正候補は`evaluation/sentence_claims.py`と`configs/order_phase10_v3.yaml`。
3Bの意味誤りが残るため、`configs/order_phase10_v4.yaml`ではJudge/書換えの7B候補を明示する。
`generation/auxiliary.py`で専用Manifestと全ModelファイルのHashを検証し、`LocalServer`へ渡す。
既存`artifacts.model_identity()`と初回3Bは変更しない。RunにはBaselineと補助Modelの両方を記録する。
初回回答を決定的な文単位として保持し、本文の再構成を検証する。原子的な事実分解ではない。
候補v3は抽出のModel呼出し0回。Fの分母と費用が旧v5と異なるため、Runと結果を分ける。
`json_schema_source_spans_compact_v3`は理由→証拠→Labelの順に出力し、引用320文字・理由120文字、
支持/矛盾には最低1件の原文引用をDecoder側でも要求する。引用集合は提示順序から独立する。
補助Context 12,288・Judge出力予約3,072を用い、入力本文の切詰めや自動再試行は行わない。
既知診断と新規10問の条件・完了基準、事後の引用重複修正は[測定系修正記録](phase10_measurement_revision.md)による。
さらに`configs/order_phase10_v6.yaml`は、巨大な引用Enumを外したJSONと原文への引用位置解決を検証する候補。
`evaluation/quote_alignment.py`はRaw引用を保持し、単語列の一意一致だけを原文へ解決する。
語順・語/数値/否定の違いは修正せず失敗とする。理由400文字、Judge出力予約4,096。
根拠→質問/初回回答→固定Claimの入力順も全条件へ共通適用する。
`configs/order_phase10_v7.yaml`は同じJudgeと、1回のJSON点検付き書換えを組み合わせる候補。
`source_facts`/`draft_issues`/`answer`を1回で生成し、最後のanswerのみを候補として保存する。
`configs/order_phase10_v14.yaml`はQwen3-4Bによる追加候補であり、初回生成3Bは維持する。
補助専用Sampling、Runtime推論予算512、Context8,192、Judge/書換え全体上限2,048を明示する。
終了タグ・実Token列を監査し、推論を閉じた後のJSONだけを厳密に検証する。
終了タグ後のJSON開始括弧を捕捉する正規表現で、最終JSONだけのSchema制約を有効にする。
Native設定と実出力の開始位置を監査し、無視された形式制約を有効と記録しない。
Judgeは矛盾有無/全詳細支持の二値を返し、固定Ruleで三Labelに対応付ける。
実在IDに対応する原文全体を監査用に添付し、モデルが選択した証拠Spanとは区別する。
形式検証は意味上の正解を保証しない。既知の正しい結論の誤棄却も記録する。
詳細と候補ごとの診断は[修正記録](phase10_measurement_revision.md)による。
全体予約1,024、最終回答のTokenizer長は512以内。点検欄もToken/時間/Callsの費用へ含める。
自動再試行、候補の事後選別、Judge Feedbackの追加は行わない。
以下の原子的Claim抽出と8,192/1,536予算は初回Pilotまでの履歴である。

回答内の検証可能な最小の事実主張だけを順序付きJSONで抽出する。回答を訂正・補完せず、
質問・根拠・Referenceを使って主張を追加しない。拒否やClaimなしと抽出失敗を区別する。
回答HashをKeyに、同じ回答のClaimを全試行で固定する。抽出の内容妥当性をPilotで監査する。

### 根拠検証

固定Claimを根拠本文だけに照らし`supported / contradicted / not_supported`へ分類する。
根拠は指示ではなくDataとして扱い、与えられていない知識で支持しない。
支持/矛盾の根拠IDと短い原文引用を要求し、未知ID・本文にない引用を構造検証する。
引用一致は意味上の支持を保証しないため、独立した監査を別に行う。
Claimの欠損/重複、未知Label、範囲外Scoreを許可せず、FはLLMの自己申告値ではなくLabel数から計算する。

固定した文書オブジェクトの配列順だけを変える。ID・本文・Titleは不変。
元検索順位を表示順位として書き換えたり、文書番号を振り直したりしない。順序以外の変更が必要なら別条件にする。
全Promptを実Tokenizerで計測し、Claim/回答追加で予算を超えたら本文を削らず`input_overflow`とする。
Pilotで予算・Modelの妥当性を見て、Phase 11前に十分な入力窓か共通の適格条件を決める。
Model名、固定Revision、量子化、Tokenizer、Runtime、温度、Seed、入力窓、最大出力、Threadsを保存する。

### 書換え

初回回答を点検し、根拠外・矛盾・質問への不足を修正して、回答全体と根拠IDを返す指示にする。
根拠が不十分ならその旨を述べ、情報を補って捏造しない。Scoreや診断は渡さない。
初回と同じTokenizer・書換え最大出力512を維持する。Phase 7の実測により、補助Runtimeの入力窓は8,192とした。
Claim抽出の最大出力は1,024、根拠検証は1,536。初回生成の入力窓4,096は変更しない。
21入力Probeで入力+出力予約が最大5,748、6 Probeが4,096を超えたため、情報量を保つ目的で変更した。
Phase 8で実Claimと根拠の入力予算を都度検査する。少数のSmokeを全QAの収まりの検証と扱わない。
超過時にContextを削らない。別予算へ変える場合は実装・計画・Configに理由を記載し、比較全条件へ共通適用する。
Phase 7の初期PromptとPhase 8の開発改訂を分けて保持し、各Runへ実際のHashを保存する。
開発用の固定とPhase 11の最終凍結を区別する。

## 5. 試行・判断・再開

- 初期の順序群は元/逆/Shuffle 3通り、反復群は元順序5回。共通初回を含め9呼出し/問/評価器を基本とする。
- Model切替え等の交絡を避け、呼出し順・Seed方針を記録する。温度0でも同一入力反復を測る。
- 通常の`accept/rewrite`は有効Fのみ。F>=τが採用、F<τが書換え。τ初期0.7、最終凍結はPhase 11。
- Claimなし・拒否等は`not_applicable`、JSON不正/timeout等は`error`として、両者を区別する。
- 採点不能/評価失敗は`unscorable`、最終回答は初回保持。書換え失敗時も初回保持し`rewrite_failed`を記録する。
- 隠れた追加回答生成は行わない。主実験の抽出/評価/書換えの自動再試行上限は初期0とし、変更時はPhase 11で固定する。
- 再開は未実施Trialだけを対象にする。既存の有効出力を再抽選しない。Hash差は上書きせず停止する。
- 同一Promptの反復もTrialごとに実Modelを呼び出す。Prompt HashだけのCacheで反復を省略しない。
  再開用KeyはTrial ID・Model/設定を含め、同一Promptを測り直す目的と計算結果の再利用を区別する。
- Runtime障害による再実行は元失敗も保持し、Protocolに従い費用へ計上する。成功まで繰り返して失敗を消さない。

最終品質比較は同じ初回/書換えの保存結果から経路を再構成する。
Fallbackは採用の正解認定ではない。正常例の共通比較と、Fallbackを含む全対象の運用結果を分けて示す。

## 6. 独立品質評価の実装

Exportは質問・候補本文・同じ実使用Context・Reference/Gold根拠・基準のみを表示する。
方式名、順序、Score、判断、初回/修復の区別を隠す。初回と修復は無作為順に並べ、対応表は別保存。
自己評価のClaim分解・検証理由も表示せず、回答全体の誤りと欠落を独立に調べる。
Importで候補Hash/基準Version/採点用IDを検証し、未採点をY=0へ変換しない。
AIの確認経過時間・判定理由・再確認履歴・実採点者を残す。人間の採点時間や独立した二者一致度とはしない。
来歴にhuman_reviewed=falseとモデル識別子の取得可否を保存する。旧人手ImportへAI Labelを流し込まない。
Yと判定不能の定義は研究計画第6節、分母は同第7節にそろえる。

Phase 9実装では匿名IDをSeed 44で決定し、別対応表を保存する。同一の質問/候補/Context/Referenceは一度採点する。
基準本文の練習例は表示しない。採点基準Version、Packet/Candidate Hash、ID集合、引用の原文一致、
3観点とLabelの整合、理由・要点・確認者・秒数・日時を検証する。
Importは日付付き新Directoryへ保存し、過去のAnnotationを上書きしない。
未採点と判定不能を分け、既知の四遷移へ算入するのは初回/書換え双方のYが確定したQAだけである。
書換え失敗時の候補は採点対象へ追加せず、最終出力は初回Fallbackに対応付ける。
CLI・実出力・未確認事項は[Phase 9記録](phase9_answer_rewrite.md)による。
Phase 10では初回の質問ごとに匿名Packetを封印して採点を進め、全候補の採点JSONを固定してから
内部結果と対応表を開示する。完全有効な順序群/反復群の共通QAで不一致率の差を記述集計する。
最終統計、正式な信頼区間、本番の採点セッション固定は後続工程とする。
実走後はCLIに固定済みBaselineの読取専用再利用を追加し、内部Manifestが参照する来歴Hashを変えない。
推論Module・Prompt・Configは変えていない。実データの再参照・内部再開は追加Completion 0回、
来歴不変の回帰確認を含む全223 TestとRuffが成功した。

## 7. 集計と計算量

質問内の全ペア不一致を一つの質問の値へまとめ、元質問/Titleの対応を保持する。
順序群と反復群は共通初回を持つ対応比較であり、独立した二群と仮定しない。
品質はY0/Y1から四遷移と条件ごとの最終Yを構成する。修復なし/常時修復も同じ候補を使用する。
条件別の構成比、分母0、Claimなし、判定不能、実行失敗を明示し、各Metricの適用対象を固定する。

費用は次を別集計する。

1. 実験収集の実Calls/Token/壁時計時間（全Trial・全候補・失敗を含む）。
2. 各方式の運用経路費用（共通初回＋その方式の抽出/評価＋必要時書換え）。
3. Offline品質採点・分析の費用。

Cacheで共用しても、各方式へ必要な初回/書換え費用を計上する。
保存済み処理時間を足した経路推計を実運用の測定Latencyとは呼ばない。
200問・9回・評価器2種類ならJudge 3,600回が出発目安。Claim抽出・候補生成等は別に加わる。
本実験件数・別評価器の範囲はPilotの実測平均時間と採点負担から決める。

## 8. 確認・Testの実装範囲

- 既存Baseline/Source/Manifestを変更せず再利用でき、推論へ評価専用Fieldが漏れない。
- 同一Traceで文書集合と本文Hashは一致し、順序だけが変わる。重複順序・文書1件・Seed再現を扱える。
- 逆順/Shuffleでも再Packing・再切詰めせず、実Prompt全体の超過を検知する。
- 同一順序の5反復が実際に呼び出され、共通初回を除く評価の省略や二重計上がない。
- 固定Claimの再利用、空Claim、JSON不正、未知ID/Label、欠損Claim、引用不一致を扱う。
- Fの計算・閾値等号・採点不能Fallback・再試行0・Hash差停止が仕様どおり。
- 書換えに元Contextと初回回答だけを渡し、Judge FeedbackやGoldを入れない。全条件で同じ候補を選ぶ。
- 盲検Exportに条件/段階/Scoreがなく、Importは未採点・Hash不一致を検知する。
- 四遷移、判断ペア分母、適用不能、共通QA、品質不明の感度分析、費用の共用補正を小さな手計算例と照合する。
- 予備のDevelopment実入力でModel応答の妥当性・入力完全性・時間を確認する。Mock成功だけでGateを通さない。

今後の実装Testには挙動の境界・漏洩・公平性を検証するものを用い、単にコードをなぞるTestを増やさない。
Phase 7は入力検証、Phase 8は固定Trace・順序/反復・Claim/引用/Score・失敗・再開・来歴照合の
境界Testと少数Developmentの実応答確認を行った。Phase 9で独立品質Export/Import、書換え失敗、
品質遷移、方式別運用費用、保存データ改変検知の34 Testを追加した。
全216 Test成功。実際の品質採点と統計・信頼区間は後続工程である。
実績と既知の問題は[Phase 8記録](phase8_order_evaluation.md)と[Phase 9記録](phase9_answer_rewrite.md)へ残す。

## 9. Phaseと成果物の対応

Phase 11の初期実装は`calibration/preparation.py`・`calibration/report.py`と
`scripts/run_calibration.py`、`configs/phase11_calibration.yaml`・`order_phase11_calibration.yaml`。
既存のProtocol/Trace読込・Baseline・内部実行は、明示的な`split="calibration"`のときだけ
Calibrationへ対応する。既定のDevelopment条件を維持し、Evaluationは許可しない。
初回生成は`--max-new-questions`で未実施件数だけを制限でき、全選定ID・失敗・未実施を保持する。
内部実行は全Baselineの試行終了後に開始し、匿名品質の全Label固定前には内部結果を開示しない。
候補ManifestはConfig/Prompt/Model Manifest/全研究Module/依存定義のHashに結び、
変更時には既存Runを上書きせず新Versionとする。旧Runの来歴Hashも更新しない。
`status`は公開進捗と未確認事項だけを示し、`report`は品質採点後にだけ内部結果を照合する。
どちらも`gate11_passed=false`・`phase12_allowed=false`。これは初期実装時の範囲である。
具体的な実行手順・確認済み/未実施の区分は[Phase 11記録](phase11_calibration.md)による。

本実装として`scripts/finalize_phase11.py`と判断草案`configs/phase11_freeze_decisions.json`を追加した。
匿名品質の全Label・来歴を確認してから内部対応を読み、元Taskと集計を照合する。
Parser/実行、全固定文の意味監査、拒否Fallback、外部品質、CUDA実行、分析計画がそろったときだけ
新しい最終Manifestを保存する。固定済み条件の変更・上書きは拒否する。
現在のCUDA根拠と本番件数は未決であり、検証処理の成功を実験完了と呼ばない。
Evaluationの対象ID選定はSplit ManifestのIDだけで行い、質問本文や結果で選ばない。
`scripts/assess_calibration.py`は公開済みPacketの専用Lockを用い、内部実行中も匿名採点を進められる。
`scripts/inspect_execution_environment.py`はOS/Memory/Disk/GPU/Driver等の記録専用で、推論成功の証拠とはしない。
詳細・研究室側の確認事項は[最終固定とGPU引継ぎ](phase11_finalization.md)による。

Phase 1〜6は完了済み、Phase 7で専用Protocol・Prompt・設定を具体化、Phase 8で固定Trace/Judge/順序、
Phase 9で書換えと独立採点の入出力、Phase 10でPilot、Phase 11で最終凍結、Phase 12で本実験、
Phase 13で分析（任意の対策を含む）、Phase 14でICIAE原稿と卒論を進める。
各工程の実施状況・完了条件は[ロードマップ](research_roadmap.md)を参照する。

## 10. Ubuntu/CUDA候補の追加

`generation/cuda_runtime.py`と`configs/lab_cuda_runtime.json`で、公式b11433 Linux CUDA版と
SHA固定した既設CUDA 12.9ライブラリを別Directoryへ準備する。
既定のWindows CPU経路を保ち、Configの明示的`execution`がある場合だけ切り替える。
`LocalServer`はCUDAデバイス・全Layer Offloadをログで検証してからCompletionを許可する。
RunへRuntime全ファイルHash、Command、Version、Offload、時間を保存する。
初回と補助の両方へ明示設定を伝え、`pilot`の来歴にもRuntimeを含める。

`scripts/audit_lab_transfer.py`はSource/Split/Corpus/Index/過去RunのHashを読取専用で確認し、
Evaluationの本文は解析しない。`scripts/audit_lab_models.py`は全現行モデルを転送前Hashと照合する。
既知Developmentの実GPU確認は`probe_lab_generation.py`、既存の測定診断CLI、
`probe_lab_judge_semantics.py`で行う。これらへ未使用20問を渡さない。

追加Calibrationは`phase11_gpu_calibration_v2.yaml`と`order_phase11_gpu_calibration_v2.yaml`。
元の20問Manifestを上書きせず、除外Title/選定規則/全IDを照合して再利用する入口を追加した。
初回Promptは元のまま。補助推論1536/出力3072、Context8192、最終回答512以下。
事前Health Gateは20問で完全比較8問以上、Judgeエラー率0、入力超過で途中停止。
意味上の合否・品質・最終Gateは別監査とし、Health Gateだけで最終凍結しない。
旧CPU Runは再開せず、新RunとソースSnapshotを使う。詳細は[実機検証記録](phase11_lab_validation.md)。

2026年10月20日の[GPU追加Calibration結果](phase11_lab_validation.md)では20問/40候補の採点を固定し、
Judge108回・完全比較12問・Health Gate通過、全34固定文のAI意味監査まで完了した。
順序判断反転1/12・同順序反転0/12を確認したが、明確な誤支持が残り最終条件の採用は保留する。
本番200問・元/逆/Shuffle3種・同順序5回・Title対応Bootstrap10000回/95%CIは案で未凍結。
今回の20問を未使用へ戻さず、別の未使用20問を事前選定した。新候補の回帰診断と条件保存後に確認し、
意味妥当性・分析規模と最終ManifestがそろうまでGate 11を通さず、Phase 12は開始しない。

## 11. 日本語Dataset追加と日英比較への拡張（Phase 11、対応中）

Sourceは[候補比較・構造監査](japanese_dataset_selection.md)により
`baobab-trees/wikipedia-human-retrieval-ja`、Revision `02e85c83a64f345aee62fba3a35af99c075a331f`を選定した。
回答付き838件と回答なし433件は取得・Hash照合済み。参照断片だけのOracle条件は主検索にしない。
全検索記録の記事全文の取得・整形・分割を別Versionで実装し、原QAの文ごとの引用と人手要約を区別する。
複数の引用記事を持つQAは連結Groupとして分割し、Redirect/別名も確認する。
プレビュー閲覧の保守的な開発予約は先頭100件と同Group（初期132 QA）。最終分割は未実施。
選定Manifestは`data/manifests/phase11_japanese_source_selection.json`。
以下の対応対象のうち、Source検証・記事取得処理・日本語文単位を実装した。
全Pipeline・Validatorは未完了で、原QA取得や個別ComponentのTestを日本語対応の完了とは扱わない。

既存の固定Trace・順序操作・同一順序反復・共通書換え・匿名品質採点を再利用する。
英語の旧Run/Source/Split/Manifestは保持し、日本語Sourceと共通処理の変更を別Versionへ保存する。
現行コード・Config・最終固定Validatorは日英比較の準備完了を保証していない。

| 変更対象 | Phase 11で追加・確認する内容 |
|---|---|
| Data Adapter/選定/Split | 日本語QA・Reference・根拠・Corpusを正規化し、Datasetと言語・安定ID・文書Group・取得/分割Hashを保存。CLAPNQ固定Path/IDへの依存を点検する |
| 検索 | 日本語Tokenize/Embeddingと検索品質を開発・Calibrationで確認。英語との差とCorpus/候補集合の条件を記録する |
| 初回生成/Judge/書換え | 共通Modelの日本語での妥当性、指示文の言語方針、支持/矛盾/不足と拒否を確認する |
| `evaluation/sentence_claims.py`等 | 日本語文境界・引用・拒否の扱いと本文保持を検証。日英文単位の定義をそろえ、Fの分母への影響を監査する |
| 入力/出力予算 | 実Tokenizerで計測し、QA内の全順序で同じ根拠本文を保持。日英の実長・根拠数・文単位数を記録する |
| 品質Export/Import | 両言語で同じ意味の品質基準と匿名化を検証。条件・Score・段階を隠し、全品質固定後に内部対応を開く |
| Report/統計 | 言語別のQA内不一致率の増分と日英差、品質・費用・欠測の分母を扱う。日英QA間に対応を仮定しない |
| 最終固定Validator | 日本語Source/Split、実対応、意味監査、英語回帰、両言語の対象/条件/統計の根拠を必須化する |

検索用の言語依存処理と評価器側の順序操作は分け、Gold/Referenceを推論へ渡さない。
新実装では英語の回帰と日本語の境界・漏洩・予算・記録のTestを行い、pytest/Ruffをuvで実行する。
形式成功だけでJudgeの意味妥当性を認定せず、少数Developmentの実走と独立AI採点を監査する。
既知例での修正後は別の未使用Calibrationで確認し、対象・停止条件を新規結果前に保存する。
日本語予備検証の20〜30問は出発目安で、本実験件数・検出力の保証ではない。

Phase 11で両言語のSource/Model/Prompt/文単位/閾値/予算/順序・反復/Fallback/品質基準、
対象ID・件数・除外/欠測・統計を固定する。旧英語200問案を日英の採用件数には転用しない。
Phase 12は日英の本実験と独立採点、Phase 13は固定した計画での統計と比較考察、
Phase 14は原稿への反映。分析処理の拡充をPhase 13で行う場合も、比較・統計の設計はPhase 11で固定する。
別Dataset間の差を言語単独の因果効果とは扱わない。選定と実装の完了状況はロードマップへ反映する。

### 日本語Sourceと記事取得の実装（2026年10月21日）

`data/baobab_source.py`は固定版2ファイルの再取得・Hash検証と、回答/文列/引用対応の検証を行う。
人手要約をquoteへ変換せず、回答なしの検索記録も記事Title一覧の構成へ使う。
`data/wikipedia_snapshot.py`と`scripts/prepare_japanese_corpus.py`は、全参照2178 Titleを
共通の2023-12-25T23:59:59Z以前の最新Revisionで照会し、その`oldid`の本文を取得する。
この共通時点は配布元の収集終了日に基づき、個々のQA収集日時との完全一致は保証しない。

設定は`configs/phase11_japanese_corpus_v1.json`。リクエストは直列、開始間隔0.5秒以上・
maxlag5秒・timeout45秒・最大3試行。429/一時障害はRetry-Afterと待機を記録し、
連続5取得エラーで停止する。これはSource HTTP取得の再試行であり、モデル再試行0とは区別する。
取得先・条件・実行Source Hash・API応答・失敗と本文Hashを保存し、既存の終端失敗を再抽選しない。
古いRevisionが得られない場合に現在版へ切り替えない。再開時に保存応答・Source Snapshotを照合する。

現在のRedirect解決と取得した過去の記事Revisionを別々に保存する。過去RevisionのHTMLも
Template等が現在の状態で描画され得るため、oldidのみを再現性の根拠にせず、実際のAPI応答・抽出本文をHash固定する。
HTMLは実行せず本文へ変換し、見出し・段落・箇条書き・表の文字を保持、Script/Style・脚注番号・ナビゲーション等を除く。

既知の開発記事1件はRevision98468367（2023-12-14）、抽出19251文字で実取得に成功した。
`phase11_japanese_acquisition_preflight.json`にHashと確認範囲を記録した。
全284 Tests（ホスト4.39秒）とRuffに成功。制限環境での既存Socket Test1件の失敗は環境制約として別記録とする。
全文Corpusの全記事取得・Passage化・Group分割・検索・日本語推論Pipelineと最終Validatorはまだ完了していない。

### 日本語の固定文単位候補（2026年10月21日13:44 JST）

`claim_units: verbatim-sentences-ja-v1`を明示したときだけ日本語用処理を使い、
`unit_version: verbatim-sentence-units-ja-v1`を保存する。言語の自動推定は行わない。
旧英語`verbatim-sentences-v1`と既定の関数出力はそのまま保持し、設定名不明は実行前に拒否する。
モード名をTaskの入力Hashへ含め、異なる文単位の保存結果を再利用しない。文抽出のModel呼出しは0。

- 旧英語と同じ既知の数値/Passage引用記号だけを除き、空白を正規化する。未知の角括弧内本文は残す。
- `。！？!?`を空白の有無によらず境界とする。連続句読点はまとめる。小数の`.`は切らず、
  空白を伴う英文の終止`.`は既知の略語/Initialを除いて境界にする。HTTP/HTTPS URL内では切らない。
- `「」『』（）`、対応する括弧・曲線引用符と二重引用符の内側は複合単位として保持する。
  閉じていない括弧は残りをまとめて保持し、未閉鎖の記号を監査情報へ保存する。
- 正規化本文の連続Spanが全文を重複・欠落なく覆うことを検査する。日本語の境界に空白を挿入せず、
  Spanの部分文字列をそのまま連結して本文を再構成する。各ClaimはSpan両端の空白だけを除いたもの。
- 定型拒否「提示された根拠には、この質問に答えるための十分な情報がありません」（句点は任意）と
  既知の英語拒否の単独回答だけを除く。拒否と事実本文の混在や曖昧な拒否は本文として残す。

日英とも固定の原文単位であり原子的事実分解ではない。ただし、日本語候補の引用/括弧内を保守的に
まとめる規則は旧英語の境界規則と完全には同じでない。複合単位は全詳細の支持を必要とし、
単位数とFの分母に影響する。これは本実験採用済みの条件ではなく、Developmentで分割の妥当性と
日英の単位数・複合性を監査する。共通規則へ追加変更する場合も旧英語Runを上書きせず別版で検証する。

合成例のみの新規32 Test、全316 Test成功（ホスト4.62秒）、Ruff成功。
既存英語の保存抽出65件と合成7例は変更前Commitの抽出結果と一致し、既存Run2500ファイルのHashは不変。
`data/manifests/phase11_japanese_sentence_component.json`に確認根拠を保存する。
日本語Model実走・検索・意味上の支持判定・未使用Calibration・日英文単位の最終採用は未完了である。

### 日本語QA Adapterと文書Group分割（2026年10月21日13:59 JST）

`data/japanese_dataset.py`と`scripts/prepare_japanese_dataset.py`を追加した。
設定は`configs/phase11_japanese_dataset_v1.json`。回答付き838件すべてを既存の内部QAの基本Fieldへ対応させ、
言語・原行Hash・引用原文/人手要約・回答文と引用Index・文書Groupを追加で保存する。
原文引用だけを`selected_sentences_by_reference`へ入れ、人手要約を原文へ変換しない。
`gold_passage_ids`はPassage構築前には空のまま`pending_passage_build`を明示し、引用断片のIDを捏造しない。
人手回答の存在は共通Corpusによる回答可能性の保証とは区別する。回答なし433件へ回答不能Labelを付けない。

Groupは回答の引用先に限らず、同QAの全取得記事、正規化Title・Redirect/別名・Page ID・同じ記事全文Hash、
同文の質問/Reference回答の連結成分とする。開発予約が1件でも含まれる成分全体をDevelopment専用とする。
TitleはUnderscore/空白・NFC・Casefoldを保守的に正規化し、RawのTitle/URLはそのまま保持する。
質問/回答の同文確認はNFC・空白除去後のHashによる機械処理のみで、未使用QA本文を条件調整へ閲覧しない。

目標比率は既存英語と同じDevelopment65%・Calibration10%・Evaluation25%、Seed42。
予約GroupをDevelopmentへ割り当て、残りをサイズ降順・Seed付きSHA256順に処理し、
各割当て後の目標QA数との二乗誤差の増分を最小にする。Groupを切り分けたり、都合のよい例を補充したりしない。
実際のQA数と比率のずれを報告し、本実験の言語別採用件数は別途Calibration後に決める。

`audit-source`はTitleと同文Hashによる暫定監査に限定し、`research_split=None`のまま保存する。
実838件の取込み・原行Hashを確認し、暫定706 Group、初期予約132件からの開発閉包142件を得た。
引用先に非quoteを含む94 QAも保持した。同じ出力での再実行は全Byte不変だった。
正式な`build`は完了済みCorpus取得記録と排他的Lockを必要とし、記事/HTTP応答/Revision/本文/Source Archiveの
Hashと取得件数・重複記事の整合を検証する。取得中・未完了・取得エラー未解消では正式Group分割を生成しない。
取得中の実プロセスに対して生成を試み、Lockで拒否されQAが書かれないことも確認した。

新規22 Test、全338 Test成功（ホスト4.54秒）、Ruff成功。既存Run2500ファイルのHashは不変。
確認根拠は`data/manifests/phase11_japanese_dataset_preflight.json`。
Redirect解決後の正式Split、記事Passage化/Gold対応、検索と日本語Model/品質実走はこれからである。

### 多言語検索候補と本文Passage分割（2026年10月21日）

[実装・実機確認記録](phase11_multilingual_retrieval.md)のとおり、公式Multilingual E5 smallの
固定版FP32 ONNX、用途別Prefix・Mask付き平均Pool/L2、512 Token超過の事前拒否を追加した。
BM25には同TokenizerのSubword IDを使い、共通のIndex/検索/RRFを再利用する。
新CorpusのDatasetを明示し、既定のCLAPNQ/旧MiniLM・単語BM25のConfigと既存Indexは保持する。

記事本文の連続文字Spanを実Tokenizerで分け、Prefix/Special込み512 Token以下・全文再構成を確認する。
文字Span・過去Page/Revision・URLと本文Hashを保存し、描画本文Hashを含む96-bit派生数値IDで旧引用形式へ対応する。
QA/ReferenceをCorpus生成へ渡さない。既知の開発1記事19251文字は27 Passage・最大501 Tokenとなり、
CPUでBM25/Embedding/Hybrid検索・入力超過の推論前拒否・再開追加0回を確認した。

新規13 Test、全351 Test/Ruff成功。旧Run2500/英語Index23ファイルのHashと旧既定Configは不変。
確認根拠は`phase11_multilingual_retrieval_preflight.json`。
英語Corpus3130件に新Tokenizerの上限超過があるため、英語にも元のPassage/Gold参照を保持した分割を新Versionで作る。
全Corpus/Gold対応・正式Split、新RAG Factory・指示文/予算/品質への接続、日英の検索/意味監査・Calibrationは未完了。
既存の英語Phase 6用Factoryを、新候補の最終固定済みFactoryとは扱わない。

### 本文欠測と英語Corpusの準備（2026年10月21日）

[Corpus準備・親参照の確認](phase11_corpus_preparation.md)として、削除過去本文の欠測規則を
`source_availability.py`と`phase11_japanese_dataset_v2.json`へ追加した。
保存応答・過去Page/Revision/時点が一致した指定エラーだけを本文取得不能として別記録し、原status=errorを保持する。
v1・Raw・全838 QAを保持し、通信/別権限エラーは未解決として止める。現在版Fallbackや別時点の補充はしない。

`token_bounded_corpus.py`と`scripts/prepare_english_token_corpus.py`で英語の上限超過3130親を分割し、
175760親の元ID/本文を保持した。全183889子・親対応表・実Token上限512を保存し、元の全178890本文を再構成できた。
元QA/Split/Reference/Gold IDを書き換えず、全4345 QAのID/Gold親Metadataのみを機械照合して2074親の欠落0を確認。
`parent_relevance()`は同一Gold親の重複子を加算しない。検索評価/品質への接続は未完了で、各子の完全な支持を仮定しない。

全365 Test/Ruff成功、旧Run2500/英語Index23ファイル不変。新Index・日本語全Corpus/Gold対応・正式Splitは未了。
分離uv環境の合成GPU ProbeはCUDA349/CPU2 NodeとCPU数値差の事前基準を確認したが、正式Encoder/CLIへは未接続。
確認根拠は`phase11_corpus_preparation_manifest.json`。GPU実行の正式対応・Commit固定Index構築、日英RAG実走は次に行う。

### 日本語の全取得と正式Group分割の結果

全2178 Titleを取得し、本文成功2126記録/2118種類のPage・取得不能50・指定削除本文エラー2を保持した。
完了件数・全保存応答/Revision/Source/本文Hash・同一Pageの整合を確認して`02e85c8-groups-v2`を生成した。
838 QA、706 Group、Identity Key4790のGroup間重複0、開発予約142 QAはDevelopmentのみ。
正式SplitはDevelopment545/Calibration84/Evaluation209である。原質問/Reference/行Hash・全838 QAを保持した。
全6494 Rawファイルを正規配置へ複製しByte一致、保存Splitの和集合/互いの非重複と原行対応を独立検証した。
`phase11_japanese_snapshot_group_manifest.json`へ成果物と検証ScriptのHashを保存する。
`gold_passage_ids=[]`/`pending_passage_build`は継続し、記事Passage化・引用/人手要約と欠測の対応は次に行う。

### 多言語Encoderの明示CUDA実行

[実機監査](phase11_embedding_cuda.md)のとおり、専用uv環境と正式Encoder/CLIのGPU入口を追加した。
GPU版Runtime単独・実CUDA Session・Device0/TF32無効を検査し、Pythonの自動Provider Fallbackを無効にする。
Provider/Options/実Session/Runtime版をIndex Configへ含め、異なる条件の再開/検索を拒否する。CPU既定Configは不変。
合成入力のCUDA1396/CPU8 NodeとCPU数値差、既知27 Passageの構築・再開追加0・検索・超過拒否を確認した。
全380 Test/Ruff成功。根拠は`phase11_multilingual_cuda_encoder_manifest.json`。全Corpus Index/日英RAG/Calibrationは未完了。

### 日本語のSource専用Token Corpus

`japanese_token_corpus.py`と専用CLI/Configで、完了済み歴史的Snapshotだけから共通Corpusを生成する。
固定Plan/Source・全保存応答/Revision/本文Hash・欠測規則・一意Pageを検証し、QA/Referenceや未知Fieldを拒否する。
全2118記事から30065 Passage、最大501 Token、全文22341944文字を保持した。
別名をまとめた親子対応表と全2178 TitleのCatalogを保存し、取得不能50/原削除本文エラー2も保持する。
全保存子のSpan/Hash/実Tokenと全親本文再構成・Raw6494ファイル不変を別Scriptで確認した。
新規12 Testを含む全392 Test/Ruff成功。根拠は`phase11_japanese_token_corpus_manifest.json`。
QAのGold対応は未実装で、原QAの空Gold/保留状態と新Corpusの`pending_qa_parent_and_quote_audit`を維持する。

日英全CorpusのEmbedding IndexはCommit ded26faの固定Checkout・同CUDA/Batch16/専用Lockで構築済み。
英語183889/日本語30065の全Vector・Corpus ID/Offset・親対応、正規配置のByte/Hash、再開追加0/合成検索を確認。
根拠は`phase11_bilingual_dense_index_manifest.json`。新BM25/Hybrid・QA対応・日英RAG実走は未了。

### 日本語参照のOffline監査と全Corpus語彙検索

`japanese_evidence.py`と専用CLI/Configで、固定したGroup/Corpus Reportから全838 QAの引用記事/引用位置を対応させる。
原質問・Reference・Group/Split・原行HashとSource回答有無は保持し、引用/非引用と取得不能を分ける。
`gold_parent_ids`は取得できた引用元記事、`gold_passage_ids`は原文の確認済みSpanと重なる子に限り、検索MetricのGoldへ流用しない。
人手要約は非原文のまま、欠測参照単位も別に保持する。全838件のField/引用/位置/Hashを別Scriptで監査し、全411 Test/Ruff成功。
原HTMLの脚注表示の検証と投影、親単位Metricと品質Packet/Factoryの接続は未実装。
日英BM25は固定Commit ded26faで構築・全Hash/ID/Offsetを確認、合成質問のHybrid動作まで実走した。
根拠は`phase11_japanese_reference_audit_v1.json`と`phase11_bilingual_bm25_hybrid_preflight.json`。

### 原HTML脚注の本文位置投影v2

`wikipedia_reference_projection.py`で実際の`sup.reference`のHTML位置/可視文字/Hashを取得する。
脚注以外の全可視文字が既存Corpus本文へ完全に対応し、引用全体が脚注付き描画に一致する場合だけ、
本文Spanへ投影する。空/非表示要素・別位置/途中の脚注・通常上付きや本文の括弧数字を根拠化しない。
空の脚注で停止した初回処理を保持し、表示文字0から根拠を作らない修正後に全838 QAをv2へ保存した。
全432 Test/Ruff成功、別ScriptのSource接頭部描画/脚注再挿入による全位置/Hash照合と、全6ファイルの同一Byte再利用を確認。
引用位置確認1493・不一致116・原文なし102・原文引用あり本文欠測30。全原QA/Group/Split/欠測とCorpus/Index/v1を保持した。
根拠は`phase11_japanese_reference_projection_v2.json`。親単位Metric/品質Packetと新RAG/Factory接続は未実装。
