# Phase 11 temperature0.2候補v20の事前登録

2026年10月23日。[Q6旧回帰v8の全不採用結果](phase11_known_trace_direct_result_v8.md)と
[候補v20の準備](phase11_qwen35_q6_low_temperature_candidate.md)はa2233ddへCommit・通常Pushし、
GitHub mainとの一致を確認した。新条件の結果を見る前に実行上限/順序/停止規則を保存する。

## 条件と上限

事前登録は`data/manifests/phase11_qwen35_9b_preregistration_v17.json`。
変更はStudy Versionと補助temperature1.0→0.2だけで、Judge/書換えの双方が対象となる。
Model/Runtime/Context12288・全層CUDA・日英Prompt/予算/Seed/その他Sampler、
元全対象/全文/固定文/根拠とExpected/基準/曖昧/裸拒否8は維持する。

| 枠 | 最大新規Call | 進める条件 |
|---|---:|---|
| 新Native形式 | 10 | 全入力の生成0確認後。全9 Strictに通過する |
| 日英意味診断 | 70 | 新形式通過後。元29例/35文/58条件・元の意味Gateを使用する |
| 同じ旧全15 QA回帰 | 84 | 全意味通過・全終了後監査後。元42文/30条件を維持する |
| 合計 | 164 | 再試行0。失敗/未知/未試行を保持する |

開始前全9B記録試行756（Q4 317/Q5 317/Q6 122）から累積最大920とする。
旧Q5の応答不明1は保持し、全756出力が既知という意味にはしない。
今回Q6旧回帰の未使用42、旧Q5回帰v7の42/v6の81/v5の42は埋めず、再配分しない。
新164は別条件の明示枠で、以前の未実施生成を完了扱いにするものではない。

## 実行と採否

1. この登録をCommit・通常Pushし、次の固定Commitで`.tools/worktrees/phase11-qwen35-9b-q6-v20`を作る。
2. Model/RuntimeをストリームHash検証し、可変JSON/Rawはコピー、不変のModel/RuntimeだけHardlinkする。
   相対リンクのWT内解決を確認し、GPU環境をLockどおりOffline再現する。
3. 全70実入力を生成0・全層CUDAで確認し、同じWTで新形式、意味診断を資源観測付きで実行する。
   temperature1.0の形式成功や実費を、新温度のNative実績へ流用しない。
4. 全意味の元基準通過・全監査後だけ、同じ旧全15 QA/84 Callへ新前提を結ぶ。
   負例12 Critical条件/42 Callが全一致した場合だけ残る正例18条件へ進む。
5. 各終了後に元Raw不変・追加0再開/入力/順序/文ID/Source/実費/未知/失敗/未試行、
   独立Native JSON/Schema・全理由/Sourceと資源を監査・正規保存し、WTとByte照合する。

閾値/意味採用基準/Expectedを緩和せず、反転率や有意差の大きさを採用条件にしない。
温度を自動探索したり、結果を見て同じ枠を再生成したりしない。
旧T1の資源見積りは過去の計画資料で、新温度の速度/安定性/最終Nの確定値にはしない。
全旧回帰採用・全監査後だけ新Main Policy/実Mainへ進み、予約Calibrationを先行させない。

## 確認済みと残作業

候補準備は全761 Test（29.32秒）/Project・Helper Ruffに成功。
登録時に全入力参照9、親144/準備9 Artifact・実95 Source/Core27と予算算術を再検証した。
追加Model Call/Server・新規QA本文読込み0、実新形式/意味/旧全回帰は未実施である。
Main/予約Cal/最終N/資源/条件/凍結は未了。Gate 11未通過・Phase 12未実施、Goal継続中。
