# 固定v23 Mainの書換え本文上限を保全した再開（2026-10-30）

2026-10-30 外的監視中断の再実行（以下の一般停止規則より限定的に優先）: ユーザーは復旧v2監視による外的中断1件を候補欠測とせず、同じ入力で書換えだけ1回再実行するよう明示した。[復旧v3](phase11_fixed_v23_recovery_v3.md)で元要求/全既存結果・費用不明を保全し、完了済み初回/内部評価を再利用する。旧長さ欠測2件は維持し、他の未知/エラーの再送やCalへの例外拡大はしない。全試行上限・累積wall・条件・全匿名採点封印とCal進行条件は維持する。現在の進捗は `docs/fixed_v23_automation_status.md` を参照する。

2026-10-30 追加委任: ユーザーはMain収集後の全採点・解析からCal自動起動/収集/全採点/解析・図表までの[自動進行](phase11_fixed_v23_automation_v1.md)を委任した。以下の「Calはユーザー起動」は旧担当分担の記録となり、新Protocolの条件確認後は専用サービスが起動する。元Mainの本復旧制御・推論Source・Rawは変更しない。

ユーザーは今回停止した続きから収集を再開し、その後も同じ書換え本文上限では停止しないことを指示した。本Protocolは[初回回答の復旧v1](phase11_fixed_v23_recovery_v1.md)を拡張する、結果観測後の停止規則変更である。v1の登録・入口・保存済み成功/失敗・元推論Source/設定/Releaseはそのまま保全する。

## 停止原因と開始前の状態

2026-10-29 17:28 JST、日本語の書換え1件で本文747 tokenが候補上限512を超え、`Final answer exceeds 512-token candidate budget` が記録された。応答全体は4018 token、予約上限6144以内で自然終了（`stop_type=eos`）、入力3224、`truncated=false`、`cost_incomplete=false`。生成打切り・応答不明ではなく、本文だけの長さ検証エラーである。

開始前は累積565試行・失敗2・未知0、入力1,327,110/出力1,924,970 token、既消費active-wall 37,310.69588450799秒。英語は20問完了、日本語は初回成功19/初回欠測1、内部評価の処理終了3/書換え成功2/書換え失敗1。v1公開状態の成功22/残り17に対し、v2では既存の書換え失敗1を処理済みに数え、成功22/初回欠測1/書換え失敗1/処理済み24/残り16とする。成功数を増やしていない。

## 変更と分析上の扱い

- 初回の固定512 token打切りはv1どおり失敗・欠測として保存する。
- 取得・checkpoint整合性確認済みで、自然終了し、本文の512 token超過だけで失敗した書換えも保存して次のQAへ進む。同じQAを再生成せず、回答を切り詰めず、別QAで補充しない。
- 書換え失敗QAの有効な初回回答・固定文・内部評価は保持する。失敗書換えは候補として匿名採点へ出さず、初回回答のみを採点する。書換え要求時には元設定の `keep_initial_answer_with_rewrite_failed_status` に従い初回を保持する。品質遷移は不明であり、書換え成功・改善・品質不良に補完しない。
- `report.private.json` の `records` には初回と評価を保持した行を含め、`rewrite.status=error` は変えない。`failures` は初回失敗に対応する元Schemaを維持する。別の `failure_inventory.json` に初回と書換え両方の失敗・Raw Hash・再送なしを保存する。既存の読込Validator/品質Export/方策再構成がこの形を検証できる。
- 全40選定、初回欠測数、書換え欠測数、正常完了数、比較可能数を別々に報告する。完全例の品質遷移が全40問を代表するとは保証できず、長い書換えに偏る欠測と2回の事後改訂を報告する。順序感度の分析に使える初回/内部評価と、初回対書換えの品質比較の分母を分ける。
- 元モデル/Prompt/Seed/温度/生成上限/閾値0.7/選定を変更しない。1660 Call/言語、5新規QA/段階、Retry0、段階12h/累積72hを持ち越す。失敗Call/Token/時間も累積に含める。
- 応答不明・通信/GPU・入力超過・JSON/意味形式・内部Judge・書換えの他エラーは停止する。6144 tokenで書換え応答全体が打ち切られた場合は今回の「自然終了済み本文超過」と異なるため停止する。

実Runtimeは温度0.2をfloat32由来の `0.20000000298023224` と返すため、分類では固定0.2と狭い許容誤差で照合する。Sampler変更ではなく表現差への対応であり、0.201は拒否する。実設定は元Release/言語Manifestでも固定する。

## 保全・実装・検証

