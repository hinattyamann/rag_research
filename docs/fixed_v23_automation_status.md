# 固定v23 自動実行の状況

更新: 2026-10-31 17:54:35 JST

現在の工程: **publish-main**

Codex CLI起動予約数: 42（ChatGPT認証、APIキーへの切替なし）

収集待ち・GPU収集・通常のPython集計・Git反映ではCodexを呼ばない。CLIは匿名AI採点でのみ起動する。

| Main項目 | 値 |
|---|---:|
| state | awaiting_scoring |
| updated_at_utc | 2026-10-30T12:48:39.021627+00:00 |
| attempts | 1005 |
| failed | 2 |
| unknown | 0 |
| completed_qa | 38 |
| baseline_failed_qa | 1 |
| rewrite_failed_qa | 1 |
| processed_qa | 40 |
| remaining_qa | 0 |
| archived_external_attempts | 1 |
| historical_unknown_responses | 1 |
| external_reexecutions_started | 1 |
| token_totals_complete | False |

| Cal項目 | 値 |
|---|---:|
| baseline_success | 20 |
| baseline_failed | 0 |
| rewrite_success | 10 |
| rewrite_failed | 0 |
| completed | False |

直近の作業: `{'updated_at_utc': '2026-10-31T07:03:26.642623+00:00', 'stage': 'collect_cal', 'cohort': 'cal', 'language': 'en', 'phase': 'internal', 'codex_running': False}`

## 工程と完了条件

Main収集 → 日英全品質/Expected採点封印 → Main解析 → Cal進行条件確認/登録 → Cal収集 → 日英全採点封印 → Cal解析 → 図表/集計/結果説明資料。
正常な完了状態を検知して進み、時刻だけでCalを開始しない。比較数不足・未知/他エラー・利用枠不足では保存して停止する。
実行中のMain unknownは応答待ちのstarted記録を含む。終了済みの応答喪失と同一視しない。

外的中断の許可済み再実行がある場合、元要求はarchived_external_attempts/historical_unknown_responsesに残す。現在のunknownとは別で、過去の応答/最終費用が復元された意味ではない。

## ノートPCからの確認

このBranchの最新を取得し、このファイルと `data/manifests/fixed_v23_automation_status_v1.json` を読む。
集計・図表は `reports/fixed_v23_order_study_v1/`。工程の切替・完了・予期しない停止など、意味のある区切りでcommit/pushする。定時送信はしない。
GitHubの更新時刻は最後に反映した区切りを示す。収集中は更新がなくても停止とは限らない。ローカルの状態記録は約1分ごとに更新する。
Raw、環境、モデル、採点途中のラベルはGitで転送しない。研究室PC側の稼働を維持する。
同じBranchで同じ箇所を両PCから同時編集しない。ノート側で収集を二重起動しない。

## 残る著者作業

図表完了後も、論文執筆・数値/主張/引用の照合・教員確認・投稿形式への整形・提出は未実施。
旧Gate11/Phase12は未達のまま。限界と欠測を含めて結果を説明し、採択を保証するものではない。
