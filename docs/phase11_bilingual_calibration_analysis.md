# Phase 11 Calibrationの匿名採点・隔離した意味/統計解析

2026年10月22日。[専用準備・共通収集](phase11_bilingual_calibration_execution.md)の後続として、
品質/文Expectedの封印と意味・統計・実費の接続を追加した。
現在、通過した実主証明書/実Calibration Runはなく、以下は実装と制御検証の記録である。
実データの採用、最終N/凍結、Gate 11の成功を主張しない。

## 採点の入力と封印

`bilingual_quality.py export`は元の日英Calibration Runから匿名品質Packetを作り、
`review_bilingual_units.py export`は同じ候補/実使用Contextだけの文Packetを作る。
品質採点のReference/Goldを文Expectedへ混ぜない。文Packetは候補段階/F/判断/Referenceを隠す。
全ての文と引用・拒否/文なしの扱いは既存の定義を保つ。

品質QAのPath/HashはAssetsの元Splitと直接照合してから本文を読む。
英語は元Developmentの別予約、日本語は元Calibration、分析用途は両方Calibrationである。
別のQA FileのHashが正しくてもEvaluationを採点入力として読まない。
CalibrationをDevelopmentのPath/用途へ移して解析することも拒否する。

Calibrationの単独Runの`import`から内部対応を開かず、専用の両言語Batchへ進む。
入力JSONは各言語1件で、Fieldは`run`、`quality_bundle`、`quality_annotations`、
`unit_bundle`、`unit_annotations`、全て元のCalibration Run内を指す相対Pathとする。
両言語の全品質/全文Expectedを検査した後だけ私用Hash/内部結果を読み、
片方・どちらかの採点がpending/欠落/不整合なら照合しない。
Development用の既存解析も、全言語の封印後にレビューFileのHashを記録する形へ整理した。

## 原本を保つ解析

`analyze_bilingual_calibration.py --inputs ... --output-dir ...`はModelを起動せず、
元RunをLockして全Fileを同一Byteの隔離コピーへ複製する。MutableなRawをHardlinkしない。
コピーは`bilingual_calibration_replay`配下に置き、実行用/利用履歴用のRootから分ける。
これは同じ使用済み結果の再生で、新たな未使用QAや独立した結果ではない。

元Runとコピーの全Hash、元Protocol/Source・採用済み主条件、全Expected/分母、
両言語の条件一致を検査する。私用ManifestのModel/初回設定の条件Hashも主証拠と照合する。
コピーが改変されていれば再生を許可しない。原本/コピー/封印/入力/検証Sourceの不変を終了時にも調べる。
通常終了/例外/KeyboardInterruptでコピーとLockを解放する。

品質Rubric・統計計画・解析/採点CLIもProtocolのSource Hashへ含め、
新しいCalibration結果を見てから定義を変えられないようにした。
解析自身もこれらの定義を開始/終了で照合する。

## 集計と採否

完成した候補Reportからの意味集計は全予定判定、支持/非支持/曖昧分母、誤支持、完全比較QA、文なし/失敗を保持する。
曖昧は精度だけから除きFの分母から落とさない。
統計は同じ予約全20 QA/20 Groupを使い、不完全/比較不能を別記して補完・補充しない。
QA内判断不一致増分と独立した日英Group Bootstrap/日英差・95%CIは既存の事前計画を使う。
言語差を言語単独の因果効果と呼ばず、反転や有意差・品質改善を成功条件にしない。
意味監査と統計の比較可能件数が一致することも要求する。

初回/補助の実Native Leafを一度ずつ数え、全選定QAのCalls/Token合計と一致を調べる。
実CUDA Session/全層/Context/Runtimeの証拠も別検査する。
資源証拠が欠けた場合はHealthを不通過にし、取得済みの費用は捨てず、未知を補完しない。
Step秒和と起動/検索/採点負担、総応答時間やGPU Kernel時間を区別する。
採点者表示・採点秒、文Expectedに記録された厳密Model IDの有無/履歴分離を保存し、
品質LabelのSchemaから得られない厳密Model IDを推測しない。人手確認false/履歴独立の非仮定は維持する。

成功後は新しい`bilingual_calibration_analysis`配下へ私用結果と全証拠Hashを保存する。
Calibrationのcomponent Gateは両言語の全20健康実行と既定の意味基準/比較数に限り、
最終件数/条件・拡張Validator/最終凍結は別の未完了要件である。
`research_sample_size_frozen`、`gate11_passed`、`phase12_allowed`はfalseを保つ。

## 検証の範囲

合成20 QA/言語で実際のLabel/引用/封印Validator、意味集計、統計とNative費用集計を接続した。
採用前提・Raw再生/一部QA読込み・GPU資源は明示的なDoubleで、実主/実Calの成功とは数えない。
順序差0/CI0でも通過できること、比較9 QAなら全20 QAを残したまま不通過になること、
Native Call欠落/件数不一致、未封印、コピー/原本の改変、定義の途中変更、中断を検証した。
直接/読解方式の合成20 QA収集から品質/文Packetの出力まで接続し、単独importを拒否した。

実保存データでは旧日英接続のQA Path/Hashと元Splitの一致だけを確認し、
旧DevelopmentをCalibration Batchへ渡すと内部照合前に拒否した。旧Sourceを現在のCodeで再認定した意味ではない。
Native Core26+形式Probe1の27 Hashは不変で、固定v13のGPU診断は別Worktreeのまま継続する。
実主/Calの全実走・採点/採用・再開監査から最終凍結までの実証は引き続き必要である。
収集中断で候補Reportが完成していない場合はStop/Raw/未試行を保持し、本Batch解析の成功とは扱わない。
実際の停止Runの採点可能範囲/費用監査も、発生時に別途確認する必要がある。

新規21 Testを含む全674 Test/Ruffに成功した（最終24.54秒）。解析CLIのHelpも確認した。
これは採用前提と実Model/GPUを置換した制御検証を含み、実データでのCal通過は未確認である。
