# 別チャットから再開するための引継ぎ

更新日: 2026年10月21日。Phase 10実装・結果の基点Commitは `60c4eec`、
Phase 11準備実装は `c0d5891`、本実装・CPU結果は `83da39c`。
この文書は再開用の入口で、現在地・工程の正本は [research_roadmap.md](research_roadmap.md)。

最新方針（2026年10月21日）: 英語CLAPNQに近い別の日本語Datasetを追加し、日英で順序感度と
判断・品質・費用を比較する。翻訳対は主実験に使わない。[拡張方針](english_japanese_expansion.md)の
選定・取得・日本語対応・予備検証・両言語の条件固定をPhase 11で行う。
同日のGoal実行で[候補比較と日本語Source選定](japanese_dataset_selection.md)を実施し、
`baobab-trees/wikipedia-human-retrieval-ja`の固定版838回答付き/433回答なしQAを取得・構造監査した。
全検索記録の記事全文Corpusは取得中。文書Group分割・全Pipeline実走・予備検証・最終固定は未完了で、Gate 11は未通過。
取得CLIは`scripts/prepare_japanese_corpus.py`、設定は`configs/phase11_japanese_corpus_v1.json`。
再取得/取得履歴・Hashと現在版Fallback防止を実装し、既知1記事の本文取得を確認済み。
実行手順と未達事項は[Source選定記録](japanese_dataset_selection.md)第5節を参照する。
全2178 Titleの取得はCommit `61b4a5c`の専用Checkout
`.tools/worktrees/phase11-japanese-corpus-v1`で実行している。取得中に当該CheckoutのCode/Configを変更しない。
Raw保存先は同Checkout内の`data/raw/wikipedia_human_retrieval_ja/corpus-20231225-v1/`。
Main側は日本語の固定文単位候補を追加し、全316 Test（ホスト4.62秒）・Ruff、旧英語保存抽出65件の一致を確認した。
文単位だけのComponent検証であり、日本語検索・Model/品質実走・日英文単位の最終採用はこれから。
その後QA Adapter/Group分割処理を追加し、実838件の取込みを確認。全338 Test（4.54秒）・Ruff成功。
暫定監査は`data/processed/wikipedia_human_retrieval_ja/02e85c8-source-audit-v1/`。
706 Group・開発予約142件で全QAは`research_split=None`。正式SplitとGold Passage対応を完了済みにしない。
手順と取得中の正式生成拒否は[Source選定記録](japanese_dataset_selection.md)第6節を参照する。
既存の英語最終固定Validatorだけでは追加要件を確認できない。日本語の準備を満たすまでPhase 12へ進まない。

GPU検証記録（2026年10月20日、Ubuntu研究室PC）: 環境・事前条件はCommit `d2c6550`。
[GPU検証結果](phase11_lab_validation.md)のとおり、CUDA対応と追加20問/40候補AI採点・34単位監査を完了。
完全比較12/20、Judge108回すべて形式有効、Health Gate通過。ただし意味妥当性の採用と分析規模が未確定で
Gate 11未通過、最終凍結・Phase 12は未実施。旧CPU5問の不通過も保持する。
現在のRunは`data/runs/calibration/phase11-gpu-twenty-v2/`で全計算・採点が終了している。
次の未使用20問は`phase11_additional_validation_selection_manifest.json`。今回の20問を未使用と呼び直さない。
この最新追記とロードマップを、以下の移行前のGPU未実施記録より優先する。

10月19日の引継ぎ整備は、認証エラーにより当時のCommitを未実行のまま保存していた。
10月20日にユーザーから未Commit分をまとめる指示を受け、Phase 11の現在地に更新してCommit対象とした。
当時のエラーと未Commit状態は研究日誌の履歴であり、現在の作業状態は `git status` で確認する。

## 最初に読む記録

1. ルートの [AGENTS.md](../AGENTS.md) と、[研究計画7.12](rag_research_plan.md)・[実装計画8.14](rag_implementation_plan.md)。
2. [ロードマップ](research_roadmap.md): フェーズ、現在地、次工程、完了条件。
   [日英比較の拡張方針](english_japanese_expansion.md): 日本語選定基準、比較の限界、追加するPhase 11の要件。
3. [Phase 11の結果・最終固定とGPU引継ぎ](phase11_finalization.md) と [Calibration手順](phase11_calibration.md)。
   [Phase 10再確認結果](phase10_recheck_results.md)では、新規10問、具体例、品質・費用・限界を確認する。
4. [測定系修正記録](phase10_measurement_revision.md): モデル・Prompt・抽出・予算・後処理の変更理由。
5. [AI品質採点Protocol](ai_quality_protocol.md) と、[研究日誌](研究日誌.md) の最新日付の記録。
6. 研究室PCへ移す場合は [引継ぎ・仕様](lab_pc_handover.md) 第6節以降も確認する。

## 再開時点の状態

