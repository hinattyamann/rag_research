# Phase11 新基準v2・全Known回帰v10の停止結果

2026-10-23。**候補は不採用、Gate11未通過、Phase12未開始。**
新しい意味採用経路は実装・検証したが、実Main/予約Cal/最終凍結は未達である。
正本は`data/manifests/phase11_known_trace_result_v10.json`。
停止結果のFile Hashは同名`.sha256`へ保存し、`sha256sum -c data/manifests/phase11_known_trace_result_v10.sha256`で照合する。
これは負の結果のManifestであり、Gate11最終凍結Manifestではない。
この停止を実験成功やPhase11完了へ読み替えない。

## 実施した範囲

- `support-binary-v2`をKnown→Main→Cal→最終Validatorへ接続し、旧v1の拒否と旧失敗を保全した。
  支持Recall/非支持Specificity各0.90、異なる支持10文/非支持5文・各3 Group、不足時の不通過を新結果前に固定した。
- 全780 Test/Ruffと未達拒否を検証した`9bfe78d`を固定し、生成0・全84入力・最大3927 Token・全CUDAに通過した。
- Smoke初回は正常終了。2回目は私の追加したSmokeコードがGlobal c2を単独で渡して送信前に拒否された。
  元の成功・停止・消費122.924029壁秒を保存し、全Src91 File/推論条件不変の`903f4cf`で未送信分1回だけを継続した。
  修正後の全782 Test（30.34秒）/Ruffは成功。Smoke計2 Call/未知0・Schema/Sampler/全回帰と同一Payloadの照合に通過した。
- 同じ固定`903f4cf`の専用WTで、元15 QA/42文/30条件/84 Callを一度開始した。
  旧の意味70 Call/形式証拠は推論条件・Core不変を照合して再利用し、人工同一入力を再生成しなかった。

固定WT: `.tools/worktrees/phase11-binary-v10-recovery`。
Run: `data/runs/semantic_diagnostics/phase11-binary-v10-known`。
監査: `data/runs/development_screening/phase11-binary-v10-audit-v1`。
共有台帳: `data/runs/development_screening/phase11-review-budget-recovery-v1/ledger.json`。
いずれも正規保存済み。Native/監査Sessionは終了している。停止Runを再起動しない。

## Runtime停止と意味不適合

| 項目 | 実結果 |
|---|---|
| 条件 | 30予定、17正常・1エラー、12未試行 |
| Native Call | 84予定、56記録試行＝55応答取得＋1応答不明、28未試行 |
| 停止箇所 | Camp David逆順c5、入力3470 Token。Expectedは元から曖昧で変更しない |
| 実ログ | `cudaStreamSynchronize`でCUDA launch timeout、応答前切断 |
| Kernel | 2026-10-23 10:21:46 UTC（19:21:46 JST）、PID209069 llama-server、Watchdog/Xid8 |
| 全予定分母の意味指標 | Health不適合・正例対照未完了のためnull |
| 取得済み文の支持 | 34/34。全予定58支持判定に対するRecallではない |
| 非支持 | 予定16判定を全件取得、正しく非支持14/16＝87.5%、誤支持2件。基準0.90未達 |
| 二次指標 | C↔NS誤り3件。取得済み確定50判定で三分類45/50、二値48/50 |

誤支持はTom c5元順序（TV miniseriesをfilmへ一般化）とTar Heel c2逆順序（別の伝説と逸話を因果的に接続）。
Tom c5逆とTar Heel c1両順序のC↔NSは二次診断に残す。
暖鋒c2は両LabelがExpected Cと一致するが、理由は両方とも表の「通過中」の雨を「通過後」と誤読している。
Council c6/Camp David c1・c5の曖昧さと全Rawを保持し、応答不明c5を推測で埋めない。

取得済み9 Groupを再標本化した記述的Bootstrap（10000回、Seed42）のSpecificity 95%区間は
`[0.714286, 1.0]`（有効9999、クラス欠落1）。支持の区間は`[1.0, 1.0]`だが、観測群に条件付けた
Bootstrapの退化であり、母集団精度100%の保証ではない。全Runの区間・採用判定と混同しない。
完全な非支持層だけでも0.90未達で、CUDAだけを修復してもこの候補は採用できない。

