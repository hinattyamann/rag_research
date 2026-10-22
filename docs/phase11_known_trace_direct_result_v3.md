# Phase 11 旧15 QA直接回帰v3の不通過と保存

2026年10月22日。固定8ea37e1、Qwen3.5-9B Q4_K_M、直接固定文照合、24k Context・推論4096/判定6144。
先に全通過したv13日英診断と同じModel/Runtime/Prompt/Sampler/Seedで、旧全15 QA/42固定文/30条件を計画した。
session93865は終了済みで、再起動しない。

## 事前Gateと実施状況

明確負例を含む6 QA/12 Critical条件を先行し、全一致後だけ残り9 QAへ進む規則を維持した。
42 Call・12条件は全て形式/実行上は成功したが、Critical完全一致8/12・誤支持4で不通過。
18条件/9 QAは未試行のまま保存し、正例補充や再試行をしない。全体の上限84 Callを延長していない。

| 項目 | 計画 | 実施・結果 |
|---|---:|---:|
| QA | 15 | 6 |
| 条件 | 30 | 12、残り18未試行 |
| 固定文のNative判定 | 最大84 | 42 |
| Critical完全一致 | 12/12必須 | 8/12 |
| 確定Labelの条件数 | 74 | 観測40、正確一致34 |
| 支持Expectedの条件数 | 58 | 観測24、正確一致24 |
| 明確負例の誤支持 | 0必須 | 4 |
| 曖昧条件 | 10 | 観測2、全F分母に保持 |

未試行があるため、Reportの全計画精度・支持精度はnullを保持する。
部分的な34/40・24/24を全74/58条件の採用精度に読み替えない。
追加Native費用は入力130198/出力156604 Token、Task秒和2584.749639秒（約43.08分）。
起動/検索/採点を含むEnd-to-end時間やGPU Kernel専用時間ではない。
9Bの実完了累積は144+42=186 Call。主/予約Calibration/Evaluationの新規推論は0。

## 意味上の不一致

- Tom c5元順序: ラジオ/ミニシリーズの記載から映画の例まで支持した。Expected支持不足、実際は支持。
  逆順は支持不足で一致。映画での言及そのものを全否定する根拠はなく、Expectedを矛盾へ変更しない。
- Warm front c2逆順: 表の列は通過前/通過中/通過後。持続する中程度の雨は通過中、通過後は次第に止む弱い霧雨。
  逆順は通過中のセルを通過後へ転記して支持した。元順序の矛盾判定は一致したが、理由は表を十分に解読せず
  他の「通過後に晴れる」記述も使っており、正解Labelだけで表の安定した理解を認定しない。
- Tar Heel c1両順序: 語源不明とfolkloreは無限定の起源の事実を支持せず、反対の事実も直接は示さない。
  Expected支持不足に対し、両方が矛盾となった。誤支持とは別の2不一致として保持する。
- Tar Heel c2両順序: 隊列を保った伝説と丘を保てず笑われた逸話は別々の記載。
  両方が原文にあることから、その間の主張された因果的な結び付きまで支持した。Expected支持不足に対し両方が支持。

| 既知QA | 元F/判断 | 逆F/判断 |
|---|---|---|
| Council | 6/7・採用 | 5/7・採用 |
| Zidane | 0・書換え | 0・書換え |
| Tom | 1・採用 | 0.8・採用 |
| Armistice | 1/3・書換え | 1/3・書換え |
| Warm front | 0.5・書換え | 1・採用 |
| Tar Heel | 2/3・書換え | 2/3・書換え |

閾値0.7は変更しない。Council c6の曖昧Expected=nullも全7文のF分母に残す。
Warm frontの判断反転は誤支持を伴う既知例で、妥当な測定の成功や一般的な順序効果と主張しない。
既知例の反復による方法選択を独立した精度確認に使わない。

## 監査と保存

固定WTの`/tmp/phase11_direct_audit.py`を位置引数Config/Runで実行した（audit session33134、終了済み）。
94 Source Hash、12集計と42子Taskの全原文/全草稿/固定文/局所c1/費用を照合した。
再開前後60 File不変、追加Call/Server0。監査2 Receiptを加えた原本62 Fileを同一Byteで正規保存した。
全42最終Label/理由/引用IDと、不一致の使用原文をCodex AIが確認し、追加AI記録1+準備/生成0の5を含む全68 ArtifactへHashを付けた。

正規Runは`data/runs/semantic_diagnostics/phase11-qwen35-9b-known-regression-v3`、
結果Manifestは`data/manifests/phase11_known_trace_result_v3.json`。
監査はhuman_reviewed=false、厳密AI Model ID不明、履歴共有である。
理由の字数途中切れや局所c1の表示も保持し、全理由の流暢さや独立人手精度の証明としない。
元の全Expected・Source25 Binding・裸拒否8 Trace、失敗/未試行を変更していない。

## 次候補の実行

[カテゴリー完全支持のv14候補](phase11_category_coverage_candidate.md)は固有名を含めない一般Prefixだけを追加する。
表・因果関係等も全旧回帰で再確認する必要があり、この一般規則で全不一致が直るとは仮定しない。
固定f92298bの専用WTへ181 File Binding/内部相対Symlink10を配置し、全Hashを照合した。
Mutable Raw/JSONはコピーし、Hardlink55は不変のModel/Runtimeに限る。GPU用uv環境58 PackageをOffline再現した。
初回のSymlink検査を中間リンク作成前に行った準備失敗も保全し、全リンク作成後の解決先検査へ修正した。

全70実入力/生成0のPreflightに通過し、最大3478 Token・Context24576/全層CUDAを確認した。
VRAM6513/8151 MiBは一点観測で、生成中のPeakを保証しない。失敗/準備Script/成功とPreflightの全7 Artifactを保存した。
Native Core26+Probe1と再利用する形式15 Artifactの不変も確認した。
同じ固定WTで全58条件/最大70 Callの意味診断を開始した（session54441）。
形式/意味・既知回帰の全基準、全対象/Expected/全分母、Retry0を維持する。
実完了186を起点に新規最大154、全後続を実施した場合の累積最大340。
旧Preregistration v6の保守的382は、親の未確定な登録上限を含む当時の記録として保持する。

現候補の主/Cal採用は未確定。実主/Cal全実走・採点/証明、最終N/条件・凍結は未了。
Gate 11未通過、Phase 12未実施。
