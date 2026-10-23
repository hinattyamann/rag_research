# Phase 11 Q6の低temperature候補v20

2026年10月23日。候補設定は`configs/phase11_semantic_candidate_v20.yaml`。
Q6 v19からStudy Versionと`auxiliary_runtime.temperature`の1.0→0.2だけを変更する。
補助生成のJudgeと書換えがともに対象であり、初回3B生成のtemperature=0は維持する。

## 選択理由と研究への影響

Q6旧回帰v8で、元順のradio/miniseriesをfilmまで広げる誤支持と、逆順で一つの映画版における
非描写を映画版一般の言及への矛盾とする誤判定を確認した。Expected NSはそのまま保持する。
既存の一般Promptにも媒体の非同一性や部分支持の扱いは書かれており、量子化変更だけで解消したとはいえない。
別候補では補助生成の確率的選択を弱めた条件で、同じ全文入力と意味基準を再検証する。
改善の保証や、この誤りがtemperatureだけで生じたという因果主張ではない。

Auxiliaryの既存検査はtemperatureを(0,2]に制限するので、その中の0.2を使う。
0.2も確率的な条件であり、同一順序のばらつきと根拠順序の感度は変わり得る。
日英とも同じ候補を使用し、結果は採用した設定に限定する。反転率や有意差の大きさで採用を決めない。
新しい書換え条件の品質は、採用後のMain/Calで匿名品質Labelを封印してから確認する。

## 変更しない条件と準備検証

Model Q6_K/固定Revision、Runtime、全層CUDA/Context12288、日英Prompt v11、
各Task出力/推論予算、閾値0.7、全対象/全文/固定文/根拠ID・本文・Title、Seed42、
その他Sampler/Grammar/Prefill・全Expected/基準/曖昧/別保存の裸拒否8は維持する。
同一順序の結果をキャッシュせず、文切捨て/補充/再試行/Labelの事後修復は行わない。

実Loaderと全Task構築に成功し、日英診断70+旧全回帰84の全154 Message不変、
Core27と実行中の固定WTを含むNative95 Source不変を照合した。
親意味195/新Q6形式37/資源見積り7/Main未完了拒否7/部分誤支持1 Artifactも再照合した。
準備HelperのRuff、全761 Test（29.32秒）とProject Ruffに成功した。
追加Model Call/Server・新規QA本文読込み0である。

## 実走の前提と採否

[旧回帰v8の全不採用結果](phase11_known_trace_direct_result_v8.md)は終了・全監査/正規保存済みである。
全144 Artifact/Raw62、Critical8/12・誤支持3・残18条件未試行と実費を保持する。
新しい実行上限を保存し、Commit固定WTで全入力生成0・全層CUDAと新形式最大10 Callを確認する。
Samplerが異なるのでv19の形式実費/成功を新候補のNative実績として再使用しない。
その後、元と同じ日英意味70 Call、全基準通過後だけ旧全15 QA/84 Callを実行する。
最大新規164 Call・Retry0を別登録し、以前の未知/未使用Callを埋めたり再配分したりしない。
意味/旧全回帰の元基準を満たさない場合は、失敗・未知・未試行と全分母を保持する。

現在は候補の準備までで、実GPU生成0/新形式/意味/旧全回帰の採用は未了。
Main/予約Cal/最終N/資源/条件/凍結は未了、Gate 11未通過・Phase 12未実施。
