# Phase 11 関係・説明の範囲を照合するv17の実走

2026年10月22日16:49 JST追記。session6340は全58条件/70 Callを終了し、
Critical4/4・英語24/24・日本語28/30・誤支持0で元診断基準に通過。監査49997は
95 Source/再開133 File不変・追加Call/Server0、全70出力独立Schemaを確認した。
[全結果と旧回帰v6への引継ぎ](phase11_relation_scope_semantic_result_v1.md)を次の再開先とする。
以下は各時点の開始・未完了Guardの履歴であり、同じ6340を再生成しない。

2026年10月22日15:49 JST時点。[候補と事前登録](phase11_relation_scope_candidate.md)を
`1214dbf82eaabafa8edd6076804c7bab24dba58c`へCommit・通常Pushし、リモート一致を確認した。
候補資料/旧失敗は保持し、全意味診断の採否はまだ未確定である。

## 固定資源と生成0

専用WTは`.tools/worktrees/phase11-qwen35-9b-q5-v17`。
準備session57377で650 File Binding、56不変Hardlink、内部相対Symlink10を照合した。
JSON/Rawはコピーし、全リンクの作成後に内部解決を確認。GPU環境58 PackageをOfflineで再現した。

session8327は全70実入力/Completion0に通過。最大3793 Token、Context24576/全Layer CUDAを確認。
VRAM7275/8151 MiBは一点観測で、最大使用量やKernel時間ではない。
準備/Preflight6 Artifactを正規保存して固定WTとByte一致を確認した。
その後もNative Core/Probe27と新Q5形式24 Artifactの不変を照合し、追加の人工形式Callは0。
証拠は`phase11_relation_scope_preflight_v1.json`。

## 現在の実走と継続方法

同じ固定WTで全58条件/最大70 Callをsession6340として開始した。
出力は`data/runs/semantic_diagnostics/phase11-qwen35-9b-q5-relation-v17`、
開始記録は`phase11_relation_scope_launch_v1.json`。
最初のCritical4条件が全一致した場合だけ人工54条件へ進む。
全元対象/Expected/基準・固定文/全文/Schema・Sampler/Seed・Retry0を維持する。
既存9B実439/累積上限593、新候補の全意味70+通過時の全旧回帰84=最大154を保持する。

同じHandleを継続観測し、終了前に再起動しない。終了後だけ固定WTのuvで、保存済み
`data/runs/development_screening/phase11-q5-known-v5-audit-v1/audit.py`へ
Config v17/新Runを位置引数で渡し、全入力/順序/文ID/Source/費用/失敗/未試行と追加0再開を監査する。
このHelperは旧結果に束縛されていない同一Byteの汎用Direct監査である。

全意味基準通過・全Raw監査後だけ、同じ旧全15 QA/42文/30条件・84 Callを新前提へ結ぶ。
旧Q5回帰v5の不採用/18条件未試行を置き換えず、Source25/Expected/基準/裸拒否8も保持する。
全旧基準通過後だけ新主Policy/実費へ進む。
主/予約Cal/Evaluationの新規QAは使用していない。
主/Cal採用・最終N/資源/条件/凍結は未了、Gate 11未通過・Phase 12未実施、Goal継続中。

## 旧全回帰v6への準備Guard

2026年10月22日16:13 JST。実行中session6340の終了・監査を待つ間に、
旧回帰v5の準備Helperから、候補v17/新Runを前提とするv6用の別Helperを作成した。
全旧15 QA/42文/Source25/全Expected/基準/裸拒否8は原版との一致を確認し、
正の処理は全58条件/70 Callの通過・終了後監査・全Rawのコピー上での再検証を必須とする。
新しい回帰Config/Planはまだ作成していない。

実未完了の固定WTをPRIORへ指定する確認では、終了・監査不足を実際に拒否した。
この確認でのみ参照先を固定WTへ向け、正の処理の参照先は正規Runのままとした。
拒否はConfig読込み/Run Lock/再開より前で、完了済みCritical4集約FileもByte不変。
稼働中の他Task全体は固定・Snapshotしていない。追加Model Call/Serverは0。
構文/Ruffに成功し、Helper/確認Script/Receipt/標準出力・エラー/検査Logの7 Artifactを
`phase11_relation_scope_known_preparation_pending_v1.json`へ結んだ。
これは準備Guardの検証であり、全診断通過・正の登録・旧回帰の採用を示さない。
