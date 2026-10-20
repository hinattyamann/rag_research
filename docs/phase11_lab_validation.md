# Phase 11 Ubuntu移行・GPU事前検証

2026年10月20日。旧CPU結果・失敗履歴・既存Manifestは保持する。
本書の実行条件は新しいCUDA候補であり、Gate 11の最終凍結ではない。

## 実機と転送の確認

Ubuntu 24.04.3 LTS、Kernel 6.14.0-35、Intel Core i5-14400、RAM 8,072,888,320 bytes。
NVIDIA GeForce RTX 5060 Ti、VRAM 8,151 MiB、Driver 580.95.05。
最初のDisk空きは約391 GiB。購入予定仕様ではなく実機の記録である。
CUDA Toolkit 12.9が既設。DriverのCUDA表示13.0とToolkitのVersionを区別する。
制限環境内ではGPUデバイスとネットワークが見えないため、ホスト側で検査した。
Driver再導入・OSの管理者操作は行っていない。

- `data/runs/lab/ubuntu-inventory-v1.json`: 既存CLIで保存した実機情報。推論成功を示す記録ではない。
- `data/runs/lab/transfer-audit-v1.json`: Manifestの照合1,213件、対象Path 1,081件、欠落・不一致0。
  Raw/Split/Corpus/IndexのHashを照合し、EvaluationはByteのHashのみで本文を解析していない。
  Runsを含むローカル1,876ファイルのHashを追加保存した。
  元PCのManifestにないファイルはローカル基準Hashであり、転送元との完全一致を証明していない。
- `data/runs/lab/model-audit-v1.json`: MiniLM ONNX、Qwen2.5-3B、Qwen3-4Bの全固定Hash一致。
  MiniLMの取得後Manifestを、転送前の検索Manifest内の固定Hashと照合した。
  7Bは取得していない。モデルのRevision・ファイル名・量子化は変更しない。

開始時はmain / 309fcde、未コミット変更0。再ログイン後のGitHub mainも309fcdeと確認した。
uv 0.13.3を`.tools/bin`へ導入し、UbuntuのPython 3.12.3で`uv sync --locked`を実施した。
Windowsの仮想環境は使用せず、依存定義とLockは変更していない。
制限環境内でuvを使う際は`PATH="$PWD/.tools/bin:$PATH" UV_CACHE_DIR="$PWD/.tools/uv-cache"`を指定する。

## CUDA候補と既存CPU条件の境界

公式llama.cpp b11433、Commit 50569eb87df530daff11afda229ceb9ab8e6cae8を使用する。
Ubuntu CUDA 12.8版の取得元・Size・SHA-256を
`configs/lab_cuda_runtime.json`へ事前固定した。公式Release APIのDigestを利用する。
対応ライブラリの配布Archive取得が途中で停滞したため、その履歴を
`data/runs/lab/runtime-download-attempt-v1.json`に残した。
既設CUDA 12.9のcudart/cublas/cublasLtを実測SHA-256で固定し、実行Directoryへコピーする。
`LD_LIBRARY_PATH`はそのDirectoryを指定し、未固定のライブラリへの暗黙の置換を避ける。
組合せを`b11433-ubuntu-cuda12.8-system12.9-v1`として、生成前に別保存した。
取得CLIは`scripts/prepare_cuda_runtime.py`。旧Windows Runtime用定数とManifestを変更しない。

新規`execution`設定がある場合だけCUDA Runtimeを検証し、`--device CUDA0 --gpu-layers 99`で起動する。
起動ログに正のCUDA Offload数と全Layerの移送がなければ停止する。
単なるnvidia-smi検出、Model Load、Health API成功だけでは推論成功としない。
RuntimeファイルHash、実Command、Version、実Offload、Taskの入出力・予算・時間を保存する。

初回候補は`phase11_gpu_baseline.yaml`、補助診断は`order_phase11_gpu_diagnostics.yaml`、
Calibrationは`phase11_gpu_calibration.yaml`と`order_phase11_gpu_calibration.yaml`。
この時点ではGPUによる品質改善を仮定しない。既知Development入力で先に診断する。

## 未使用20問の事前規則

既存`phase11_gpu_calibration_selection_manifest.json`は上書きせず、その20 IDと除外Titleを照合して使う。
環境Probeと調整にはこの20問を使用しない。候補条件に修正があれば実行前に新Versionとして保存する。

