# Phase 11 12k候補v18の全意味診断と旧全回帰v7

2026年10月23日10:00 JST。固定5c8b8b0の観測付きsession74326は全58条件/70 Callを終了し、
Critical4/4・英語人工24/24・日本語28/30・誤支持0で元の事前基準を満たした。
旧全回帰・Main/Calibrationの採用とは区別する。

## 意味判定と元の失敗

ja-qualification-3の元/逆は、Expected支持不足に対して矛盾となった。
由来が不明で一説がある本文について、限定なし内容主張を明示的な否定と取り違えている。
全58条件の判定/理由/引用/Fは元24k候補v17と同一で、Context変更による意味改善を主張しない。
両不一致・全元Expected/基準・以前の失敗/未知1を保持する。

Council c4とZidaneは両条件で矛盾。Council c6の曖昧Expected=nullは保持し、観測は両NS。
曖昧文を精度からだけ除き、Fへ残すためCouncilは矛盾を含んだまま両F5/7で閾値0.7以上になる。
閾値や新しい拒否規則は追加していない。人工27組は1文書で同一入力であり、独立した順序頑健性の証拠ではない。

入力140500/出力181440 Token、Task秒和3301.218209753104秒、費用不明0。
Task秒はGPU Kernel専用時間やEnd-to-end時間とは異なる。
全9B記録試行592（Q4 317/Q5 275、過去の未知1を保持）、v13の条件付き旧回帰84/累積上限676・Retry0を維持する。
旧未使用81/42は再割当てしない。

## 全Raw・Native JSON・資源の監査

終了後の監査79395は95 Source、全入力/順序/文ID/費用を照合した。
再開時は元133 File不変、追加Call/Server0。監査付きRaw135を正規Run
`data/runs/semantic_diagnostics/phase11-qwen35-9b-q5-context-v18`へByte一致保存した。
全70 Native最終JSONを直接Decodeして保存Rawと照合・独立Draft-7検証、Native出力Token一致/入力非切捨てを確認した。
全35組でSchema不変。最終判定/理由を全70件読み、元の同一Source/全文入力の契約を再確認した。
確定68判定は66一致、曖昧2は保持する。

理由が160文字の10件と、159文字でも不完全な末尾を保存した。
Council元c3の末尾No conflictは意味の通る句で、長さだけで切断と断定しない。
他の不完全な末尾や誤分類を修復していない。AI確認は同じCodex、human_reviewed=false、履歴分離なし、正確なModel ID不明。
Sourceは以前読解済みの固定Plan v4と全154 Messages一致契約に基づき、別採点者の独立確認とはしない。

資源観測663点/取得エラー0。観測最大GPU6926/8151 MiB、最小Host Available4344584 KiB、
観測Process全体の経過3318.4052627799974秒だった。件数/欠測/最大・最小/Config/Source/固定Commitを
別Helperで再計算し、元3 File不変を確認した。RSS和は共有Pageを重複計上し得る。
観測最大は連続Peakではなく、OS/表示/観測負荷を含む。旧の一点計測との因果比較や、将来の安定性保証には使わない。
今回は全70が正常終了したが、旧24kのCUDA停止/未知を埋めた扱いにはしない。

AI確認付きRaw136/監査Sidecar10/意味資源3/新形式等32/開始記録1の全182 Artifactを
`phase11_context12k_semantic_result_v1.json`へ固定し、WTとByte照合した。
開始記録のWT内実保存先launch.jsonとの対応も明示し、Rootと同じManifestパスが固定Commit内にあるとは仮定しない。

## 同じ旧15 QAの回帰v7

準備12627は親136 FileのByte一致コピー上で全前提を再検証し、元136 File不変・追加Call/Server0で成功した。
元全15 QA/42文/30条件・84 Call/Source25/Expected/基準/曖昧/別保存の裸拒否8は不変。
Config v7の差は候補v18からStudy VersionとDiagnosticsだけ。
正の準備検証は`phase11_context12k_known_preparation_validation_v1.json`。

事前登録v14は元v13の条件付き84だけを使う。Context12288・同じ資源観測を保ち、
記録済み592/累積上限676・Retry0、旧未知1/旧未使用81/42の保存を維持する。
全750 Test（29.14秒）/Ruff・監査HelperのRuffと、Core27/新形式32 Artifactの不変を確認した。
最初の負例6 QA/12 Critical条件・42 Callが全一致した場合だけ残る正例9 QA/18条件へ進む。

新固定WT/全84入力生成0/実旧回帰は未実施。全旧基準通過後だけ新Main Policy/実費へ進む。
Main/予約Cal/Evaluationの新規QAは使っていない。
主/Cal採用・最終N/資源/条件/凍結は未了、Gate 11未通過・Phase 12未実施、Goal継続中。
