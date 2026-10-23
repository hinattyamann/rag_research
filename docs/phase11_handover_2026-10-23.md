# Phase 11 新チャットへの引継ぎ

更新日: 2026-10-23。新チャットでは本書と[評価器・資源・テスト見直し方針](phase11_evaluator_review_policy_v1.md)から読む。
工程の正本は[research_roadmap.md](research_roadmap.md)。長い日誌/過去の引継ぎは履歴であり、必要な箇所だけ参照する。
新チャット用の貼付文は[phase11_next_chat_prompt.md](phase11_next_chat_prompt.md)。

2026-10-23の再開追記: [基準v2の実装と新回帰登録](phase11_binary_adoption_v2.md)を追加した。
旧v1/旧Runを保全し、全780 Test/Ruff・未達拒否を確認。新しいNative実行先は同資料と最新ロードマップを使う。
以下の「新基準未実装」「新枠未登録」は移行時点の履歴である。

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

## 5. 採用した見直しと未実装事項

詳細は`docs/phase11_evaluator_review_policy_v1.md`。

- C↔NSだけの誤りは二次診断。主採用を支持/非支持に対応させる設計とし、支持Recall/非支持Specificity各0.90以上を新Versionへ実装する。
- 旧の誤支持0/全Critical3分類完全一致を要求する経路は保存し、新VersionをKnown→Main→Cal→最終Validatorまで結び付ける。現在のGuardは未変更。
- 新鮮な結果を見る前に必要なクラス被覆/分母0/不足時の扱いまで固定する。クラス不足を補充や自動通過で埋めない。
- 次の追加候補は最大1個。追加開発は全体で188試行またはNative Task経過4時間まで、診断24はその内数。実行前に別事前登録し、無制限更新しない。
- 旧851から新開発累積上限は最大1039。これは設計上限で、新規Runはまだ登録/実行していない。
- Main各20/予約Cal各20、実QAの5順序/5反復、全文/固定文、閾値0.7、裸拒否の一回書換えは維持。

温度0.2の暫定Judge平均54.964秒。各20 QA/平均5文/9試行ならJudgeだけMain25.6〜33.8時間、
同規模Cal込み51.2〜67.6時間。総時間/上限/CIではない。各言語で同じ平均文数を仮定した算術で、
実際の言語別原子上限1660は別に守る。根拠:
`data/manifests/phase11_qwen35_q6_temperature_resource_estimate_v1.json`（7 Artifact）。

## 6. 次に行うこと――依存順と完了条件

1. **旧成果と移行を検証する。** 本書のManifest/Raw/Source/Hash、Gitと実機、Goal状態を確認。
   既存の日本語整備やIndexを作り直さず、Evaluation QAを開かない。
2. **新しい基準Versionを具体化する。** 見直し方針を研究計画/実装計画/Protocol/採用Guard/Testへ反映。
   旧v1拒否は保持。Known/Main/Cal/最終Validatorの整合を検証し、全Test/Ruff・検証Source Hashを更新。
   この作業は新規QA/Native推論なしで進められる。
3. **CUDA障害を分離して調べる。** 保存済みLogとDriver/Kernel/NVIDIAの一次資料を調べる。
   Root Cause未確定を明記し、必要な変更案/影響を具体化。GPU Reset/再起動/Driver/OS設定を勝手に変更しない。
   新枠を事前登録し、生成0→内数24以内の診断→最終追加候補1個の検証へ進む。
   新しい完全Known回帰とHealth/意味基準の両方がそろって初めてMainへ進む。
4. **実Main各20 QAを完了する。** 採用候補に一致する新しいPolicyを作り、固定選定IDのまま実走。
   BaselineとInternalのProcessを分離し、新規5 QA/段階Session・1660/言語・全文/全固定文原子予約。
   Mainの内部Fを含むstdoutをファイルへ退避し、両言語の全候補品質と全Expected封印前に読まない。
   完全比較QA各10以上、全失敗/未試行/品質不明/費用、意味/品質/判断を照合し実証明書を作る。
5. **予約Cal→最終凍結。** 実主証明書後だけCal Protocolを事前保存し、予約各20を一度実走。
   全品質/Expected封印後だけF/対応を結合。調整が必要なら使用済みCalとして保持し、同じデータで条件探索しない。
   実主/Calの費用、比較率/CI/採点負担から最終N/資源を決め、拡張Validatorを実証拠で通す。
   最終Manifest/Hash/全Gate11証拠がそろった場合だけGoal完了。Phase 12は開始しない。

上限/障害で進めない場合は未達を明示し、具体的な代替と必要な判断を示す。
単にテスト/形式/計画が整っただけではPhase 11を完了としない。

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