- 主題は「根拠提示順序に対するRAG自己評価の感度と修復判断への影響」。旧原因別三修復へ戻さない。
- 主題に日英比較を追加したが、実測は英語のみ。別Dataset間の差を言語単独の因果効果と断定しない。
- Phase 1〜9、Phase 10の初回20問、測定系修正、既知診断、新規10問/20候補AI採点と集計を完了。
- 元v14の事前Gateは引用ID重複1件で不通過として保持。事後の引用後処理v15による検証は別結果。
- Phase 11の本実装とCPU Calibration 5問・匿名10候補AI採点・集計は完了。ただし全5問が拒否でJudge 0回・完全比較0、元Health Gate不通過。Phase 11全体は未完了。
- GPU20問の選定・実行・全品質固定・集計は完了。意味誤支持が残り最終凍結は未実施。追加の未使用20問を事前選定したが新Protocol/Health Gateは未確定。Phase 12と遠隔接続は未実施。
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
| `data/manifests/phase11_gpu_calibration_selection_manifest.json` | GPUで使用済みの20問の事前選定 | 対象 |
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
2026年10月20日にユーザーが、確認済みの変更をCommit後にGitHubへPushする運用を継続的に許可した。
各PCのCodexはAGENTS.mdに従ってCommit・通常のPushまで実行し、成否を報告する。force pushは行わない。
この許可前は25 Commitがローカルだけにあった。同期状態は `git status -sb` とリモートの最新履歴で確認する。

## 直近のGPU・遠隔接続の検討（実施済みと区別）

- 購入仕様: Ubuntu24.04 / i5-14400 / RAM8GB / RTX5060Ti / NVMe500GB。
  VRAM8GB版か16GB版か、Driver、現在のRAM・Disk空きは未確認。実機の計測結果ではない。
- GPU高速化を期待するが、倍率・短縮時間は未測定。まず現在の4Bを同条件で動かして測定する案。
- 移行前はWindows CPU固定だった。現在は明示的execution設定のときだけCUDAへ切り替える別Versionを追加済み。
  既定CPU条件・旧Runは保持し、GPUの37/37 Layer Offloadと実生成は新Runで確認した。
- 自宅→学校指定VPN等→SSH→研究室PCで計算、という構成を説明した。
  学校のVPN提供・SSH許可・接続情報・アカウントは未確認。接続や設定変更は実行していない。
- 長時間実験をtmux等で維持する案を説明した。導入済み・動作確認済みとは記録しない。
- 実行環境変更は別Version/Manifestへ記録し、GPU移行後にCalibrationし、最終凍結する方針を提案した。

## 次に行うことと再開用メッセージ

まず拡張方針に従って日本語候補の仕様を比較・選定し、取込み・言語対応と少数予備検証を追加する。
既存英語の妥当性改善と併せ、両言語の未使用Calibrationを確認し、対象・条件・件数・統計を固定する。
日本語選定前にも既知英語例の診断は進められるが、その完了だけで最終凍結しない。

Phase 11の続きとして、既知例で支持判定・拒否方針を別Versionで検証し、条件とHealth Gateを保存してから
新たに事前選定した未使用20問へ進む。実機確認と今回のGPU20問/40候補の採点・集計は完了している。
今回の20問を再び未使用と扱わない。件数/反復/統計の最終凍結は追加検証後に行う。
候補条件とHealth Gateは新規結果を見る前に保存する。20問を実行しただけで自動的に最終固定しない。
モデル・Prompt等を変える場合は理由と影響範囲を仕様にも記録し、別Version/Runで検証する。
Fは支持割合で正答確率ではない。支持判定の誤りと、質問への回答不足を分けて監査する。
順序反転を増やす目的で閾値や例を選ばず、測定の妥当性と有効比較数を確認してから最終凍結する。
最終Evaluationを見て条件を調整しない。元Runを新しいソースで再開・上書きしない。

別チャットには、例えば次を伝える:

> AGENTS.mdと現行計画・ロードマップ、docs/english_japanese_expansion.mdを確認してください。英語のGPU20問/40候補AI採点・34単位監査は完了しましたが、意味妥当性と分析規模は未確定でGate 11未通過です。10月21日に別の日本語Datasetとの比較を採用しました。CLAPNQに近い候補の比較・選定、日本語対応、日英の予備検証と未使用Calibration、両言語の条件固定をPhase 11で行います。旧Runを保持し、両言語の準備がそろうまでPhase 12へ進まないでください。まず現在地と次の作業・成果物を説明してください。

## Ubuntu研究室PCで続けるとき

実機はUbuntu24.04.3 / i5-14400 / RAM約7.5GiB / RTX5060Ti VRAM8151MiB / Driver580.95.05。
uvは`.tools/bin/uv`。`export PATH="$PWD/.tools/bin:$PATH" UV_CACHE_DIR="$PWD/.tools/uv-cache"`後にuv runを使う。
3モデルは固定Hashを照合済み。旧Runtimeを起動せず、`configs/lab_cuda_runtime.json`の別Runtimeを使う。
制限環境内ではGPUとnetworkが見えない場合がある。ホストでの確認とDriverの故障を区別する。

元CPU条件と失敗履歴を保持し、使用済みGPU20問を新コードで再開しない。
候補v2のソースはRun内`source_snapshot/`へ保存済み。
全128 Native Task、34固定文、40品質Label、Runtime根拠と全生データHashは
`phase11_gpu_calibration_result_manifest.json`等に対応する。
新しい最終固定の判断は`configs/phase11_gpu_freeze_decisions_v2.json`。
品質/Parser/Runtime等は確認済みだが意味妥当性と分析はpendingなので、freezeは実行していない。
次は既知例で支持判定・拒否方針を別Versionで検証し、新条件/停止条件を保存してから別の未使用20問へ進む。
本番200問とTitle対応Bootstrap10000回/95%CIは未凍結の案。Evaluation本文・結果を調整に使わない。
