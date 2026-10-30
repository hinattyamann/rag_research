# 固定v23 自動実行の状況

更新: 2026-10-30 14:07:26 JST

現在の工程: **failed（Main中断により自動進行を停止）**

Main欄は13:52:38 JSTの古い公開値です。実プロセスは終了しており、実Rawの監査値は629試行・既知失敗2・応答不明1です。[中断監査](../data/manifests/fixed_v23_main_monitor_interruption_v1.json)と[未実施の復旧案](fixed_v23_interrupted_rewrite_recovery_proposal_v1.md)を参照してください。収集再開・Cal開始は行っていません。

Codex CLI起動予約数: 0（ChatGPT認証、APIキーへの切替なし）

収集待ち・GPU収集・通常のPython集計・Git反映ではCodexを呼ばない。CLIは匿名AI採点でのみ起動する。

| Main項目 | 値 |
|---|---:|
| state | collecting |
| updated_at_utc | 2026-10-30T04:52:38.095388+00:00 |
| attempts | 628 |
| failed | 2 |
| unknown | 1 |
| completed_qa | 22 |
| baseline_failed_qa | 1 |
| rewrite_failed_qa | 1 |
| processed_qa | 24 |
| remaining_qa | 16 |

停止理由: ValueError: Main collector exited while status still says collecting; preserve unknown outcomes and inspect supervisor.log

## 工程と完了条件

Main収集 → 日英全品質/Expected採点封印 → Main解析 → Cal進行条件確認/登録 → Cal収集 → 日英全採点封印 → Cal解析 → 図表/集計/結果説明資料。
正常な完了状態を検知して進み、時刻だけでCalを開始しない。比較数不足・未知/他エラー・利用枠不足では保存して停止する。
実行中のMain unknownは応答待ちのstarted記録を含む。終了済みの応答喪失と同一視しない。

## ノートPCからの確認

このBranchの最新を取得し、このファイルと `data/manifests/fixed_v23_automation_status_v1.json` を読む。
集計・図表は `reports/fixed_v23_order_study_v1/`。原則1時間ごと、工程の切替・終了・失敗時にもcommit/pushする。
Raw、環境、モデル、採点途中のラベルはGitで転送しない。研究室PC側の稼働を維持する。
同じBranchで同じ箇所を両PCから同時編集しない。ノート側で収集を二重起動しない。

## 残る著者作業

図表完了後も、論文執筆・数値/主張/引用の照合・教員確認・投稿形式への整形・提出は未実施。
旧Gate11/Phase12は未達のまま。限界と欠測を含めて結果を説明し、採択を保証するものではない。
