# Phase 11 温度0.2既知15 QA回帰v9のCUDA停止と全監査

2026年10月23日16:55 JST時点。固定`9727409eee7a3f8c1ca76f879234f32de0462bb9`の
session72566は16:43 JSTに3条件/15記録試行で終了した。
3条件目のZidane元順序でCUDA launch timeoutにより応答が失われ、全既知回帰は不採用である。
Runnerの終了Code0は、実験Healthの通過を意味しない。

## 取得できた結果と取得できなかった応答

会議例の元/逆2条件・14最終判定は取得済みで、確定12/12、支持10/10、観測誤支持0。
c4は両C、曖昧c6は両NSで、曖昧をFから除かず両F5/7を保持した。
全14理由と既読の同一Byteの会議根拠10 Passageを確認し、引用・不完全な末尾を修正していない。
同じ開発履歴の非匿名Codex AI確認であり、human_reviewed=false/履歴隔離なし/厳密Model識別子null。
Mainの匿名候補品質採点を行った意味ではない。

15回目は`known-gpu-31e646aa9601-original.claims/c1.json`。
要求温度0.2・入力3793 Token・クライアント経過27.369667440秒を保存したが、
`raw_output`/`runtime_response`/`raw_cited_verdicts`はなく、出力Token数とLabelはnullである。
実Server Logは`CUDA error: the launch timed out and was terminated`を示し、接続が応答前に切れた。
Logには途中の生成進捗があるが、最終応答・最終費用を復元せず、根本原因も特定済みとはしない。
同じ入力に対する以前の成功結果を、この失敗Runへコピーしない。

| 予定/観測 | 状態 |
|---|---|
| Critical | 全12予定、3条件実施/2正確一致、1実行エラー |
| 全条件 | 30予定、3実施/27未試行 |
| 全確定/支持Label | 74/58予定、全体精度null |
| 曖昧 | 全10予定、今回観測2/Fに保持 |
| 記録試行 | 15、うち応答取得14/不明1 |
| 今回の未使用枠 | 69、補充・再試行・再配分なし |

記録済み入力54841/既知の出力44560 Token、Task経過秒和938.478628298秒。
入力には失敗要求のクライアント計数3793 Tokenが含まれる。出力44560は取得14応答の合計であり、
費用不明1を含む全実生成量ではない。Aggregateの欠損出力の加算値0をNative費用0と解釈しない。
全Source25/Expected/基準/曖昧/別保存の裸拒否8、元15 QA/42文を維持した。

## 終了後の監査と保存

監査23121は95 Source/元23 File不変・追加Call/Server0で、全15要求の全文入力/順序/固定文/費用を照合した。
独立検査で全15提出Schemaを確認し、取得14のNative最終JSON/Draft-7・実温度0.2/Seed42/主要Samplerを検証した。
対応する7文組でSchema不変を確認し、Zidaneの片側1組は未成立として残した。
全15 Message/Schema/要求設定は通過済み親診断の対応入力と一致した。

193資源観測/取得エラー0、観測最大GPU7659/8151 MiB、最小Host Available4413128 KiB、
Observer経過958.900337586秒。元3 File不変を確認した。
5秒の観測最大は連続Peakではなく、エラーなしの資源取得もCUDA処理の成功や根本原因の説明ではない。
実Main準備CLIは、通過30条件/84 Callがないとして選定/QA出力前に拒否し、新出力0・元25 File不変を確認した。

監査後Raw25を正規保存し、AI確認を加え26 File、全110 Artifactを
`phase11_known_trace_result_v9.json`へ固定した。全Root/固定WT Byte一致を確認した。
親全意味202 Artifact/新温度形式40/Core27と、[温度0.2の暫定時間見積り](phase11_qwen35_q6_temperature_resource_estimate_v1.md)7 Artifactは不変。
見積りは16:38 JST時点の完了診断だけによる資料であり、この停止Runや長時間安定性の証明に使わない。

全9B記録試行は851（Q4 317/Q5 317/Q6 217）。旧未知1と今回1の計2、今回未使用69と
旧未使用42/42/81/42を保持し、累積上限920・Retry0を緩和しない。
src/実験条件/全Expected/基準は変更していない。実装は全761 Test（30.43秒）/Ruff成功時と同じで、
今回の確認は実失敗・全Raw/Source/費用/追加0再開・独立Schema/Sampler/理由/資源・Main拒否とHelper Ruffである。

## 現在地と次の作業

72566/監査23121は終了済みで、同じRunを再起動しない。GPU/Driver/Kernelの読取り情報と過去停止Logを調べ、
根本原因が不明なまま温度や量子化の効果と断定しない。必要なRuntime変更や再検証は、理由・影響・別Version/上限を保存してから行う。
現在は新候補/新Native実走を登録していない。旧未使用枠の再使用や失敗の除外は行わない。

Main各20 QA/全品質・Expected封印と証明、予約Cal、最終N/資源/条件/Validator/凍結は未了。
Gate 11未通過・Phase 12未実施・Goal継続中。
