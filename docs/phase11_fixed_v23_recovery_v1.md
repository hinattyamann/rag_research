# 固定v23 Mainの出力上限停止と途中再開（2026-10-29）

元Run `data/runs/bilingual_development/fixed-v23-main-v1` の停止を調べ、保存済み結果を保全した再開入口を追加した。長時間の実収集はまだ再開していない。ユーザーが以下のコマンドで起動する。

## 停止した原因

2026-10-28 19:51 JST、日本語の初回回答3問目で、初回生成器Qwen2.5-3Bが固定の出力上限512 tokenまで生成し、自然終了する前に打ち切られた。Native応答の `stop_type=limit`、`tokens_predicted=512`、`n_predict=512` と、保存記録の `finish_reason=limit` が一致する。応答は取得・保存済みで、`cost_incomplete=false`。入力3309＋予約出力512＝3821はcontext 4096内で、`truncated=false` だった。

元の生成器は上限打切りを `Output token limit reached; answer may be incomplete` エラーとして保存する。元のMain制御は1件の失敗でも全体停止し、通常の `resume` も既存エラーを検出して拒否する。この組合せが今回の停止と再開不能の直接原因である。なぜモデルが512 token以内に自然終了しなかったかまでは確定していない。機械的な停止情報からGPU故障や無限反復と断定しない。[診断証拠](../data/manifests/fixed_v23_main_interruption_v1.json)に記録した。

停止時点では英語20問の初回回答・内部評価・一回書換えが完了している。日本語は初回回答2問が成功、1問が上限打切り、17問が未着手。日本語の内部評価は未着手。試行410、応答不明0、失敗1だった。

## 変更したことと研究上の扱い

新入口 `scripts/recover_fixed_v23.py` と `fixed-v23-recover.sh` を専用Checkoutへ追加した。元の封印済み `src`、設定、Release、言語Manifest、英語結果、日本語の保存済み成功・失敗Rawは変更しない。元の回答生成・文抽出・評価・書換え関数を使い、元モデル・Prompt・出力上限512・温度・Seed・閾値・選定QAを維持する。

取得済みで整合性確認済みの「初回回答が固定512 token上限で打切り」のみ、当該QAを欠測として残し、未実行の選定QAへ進む。失敗回答を正常回答として内部評価せず、同じQAを再送せず、別QAで補充しない。今後同じ種類の初回打切りが発生した場合も失敗を保存して進む。応答不明、通信/GPU障害、入力超過、その他の初回エラー、内部評価/書換えエラーは従来どおり停止する。

これは**停止結果を見た後の停止規則変更**であり、元の事前登録どおり完走したとは記載しない。選定分母は英20＋日20＝40のまま、成功・欠測・未実施・完全比較可能数を分ける。追加失敗がなければ有効な収集対象は英20＋日19＝39問となる。欠測をF=0や品質不良へ補完しない。長い回答を必要とするQAが欠測になり得るため、完全例の分析だけでは全40問を代表すると保証できない。この限界、言語別欠測数、変更前後の実行区間を論文で報告する。

失敗Callとtoken費用は削除せず累積に含める。1660 Call/言語、新規5 QA/段階、Retry0、通常段階12h・累積Main72hの元上限を維持し、既消費wall約7.78hを持ち越す。再開後は日本語の初回未実行17問、その成功分と既存成功2問の内部評価・書換えへ自動で進む。英語を再生成しない。

## 保全と実データ検証

専用Checkoutは `.tools/worktrees/fixed-v23-study-v1`、元Commitは `f0b7c71c4375a617c7142c67e3aa0610f73edb14` のまま。停止時Run全665ファイルを別ディレクトリ `data/runs/recovery_audits/fixed-v23-terminal-limit-v1/before` に独立コピーし、全Hash一致を確認した。科学的記録641ファイルは再開時にもHash検査する。可変な公開状態・制御状態・進捗は元スナップショットに保管する。

専用Checkoutの `fixed-v23-recovery-v1.json` が新入口・Wrapper・元Release・保全記録を結ぶ。Gitで配布する[再開検証記録](../data/manifests/fixed_v23_main_recovery_validation_v1.json)はそのHashと実検証結果を保存する。Git管理外のRun・環境・専用CheckoutはGitHubへのPushでは転送されない。

`check` は元Source/設定/入力と旧結果を照合し、元の読込Validatorで英語全20問を再検証する。新しいモデル推論は行わない。`arm` は所有プロセス終了を確認して `recovery_ready` を保存するだけで、収集を起動しない。

## ユーザーが行う操作

研究室PCの通常の端末で実行する。

```bash
cd '/home/uchida/デスクトップ/code/rag_research/.tools/worktrees/fixed-v23-study-v1'
./fixed-v23-recover.sh resume --run data/runs/bilingual_development/fixed-v23-main-v1
```

`started: true` が出たら、次のコマンドで確認する。

```bash
./fixed-v23-recover.sh status --run data/runs/bilingual_development/fixed-v23-main-v1
```

必要なときの安全停止要求も新入口を使う。

```bash
./fixed-v23-recover.sh stop --run data/runs/bilingual_development/fixed-v23-main-v1
```

今回のRunに旧 `fixed-v23.sh resume` は使わない。旧入口は既存失敗を引き続き拒否する。`check` はいつでも推論なしで整合性確認に使える。`prepare`/`arm` を繰り返す必要はない。

## 新しい状態表示と終了後

|項目|再開準備時|意味|
|---|---:|---|
|`state`|`recovery_ready`|起動待ち。まだ収集中ではない|
|`attempts` / `failed` / `unknown`|410 / 1 / 0|元の失敗と費用を残した累積|
|`completed_qa` / `successful_qa`|20|初回・内部評価・書換えまで成功したQA|
|`baseline_qa`|22|初回回答の成功数|
|`baseline_failed_qa`|1|確認済み初回上限打切りの欠測数|
|`baseline_remaining_qa`|17|初回回答の未実施数|
|`processed_qa`|21|成功完了＋欠測として確定した選定QA|
|`remaining_qa`|19|内部評価等が残る選定QA（初回成功2＋未着手17）|
|`unhandled_failure_records`|0|今回の欠測規則で扱えないエラー数|
|`collection_has_missing`|`true`|欠測を含む。全40問成功とは扱わない|

成功継続時は `state=collecting`、所有Supervisor/childが生存する。`failed=1` が残ること自体は今回の既知失敗を保持しているためである。新たな `failed` 増加は、`baseline_failed_qa` と `unhandled_failure_records` および `reason` を併せて確認する。`updated_at_utc` やログ更新も確認し、所有プロセス生存だけで進捗を断定しない。

全選定QAを成功または欠測として処理すると品質/Expected Packetと `failure_inventory.json` を出し、`awaiting_scoring` で終了する。追加失敗がなければ `processed_qa=40`、`completed_qa=39`、`baseline_failed_qa=1`、`remaining_qa=0`。`collection_completed=true` は欠測を含めた収集処理の終了であり、全40問成功や品質合格を意味しない。

ユーザーは終了時の新 `status` と `report_to_codex.txt` をCodexへ渡す。Codexは日英全品質Label/実使用根拠のみの文Expectedを封印してから内部F/判断と結合し、欠測を明記してMain解析する。Calは両言語10完全比較以上・全採点封印等を確認した後に別Protocolで準備する。Calの即時起動、閾値/Prompt再調整、旧Gate11合格への読み替え、Phase12開始は行わない。日本語の実測時間がまだないため、従前の終了日時やCal開始日を確約せず、再開後に再見積りする。