元Checkout `.tools/worktrees/fixed-v23-study-v1` の `src` 外へ新 `scripts/recover_fixed_v23_v2.py` / `fixed-v23-recover-v2.sh` を配置する。元 `fixed-v23-recovery-v1.json` とその入口を変更せず、新 `fixed-v23-recovery-v2.json` からHashで結ぶ。元Releaseの全Source/設定、親登録、今回開始前の科学的記録を検査する。

準備時には停止Run全ファイルを `data/runs/recovery_audits/fixed-v23-answer-length-v2/before` へ独立コピーし、全Hash一致を確認する。新規Native0のまま日英の試行/失敗/未知と元英語20問を検証し、その後同じRunを再開する。実検証・起動記録は `data/manifests/fixed_v23_main_recovery_validation_v2.json` に保存する。専用Checkout/Run/環境はGit管理外であり、Pushでは転送されない。

追加テストは、限定分類、未知/他エラー拒否、失敗Call費用、親Source/Raw改変拒否、欠測別進捗、両段階の失敗一覧、元Runnerの実関数と合成Clientによる途中失敗→続行→新たな同種失敗→段階続行→完了後追加Call0、保存Byte不変、匿名品質/文Expected Export、書換え失敗時の初回保持を検証する。合成Clientの成功を新しい実機推論の成功と呼ばない。

## 今後の操作

2026-10-30 12:37 JST、準備・検証後に実際に再開した。応答 `started=true` / Supervisor PID130099と公開状態 `collecting` を確認した。準備時に866ファイル全体を独立退避し、835科学的記録・元Release/親登録・元Source/設定・英語20問を推論0で照合した。全1362テスト（41.58秒）/Ruffと、固定Checkout Sourceを指定した追加26テスト（1.11秒）が成功した。26件は全体にも含まれるため件数を合算しない。全Main収集・匿名採点・Calは未完了。

12:40 JSTの起動後監査ではSupervisor/childがともに生存し、565→567試行（新規2、うち応答待ち1）へ進んだ。失敗2は不変、初回Native40回は不変、既存835科学的記録の全Hashも一致した。実行中の `unknown=1` は応答待ちのstarted記録を数える現行表示であり、終了済みの応答喪失とは区別する。実験全体の完走や残りQAの成功を保証する観測ではない。

ユーザーは今回Codexによる続きからの起動を明示的に依頼した。準備と検証後、このコマンドで再開する。

```bash
cd '/home/uchida/デスクトップ/code/rag_research/.tools/worktrees/fixed-v23-study-v1'
./fixed-v23-recover-v2.sh resume --run data/runs/bilingual_development/fixed-v23-main-v1
```

状態確認とQA境界での安全停止要求:

```bash
./fixed-v23-recover-v2.sh status --run data/runs/bilingual_development/fixed-v23-main-v1
./fixed-v23-recover-v2.sh stop --run data/runs/bilingual_development/fixed-v23-main-v1
```

今回のRunに旧 `fixed-v23.sh resume` / `fixed-v23-recover.sh resume` は使わない。全QAの初回処理は終了済みなので、再開時に初回回答の追加推論は不要。既存成功22問と書換え失敗1問の保存済み推論を再利用し、日本語の残り16問へ進む。

公開状態は `completed_qa` / `successful_qa` を正常完了数、`baseline_failed_qa` を初回欠測、`rewrite_failed_qa` を内部処理済みの書換え欠測、`processed_qa` をその合計として表示する。`remaining_qa=40-processed_qa`。`failed` は累積失敗件数を保持し、`unhandled_failure_records` だけが既知の長さ超過以外を示す。書換え失敗が追加されても成功件数へ加算しない。

追加失敗がなければ最終的に正常完了38/初回欠測1/書換え欠測1/処理済み40/残り0で `awaiting_scoring` となる。書換え欠測が増えれば正常完了数はその分減る。`collection_completed=true` は欠測を含めた収集処理の終了であり、全40成功・全40完全比較ではない。

終了後はCodexが全日英匿名品質/文Expectedを先に封印し、その後内部F/判断と結合して品質・順序対反復・費用/欠測を分析する。両言語10完全比較以上等のCal進行条件は維持し、Calは別Protocol/ユーザー起動、Phase12は開始しない。終了時間は再開後の実測から見直す。


2026-10-30 14:04 JST 追記: 実走の監視Callbackがstatus=startedの書換えに完成Hash検証を行い、13:52頃にChild終了/応答不明1件を生じさせた。Root候補はstartedを監視集計から外す修正と再発Testを追加したが、元登録Sourceは保持し、今回の未知は再送せず停止する。詳細は[自動化の起動・中断記録](phase11_fixed_v23_automation_v1.md#2026-10-30-実起動とmain中断の検出)。本文上限512超過の限定許容を未知に拡張した意味ではない。
