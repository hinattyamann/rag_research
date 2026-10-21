# Phase 11 最終JSON境界の形式失敗と別候補

2026年10月21日。使用済み15 QAの回帰v1はHealth Gate不通過であり、採用しない。
固定2ae5133の5/30条件目、Tom Bombadilの読解が最終回答を配列で開始した。
旧PATTERN `</think>\s*(\{)` は到達せず、宣言した制約が有効にならなかった。
21 Completion、入力84642/出力21107 Token、Task秒和342.057456秒。
最初の4 Critical条件は一致したが、残る25条件は未試行。全予定に対する精度はnullのまま。
出力はeos、推論1380/1536 Tokenで、出力上限による打切りとは区別する。
旧出力の配列除去・修復・再試行を行わず、全43 Artifactを結果Manifest
`phase11_known_trace_result_v1.json`へ保持した。固定Sourceの再開監査は37 File不変・追加Call/Server0。

## Runtimeの根拠と修正範囲

固定Runtime b11433、Source Commit `50569eb87df530daff11afda229ceb9ab8e6cae8`の一次資料を確認した。
[common.h](https://github.com/ggml-org/llama.cpp/blob/50569eb87df530daff11afda229ceb9ab8e6cae8/common/common.h)の
WORD=1/PATTERN=2、[sampling.cpp](https://github.com/ggml-org/llama.cpp/blob/50569eb87df530daff11afda229ceb9ab8e6cae8/common/sampling.cpp)の
推論中の制約抑制と終了列の再投入、[llama-grammar.cpp](https://github.com/ggml-org/llama.cpp/blob/50569eb87df530daff11afda229ceb9ab8e6cae8/src/llama-grammar.cpp)の
Trigger一致区間をGrammarへ再投入する実装から、JSONだけのGrammarへ終了Tagを投入すると不整合になる。
これは過去v13の失敗とも整合する。旧PATTERNはこの問題を避ける一方、配列等で始まる最終回答を制約できない。

新しい任意設定`sampling.final_json_grammar_mode: closing_tag_root_v2`は、
GBNFのRoot自体を`"</think>" ws <closed-object> ws`とし、WORDの終了Tag一致で制約を開始する。
終了Tagを正当に消費した直後から、配列・説明文・Fenceを許さない設計である。
Native応答が同じ全文Grammar/WORD/Lazy設定であることと、終了直後のObjectを照合する。
これらの設定表示だけで実際の制約を確認できたことにはせず、次節の敵対的な人工入力で検証する。

`generation/json_grammar.py`は本研究で使う閉じたSchemaの部分集合だけを独自変換する。
全Field必須/追加Field禁止Object、固定Tuple/上限付きArray、Boolean、String、Const/Enumを扱い、
未対応のSchemaは生成前に拒否する。Fieldは宣言順で固定する。引用/IDの候補は原資料から作り、正解Labelを入れない。
書換えの最大2400文字には、固定Runtimeの単一反復展開上限2000を避ける有限の右再帰を使う。
旧`brace_trigger_v1`は既定値のまま残し、旧Config/Runを上書きしない。
新Config v7はv6のModel/Runtime/Prompt/Expected/予算/Seed/採用基準を保ち、この形式制約とStudy Versionだけを変える。
Decoder制約の変更が出力へ影響しうるため、同じ意味診断を新Runで再実行する。

## 実走前に固定する検証

入口は`scripts/probe_final_json_boundary.py`。研究QAを使わない人工6 Completionを上限とする。
旧制約への配列指示1回は比較用で、失敗を必須条件にはしない。
新制約は配列指示、説明文/Fence指示、固定ID/引用Tuple、Unicode/Quote/改行/Backslash、
実際の書換えと同じString上限1200/600/2400の5条件を確認する。
厳密な5条件すべてでNative制約設定・終了Tag/推論予算・正常終了・最終Schemaを満たすことを要求する。
厳密条件の失敗は即停止・Retry0で、未試行も保存する。
構造専用の出力上限512/推論128を明示し、Model/Sampler/Context12288/CUDA全層は候補と同じにする。
Plan/全Source Hash・全要求/応答・Token/時間・Server終了を固定Commitの専用Worktreeへ保存する。
この形式検証は意味採用やGate 11の通過ではない。

通過後、v7の全128予定入力を生成0 Preflightし、既知Critical4全一致のときだけ人工54条件へ進む。
旧v6と同じ全58条件/最大128 Completion、各言語90%以上・明確な非支持の誤支持0・Task失敗0を維持する。
その結果も通過した場合だけ、旧Expectedを変えず既知15 QAの新Plan/Runへ進む。
変更したCoreで旧v6の前提照合をすり抜けず、新しい通過Reportを前提として固定する。
日英主Development・未使用Calibration・最終凍結はその後であり、Phase 12は開始しない。

## 人工検証v1の不通過とv8の事前条件

固定8a77dc3の人工検証は2/6 Callで停止。旧制約は配列[0]でTrigger未到達を再現した。
新v7はObject開始を制約したが、無制限の空白を繰り返して512 Tokenの上限に達した。
入力94/出力656 Token、残る4条件未試行。Raw/Plan/Report/Logの全6 Artifactを
`phase11_json_boundary_result_v1.json`で保持する。新制約の形式合格とはしない。

別候補v8は`closing_tag_root_v3`で、各位置の空白を最大2文字にする。v2の無制限空白とConfig v7は保持する。
同じ6人工入力/上限/厳密条件/停止規則を新Runで検証し、出力上限を延ばして失敗を隠さない。
また、固定Sourceの[server-schema.cpp](https://github.com/ggml-org/llama.cpp/blob/50569eb87df530daff11afda229ceb9ab8e6cae8/tools/server/server-schema.cpp)は、
保存WORDが一つのTokenに対応するとNative設定をTOKEN=0へ正規化する。
v3の監査は実Tokenizerの終了IDと保存Token一覧を独立照合した場合だけ、このNative表現を受け入れる。
違うID/保存漏れ/Tokenizerなし/Grammar差を拒否する。Native表示をWORD型へ書き換えない。
人工検証v1はこの照合へ進む前の出力打切りで不通過であり、事後に通過へ変更しない。
全510 Test/Ruff成功。実GPUのv8と、通過後の同じ128 Call意味診断はこれからである。

## 人工検証v2の通過と意味診断v8の開始

固定43ccf05の別Worktreeで同じ6 Callを完了した。旧制約は配列[0]で不通過を再現し、
新制約の厳密5条件はすべて正常終了/Schema一致・Native設定/推論予算監査に通過した。
入力278/出力967 Token、生成秒和13.423958秒。83 Source Hash/全Native応答・最終Object/費用を照合し、
原本10 File不変・監査追加Call/Server0、同一Byte複製と監査を含む11 Artifactを
`phase11_json_boundary_result_v2.json`へ保存した。これは形式検証であり、意味採用ではない。

次にv8の全128予定入力をCompletion0で確認し、最大3874 Token・中間4096/判定3072予約込み予算内、
CUDA全層Offloadで通過した。GPU7070/8151 MiBは一点観測。
初回は旧AI監査JSONの未配置を設定読込みで検出したため、Server/生成0の準備失敗を保存し、
原本Hashを確認して複製後、まだ開始されていなかったPreflightを実施した。

同じCommitの`phase11-json-boundary-v2` Worktreeから
`data/runs/semantic_diagnostics/phase11-8b-source-reading-v8`を実行開始した。
生成0 Receiptと人工検証Report Hashを先に保存した。最初の既知Critical4条件が全一致した場合だけ人工54条件へ進む。
最大128 Call/Retry0、同じExpected/意味基準・Model/Prompt/予算/Seedを維持し、全結果/採用は未確定。
Launch Manifestは`phase11_source_reading_launch_v8.json`。実走中のCode/Configを更新しない。

## v8の日英意味診断通過・監査と既知回帰v2

固定43ccf05の全58条件/128 Completionを完了し、Critical4/4・人工英語24/24/日本語28/30、
明確な非支持の誤支持0、Task失敗/Overflow0で事前診断基準を通過した。
入力162583/出力116590 Token、Task秒和1677.570092秒（27.96分）。
固定Source86 Hash/全58集計・128子Taskの元本文/ID/全分母/費用を照合し、
再開251 File不変・追加Call/Server0を確認した。原本253 Fileを同一Byteで正規配置し、
Preflight/準備失敗/意味監査を含む259 Artifactを`phase11_source_reading_result_v8.json`へ保存した。

同じCodex AIで全58読解/94文書行・70最終固定文判定を原資料と照合した。
既知Council元順序の委託/因果/移転3行と、Zidaneの別内容文書4種類×両順序8行、
計11行に文書内非対応/過大一般化がある。原文Quote/ID一致だけで意味を保証しない。
人工例の時刻/市長承認/限定/表対応の読解省略、複数主体/行為の曖昧な圧縮も残る。
最終2不一致は同じ日本語未知語源例の支持不足→矛盾。両LabelともFの非支持0で、Expectedを変えない。
1文書の人工例では元/逆が同一入力であり、独立した順序条件例を54件得た意味ではない。
human_reviewed=false・厳密Model ID未取得・同一開発履歴を明記し、未Flagの完全性を認証しない。

Council c6は事前に曖昧/Expected nullのまま残した文で、v8では両順序で支持となりF6/7、
v6では両順序で矛盾/F5/7だった。いずれも閾値0.7で採用になる。
形式制約の改訂も出力に影響しうる。曖昧単位を精度の分母へ後付けで入れず、F全7文を保持する。
誤帰属c4の検出と、回答の品質改善/修復判断の妥当性を混同しない。

次の既知回帰v2は同じ15 QA/42文・Expected v1/全基準/最大114 Callを保持し、
新v8通過Report Hashを前提とする。Source Core/Model/Runtime/Prompt/予算の事前照合に成功した。
`phase11_known_trace_candidate_v2.yaml`/`phase11_known_trace_regression_v2.json`を
固定Commitの別Worktreeで全114入力/生成0 Preflight後に実走する。主20問はまだ生成しない。
