# Phase 11 補助Modelの追加代替・資源調査

2026年10月21日。8Bの読解診断を固定Worktreeで実行中に、採用できない場合のローカル代替を一次資料と公開Metadataで調べた。
この調査で重みを取得・推論しておらず、新Modelを採用していない。新規Calibration/Evaluationは開いていない。

元モデルは[Qwen3.5-9Bの発行元Card](https://huggingface.co/Qwen/Qwen3.5-9B)、GGUF変換配布は
[Unsloth 9B](https://huggingface.co/unsloth/Qwen3.5-9B-GGUF)・[Unsloth 4B](https://huggingface.co/unsloth/Qwen3.5-4B-GGUF)。
発行元Cardは9B・32層・8組の3線形Attention+1通常Attentionという構成を記載する。公開Benchmarkを本研究の支持判定精度の証拠には使わない。
APIで各RepoのRevision・License・該当ファイルのByte数/LFS SHA256を取得し、`phase11-qwen35-candidates-v1/metadata.json`へ保存した。
変換元の申告と、変換時の元重みRevisionを独立に完全検証できたことは区別して記録する。

| 候補Artifact | 固定Repo Revision | Byte数 | 資源上の位置付け |
|---|---|---:|---|
| Unsloth Qwen3.5-9B Q4_K_M | `3885219b6810b007914f3a7950a8d1b469d598a5` | 5,680,522,464 | 重み約5.29GiB。8GiB実機の次の検討候補。適合は未実測 |
| Unsloth Qwen3.5-9B Q5_K_M | 同上 | 6,577,841,376 | 重み約6.13GiBにRuntime等が加わり、余裕が小さい |
| Unsloth Qwen3.5-9B Q8_0 | 同上 | 9,527,502,048 | 重みだけでVRAM総量を超え、現行の全層GPU条件には適合しない |
| Unsloth Qwen3.5-4B Q8_0 | `e87f176479d0855a907a41277aca2f8ee7a09523` | 4,482,403,488 | 重み約4.17GiB。高精度量子化を使う別の資源候補、意味性能は未実測 |

いずれも公開MetadataのLicenseはApache-2.0。9B Q4_K_MのLFS SHA256は
`03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8`。
元Qwen9B Repoの照会時Revisionは`c202236235762e1c871ad0ccb60c8ee5ba337b9a`。

発行元の9B構成に基づく通常Attention層のFP16 KVだけの概算は、Context12288で約384MiB。
線形層の状態、計算Buffer、Driver/画面・同時Processを含まないため、この値を実VRAMピークや起動可能の保証にしない。
現在の固定b11433ライブラリでqwen35の実装Symbolを検出した。HashとSymbolを保存したが、実Modelの読込み・全CUDA演算・Chat Template/推論終了/JSON制約の互換性は未検証。

追加候補を実行する場合は、先にRepo/Artifact/RuntimeとPrompt・予算・Expected/採用/停止規則を別Manifestへ固定する。
重み取得/Hash検証後にCompletion0の資源/Tokenizer確認を行い、同時に別Modelを載せない。
初回生成Model・原回答/全固定文/根拠・Expectedを保持し、Jointの元の改訂PromptでModel変更を先に切り分ける案を基本にする。
実行可否を測り、既知Critical全一致・日英人工基準・旧既知回帰と新規Developmentを通した場合だけ後続の採用を検討する。
Model変更だけでGate 11を通したり、新規Calibrationを先に使ったりしない。
