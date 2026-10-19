# 別チャットから再開するための引継ぎ

更新日: 2026年10月20日。Phase 10実装・結果の基点Commitは `60c4eec`、
Phase 11準備実装は `c0d5891`、本実装・CPU結果は `83da39c`。
この文書は再開用の入口で、現在地・工程の正本は [research_roadmap.md](research_roadmap.md)。

10月19日の引継ぎ整備は、認証エラーにより当時のCommitを未実行のまま保存していた。
10月20日にユーザーから未Commit分をまとめる指示を受け、Phase 11の現在地に更新してCommit対象とした。
当時のエラーと未Commit状態は研究日誌の履歴であり、現在の作業状態は `git status` で確認する。

## 最初に読む記録

1. ルートの [AGENTS.md](../AGENTS.md) と、[研究計画7.8](rag_research_plan.md)・[実装計画8.8](rag_implementation_plan.md)。
2. [ロードマップ](research_roadmap.md): フェーズ、現在地、次工程、完了条件。
3. [Phase 11の結果・最終固定とGPU引継ぎ](phase11_finalization.md) と [Calibration手順](phase11_calibration.md)。
   [Phase 10再確認結果](phase10_recheck_results.md)では、新規10問、具体例、品質・費用・限界を確認する。
4. [測定系修正記録](phase10_measurement_revision.md): モデル・Prompt・抽出・予算・後処理の変更理由。
5. [AI品質採点Protocol](ai_quality_protocol.md) と、[研究日誌](研究日誌.md) の最新日付の記録。
6. 研究室PCへ移す場合は [引継ぎ・仕様](lab_pc_handover.md) 第6節以降も確認する。

## 再開時点の状態

- 主題は「根拠提示順序に対するRAG自己評価の感度と修復判断への影響」。旧原因別三修復へ戻さない。
- Phase 1〜9、Phase 10の初回20問、測定系修正、既知診断、新規10問/20候補AI採点と集計を完了。
- 元v14の事前Gateは引用ID重複1件で不通過として保持。事後の引用後処理v15による検証は別結果。
- Phase 11の本実装とCPU Calibration 5問・匿名10候補AI採点・集計は完了。ただし全5問が拒否でJudge 0回・完全比較0、元Health Gate不通過。Phase 11全体は未完了。
- 未使用の追加Calibration 20問を事前選定済み。GPU実機確認・GPU対応・追加検証・最終凍結は未実施。Phase 12の最終Evaluationと遠隔接続も未実施。
- Phase 12は研究室PCのGPUを使うユーザー方針。研究室側のCodexで実機情報を確認し、Phase 11の残作業から再開する。
- ユーザーは品質採点をCodex AIへ委任している。表示名はリサーチャー01、human_reviewed=false。
  人手確認済みとは扱わない。採点モデルの厳密なIDと完全なセッション分離は最終凍結前の確認事項。

## Phase 11の保存済み結果

- CPUの初期5問は全て単独拒否でF=null。順序効果を測れておらず、「順序効果がない」とは結論しない。
- 共通書換え5件・匿名10候補のAI品質を固定した後に集計。品質遷移は0→0が3問、0→1が2問で、他の遷移と不明は0。
- 現行の拒否Fallbackは初回保持のため改善2問を見逃した。順序による改善見逃しとは区別する。
- 書換え5件のNative予算・最終JSON文法適用は確認済み。新規Judgeの形式・意味妥当性は未確認。
- 補助費用は入力11,757/出力3,661 Token、Step和1,030.20秒。初回生成・検索・起動・外部AI採点を含む応答時間ではない。
- 実験プロセスと全10候補の採点は終了済み。最終凍結Manifestは未作成、Gate 11未通過・Phase 12不可。

## Phase 10の保存済み結果と、数字の意味

