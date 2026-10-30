# 固定v23 Main復旧v3 — 外的な監視中断1要求の限定再実行

2026-10-30。ユーザーは、監視プログラムによる外的中断は書換え候補欠測とせず、エラーが生じた箇所から再開するよう明示した。前回の[欠測として扱う未実施案](fixed_v23_interrupted_rewrite_recovery_proposal_v1.md)を採用しない。本Protocolがその案と旧「未知は一切再送しない」の一般規則に優先するのは、以下でHash固定した1要求だけである。

原因は復旧v2の `rewrite_missing_count` が未確定status=startedへ完成Hash検証を行い、例外後のfinallyが収集ChildをSIGTERM終了させたこと。自動化サービスの追加実装が推論Coreや条件を書き換えたためではなく、既存の復旧v2監視の不具合である。新自動化サービスはその後に停止を検出した。[中断証拠](../data/manifests/fixed_v23_main_monitor_interruption_v1.json)を保持する。

## 許可範囲と元条件

- 元専用Checkout f0b7c71、Main `data/runs/bilingual_development/fixed-v23-main-v1` の日本語 `internal/4c57945331dd21845abdf886/rewrite.json`、元SHA `a9197387192b1f488b4dcab03a61a954ee91ff9cd559264672b596834a67f76d` の要求1件だけ。同じQAの初回回答と9条件すべての内部評価は保存済みで、これらを再実行しない。
- 元のstarted記録はRun内 `external_interruptions/monitor-cancellation-v1/request.started.json` へByte不変で退避し、元Run全体も独立退避/全Hash照合する。再実行結果は元の書換えPathへ保存する。旧記録のstatus/内容を書き換えず、旧v1/v2登録・入口・推論Core・全既存結果を保持する。
- 送信直前に、元要求のrequest Hash、binding、messages、settings、prompt token列、rendered prompt Hash、input token数を照合する。一致しなければ新しいNative要求を送らない。送信予約を永続化し、外的中断の再実行は最大1回とする。さらに中断/通信/GPU/入力/他形式エラーが起きても再送を繰り返さない。
- モデル/Prompt/Temperature/Seed/文脈長/生成上限/本文512/閾値0.7/選定QAは不変。今回の中断自体を候補欠測にしない。ただし、再実行して受信した新しい応答が既存の限定長さ失敗に該当すれば、その応答には従来の失敗・欠測保存規則を適用する。以前からある初回/書換えの長さ欠測2件は再送しない。

## 費用と分析への影響

開始前の実試行は629。元の中断要求も試行上限へ含め、再実行分は新しい別試行とする。1660 Call/言語、5新規QA/段階、12h/段階・Main累積72hは持ち越し、spent wallをリセットしない。

元要求の応答・最終出力Token・処理時間は不明のまま。稼働中の `unknown` は現在の未確定要求だけを数え、退避した過去の未知応答1件は `historical_unknown_responses`、余分な試行は `archived_external_attempts` として別表示する。`token_totals_complete=false`、総output Tokenはnullを保ち、0や再実行結果で元の費用を補完しない。

全選定40・各完全比較分母と既知長さ欠測の扱いは変えない。Mainの全候補採点・全文Expectedを先に封印してから内部結果と結合する。Cal進行の現在の未知0、言語別10完全比較以上等の条件は維持し、外的中断の過去費用不明を別に明示する。旧Gate11/Phase12は未達のまま。Calにはこの再実行例外を適用しない。

収集費用のNative試行数には退避した要求を含め、入力Tokenは確認済み分、出力Token/時間は既知分と不完全性を報告する。図表と説明資料で「既知分の下限」と明示する。各方策の運用費用と、今回だけの外的中断の追加費用は区別する。これは原因が確認された実装障害に対する事後の再実行例外であり、元要求の不確実性が消えたとは説明しない。

## 実装と実行

新入口 `scripts/recover_fixed_v23_v3.py` は封印済み復旧v2を読み、監視集計のstarted除外、1要求の照合/送信予約、試行費用保全だけを外側から追加する。新登録 `fixed-v23-recovery-v3.json` に親v2・新入口・Wrapper・保存済み結果・元要求・取消ログをHashで結ぶ。登録後の旧ファイル差替えは行わない。

実験はsystemdユーザーサービス `fixed-v23-main-recovery-v3.service` で起動し、完了後の既存自動化監視も再起動する。ノートPC向け進捗は原則1時間と工程切替/完了/失敗時にGit反映する。

```bash
./.tools/worktrees/fixed-v23-study-v1/fixed-v23-recover-v3.sh status --run "$PWD/.tools/worktrees/fixed-v23-study-v1/data/runs/bilingual_development/fixed-v23-main-v1"
uv run python scripts/automate_fixed_v23.py status
```

Wrapperは専用Checkoutへcdするため、Runを明示する場合は絶対Pathを使う。二重起動しない。起動・現在地・テストの実証は `data/manifests/fixed_v23_main_recovery_validation_v3.json` と研究日誌へ記録する。実収集が完了するまでMain完走/実採点/Cal収集/図表完了とは扱わない。


2026-10-30 14:29 JST 実起動証拠: 14:24:51 JSTの初回systemd起動はCUDA共有ライブラリPath未継承により `llama-server --version` がexit127で終了し、新Native0/再実行予約未使用だった。通常端末と同じ `LD_LIBRARY_PATH=/usr/local/cuda-12.9/lib64` をMainと自動化双方へ指定し、14:26:34 JSTに再起動した。Supervisor154056/Child154210・collectingを確認。中断書換えは同一request Hash/Token列でstatus=okとなり、既存911記録不変、旧長さ失敗2不変で次QAへ進んだ。自動化監視も14:27:19 JSTに再起動し、waiting_main/CLI0と進捗38adf5dの自動Pushに成功した。現在の応答待ちunknownと、退避した過去応答不明1は区別する。
