# Phase 11 12kの旧15 QA直接回帰v7は不採用

2026年10月23日10:55 JST終了。固定5f4a6b6/session64437は12 Critical条件/42 Callを完了し、
Critical完全一致9/12・誤支持3で不通過となった。残る正例9 QA/18条件は事前規則に従い未試行。
人工意味診断通過・形式成功・Runtime正常を、全旧回帰やMainの採用へ読み替えない。

## 判定・理由と全分母

| 条件/文 | 元Expected | 観測 | 根拠との不一致 |
|---|---|---|---|
| Tom元 c5 | 支持不足 | 支持 | Radio/TV miniseriesをfilmまで一般化し、「すべての映画を否定していない」を支持に使った |
| Tar Heel元 c1 | 支持不足 | 矛盾 | 由来不明/仮説という留保を、由来自体の否定とした |
| Tar Heel逆 c1 | 支持不足 | 矛盾 | 同上 |
| Tar Heel元 c2 | 支持不足 | 支持 | 別々の伝承を、句が別の逸話から生じたという関係へつないだ |
| Tar Heel逆 c2 | 支持不足 | 支持 | 同上 |

観測した確定40判定は35一致、支持24判定は24一致。観測率は35/40・24/24だが、
全予定74確定/支持58判定の精度はnullとし、未試行を成功に数えない。
全旧15 QA/42固定文・30条件/84 Call、Source25、全Expected/基準、曖昧5文、別保存の裸拒否8は原版不変。
今回の曖昧2判定はCouncil c6の両順序で、観測NSをFへ残し精度だけから除外する。

暖鋒c2は両LabelがCでも、元の理由が表の持続雨を「通過後」へ誤帰属した。
表の列は通過中の持続雨、通過後の弱い霧雨/漸減である。正しい晴天化のSourceも引用しているが、
理由の誤読を補修せず保存した。逆順の理由は通過後の霧雨/減衰へ対応していた。
Tom逆c5はNS、Council c4は両C、Zidaneは両C、Armisticeは署名5時と発効11時を両順序で区別した。
不完全な理由の末尾もそのまま残す。160文字ちょうどは12件で、それ以外の断片もある。

Councilは両F5/7、Tomは元F1/逆F0.8で、いずれも閾値0.7以上の採用相当になる。
Councilの矛盾c4を含む採用相当と、Tomの順序間差も保持する。
Zidaneは両F0、Armisticeは両F1/3、暖鋒は両F1/2、Tar Heelは両F2/3で書換え要求相当。
この診断で実書換え・匿名回答品質の新結果は生成していない。

## 終了後監査と資源

入力148888/出力153689 Token、Task秒和2827.8889923789247秒、費用不明0。
全9Bの記録試行は592→634（Q4 317/Q5 317）。旧応答不明1を含む記録試行数であり、
634すべての出力が既知という意味ではない。今回84 Call枠の未使用42、旧v6の81/旧v5の42は埋めず、再配分しない。

終了後の監査63748は95 Source・全実入力/順序/文ID/子Task/実費を照合した。
再開で元59 File不変・追加Call/Server0。監査付きRaw61を正規Run
`data/runs/semantic_diagnostics/phase11-qwen35-9b-q5-context-known-regression-v7`へByte一致で保存した。
独立に全42 Native最終JSONをdecodeしてDraft-7検証し、21組のSchema不変も確認した。
全42最終判定/理由と6 QAの全Source本文を実際に確認し、AI記録を加えたRaw62を保存した。
AI確認は同じ開発履歴のCodex、human_reviewed=false・正確なModel ID不明・履歴分離/盲検なし。
これは新しいGround Truthや独立匿名品質の封印ではない。

資源は569点/取得エラー0、観測最大GPU6898/8151 MiB、最小Host Available4323548 KiB、
Observer経過2846.463536962983秒。終了済み3ファイルのHashを保ち、値を再計算した。
5秒観測の最大/最小であり連続Peak・GPU Kernel時間・長時間安定性や因果の証明ではない。
Native終了Code0/Runtime失敗0と、意味Gate不通過を分けて保存する。

全93 Artifactを`phase11_known_trace_result_v7.json`へ結び、固定WTとByte照合した。
開始記録だけはWT内のmodelscreening/launch.jsonへの実保存先Aliasを使う。
元Native Core27/新12k形式32 Artifactも不変。Main準備CLIへ今回の正規不通過Reportを渡し、
QA/Policy読込み前の拒否・出力なしも確認した。主/Calへは進めない。
生データ/モデル/環境はignoredで、Git Pushだけでは転送されない。

## 次に取り組むべき内容

1. 今回と旧全失敗・未知・未試行・Expected/採用基準を保持し、再生成で置き換えない。
2. [同じ固定RevisionのQ6資源調査](phase11_q6_resource_feasibility_v1.md)を踏まえ、
   量子化だけを分ける別候補を検討する。取得Size/Hash・事前登録・生成0全層CUDAを先に確認し、
   新形式/全意味診断/条件付き旧全回帰で検証する。精度向上や現行GPUへの配置成功は未確認。
3. 全旧基準通過後だけ新Main Policy/日英各20 QA、全匿名採点封印/証明、予約Cal、最終N/資源/条件/凍結へ進む。
   Gate 11未通過、Phase 12未実施、Goal継続中。
