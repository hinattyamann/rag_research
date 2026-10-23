# Phase 11 同じ9BのQ6を検討するための公開Metadataと資源試算

2026年10月23日10:51 JSTの記録。Q6/Q8の重みは未取得で、追加推論/Server起動0。
これは採用や新規Main/Calibrationの実行許可ではない。

同じ固定Revision `3885219b6810b007914f3a7950a8d1b469d598a5` の
[Unsloth Qwen3.5-9B Q6_K](https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/blob/3885219b6810b007914f3a7950a8d1b469d598a5/Qwen3.5-9B-Q6_K.gguf)と
[Q8_0](https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/blob/3885219b6810b007914f3a7950a8d1b469d598a5/Qwen3.5-9B-Q8_0.gguf)を調査した。
Repository APIと各Raw LFS Pointerを保存し、Revision・Byte数・SHA256の一致を確認した。
公開LicenseはApache-2.0。変換元の正確なRevisionは独立検証済みとはしない。

| 量子化 | GGUF Byte数 | 公開SHA256 |
|---|---:|---|
| Q6_K | 7458301152 | 91898433cf5ce0a8f45516a4cc3e9343b6e01d052d01f684309098c66a326c59 |
| Q8_0 | 9527502048 | 809626574d0cb43d4becfa56169980da2bb448f2299270f7be443cb89d0a6ae4 |

終了済みQ5/12k全意味診断の全182 Artifactを再照合した。GPUの5秒観測663点の最大6926/8151 MiBに対し、
量子化間のファイル差分をすべてGPU上の増分と仮定して加算すると、次の値になる。
実行中の旧回帰の途中の費用/観測値は使っていない。

| 量子化 | Q5とのファイル差分 MiB | 単純加算 MiB | 8151 MiBとの差 MiB |
|---|---:|---:|---:|
| Q6_K | 839.671875 | 7765.671875 | 385.328125 |
| Q8_0 | 2813.015625 | 9739.015625 | -1588.015625 |

GGUF Byte数とCUDA配置量は別で、CPU Mapped Tensor、量子化形式、Buffer、Allocatorの差がある。
この加算は配分の一つの仮定であり、上限・連続Peak・配置成功・長時間安定性を保証しない。
元Q5の実RuntimeではCPU Mapped Model666.88/CUDA Model5595.78/KV384.00/RS50.25/Compute29.01 MiBだった。
全33層CUDAとCPU Mapped部分の区別も維持する。

Q6は実資源確認へ進める余地のある候補として検討する。Q8はこの同条件試算で容量を超えるため、
まずQ6を優先する。どちらも実配置/意味精度の確認はしておらず、Q6の精度向上を予告しない。
進む場合は、終了済み旧回帰の全監査・新しい別Versionの取得仕様/Manifest/事前登録を先に保存し、
実ファイル全体のSize/Hash、全文の実入力/生成0・全層CUDAを確認してから、形式/意味/旧全回帰を再検証する。
同じPrompt/Runtime/Context12288/Task予算/Sampler/全対象/Expected/基準を保ち、
量子化だけを別候補へ分ける。変換元Revisionの未検証もあるため量子化の因果効果とは断定しない。
資源失敗時にCPU fallback、全文/予算の切捨て、未知結果の再試行、基準緩和へ切り替えない。

証拠は`data/manifests/phase11_q6_resource_feasibility_v1.json`。
Metadata/API/Pointer/試算コードと結果はignoredの`data/runs/model_screening/phase11-qwen35-9b-q6-metadata-v1`にあり、
Git Pushだけでは別PCへ転送されない。Gate 11は未通過、Phase 12は開始しない。
