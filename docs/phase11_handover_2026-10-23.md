# Phase 11 新チャットへの引継ぎ

2026-10-26最新: [自律継続v3](phase11_autonomy_v3.md)の新Guard/累積台帳/chain/段階実行を実装し、実機全844 Test/Ruffに成功した。現行資産照合と旧Run5818Fileのコピー照合、Graph OFF固定Source隔離Build/生成0のVersion・CUDA認識を完了。新Runtimeでの実生成/採用/主/Cal/最終凍結はこれから。旧909試行/未知3/v10不採用を保持、Goalはこの新チャットでactive、Gate11未通過・Phase12未開始。以下の旧停止指示は10月24日の新許可により置換する。

2026-10-24の作業指示更新: [研究室向け開始文](phase11_lab_weekend_start.md)と[週末Goal](phase11_lab_weekend_goal.md)を保存。
旧の候補1個/188回/4時間/障害時Goal停止は新規の自律継続方針へ置換する。旧失敗/未知/台帳は保存し、意味基準は維持する。
研究室での新Protocol実装・実験開始はまだ行っていない。以下の不採用/停止結果は実績として有効である。

更新日: 2026-10-23。新チャットでは本書と[評価器・資源・テスト見直し方針](phase11_evaluator_review_policy_v1.md)から読む。
工程の正本は[research_roadmap.md](research_roadmap.md)。長い日誌/過去の引継ぎは履歴であり、必要な箇所だけ参照する。
新チャット用の貼付文は[phase11_next_chat_prompt.md](phase11_next_chat_prompt.md)。

2026-10-23再開後の最新: **[新Known v10は不採用・全終了](phase11_known_trace_direct_result_v10.md)**。
新基準v2の全経路実装と全782 Test/Ruff、生成0/全84入力/全CUDA、Smoke計2 Callは通過した。
固定903f4cfの全Knownは56試行（55応答/未知1）でCUDA launch timeout・Watchdog/Xid8再発。
非支持全16判定も14/16＝87.5%で0.90未達。全予定率null、28 Call未試行を保持。
正本は`data/manifests/phase11_known_trace_result_v10.json`、Raw81/全123 Artifactを正規保存・WT照合した。
**稼働中のNativeはない。** 現チャットSession68501/監査74660は終了。旧Runも新v10も再起動しない。
新開発58/188・累積909/1039・未知計3、Task4310.915004秒/14400秒、保守的壁4381.357537秒。
未使用130（Known28+未割当102）と旧69・42/42/81/42は自動再配分しない。
Main各20/予約Cal各20/品質・費用/最終N・凍結は未了、Gate11未通過・Phase12未開始。
ユーザー指定の障害時一時停止条件に該当する。保存・同期後にGoalを一時停止し、再開は下記第6節の判断から行う。
以下の初回移行時・実行中・新基準未実装の記録より、この追記とロードマップを優先する。

## 1. 今回の依頼と引継ぎの意味

ユーザーは、評価器の改善へ時間をかけすぎているため、研究目的と資源からテスト・妥協範囲・打切りを見直し、
別チャットの新しい`/goal`でPhase 11全体を完了したいと依頼した。
無制限の評価器最適化を再開しない。研究は順序感度・採用/一回書換え・独立回答品質・費用の日英比較である。

