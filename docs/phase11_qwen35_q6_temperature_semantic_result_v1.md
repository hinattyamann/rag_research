# Phase 11 温度0.2の全意味診断と既知15 QA回帰v9の登録

2026年10月23日16:20 JST時点。固定`17d57c6b4186a158685b85eb50da71fb4d04d93b`の
session89310は16:14 JSTに終了し、元29例/35文/全58条件・70 Callの診断基準に通過した。
終了後監査60518も完了した。新しい全既知回帰やMainの採用を意味しない。

| 元の事前基準に対する結果 | 一致/対象 | 誤支持 |
|---|---:|---:|
| 既知Critical条件 | 4/4 | 0 |
| 人工英語条件 | 24/24 | 0 |
| 人工日本語条件 | 28/30 | 0 |

確定Labelは66/68、支持Labelは28/28一致した。日本語`ja-qualification-3`は両順序とも
Expected支持不足に対し矛盾で、「由来は不明・一説のみ」という記載から断定文を矛盾とした。
この2不一致は旧温度1.0と同じであり、正解/基準を変えない。
全70入力Message/Schemaは旧Q6と同一、Leaf要求設定の差はtemperatureだけで、全68確定Labelも同一だった。
曖昧Council c6の元順序だけC→NSに変わり、今回は両NS。曖昧の扱いと全7文のF分母を保つ。
両F5/7は閾値0.7以上で、c4の明示矛盾があっても採用相当になる問題を修正せず保持した。
温度変更による意味精度の改善は認められず、一般的な正確性や言語単独の因果効果を主張しない。

## 終了後の実証拠

- 95 Sourceと再開前133 Fileが不変で、追加Call/Server0。全質問・回答・固定文・根拠本文/ID/Titleと順序、全費用を照合した。
- 全70 Native最終JSONを独立decode/Draft-7検証し、35文組でSchema不変を確認した。全70で実温度0.20000000298023224、Seed42/主要Samplerが設定に一致した。
- 全70最終理由と29例の全文根拠を同じ開発履歴のCodex AIが確認した。human_reviewed=false、非匿名/履歴隔離なし、実採点Modelの厳密な識別子は取得できずnull。Mainの匿名候補品質採点の代用にはしない。
- 人工27例は1文書なので元/逆の入力が同一。翻訳対や独立した文書順序比較として数えない。理由が160文字に達した3件と不完全な末尾、空引用も原文のまま保存した。
- 入力140500/出力191492 Token、Task生成秒和3847.488460629秒、今回の費用不明0。772資源観測/取得エラー0、観測最大GPU7673/8151 MiB、最小Host Available4078300 KiB、Observer経過3865.091700035秒。
- 5秒の観測最大を連続Peak、Task秒和をGPU Kernel時間、今回の診断を長時間安定性の保証にはしない。旧T1の資源見積りは新温度の実測見積りへ読み替えない。

Raw135を正規保存後、AI確認を加えた136 Fileと監査/資源/形式の全202 Artifactを
`phase11_qwen35_q6_temperature_semantic_result_v1.json`へ保存し、Root/固定WTのByte一致を確認した。
元の形式40 Artifact/Core27と、待機中準備/部分Sampler検査12 Artifactも不変である。
Rawは`data/runs/semantic_diagnostics/phase11-qwen35-9b-q6-temperature-v20`、
監査資料は`data/runs/development_screening/phase11-q6-v20-semantic-audit-v1`。

## 次の回帰v9と予算

保存済みHelperを実行し、親136 Fileのコピー上で全前提を再検証した。
`phase11_known_trace_candidate_v9.yaml`/`phase11_known_trace_regression_v9.json`は
候補v20からStudy Version/Plan参照だけを変更し、元全15 QA/42文/30条件・84 Call、
全Source25/Expected/基準/曖昧/別保存の裸拒否8を保持する。全84 Messageと生成Task、Model/Runtime/Prompt/予算/Samplerも一致した。

正の準備12 Artifactを`phase11_qwen35_q6_temperature_known_preparation_validation_v1.json`、
登録検証8 Artifactと契約を`phase11_qwen35_q6_temperature_known_registration_validation_v1.json`へ保存した。
全761 Test（30.43秒）/全体Ruff/Helper Ruff成功。src/Core27は変更していない。

別の事前登録v18はv17の条件付き84だけを使う。全9B記録試行836（Q4 317/Q5 317/Q6 202）から
累積上限920・Retry0で、予算を追加しない。旧未知1と旧未使用42/42/81/42を埋めたり再配分したりしない。
新Native回帰はまだ未実施。Commit・通常Push後の新固定WTで、全84入力生成0/全層CUDAを確認する。
負例12条件/42 Callをすべて正確一致した場合だけ残18正例条件へ進み、全終了後に監査する。

Main各20 QA/全匿名品質・Expected封印と証明、予約Calibration、最終N/資源/条件/Validator/凍結は未了。
Gate 11未通過・Phase 12未実施・Goal継続中。モデル/Raw/環境はGit Pushでは転送されない。
