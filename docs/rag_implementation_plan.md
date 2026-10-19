# RAG自己評価の順序感度・修復判断分析の実装計画

## Version 8.6 — 2026年10月19日 Phase 10修正後の再確認

[研究計画 Version 7.6](rag_research_plan.md)の実装仕様。
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

## 1. 既存実装と保存する境界

| 既存資産 | 現状と利用方法 |
|---|---|
| CLAPNQ Loader/Schema/Split | 実装済み。Source・Base Data・Split・既存Manifestを変更しない |
| BM25/Embedding/Hybrid | 実装済み。共通検索としてPhase 6条件を使用 |
| `BaselinePipeline` | retrieve/generateの2 Node。`run(question)`の既存CLIを維持 |
| `LocalGenerator.generate_record` | 実装済み。初回回答と実入力・使用Context・監査を保存 |
| `generation/context.py` | 元検索順で切詰める実装。順序変更実験のために呼び直さない |
| `configs/phase6.yaml` / `configs/prompts.yaml` | 既存Baseline用。今回の文書更新では変更しない |

現行はWindows CPUでGate 6通過。Ubuntu/GPUは未確認。
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

Phase 1〜6は完了済み、Phase 7で専用Protocol・Prompt・設定を具体化、Phase 8で固定Trace/Judge/順序、
Phase 9で書換えと独立採点の入出力、Phase 10でPilot、Phase 11で最終凍結、Phase 12で本実験、
Phase 13で分析（任意の対策を含む）、Phase 14でICIAE原稿と卒論を進める。
各工程の実施状況・完了条件は[ロードマップ](research_roadmap.md)を参照する。