本チャットのGoalは実状態を確認して**paused**。完了ではない。
Goalsはチャット単位であり、新チャットに過去の内部履歴やGoalが自動継承されるとは仮定しない。
新チャットで新しい`/goal`を設定する。公式資料:
[Using Goals in Codex](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex)、
[Developer commands](https://learn.chatgpt.com/docs/developer-commands)。
長い詳細はファイルへ置き、4000文字以内のGoalから参照する。

## 2. 最初の安全な確認

Repository: `/home/uchida/デスクトップ/code/rag_research`、Branch: `main`、Origin: `https://github.com/hinattyamann/rag_research.git`。
最初にAGENTS.mdとGit状態/HEAD/接続先/追跡先を確認し、Fetch完了後の差分を調べる。
未Commit変更を保持し、CleanでRemoteだけ先行の場合のみ`pull --ff-only`。Force/Reset/Cleanを使わない。

記録済みCommit:

- `9727409eee7a3f8c1ca76f879234f32de0462bb9`: 全意味監査と旧全回帰v9登録。v9実験の固定Commit。
- `b75bd070efcfaeb83d4850736ce3ed0e48b07a84`: 回帰v9の生成0/開始記録。
- `f5edacb`: 温度0.2の実測Judge時間と資源見積りを保存。
- `c3f42dc`: 旧回帰v9のCUDA停止と未知応答の全監査を保存。

本書・方針を導入した最終Commitは`git log -1 -- docs/phase11_handover_2026-10-23.md`と実HEADから確認する。
自分自身のCommit IDを本文に埋め込むためにCommitを作り直さない。

**稼働中の実験はない。** Native session72566/監査23121/生成0の98818、親意味89310/監査60518は終了済み。
履歴にある「実行中」を見て再起動しない。新チャットのTool Handleへ過去の番号が移るとも仮定しない。
新しく開始する実験だけ、固定Commitの専用WTと新Run/上限/条件を事前保存する。

## 3. 完了済みの基盤――作り直さない

| 範囲 | 現在の実証拠・限界 |
|---|---|
| 英語Phase 1〜10 | CLAPNQ基盤・CUDA接続・旧開発確認を保持。旧修復3種類/Failure Dataset4種類へ戻らない |
| 日本語Source選定/取得 | `baobab-trees/wikipedia-human-retrieval-ja`固定Revision。838 Source-answered QA/706 Group、欠測も保持 |
| 日本語分割 | Dev545/Cal84/Eval209。開発Preview閉包142 QA/95 Groupを使用済みとして隔離 |
| Corpus/参照 | JA2118記事→30065子Passage、EN183889子Passage。全文保持、引用/脚注投影・欠測監査を完了 |
| 検索 | multilingual-e5-small固定FP32 ONNX/CUDA、日英全Index/BM25/Hybridを構築・検証 |
| 共通RAG | 日英の既知1 QAずつで初回→固定文→順序/反復→一回書換え→匿名候補品質→照合を実走。主各20 QAの代用ではない |
| 既知診断 | 人工日英27例/既知2例、旧全15 QA/42文、裸拒否8を保持。多数の失敗も保存 |
| Main/Cal入口 | 準備/実行/匿名採点封印/解析/証明の実装とTestはある。新基準への改訂と実成功側は未了 |
| 統計 | QA内の順序差−反復差、Group Bootstrap、日英非対応差を事前定義/実装 |
| 最終Validator | 日英・物理Payload・主/Cal/品質・N/資源/統計の検証を実装。未達時に凍結を拒否する。実凍結は未了 |

主な基盤資料:
`docs/english_japanese_expansion.md`、`docs/phase11_bilingual_pipeline.md`、
`docs/phase11_bilingual_indexes.md`、`docs/phase11_statistical_plan.md`、`docs/ai_quality_protocol.md`。
主なManifest:
`phase11_japanese_source_selection.json`、`phase11_japanese_snapshot_group_manifest.json`、
`phase11_japanese_reference_projection_v2.json`、`phase11_bilingual_connection_result_v1.json`、
`phase11_bilingual_connection_quality_freeze_v1.json`、`phase11_bilingual_finalization_validation_v2.json`。
いずれも`data/manifests/`内。現在のAssetsは`configs/phase11_bilingual_assets_v2.json`。

## 4. 評価器と直近の結果

初回生成はQwen2.5-3B固定/T0、補助候補はQwen3.5-9B Q6_K固定GGUF。
現在の候補`configs/phase11_semantic_candidate_v20.yaml`は温度0.2、Context12288、出力6144、
推論4096、Seed42、top_k20/top_p0.95/min_p0/presence1.5、6 Threads/Batch128、全層CUDA。
モデルGGUF SHA256は`91898433cf5ce0a8f45516a4cc3e9343b6e01d052d01f684309098c66a326c59`。
Model Manifest: `data/manifests/phase11_auxiliary_qwen35_9b_q6_manifest_v1.json`。
Runtimeはllama.cpp b11433/CUDA12.8配布物+system12.9。実機はRTX5060Ti/8151 MiB、i5-14400、RAM約7.7 GiB。

### 直近の全意味診断

固定17d57c6/89310の全58条件/70 Callは終了・全監査済み。
Critical4/4・人工EN24/24・JA28/30・誤支持0、確定66/68/支持28/28。
JAのNS→C2は保持。全68確定Labelは旧T1と同じで、温度による精度改善を主張しない。
人工27例の元/逆は1文書/同一入力。Council曖昧c6は両NS、両F5/7。
Raw136/202 Artifact、実70 Native Schema/Sampler/Source95/追加0再開を保存。
正本: `data/manifests/phase11_qwen35_q6_temperature_semantic_result_v1.json`、
`docs/phase11_qwen35_q6_temperature_semantic_result_v1.md`。

### 旧全回帰v9――停止済み、不採用

固定9727409/72566は3条件/15記録試行、会議14応答取得、Zidane元c1の1応答不明で終了。
LogはCUDA launch timeout/応答前切断。根本原因未特定。入力/出力不明を温度効果と断定しない。
会議観測確定12/12・支持10/10・誤支持0でも、全74/58精度はnull、27条件未試行/69 Call未使用。
失敗LeafにはNative応答/最終Label/出力Token数がない。過去の成功結果や途中Logから復元しない。
全15入力は親診断と同一、提出Schema15/取得14 Native Schemaと実Samplerを検証。
95 Source/元23 File不変・再開追加0、193資源観測/エラー0、Raw26/全110 Artifactを保存・WT照合。
実Main準備CLIも早期拒否し出力なし。

正本: `data/manifests/phase11_known_trace_result_v9.json`、`docs/phase11_known_trace_direct_result_v9.md`。
Raw: `data/runs/semantic_diagnostics/phase11-qwen35-9b-q6-temperature-known-regression-v9`。
固定WT: `.tools/worktrees/phase11-known-trace-regression-v9`。
監査: `data/runs/development_screening/phase11-q6-temperature-known-v9-audit-v1`。
Config/Plan: `configs/phase11_known_trace_candidate_v9.yaml`/`phase11_known_trace_regression_v9.json`。
旧事前登録: `data/manifests/phase11_qwen35_9b_preregistration_v18.json`。

旧Q6回帰v8は42 Call後に誤支持3/非支持16、支持23/24、NS/Cの取り違え2。
改訂する意味基準でも非支持Specificity81.25%で不適合。v9もHealth不適合。
どちらも旧失敗を新しい合格へ読み替えない。

全9B記録851（Q4 317/Q5 317/Q6 217）、応答不明は計2。
旧上限920、v9未使用69/旧未使用42・42・81・42を保持。次の新枠へ繰り越さない。

## 5. 新基準の実装済み範囲と未達

[基準v2](phase11_binary_adoption_v2.md)の実装/事前登録・旧v1拒否・Version整合・被覆/不足・Health境界を確認した。
推論Core/Prompt/Samplerは不変で、温度0.2の旧全意味70 Call/形式証拠をHash照合して再利用した。
全回帰のAI監査は55最終理由を読み、誤支持2/C↔NS3/表を誤読した正Label理由2を保存した。
Camp David逆の4保存応答を失わず、3支持を含む全Leafの観測34S/34とRoot有効条件の31Sを区別する。
失敗条件のF/判断・未知出力Tokenはnullのまま。全Run指標を観測部分だけで通過へ変更しない。

新Scopeで使ったModel候補は最大1個の最終v20、開発Native計58。旧851や未使用枠は保全する。
実Main/Cal/独立回答品質Yは未実施。Known意味監査をこれらの代用にしない。

## 6. 次に行うこと――再開に先立つ判断

1. 新v10の結果/Raw/Manifest/HashとGitを確認する。新規生成をせず、旧失敗と未知応答3件を保全する。
2. Runtime切分けの別計画（例: 固定SourceをCUDA Graph OFFで別Build/Hash化）を許可するか判断する。
   Root Causeは未確定で、Driver/Reset/再起動/OS設定は変更していない。システム変更は具体案/影響と明示的な承認を要する。
3. 意味候補を追加する候補上限/予算の改訂を明示的に認めるか、研究範囲を再設計するか判断する。
   CUDAだけを直しても非支持87.5%は未達。0.90/Expected/閾値0.7を自動変更しない。
4. 新たな許可/事前登録と完全KnownのHealth・意味実採用がそろって初めて、元選定のMain日英各20へ進む。
   全品質/Expected封印・完全比較各10 QA以上・実費用・主証明書→予約Cal各20→最終N/条件/統計/Hash/Gate11を維持する。

上限未到達を理由に未使用130を自動消費したり、失敗Runの残28を実行したりしない。
保存物と実装Testの完成だけでPhase11を完了にせず、Phase12は開始しない。

## 7. 実装入口と分割・統計・採点の重要事項

- Main: `scripts/prepare_bilingual_main.py`、`run_bilingual_development.py`、`certify_bilingual_main.py`。
- Cal: `prepare_bilingual_calibration.py`、`run_bilingual_calibration.py`、`analyze_bilingual_calibration.py`。
- Freeze: `scripts/finalize_bilingual_phase11.py`。`configs/phase11_bilingual_freeze_decisions_v1.json`はN/資源/証拠nullの雛形。
- Main選定: `data/manifests/phase11_main_development_selection_v1.json`（日英20 Groupずつ、使用済みを除外済み）。
- Cal予約: `data/manifests/phase11_bilingual_calibration_selection_v1.json`（各20、Main/Groupと非重複）。
  旧EN Cal225問は検索調整済みなので、新EN Calは未使用Devから別予約。JAは元Calから予約。
- QA内の質問/草稿/文単位/根拠本文・ID・Titleを固定し、文書提示順だけ操作。初回/書換えへGoldを漏らさない。
- 主量DはQA内の順序変更ペア不一致率−同一順序反復ペア不一致率。QA等重み、Group Bootstrap10000/Seed42、
  日英は非対応差/95%CI。別Dataset差を言語単独の因果効果としない。有効Group不足のCIはnull。
- 採点は内部Judgeから分け、条件/F/判断/初回か書換えかを隠す。実採点者/human_reviewed=false/
  Model識別子取得可否/実際の履歴隔離を記録。できなかった盲検や隔離を達成済みにしない。
- EvaluationはEN564/JA209のMetadata母集団からID選定だけ行い、質問/Reference/結果を条件調整に開かない。

## 8. ローカル資産と検証・Git運用

Python/工具はuv。基本: `UV_CACHE_DIR="$PWD/.tools/uv-cache" .tools/bin/uv run ...`。
GPU環境は`environments/embedding_gpu`、WTごとに`uv sync --project environments/embedding_gpu --frozen --offline`。
Nativeは対応WTをcwdにして`uv run --project environments/embedding_gpu --frozen --offline python ...`。
OSをまたいでvenvを使い回さず、大型Modelは全体をRAMへ読み込まずストリームHashする。

最後の全実装検証は**761 passed in 30.43s / Ruff成功**。新基準の実装Testはまだない。
機械的な監査証拠と、実研究での成功を区別する。新実装でSourceが変われば旧Validator検証資料も再照合する。

同じPC/Repositoryなら既存のdata/models・data/runtimes・data/indexes・data/runsが残る。
**Git Pushだけではこれらの未追跡実体は移動しない。** 別PCならManifestの参照先を別途転送/再取得し、Hash確認する。
Raw不足を理由に旧失敗やCalibrationを再生成しない。`phase11_chat_handover_v1.json`は重要証拠の照合目録であり、
全モデル/Index/環境を内包した移行Archiveではない。

各工程でユーザーへ成果・残る問題を説明する。意味ある単位で今回分だけCommit・通常Pushし、
Remote先端との一致/未Commit/未Pushと次工程を報告。研究日誌はJST時刻/決定/問題/到達点/次の完了条件を記録する。
引継ぎは最新状態を短く清書し、古い「実行中」記録を先頭へ際限なく積み重ねない。
