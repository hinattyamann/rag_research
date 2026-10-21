# Phase 11 Qwen3.5-9Bの別候補v9

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
この時点で候補Modelの生成/Runtime資源検証は未実施である。

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
