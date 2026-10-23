# Phase 11 12k Context候補v18の実走

2026年10月23日08:58 JST時点。候補/資源観測CLI/全事前条件を
`5c8b8b03f9f57be281dec671da885390480e9867`へCommit・通常Pushし、リモート一致を確認した。
[候補の実走前資料](phase11_context12k_candidate.md)は当時のSnapshotとして保持する。

## 固定準備と全入力生成0

WTは`.tools/worktrees/phase11-qwen35-9b-q5-v18`。
準備20469は865 File Binding/56不変Hardlink/内部相対Symlink10を照合した。
小さいJSON/Rawはコピーし、相対リンクは全作成後に内部解決を確認した。
GPU環境58 PackageをOfflineで再現し、準備Helperの構文/Ruffにも成功した。

観測付きPreflight52836は全70実入力/Completion0・Context12288/全層CUDAで成功した。
最大入力3793 Tokenと全70入力それぞれのToken数は以前の24kと同じで、全文/出力6144を保持する。
RuntimeのVRAM一点観測は6872/8151 MiB。5秒の観測6点は短い割当区間を捕捉せず、
観測最大808 MiB/エラー0だった。両方の値を保持し、観測最大をPeakやRuntime観測の代替にしない。
準備/Preflight6 Artifact+観測3 Artifactを正規保存・WTとByte照合し、
`phase11_context12k_preflight_v1.json`へ保存した。

## 新条件の形式検証と終了後監査

観測付きsession5446は形式10 Callを終了し、全9 Strict条件に通過した。
旧Brace Triggerの比較用Array逃れ1件は元のまま残し、成功へ変換しない。
入力630/出力1802 Token・生成合計35.35412677403656秒、費用不明0、全層CUDA。
資源12点/観測エラー0、観測最大GPU6882 MiB・最小Host Available4997444 KiBを保存した。

終了後だけNative最終JSONの独立Decode/Draft-7、実Native Grammar/Prefill/Trigger Tokenの
保存Live Witnessと実Token位置を照合した。新しいTokenizer/固定Token IDを監査時に作っていない。
92 Source Hash一致、同じ出力への再実行はServer/Completion前に拒否し、元14 File不変・追加0を確認した。
Raw16/監査Sidecar4/形式資源3/Preflight等9の全32 Artifactを正規保存・WTとByte照合し、
`phase11_context12k_format_result_v1.json`へ固定した。
形式だけでは意味採用・長時間安定性・Gate 11の証拠にしない。

## 現在の全意味診断

同じ固定WTで全58条件/最大70 Callを観測付きsession74326として開始した。
Rawは`data/runs/semantic_diagnostics/phase11-qwen35-9b-q5-context-v18`、
資源は`data/runs/resource_observation/phase11-qwen35-9b-q5-v18-semantic-v1`。
開始記録は`phase11_context12k_launch_v1.json`。最初のCritical4条件が全一致した場合だけ人工54条件へ進む。
記録済み全9B試行522/累積上限676・Retry0、全意味70+通過時の旧全回帰84を保持する。
旧応答不明1と旧未使用81/42は埋めず、元全対象/Expected/基準/曖昧/裸拒否8も変更しない。

同じHandleを継続観測し、終了前に再起動しない。終了後だけ固定WTのuvで、保存済み汎用Direct監査
`data/runs/development_screening/phase11-q5-known-v5-audit-v1/audit.py`へConfig v18/新Runを位置引数で渡す。
全Raw/入力/順序/文ID/Source/実費/失敗/未試行・追加0再開と独立Native Schema/AI確認を保存する。
資源は観測最大/最小・欠測・観測/OS負荷の限界を分けて報告し、Nativeの元採否基準を変えない。

全意味基準通過・全Raw監査後だけ同じ旧15 QA/42文/30条件・84 Callへ正の前提を結ぶ。
旧全回帰も全元基準を満たした後だけ新Main Policy/実費へ進む。
Main/予約Cal/Evaluationの新規QAは使っていない。
主/Cal採用・最終N/資源/条件/凍結は未了、Gate 11未通過・Phase 12未実施、Goal継続中。

開始記録のWT内実保存先はモデル準備Directoryの`launch.json`、
Preflight/形式Manifestのコピーは`preflight_binding.json`/`format_result_binding.json`。
Rootと同じdata/manifestsパスが過去の固定Commit内にあるとは仮定しない。

## 終了前Guardと資源観測の独立再計算

2026年10月23日09:14 JST。全意味の終了を待つ間に、旧全回帰v7用の別準備Helperを保存した。
全旧15 QA/42文/Source25/Expected/基準/曖昧/裸拒否8と最大84 Callは原版一致。
実際に稼働中の固定WTをPRIORへ向けた確認だけを行い、終了・監査不足を拒否した。
正の処理の参照先は正規Runのまま。拒否はConfig読込み/Lock/再開前で、
返却済みの2 LeafはByte不変、他の稼働中Fileは固定・Inventory化していない。
Config v7/Plan v7/正のReceiptは未作成、追加Model Call/Server0。構文/Ruffが成功した。
証拠は`phase11_context12k_known_preparation_pending_v1.json`の7 Artifact。

別の読取り専用Helperで、終了済みPreflight6点/形式12点の資源記録を独立再計算した。
件数/欠測/観測最大・最小、Config/観測Source/固定Commit、元3 File不変を照合した。
観測時刻の最大間隔・負の時刻差、Native家族のRSS和も記録し、RSS和は共有Pageを重複計上し得ると明示する。
短区間の未観測Peakを補完せず、Nativeの意味/Health採用とは別に扱う。
証拠は`phase11_context12k_resource_audit_v1.json`の4 Artifact、追加Model Call/Server0。
実行中の意味資源記録には終了後だけ同じHelperを使う。
