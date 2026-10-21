# Phase 11 多言語EmbeddingのCUDA入口と実機監査

確認日: 2026年10月21日。これは検索基盤の候補検証であり、日英RAG・意味妥当性・Calibration・
最終条件固定の完了ではない。旧CPU環境・Index・RunとModelの公式FP32ファイルを保持する。

## 実行条件

`environments/embedding_gpu/pyproject.toml`と`uv.lock`を追加した。
主要依存は先の分離GPU Probeと同じ固定版で、ONNX Runtime GPU1.30.0とそのCUDA/cuDNN依存を使う。
Rootの`pyproject.toml`/`uv.lock`/CPU環境は変更しない。CPU版とGPU版Runtimeの同居を拒否する。
配布元はPyPI/公式Wheelで、CUDAライブラリもLockに固定した。

`MultilingualE5Encoder(provider="cuda")`を明示すると、利用可能Provider・GPU版Distribution・実Sessionの
CUDA有効性とDevice/TF32設定を確認し、Pythonの自動Provider Fallbackを無効にする。
Device0・TF32無効を初期条件とし、Provider/Options/実Session/Runtime版をIndex Configへ記録する。
形状計算等のCPU Nodeは許容するが、Session全体がCPUのみになった場合は止める。
GPU指定なしのCPU既定Configは既知27 Passageの旧Manifestと完全一致した。

[公式CUDA Providerの手順](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html)に沿い、
uv環境内のNVIDIAライブラリを`preload_dlls(directory="")`で読み込む。

```bash
uv sync --project environments/embedding_gpu --frozen
uv run --project environments/embedding_gpu --frozen \
  python scripts/validate_multilingual_cuda.py \
  --output-dir data/runs/runtime_probe/<新しい検証名> --batch-size 16
uv run --project environments/embedding_gpu --frozen \
  python scripts/build_retrieval_index.py --kind embedding \
  --encoder multilingual-e5 --provider cuda --device-id 0 \
  --model-root <固定E5 Model Root> --batch-size 16 --threads 6 \
  --source-dataset <Dataset名> --corpus <固定Corpus> --output-dir <新しいIndex先>
```

`--provider cuda`は多言語E5のEmbedding構築に限り、BM25/MiniLMへの指定は拒否する。
大規模構築は、このCodeをCommit固定した専用Checkoutで行う。Model/Data/環境はGit同期対象外で、
移行時は別途配置・Hash照合と各PCでのuv環境再現を必要とする。

## 実機確認と限界

正式Encoderの検証CLIは、結果前に数値基準とBatch16を保存し、合成の日英短文と長文を使った。
質問・Reference・QAの品質結果は使っていない。最大実入力は509 Tokenで、切詰め0。

| 確認 | 結果 |
|---|---|
| CUDA/CPUのCosine下限 / 最大Vector差上限 | 事前基準0.99999 / 0.0001を通過 |
| 実測最大Vector差 | Passage約6.71e-8、Query約6.52e-8 |
| 保存ProfileのNode | CUDA1396、CPU8 |
| 合成長文Batch16・2 Batch | 約0.195秒、約164 Passage/秒 |
| 初期化と最初の2 Batch | 約1.71秒 |
| CPUとの照合を含む区間 / ピークRSS | 約4.38秒 / 2,089,340,928 Byte |

合成入力の速度を全Corpusの確定速度としない。RuntimeはPlugin登録/CPU Nodeの警告を出したが、
保存Profileで実CUDA演算を確認し、数値基準も満たした。
既知開発1記事27 Passageを正式CLIでCUDA構築し、再開追加推論0 Batch・実検索1 Batch・超過入力の
推論前拒否・全IndexファイルのHash不変を確認した。これも検索品質の検証ではない。

新規15 Testを含む全380 Test成功（ホスト5.35秒）、Ruff成功。
CPU既定維持、GPUなし/CPUのみFallback/実Options不一致/Runtime同居の拒否とIndex条件不一致停止を確認した。
根拠は`data/manifests/phase11_multilingual_cuda_encoder_manifest.json`。

全英語183889 Passageと日本語全記事の新Indexは、まだ構築していない。
日本語Passage/参照対応、新RAG Factory・指示文/予算/品質入出力、Development実走・意味監査と
未使用Calibrationは次工程である。Gate 11未通過、Phase 12未実施。
