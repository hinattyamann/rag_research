# Phase 11 本実装・最終固定と研究室GPUへの引継ぎ

2026年10月20日。準備実装は[Calibration手順](phase11_calibration.md)、現在地は[ロードマップ](research_roadmap.md)による。
ユーザーは本番を研究室PCのGPUで行うと指定した。実機情報は研究室側のCodexで確認する。
CPUでのCalibrationと、本番GPUでの確認・最終固定を区別する。Phase 11はまだ完了していない。

同日Ubuntuでの[GPU検証と追加20問の結果](phase11_lab_validation.md)を追記した。
GPU20問/40候補AI採点・34単位監査を完了し完全比較12、実行Health Gateは通過した。
意味妥当性の採用と分析規模は未確定のためGate 11未通過・最終凍結なし。以下のCPU/移行前記録は履歴である。

## CPU Calibrationの実測結果

事前選定5問の初回生成・共通書換え・匿名10候補のAI採点・全Label固定後の集計を完了した。
初回回答は5問全て単独拒否で、固定文がなくF=null。Judgeは0回、完全比較0問で、
事前Health Gateは`too_few_complete_scorable_questions`による不通過となった。
失敗例の置換、閾値変更、Gate基準の事後変更は行っていない。
**順序効果がない結果ではなく、順序効果を測れていない結果である。**

| 確認項目 | 結果 |
|---|---|
| 初回生成 / 書換え / AI採点 | 5問 / 5件 / 10候補、全て保存 |
| 書換え前後のAI品質 | 0→0が3問、0→1が2問、1→0・1→1・不明は0問 |
| 改善した例 | Buffyの母が知る時期、子宮マッサージの用途 |
| 現行の全評価経路 | F=nullの初回保持で5問全てY=0、改善見逃し2問 |
| 常時書換え | Y=1が2問、Y=0が3問。初回を含む10 Model呼出し |
| Parser/Native監査 | 書換え5件の予算・最終文法適用を確認。新規Judgeの確認は未達 |
| 補助収集費用 | 5呼出し、入力11,757/出力3,661 Token、Step和1,030.20秒（約17.17分） |

費用は書換えのStep和で、初回生成・検索・起動・外部AI採点を含む応答時間ではない。
初回保持/修復なしは5呼出しで、今回の改善2問を取り込めない。順序効果とは別の原因である。
La Merの候補は曲名不足、Pasteurの候補は根拠外の排他的帰属、Joy to the Worldは成立背景の不足でY=0。
これは外部AI品質の判定で、新規JudgeのFや意味精度を確認した例とは扱わない。
少数5問から一般的な拒否率を推定しない。全267 Test成功（40.60秒）、Ruff成功。
旧Phase 10の834 Artifactと既存の最初の回答はHash不変である。
[完了監査Manifest](../data/manifests/phase11_cpu_calibration_result_manifest.json)に集計と生データHashを保存した。

次のGPU Calibration用に、既知5問と同Titleを除いた未使用20問を
[別Manifest](../data/manifests/phase11_gpu_calibration_selection_manifest.json)へ事前選定した。
Seed42/IDのSHA256順であり、反転・改善しそうな質問を選んでいない。Model呼出しは0回。
これはGPU用の追加Calibration候補で、本番Evaluationの件数ではない。
GPUの実行条件と新しい実行Health Gateは、これらの新規Model結果を見る前に研究室側で固定する。
元の5問の不通過を新しいGateの成功で上書きしない。

## 最終固定の実装

`scripts/finalize_phase11.py`が、保存済み実験とレビューの根拠を照合する。
`configs/phase11_freeze_decisions.json`は未決の判断を含む草案。`pending`を単に`resolved`へ
置換しても、必要な実験・監査の根拠がなければ固定できない。

```powershell
uv run python scripts/finalize_phase11.py review
uv run python scripts/finalize_phase11.py freeze
```

`review`は準備状況と不足理由を示す。`freeze`は全条件がそろった場合にのみ
`data/manifests/phase11_final_freeze.json`を新規作成する。未達時には最終Manifestを書かない。
固定済みファイルはHashと内容を検証し、変更して上書きしない。