- 新規10問の初回回答を固定。4問に事実本文、6問は単独拒否でF=nullの別Fallback。
- 4問×9回=Judge36回。9回は元/逆/Shuffle3種の5条件と、元順序の追加4反復。
- 全10問で一回書換えを収集。初回10＋修正版10=匿名20候補をAI採点。
- 両Cohortの全品質Labelを固定してから、内部F・判断・初回/修正版の対応を開示した。
- 元v14はJudge35有効/1形式失敗、完全比較3問。後処理再検証では完全比較4問。
  追加生成0、既存有効35出力のLabel・理由・証拠・Fは不変。元失敗を成功に上書きしていない。
- Astrosでは元順序などがF=0/書換え、Shuffle 1だけF=1/誤採用。元v14でも全9試行が有効だった。
  同順序5反復の反転は0。資料時点の「出場1回」という誤答から「2005/2017の2回」への改善を逃した。
- 品質遷移は0→0が5、0→1が3、1→0が0、1→1が1、不明1問。全てAI採点。
  Friday Night Lightsとミトコンドリアの改善見逃しは拒否Fallbackで、順序効果とは別原因。
- 暖鋒とTar Heelsは不適切な回答でもF=1で安定した。意味誤りは残り、一般精度や反転頻度を確立していない。

## コード・固定条件

- 初回候補: Phase 6のHybrid Top-10 / Qwen2.5-3B。保存済みRunの元回答・実使用Contextは再生成しない。
- Judge/書換え: `configs/order_phase10_v14.yaml`、Promptは `configs/order_prompts_phase10_v10.yaml`。
  Qwen3-4B Q4_K_M、Context8192、Completion2048、推論予算512、最終回答512以下、閾値0.7。
- 評価対象は回答を一度だけ分けた文単位。原子的な事実分解ではなく、全文保持を検証する。
- 書換えは元の質問・元回答・元順序の実使用根拠から1回。Judge結果やGold/Referenceを渡さない。
- 後処理v15は `evaluation/reasoned_json.py` の同一既存引用IDの整理。生のID列・Boolean・理由を保持する。
- 保存出力の検証: `scripts/replay_citation_normalization.py`。Model再呼出しではない。
- 元監査: `scripts/audit_measurement_recheck.py`。凍結済み集計があれば上書きせず、不変性を検査する。
- Phase 11のCPU候補は `configs/order_phase11_calibration.yaml` と `configs/phase11_calibration.yaml`。
  最終固定の検証は `scripts/finalize_phase11.py`、判断草案は `configs/phase11_freeze_decisions.json`。
- 直近の実装確認は全267 Test成功（40.60秒）、Ruff成功。今回の引継ぎ更新で再実行した結果ではない。
  Pythonはuv。コードを変えたら変更に応じて確認する。

## Gitにある記録と、このPCにある生データ

| 保存場所 | 内容 | Git管理 |
|---|---|---|
| `docs/` | 研究目的、仕様、結果、失敗、現在地、次工程 | 対象 |
| `src/`、`scripts/`、`configs/`、`tests/` | 実装、設定、検査 | 対象 |
| `data/manifests/phase10_recheck_result_manifest.json` | 元v14集計・不通過Gate・Raw ArtifactのHash | 対象 |
| `data/manifests/phase10_recheck_quality_freeze.json` | 両Cohortの採点固定とHash | 対象 |
| `data/manifests/phase10_citation_replay_manifest.json` | 事後検証・元結果へのHash対応 | 対象 |
| `data/manifests/phase11_cpu_calibration_result_manifest.json` | CPU 5問の完了集計・不通過Gate・Raw ArtifactのHash | 対象 |
| `data/manifests/phase11_gpu_calibration_selection_manifest.json` | 未使用の追加Calibration 20問の事前選定 | 対象 |
| `data/runs/calibration/phase11-cpu-five-v1/` | CPU 5問の入力・出力・採点・対応・ログ・集計 | 対象外、このPCに保存 |
| `data/runs/calibration/phase11-main-work-before/source_snapshot/` | CPU実験時の71ソースの保存版 | 対象外、このPCに保存 |
| `data/runs/handover/phase11-83da39c.zip` | 83da39cのソースとCPU実験記録・Snapshot。今回の文書更新は含まない | 対象外、このPCに保存 |
| `data/runs/pilot/phase10-five-v2/` | 最初の新規5問の入力・出力・採点JSON・ログ | 対象外、このPCに保存 |
| `data/runs/pilot/phase10-five-extra-v2/` | 追加5問の入力・出力・採点JSON・ログ | 対象外、このPCに保存 |
| `data/runs/measurement/phase10-revision-v14/` 等 | 既知診断と失敗履歴・旧ソース | 対象外、このPCに保存 |
| `data/runs/measurement/phase10-citation-replay-v15/` | 派生結果、旧ソースSnapshot | 対象外、このPCに保存 |
| `data/raw/`、`data/processed/`、`data/indexes/`、`data/models/`、`data/runtimes/` | Dataset、検索Index、Model、実行基盤 | 対象外、このPCに保存 |