Camp David逆順はc1〜c4の4応答が保存され、そのうち支持3件は正しい。最後のc5が不明のためRoot集約はerror/F=null。
元Reportは有効条件内の支持正解31件、Leaf監査はこれら3件も保全して34件とする。
元Reportを書換えず、部分応答・全予定・観測分母を明示した。失敗条件のF/判断は復元しない。
有効な8 QA順序対でTom/Tar HeelのF差はあるが採用/書換え判断は同じであり、実Mainの順序効果・品質結果へ数えない。

旧v9で不明だったZidaneは新Runで両順序とも正常終了したが、旧未知応答へ新Label/Tokenを移さない。
今回の停止は別入力・長い実行後に発生した。Root Causeや温度効果は未確定。
Xid8の分類と単独で原因を断定できないことは
[NVIDIA Xid資料](https://docs.nvidia.com/deploy/xid-errors/analyzing-xid-catalog.html)、
[解釈上の注意](https://docs.nvidia.com/deploy/xid-errors/introduction.html)による。
Driver/OS設定/Reset/再起動は変更していない。

## 監査・資源・保全

生成0の再読で元79 File不変・追加Call/Server0、96 Source、全56入力/原子費用を照合した。
提出56 Schema、取得55 Nativeの独立Draft-7/Sampler、元/逆28提出Schema組（取得応答の両側完備は27組）を検証した。
全55最終理由をAIが確認し、human_reviewed=false、history_isolated=false、厳密な採点Model識別子は取得不可と記録した。
これはKnown意味監査であり、Main/Calの独立回答品質Yを採点したことにはしない。
Raw81 File/全123 Artifactを正規保存し、固定WTとのByte一致とHashを保持した。
実Main準備の拒否・未達最終Freezeの拒否を確認し、出力・最終Manifestは作成していない。

| 費用・枠 | 記録 |
|---|---|
| Known入力/取得済み出力 | 195268 / 202627 Token。未知1件の総出力費用はnull、0ではない |
| Known Task秒和 | 4137.650775秒（不明応答までの測定時間を含む） |
| 新開発計 | Smoke2＋Known56＝58 Completion試行、Task4310.915004秒 |
| 保守的な共有壁時間 | 4381.357537秒。起動・生成0等を含み、4時間未満 |
| 資源観測 | 830点、取得エラー0、観測最大GPU7622/8151 MiB、最小Host Available3826032 KiB |
| 開発累積 | 851→909、未知2→3。Q4 317/Q5 317/Q6 275 |
| 残枠 | 新188の未使用130＝未試行Known28＋未割当102。自動再配分しない |
| 旧未使用 | 69・42/42/81/42を元台帳のまま保全し、新枠へ繰り越さない |

資源値は離散観測で、連続PeakやCUDA原因を証明しない。Native Runnerの終了Code0もHealth通過を意味しない。
188回/4時間の数値上限には到達していないが、事前のRuntime停止規則・意味不適合で打切った。
最終候補1個の枠内で別候補を追加せず、失敗を消す再実行を行わない。

## 未達と再開に必要な判断

未達は、完全なKnown採用、実Main日英各20 QA/各10以上の完全比較・全匿名品質/Expected封印、
予約Cal各20 QA、実主/Calの品質・費用、最終N/資源/条件/統計、最終凍結Manifest/HashとGate11。
既存の日本語Source/分割/Corpus/Indexや既知接続は保全し、作り直さない。Evaluation本文/回答/結果は開いていない。

再開の判断点は次の二つで、今回は実行しない。

1. **Runtime切分けを別事前登録で許可するか。** 同じ固定Sourceの`GGML_CUDA_GRAPHS=OFF`ビルドを隔離候補として
   比較する案はある（[固定SourceのCMake定義](https://raw.githubusercontent.com/ggml-org/llama.cpp/50569eb87df530daff11afda229ceb9ab8e6cae8/ggml/src/ggml-cuda/CMakeLists.txt)）。
   Graphが原因との証明ではなく、Binary/Hash/速度/数値が変わるため新条件・形式/意味再検証が必要。
   環境変数だけで無効化できるとは確認していない。Driver更新/再起動等は表示・OSと再現条件に影響し、別途具体案と承認が必要。
2. **意味候補を追加する予算・候補上限の改訂を認めるか、研究範囲を再設計するか。**
   Runtime復旧だけでは87.5%は直らない。0.90/Expected/閾値0.7を自動変更せず、未使用Main/Calを調整用へ開かない。

ユーザー指定の障害時一時停止条件に該当する。成果のCommit・通常Push・Remote一致確認後にGoalを一時停止する。
