# Phase 11 v15の全意味診断と旧15 QA回帰v4の事前登録

2026年10月22日11:17 JST時点。固定`55d031c`の引用状態Schema v3候補は、
同じ全58条件/70 Callを終了し、事前の診断基準に通過した。
結果は`data/manifests/phase11_cited_decisions_result_v1.json`へ保存した。
実主Development/未使用Calibrationの採用やGate 11通過ではない。

## 全診断の実測と監査

| 項目 | 結果 |
|---|---:|
| 既知Critical条件 | 4/4一致 |
| 人工英語 | 24/24一致・誤支持0 |
| 人工日本語 | 30/30一致・誤支持0 |
| 完了条件/Call | 58/70 |
| 未試行/Task失敗/費用不明 | 0/0/0 |
| 入力/出力Token | 118450/194751 |
| Task経過秒の合計 | 3168.554393秒 |

95 Source Hash、各子Callの質問/全文草稿/固定対象文/根拠本文・ID・Titleと提示順、
固定文IDから子Callのc1への対応、全費用を照合した。終了後の再開で133 File不変、追加Call/Serverとも0。
Raw135 Fileを正規保存し、全70最終出力のSource/理由のAI確認1 Fileと準備/Preflight6を加えた
全142 Artifactを固定WorktreeとByte一致で保存した。

独立Draft-7検証器で全70出力を再検査した。35文の元/逆で生成Schemaは不変だった。
新生成制約でもLabelの後付け修正や理由からのID補完は行っていない。
全68確定判定は保存Expectedに一致し、曖昧2判定は元方針のまま保持した。
この結果は繰返し使用した既知/人工Developmentの確認であり、未使用QAの意味精度を保証しない。

## 解釈上の限界

- 人工27例は各1文書のため、元/逆の27組は入力自体が同一だった。全54条件を保持するが、
  独立した54例や文書提示順の効果の証拠には数えない。
- Council c6は元の曖昧扱いを維持した。観測Labelは元/逆とも矛盾だが、正解Labelへ確定し直さない。
  精度集計からだけ外し、Fの分母7には残す。
- Councilはc4の矛盾を正しく検出しても、F=5/7で既存閾値0.7以上となる。元/逆とも採用相当であり、
  意味診断通過と回答品質・修復判断の妥当性は別である。この診断で新規書換えや品質採点は行っていない。
- ja-compound-2の元/逆の理由は既存160文字上限で末尾が「10:」となる。主要な時刻比較は残り、
  最終JSONと判定は有効だが、不自然な理由末尾をRawのまま保存した。
- 確認者は同じ開発履歴を共有するCodex AI。human_reviewed=false、正確な採点Model IDは取得不能で、
  独立/盲検の人手精度評価とは主張しない。

## 次の全旧回帰v4

親の全証拠保存後、準備Helperの正の経路を実行した。親136 Fileの同一Byteコピーだけで全診断を再検証し、
原本/コピー不変・追加Call/Server0のまま新Config/Planを作った。以前の未達拒否証拠も保持する。
実準備の証拠は`phase11_known_trace_preparation_validation_v1.json`。
新Config/Planを含む状態で全734 Test（26.46秒）/Ruffにも成功した。

旧v1/v3と同じ全15 QA/42文/30条件、37確定/5曖昧、全25 Source/Expected/理由/基準/裸拒否8を保持する。
`phase11_known_trace_candidate_v4.yaml`は通過したv15からStudy VersionとPlanだけを変え、
`phase11_known_trace_regression_v4.json`の前提を今回の通過Reportへ結んだ。

事前登録v8は最大84 Call/Retry0、最初の負例12条件/42 CallのCritical全一致後だけ残りの正例へ進む。
全74確定判定と支持58判定の一致率各90%以上、明確な非支持への誤支持0、全予定完了/失敗0を維持する。
Native Core/Probe27 HashとModel/Runtime/予算/Grammarが不変なので、新形式v4の全25 Artifactを照合して再利用する。
既存9B実完了275からの累積上限359は変更しない。63〜86分程度の時間例は過去平均からの外挿で、時間上限ではない。

次は新Config/Plan/証拠をCommit固定し、専用Worktreeの全84実入力/生成0/全層CUDA確認後に実走する。
全旧回帰の通過前に新しい主Policyを採用しない。
実主各20 QA/全匿名品質・Expected封印/証明、予約Calと最終N/資源/条件/凍結は未了。
Gate 11未通過、Phase 12未実施、Goal継続中。