同じ作業フォルダを開く別チャットは、これらの文書とローカル生データを参照して再開できる。
別PCへ移す場合、Gitの取得だけで生データ・採点JSON・Modelがそろうとは扱わない。
実験Runは別途転送・バックアップし、ManifestのHashで照合する。失敗Runも一緒に保持する。
このチャットでCodexはgit pushを実行していない。Pushはユーザーの明示指示がある場合のみ。

## 直近のGPU・遠隔接続の検討（実施済みと区別）

- 購入仕様: Ubuntu24.04 / i5-14400 / RAM8GB / RTX5060Ti / NVMe500GB。
  VRAM8GB版か16GB版か、Driver、現在のRAM・Disk空きは未確認。実機の計測結果ではない。
- GPU高速化を期待するが、倍率・短縮時間は未測定。まず現在の4Bを同条件で動かして測定する案。
- 現行実装はWindows CPUに固定し、`generation/local.py` は `--gpu-layers 0` を指定する。
  Ubuntu/CUDA対応は未実装。GPUがあるだけで現行コードがGPU実行へ切り替わるとは扱わない。
- 自宅→学校指定VPN等→SSH→研究室PCで計算、という構成を説明した。
  学校のVPN提供・SSH許可・接続情報・アカウントは未確認。接続や設定変更は実行していない。
- 長時間実験をtmux等で維持する案を説明した。導入済み・動作確認済みとは記録しない。
- 実行環境変更は別Version/Manifestへ記録し、GPU移行後にCalibrationし、最終凍結する方針を提案した。

## 次に行うことと再開用メッセージ

Phase 11の続きとして、実機・GPU実行の小規模確認、初期回答の拒否とJudgeの意味判定の診断、
必要な修正、未使用20問でのCalibration、拒否Fallback・外部AI採点・件数/反復/統計の確定へ進む。
候補条件とHealth Gateは新規結果を見る前に保存する。20問を実行しただけで自動的に最終固定しない。
モデル・Prompt等を変える場合は理由と影響範囲を仕様にも記録し、別Version/Runで検証する。
Fは支持割合で正答確率ではない。支持判定の誤りと、質問への回答不足を分けて監査する。
順序反転を増やす目的で閾値や例を選ばず、測定の妥当性と有効比較数を確認してから最終凍結する。
最終Evaluationを見て条件を調整しない。元Runを新しいソースで再開・上書きしない。

別チャットには、例えば次を伝える:

> このプロジェクトのAGENTS.mdとdocs/codex_handover.md、docs/phase11_finalization.md、現行計画・ロードマップを確認してください。Phase 11はCPU 5問・10候補AI採点と集計まで完了しましたが、全拒否で比較可能0、Gate 11は未通過です。本番は研究室PCのGPUです。実機と転送データのHashを確認し、GPU対応、拒否・Judgeの診断と必要な修正、事前選定20問での検証から進めてください。最終条件固定前にPhase 12へ進まないでください。まず現在地と次に行う作業を説明してください。
