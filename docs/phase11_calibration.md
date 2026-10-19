# Phase 11 Calibrationの準備と実行手順

2026年10月20日。研究計画7.7・実装計画8.7に対応する。
Phase 10の元の事前Gate不通過、事後の引用重複修正、全生出力と品質Labelは履歴として保持する。

## 目的と今回の範囲

Phase 10で残った課題を確認し、本番の条件を固定する工程を開始する。
今回の実装は、Calibrationの事前選定・候補Manifest・実行・匿名採点・採点後の集計まで。
最終凍結とPhase 12のCLIは含まない。候補Manifestは必ず`candidate_not_frozen`、
`gate11_passed=false`、`phase12_allowed=false`であり、作成成功をGate通過と呼ばない。

実績: 5問を事前固定し、初回生成1問をCPUで実行・保存した。残り4問と内部Judge・書換え・品質採点は未実施。
入力2,104・出力14 Token、生成45.85秒。検索・起動・外部採点を含む応答時間として扱わない。
追加生成0回で保存回答を再利用し、BaselineファイルのByte不変を確認した。
旧Phase 10の834 ArtifactはHash不変。全259 Test成功（27.60秒）、Ruff成功。
選定は[選定Manifest](../data/manifests/phase11_calibration_selection_manifest.json)、
確認は[準備監査Manifest](../data/manifests/phase11_preparation_manifest.json)による。
これらは初期の実行確認であり、生成された回答の品質・評価器精度・順序効果の結果ではない。

初期バッチはCalibration Answerableの異なるTitle 5問。Seed42とIDのSHA256昇順で選ぶ。
回答やF/Yを見て選ばず、失敗・拒否を補充しない。検索Calibrationで同じ母集団225問を
既に用いた履歴を選定Manifestへ明記する。最終Evaluationの本文・回答・結果を読む処理はない。
5問で一般精度や検出力を保証せず、次のバッチが必要なら理由と選定を結果閲覧前に別Versionで固定する。

## 候補条件と比較への影響

- 初回はPhase 6のHybrid Top-10 / Qwen2.5-3Bを維持する。
- Judge/書換えはQwen3-4B、文単位F、tau=0.7、元/逆/Shuffle3種と元順序5反復を候補とする。
- 同一の初回回答・本文・固定文列を全条件で共用し、書換えは元順序で1回、候補を共用する。
- 単独拒否はF=null、初回保持Fallbackを維持する。この扱いの妥当性は未決であり、解消済みにしない。
- 自動再試行0、失敗非補充。入力超過時に根拠を切り詰めない。
- 5問の完全比較が3問未満、Judge失敗1件以上、または入力超過で停止する初期の実行確認ルール。
  F・反転・品質改善の大小を停止条件にしない。Health Gateは意味上の正しさの証明ではない。
- 外部AI品質の3観点と匿名化を維持する。現行採点補助のModel ID未固定・同一作業セッションという
  制約も引き継ぐ。Calibrationの採点が成功しても本番の採点方法を固定済みにしない。

今回の変更は別Split/Runへの入口と来歴管理であり、閾値・拒否ルール・品質定義は変更しない。
旧Development用CLIは既定のまま。共通ModuleのソースHashは変わるため旧Runを新コードで再開せず、
既存SnapshotとManifestを使って保存・検証する。

## 実行手順

リポジトリのルートから実行する。既定出力は`data/runs/calibration/phase11-cpu-five-v1/`。

```powershell
uv run python scripts/run_calibration.py prepare
uv run python scripts/run_calibration.py status
uv run python scripts/run_calibration.py baseline --max-new-questions 1
```

`prepare`はModel呼出し0回。全5問と候補条件を保存する。Config/Prompt/実装/依存定義等のHashが
変わった場合は既存候補を上書きせず停止する。以後は新Version・新Runで確認する。
`baseline --max-new-questions 1`は未実施の質問を最大1問だけ実行し、残りを未実施として残す。
同じコマンドで順番に進められる。失敗済みも試行済みなので再生成しない。
全Baselineの試行終了まで内部実行は開始できない。

```powershell
uv run python scripts/run_calibration.py internal
uv run python scripts/run_calibration.py open-quality --packet 1
uv run python scripts/run_calibration.py save-quality --packet 1 --decision data/runs/calibration/decision.json
```

`internal`はCPUで長時間かかり得る。途中の実験値は非公開ログへ保存し、進捗だけを表示する。
`open-quality`で表示した匿名候補を、基準に従いAIが実際に採点してからdecision JSONを作る。
自動でYを生成・承認する機能ではない。既存の`pilot.assessment`が候補Hash・基準・理由・原文引用を検査する。
各Packetの全候補を採点し、全Packet完了後にだけ次を実行する。

```powershell
uv run python scripts/run_calibration.py report
```

全品質Labelを固定してから内部結果と照合し、比較可能数、失敗、四遷移、方式別費用を保存する。
未採点のまま集計・内部結果の開示はしない。`status`は内部Fや候補段階を読み出さない。
停止時は処理済み候補を全て採点し、停止・未実施のIDも報告する。

## Phase 11完了前に残す判断

| 項目 | 必要な確認・決定 |
|---|---|
| 意味妥当性 | 時期・限定・不確実性・正しい結論の誤棄却。安定性と正しさを区別する |
| 拒否Fallback | 初回拒否から改善できる例の扱いと、その費用・分母 |
| Parser | 重複修正後の処理を新規の実出力で確認する。保存出力のReplayと区別する |
| 外部品質 | 独立入力/セッション、Model識別子の取得可否、制約、入力/出力保存 |
| 環境と規模 | 本番予定環境の計測、有効比較数、件数・反復数・実行予算 |
| 統計と条件 | 主比較、Title依存、95%CI、欠測と品質不明、閾値、事前条件別分析 |

Ubuntu/CUDA実装と研究室PC接続は未実施。CPUで準備を進められるが、GPU本番を採用するなら
移行後の実機確認と必要なCalibrationを終えてから条件を固定する。速度倍率は未測定。
意味誤りを全てゼロにすることを要求せず、修正・処理ルール・残る限界を根拠付きで決める。
反転を増やすための閾値変更や、Evaluation結果を用いた調整は行わない。