| Gate | 確認する根拠 |
|---|---|
| 品質と来歴 | 全匿名候補のLabel固定、採点来歴、候補/段階の対応、元Taskと集計の一致 |
| 実行とParser | 事前Health Gate、新規Judge出力の有効性、推論予算と最終JSON文法の実適用 |
| 意味妥当性 | 全固定文の支持・矛盾・支持不足のAI監査、実使用Contextの引用、残る限界 |
| 拒否Fallback | 今回は初回保持の維持理由を記録。ルール変更時は新Versionで別検証する |
| 外部品質 | 実際のモデル識別の取得可否とセッション範囲の一致。AI採点の制約を記録 |
| 本番Runtime | CUDAでの実Offloadと生成、予算/形式/意味の確認、モデル・RuntimeのHashと時間 |
| 分析計画 | 主比較、Title単位の対応Bootstrap、95%CI、分母・欠測、件数と根拠 |

外部AIの意味監査は診断用で、独立した複数採点者一致や人手正解ではない。
JSON整形式や正しい引用だけで意味判定が正しいとはしない。
全誤判定の解消ではなく、用途に対して測れる範囲と残る誤りを根拠付きで判断する。
順序反転や改善の有無をGateの合否に使わない。

Evaluationの対象IDは、件数決定後に固定Split ManifestのIDメタデータだけから
SeedとIDのSHA256昇順で選ぶ。質問・Reference・回答結果を見て選ばない。
最終ManifestへIDを保存するまで、Phase 12を開始しない。

## GPU側で必要な根拠

まず研究室PCで次を実行し、OS・CPU・RAM・Disk空き・NVIDIA GPU名・VRAM・Driverを保存する。
同名の保存先は上書きしない。これはインストールや設定変更を行わない情報収集である。

```bash
uv run python scripts/inspect_execution_environment.py --output data/runs/lab/initial_inventory.json
```

`nvidia-smi`の検出だけではGPU推論成功としない。移行前の`generation/local.py`は
Windows CPU Runtimeを検証し`--gpu-layers 0`を指定していた。現在は別Versionの明示的CUDA設定に対応済み。
研究室側でRuntimeの実装・条件を別Versionへ分け、固定モデルの生成とCalibrationを確認する。
旧CPU Runを新GPUコードで再開・上書きしない。

最終固定用のRuntime根拠は、`purpose=phase11-target-runtime-calibration`のHash付きJSONとして保存する。
最低限、次を実際の実行記録から含める。例示用の値や成功フラグを実測の代わりに投入しない。

- `backend=CUDA`、`actual_gpu_offload=true`、正の`offloaded_layers`と実GPUデバイス。
- 実生成回数`completion_attempts`、対応する候補Protocolの`protocol_sha256`。
- `native_audits_valid`、`semantic_check_completed`と、その元となる保存出力・監査。
- `summed_step_seconds`、`runtime_files_sha256`、`model_files_sha256`。
- 元のNative Taskを示す`probe_tasks`（各要素は`path`と`sha256`）と、
  `server_log`（同じく`path`と`sha256`）。Taskの成功・推論予算・文法適用と、
  ログの実Offload数を検査する。情報収集JSONのフラグだけでは通過させない。

CUDAの有無にかかわらず、元の質問・根拠・回答を固定する比較、公平な試行条件、書換え候補共用は維持する。
実行環境を変えたことを記録し、CPUの時間をGPUの見積りとして使わない。
最終対象数はGPU実測と有効比較数から決める。100〜200問は候補で、現段階では未固定。

## 引継ぎ時の保存対象

Gitで渡るコード・設定・仕様・小さいManifestに加え、次のローカル成果物を別途転送する。

- `data/runs/calibration/phase11-cpu-five-v1/`：入力・出力・匿名採点・対応・ログ・集計。
- `data/runs/calibration/phase11-main-work-before/source_snapshot/`：CPU実験時の71ファイル。
- 必要なData/Index/Model。`data/processed/`・`data/indexes/`・`data/models/`はGit対象外。

Windows実行RuntimeをLinuxへそのまま使わない。巨大なModel/Corpusは再取得または別途転送し、
固定RevisionとHashで照合する。実験Runと失敗履歴は再取得できると仮定しない。
採点前の候補では内部結果を開かず、採点済みかを確認してから集計・対応表を開く。
研究室側では`AGENTS.md`、この文書、現行計画、ロードマップ、最新日誌の順に確認する。

引継ぎメッセージ例:

> Phase 11の本実装とCPU Calibrationの記録を読み、未実施項目を確認してください。
> CPU初期5問は全拒否で完全比較0、元Health Gateは不通過です。全10候補のAI採点と集計は完了しています。
> 本番はこの研究室PCのGPUです。まず実機情報と転送した成果物のHashを確認し、
> Ubuntu/CUDA対応を別Versionとして実装・検証してください。GPUでの生成・Calibration、
> 最終件数・統計・Runtimeの固定を終え、Gate 11通過を確認してからPhase 12へ進めてください。