現時点の候補は元CPU条件と同じモデル・Prompt・Token予約・Sampling・閾値0.7・拒否Fallback。
この記述は初期候補v1の履歴である。Development診断後に実行する候補v2は、初回・補助Promptを維持し、
補助の推論1536/全出力3072へ変更する。
順序群は元/逆/Shuffle 3種、対照は元順序5回、共通初回を共有し最大9 Judge呼出し/問。
質問・初回回答・使用根拠・固定文・JSON Schemaを共用し、根拠配列の順序だけを変える。
一回書換えを元順序で生成し全判断へ共用する。拒否はF=nullで初回保持とし、誤採用と区別する。

Health Gateは20問時点で完全比較8問以上、Judge形式/実行エラー率0、入力超過なら途中停止。
8問は旧Developmentの4/10という実行可能性に対応する最低確認数で、検出力を保証しない。
効果量・反転・品質改善の大小を合否に使わない。再試行0、失敗・拒否の補充0。
GPU起動時の全Layer Offload失敗も停止する。失敗Runを保持し、同じ20問を未使用と呼び直さない。

候補ManifestとソースSnapshotを新規結果の前に保存する。
全匿名候補をAI採点しLabelを固定してから、内部F・判断・候補段階との対応を開く。
品質は必須要点・重大誤り・使用根拠の支持で判定し、Fの支持割合を正答確率と扱わない。
内部Judgeの意味監査では、誤支持と質問への回答不足を別に記録する。

本番の件数・反復・統計の最終固定は、GPU実測・有効比較数・意味監査の後に判断する。
20問の実行だけではPhase 11完了としない。最終凍結とGate 11通過前にPhase 12は開始しない。

## 実行結果

初回Probe v1は詳細ログ不足でOffloadを検証できず、生成前に停止した。
詳細ログを有効にしたv2で全37/37 LayerのCUDA Offloadと5生成に成功した。
ただし保存JSONのキー順によって元のCPU入力とToken列が異なっており、CPUとの比較には使わない。
v3では保存済みmessagesを直接使い、4実例の全Prompt Token一致を検証してから生成した。
いずれもCalibration 20問は使用していない。

v3のFriday Night Lightsは、根拠にAustin/Pflugervilleと明示されるのに単独拒否。
ミトコンドリアは回答を生成したが、この一例だけでGPUによる品質改善とはしない。
Bernetteは命名由来に回答し、時刻が欠ける人工対照では妥当に拒否した。
Tar Heelsは伝説や語源未確定という区別を含め、回答の断定と支持を別途点検する。
5生成の実Step時間は約0.13〜1.44秒。検索・初回起動・品質採点込みの応答時間ではない。

Qwen3のv1は全Layer OffloadとNative予算/JSON文法の適用を確認したが、
既知Armistice例の誤った調印時刻をsupportedとする意味誤りで事前Critical Gate不通過。
512 Tokenで推論が途中終了している保存出力を根拠に、推論1536/全出力3072の候補v2を
Developmentだけで検証する。閾値・Fの定義・モデル・量子化は変更しない。
初回生成は`prompts_phase11_v2.yaml`で、直接支持する一根拠で回答可能なこと、
無関係な根拠を無視すること、不確実性・部分回答の扱いを明示する候補を別検証する。
初回Promptと推論予算の変更は生成内容・採点内容・費用に影響するため、旧CPU条件との
改善率を計算せず、新規候補として扱う。20問の条件へ採用する前に既知診断を終える。

推論予算v2は基本12診断すべて一致、自然3例・書換え2例を含む17 Completionに形式失敗なし。
Armisticeは誤時刻2文をcontradicted、正しい日付結論をsupportedと判定した。
ただし追加の暖鋒/Tar Heelsでは従来と同じ誤支持が残った。
Pradaの翻訳説明はsupportedでも「Pradaが何を指すか」という質問には不十分である。
この不足はFの意味誤りと区別する。Bernetteの命名説明は支持と質問への回答の双方を満たす。

初回Prompt候補v2は、Friday Night Lightsで矛盾する説明を併記し、ミトコンドリアでは
原核生物の細胞質と真核生物のミトコンドリアという別の関係を誤って回答へ移した。
拒否を減らしたことだけを採用理由にせず、この候補は不採用とする。初回Promptは元のまま。
補助Prompt候補v3では、Before/During/After、平坦化表の列対応、未知の語源と説明仮説の
区別を一般的な架空例で明示する。題材固有の名称・Gold・正解Labelを推論入力へ加えない。
`order_phase11_gpu_diagnostics_v3.yaml`ではArmisticeの誤時刻1文を誤支持し、
暖鋒・Tar Heelsも誤支持が残った。このPrompt候補v3は不採用とする。
追加20問は元Promptを維持した`phase11_gpu_calibration_v2.yaml`を使う。
既知の意味誤りを隠さず、全匿名品質固定後に新規Judgeも全固定文単位で監査する。
全誤判定の解消を仮定せず、最終固定の妥当性は別途判定する。
