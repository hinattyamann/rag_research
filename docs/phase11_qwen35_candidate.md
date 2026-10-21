# Phase 11 Qwen3.5-9Bの候補v9〜v11と保存した失敗

2026年10月21日。8B v8の既知15 QA回帰v2は12 Critical条件中8一致・誤支持6で不通過。
暖鋒の通過中/後の表対応、語源の不確実性、別々の逸話をつなぐ関係の誤支持が残った。
全失敗/未試行を保持し、Expectedや採用基準を緩和せず、既に資源調査した別Modelを検証する。
主Development20問/未使用Calibration/Evaluationにはまだ進まない。

## Artifactと変更理由

元Modelは[Qwen3.5-9B公式Card](https://huggingface.co/Qwen/Qwen3.5-9B)、
実際の固定Artifactは[UnslothのGGUF変換版](https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/tree/3885219b6810b007914f3a7950a8d1b469d598a5)。
発行元と変換配布元を分け、変換時の元重みRevisionの独立検証は未達と記録する。
Apache-2.0、Q4_K_M、5680522464 Byte、SHA256
`03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8`をAPIで再確認し、
取得後の全Byte Hashも一致した。取得の記録は`phase11-qwen35-9b-v2/acquisition.json`。
取得直後は生成/Runtime資源検証が未実施だった。固定4b94794の検証結果は下記へ追記する。

読み手の草稿なし読解→固定文ごとの判定という方法と全原文/固定文/Expectedを保持する。
以前の代替調査にはJointの元PromptからModelだけを試す案もあったが、
今回はv8の既知/人工通過から方法を保ち、Modelと明示した資源/Samplerの別候補を先に評価する。
モデルだけの因果比較や、公開Benchmarkを本研究の支持精度の証拠にするものではない。

| 条件 | v9の事前値・理由 |
|---|---|
| Model/Runtime | Unsloth固定9B Q4_K_M、既存固定b11433/CUDA0・全層Offload、Jinja有効。実起動で互換を確認する |
| 入力Context | 16384。全原文と長い読解/判定予約を保つ。通常AttentionのFP16 KV概算512 MiB以外の状態/Buffer/画面は実測する |
| 出力/推論 | 読解6144、判定/書換え4096、推論2048。v8から増やす別条件で、同じ予算のModelだけ比較とはしない |
| Sampler | 温度1.0、top_p0.95/top_k20/min_p0、presence1.5、repeat1.0、Seed42。一般Thinking用公式数値を参考にし、Nativeのrepeat_last_n64を記録する |
| Prompt | v7はv6から非対応の`/think`行だけを除く。役割/全入力/Schema/判定基準は保持する |
| 採用・停止 | 旧Critical全一致、人工各言語90%以上/明確な非支持誤支持0、Task失敗0、Retry0。旧15 QAの全基準も変更しない |

公式CardはThinking既定・`/think`切替非対応を記載する。長文脈/大きな出力の推奨は
本実機の16k/上記出力枠より大きく、本候補をModelの最大能力の測定とはしない。
主結果の比較は両言語とも同じ採用後条件で行い、旧8Bや旧Englishの結果と同一条件として混ぜない。

## 実行前の順序と上限

1. 固定Commitの専用WorktreeへModel/Runtime/元資料を配置し、Completion0で起動・全層CUDA/VRAM/全128入力予算を確認する。
2. 同じ人工6 Callの形式検証を別Runで行い、終了Tag/推論予算/Schema/Native設定の厳密5条件を確認する。
3. 通過後、同じ日英意味診断58条件/最大128 Callを実行する。既知Critical4条件全一致時だけ人工54条件へ進む。
4. 全基準通過後に新Reportを前提に旧15 QAの回帰を別Plan/Runへ固定し、最大114 Callを行う。

最大248 Call、同じ停止/再開/失敗保存規則を守る。主20問は採用済み回帰を確認するGuardを通してから実行する。
v8を参照した主実行Policy v1は履歴として残し、新Model採用時には候補条件だけを結び直す別Policyを主結果前に保存する。
対象20問・閾値0.7・全分母・意味採用/封印/欠測/統計は結果に合わせて変更しない。
関連ファイルは`phase11_semantic_candidate_v9.yaml`、`phase11_semantic_prompts_{en,ja}_v7.yaml`、
`phase11_qwen35_9b_preregistration_v1.json`。重み取得で意味採用やGate 11通過にしない。

## v9の資源通過と人工形式検証の不通過

固定4b94794の専用Worktreeで全128入力のCompletion0 Preflightに通過した。
最大3795 Token、読解/判定予約込みで入力超過0、CUDA全層Offload。
VRAM6266/8151 MiBは一点観測であり、生成時のPeakではない。

同じ人工形式検証は2/6 Callで停止した。旧/厳密配列指示とも512 Tokenすべてが
推論となり、終了Tagを生成せずstop_type=limitに達した。入力98/出力1024 Token、
生成秒和16.256868秒、残4条件未試行。厳密制約の通過とせず、意味診断/既知回帰は0 Call。
原本6 File/87 Source Hash不変、監査で追加Call/Server0を確認して同一Byte保存した。
Preflight/一次資料/監査を`phase11_qwen35_9b_format_result_v1.json`へ結ぶ。

実入力の末尾は`<|im_start|>assistant\n<think>\n`で、開始Tagが既に入力にある。
一方、直接`/completion`要求はNativeの`generation_prompt`を渡していなかった。
固定Runtimeの[common.h](https://github.com/ggml-org/llama.cpp/blob/50569eb87df530daff11afda229ceb9ab8e6cae8/common/common.h)と
[sampling.cpp](https://github.com/ggml-org/llama.cpp/blob/50569eb87df530daff11afda229ceb9ab8e6cae8/common/sampling.cpp)は、
この情報から推論Budgetの初期状態を進める。
[Schema](https://github.com/ggml-org/llama.cpp/blob/50569eb87df530daff11afda229ceb9ab8e6cae8/tools/server/server-schema.cpp)も
同じ値をSamplerへ渡す。これは不通過の原因仮説で、修正版の実生成で確認する。
一次資料4 Fileを固定Commit/Hash付きで保存した。旧8Bの結果は元Worktreeのまま保持する。

## v10の事前条件と実装

`phase11_semantic_candidate_v10.yaml`はv9からStudy Versionと
`sampling.reasoning_prefill_mode: chatml_think_suffix_v1`だけを変える。
Model/Runtime/Prompt/全原文/Expected/予算/Sampler/Seed/Schema/採用基準を保持する。
全入力Tokenを変更せず、Nativeへ既存の`<think>\n`を申告する別候補である。

申告前に実際の入力TokenをDetokenizeし、ChatML assistantの正確な末尾と、
別途Tokenizeした開始Tag/改行の末尾Token列が両方一致することを要求する。
不一致はCompletion前に停止する。Native応答の`generation_prompt`一致、生成内の
開始Tag再開なし/終了Tag一つ、実推論Token上限も監査する。
旧Configの既定値はnoneで、Baseline/旧Auxiliaryに追加要求やPrefillを有効にしない。

全555 Test（ホスト8.33秒）/Ruff成功。日英入力Token不変、末尾/Token不一致の
Completion0停止、Native申告欠落/変造・再開始/未終了/上限無視の拒否、旧要求を検証した。
v10の実GPU確認はこの記録時点で未実施。事前Manifestは`phase11_qwen35_9b_preregistration_v2.json`。
新しい固定Worktreeで生成0 Preflight→同じ人工6 Call/出力512・推論128→
同じ意味58条件/128 Call→通過時だけ旧15 QA/114 Callの順に検証する。
新候補最大248 Call、過去v9の2 Callと合計最大250。自動Retry0、失敗時停止を維持する。
失敗したv9を再開/合格へ書換えず、主20問/未使用Calibration/Evaluationへ先に進まない。

## v10の人工形式通過と意味診断開始

固定645f193の専用Worktreeで全128入力/Completion0 Preflightに通過し、
最大3795 Token・CUDA全層Offload、VRAM6279/8151 MiBの一点観測を確認した。
配置Helperが内部共有Libraryの相対Symlinkで止まった準備失敗はServer/生成0で保存した。
内部に解決されるSymlinkを保ち、既知入力3 JSONをHash照合して配置後、Preflightを実施した。

同じ人工6 Callは旧配列回避を再現し、厳密5条件すべてで正常終了/Schema/Native設定・
Prefill申告/実推論上限を満たした。出力512/推論128の上限は変更していない。
入力290/出力958 Token・生成秒和16.712355秒。各Callの終了Tag前は137 Tokenで、
Runtimeが付ける停止指示分を含む監査に通過した。
原本10 File/87 Source Hash不変・監査追加Call/Server0。
Preflight/準備失敗を含む全16 Artifactを同一Byte保存し、
`phase11_qwen35_9b_format_result_v2.json`へ結んだ。旧v9の失敗は不変である。

同じ固定Worktreeで`phase11-qwen35-9b-source-reading-v10`の意味診断を開始した。
Launchに生成0/形式ReportのHashを保存。session27269は継続観測し、重複起動しない。
同じ既知Critical4条件全一致の場合だけ人工54条件へ進む。最大128 Call/Retry0、
旧Expected/基準は不変。全意味結果/採用は未確定で、主20問/未使用Calibrationは未実施。

## v10の意味不通過と全保存

固定645f193のv10は全4既知条件/20 Callを完了し、Critical正確一致3/4で停止した。
形式/Runtime/Overflow失敗0・Critical誤支持0でも、旧正確Label基準に不通過である。
人工54条件は未試行。入力96268/出力50676 Token・Task秒和860.195937秒（14.34分）。
90 Source Hash/4読解・16固定文判定の全文/ID/全分母/実費を機械照合し、
再開34 File不変・追加Call/Server0を確認した。原本36 Fileを同一Byte複製し、
対象を明示した意味確認/Preflight/準備失敗を含む全42 Artifactを
`phase11_source_reading_result_v10.json`へ結んだ。

不一致はCouncil元順序c4のExpected矛盾→観測支持不足である。Modelは1567年のPope Pius Vへの
主体帰属を認識したが、原文のwent-beyond対比を矛盾として確定しなかった。逆順c4とZidane両順序は一致。
両非支持分類ともFへの寄与は0だが、正確Label基準を事後に二値へ変更しない。
対象c4の実推論2057 TokenにはRuntime停止指示分を含み、Budget2048+監査許容範囲に適合する。
推論本文は指示の再述が長く、直接比較は2367文字目から始まり、対比の検討中に強制終了した。
文字数をToken数へ読み替えず、含まれたSource外の歴史推測も根拠にしない。
これは次候補の原因仮説で、改善した証明ではない。

Councilの曖昧c6はExpected nullを保ち、元順序矛盾/逆順支持となった。
Fは元5/7・逆6/7、閾値0.7で両方採用。曖昧c6を精度からだけ除き、F全7文を維持する。
既知一例の観測を新しい独立標本や一般的な順序効果の推定とはしない。
手動意味確認は不一致c4/逆順対応とc6を対象とし、全読解文の独立した完全監査とは主張しない。
human_reviewed=false・厳密Model ID未取得・同一開発履歴を記録した。

## 直接比較を先に行う候補v11

`phase11_semantic_candidate_v11.yaml`/Prompt v8を結果前に別保存した。
v10からJudge systemの先頭に、指示/草稿/文書列挙の再述を避け、Sourceの主体/行為・関係から
簡潔に比較し、原文の対比/限定を確認する一般指示だけを加える。既存の支持/矛盾/欠落の定義、
架空例、全文/Expected/全基準、読解/書換え/抽出、Model/Runtime/Sampler/予算/Schemaは保持する。
日英同じJudgeで、既知人名/年/ID/期待Labelを追加しない。主/予約Calibrationの出力は使っていない。

事前Manifestは`phase11_qwen35_9b_preregistration_v3.json`。
既知例を繰り返した候補選定なので、この診断の通過を独立した一般精度の証拠にはしない。
固定Worktreeの生成0で全128入力を確認してから、同じ4 Critical/日英人工診断を新Runで行う。
人工形式検証は候補Judge指示を使わない固定6入力であり、同じModel/Runtime/全Sampler/Task設定と
27 Core/Probe Source Hashが一致したため、通過済みv10の証拠を明示して再利用する。
同じ6 Callを無目的に繰り返さず、実Taskごとの終了/形式/実Budget監査は維持する。
最大新規242 Call（意味128+通過時の旧回帰114）、旧9B28 Callを含め累積最大270、Retry0。
基準不通過は停止/全保存し、全意味採用証拠がそろう場合だけ主20問へ進む。
