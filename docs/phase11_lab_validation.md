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

## 追加20問の完了結果（2026-10-20 15:18 JST）

Runは`data/runs/calibration/phase11-gpu-twenty-v2/`。
事前条件をCommit d2c6550へ保存し、GitHub mainへの通常Push後に実行した。
20初回生成・108 Judge・20共通書換えを完了。40匿名候補をすべてAI採点し、
`phase11_gpu_quality_freeze.json`へHashと固定日時を保存してから内部対応を開いた。
新規品質を内部Fに合わせて採点し直していない。人手採点、厳密な採点モデルID固定、
完全に分離したセッションとは扱わない。

| 項目 | 結果 |
|---|---|
| 初回 / Judge / 書換え | 20 / 108 / 20回、すべて保存 |
| 単独拒否 / 完全比較 | 8 / 12問 |
| 事前Health Gate | 12≥8、Judgeエラー率0、入力超過0で通過 |
| 匿名品質 | 信頼可18・不可20・判定不能2候補 |
| 初回→書換え | 0→0:6、0→1:6、1→0:0、1→1:6、不明2問 |
| 順序による判断反転 / 同順序反復 | 1/12問 / 0/12問 |
| Fの順序変化 | ZidaneとTom Bombadilの2問。後者は閾値を跨がない |
| 質問内不一致率の差の平均 | 0.03333（記述集計。独立な120ペアの検定にはしない） |
| 固定文監査 | 全34単位。指示対象・部分訳等が曖昧な5単位を明瞭な一致率から分離 |
| 元の転送ファイル | 1,876ファイルを再照合し変更0 |

Zidaneの初回「監督としてCL優勝2回」に対し、根拠は2018年の3回目まで記載する。
元/逆/Shuffle2/Shuffle3と元順序の追加4反復はF=1/採用、Shuffle1だけF=0/書換えだった。
共通書換えの「3回」はAI品質が改善し、Shuffle1だけその改善を取り込んだ。
単一のCalibration例であり、順序効果の一般頻度や位置単独の因果を示さない。

Council of Trent後の1567年にPius Vが承認した事項を、Council自体へ帰属する誤文は全9回で支持された。
Zidaneの誤回数も8/9回で支持された。これらは安定性の高さで意味妥当性を保証できない実例である。
Tom Bombadilの映画への言及という支持不足も8/9回で支持され、残り1回はcontradictedだった。
原文が述べるnot portrayedと、候補のmentionedは同じ命題ではないので、監査では支持不足とした。
全文保持は確認したが、不正な引用IDを挟んだBlackstoneの二文が一単位になるなど、
決定的分割の限界も保存した。原子的事実や常に完全な文境界を保証するとはしない。

Gossip Girlでは、資料内のSerenaの失敗やナレーターの説明を支持できても、
質問が求めるDanの正体判明へ答えていない。Châteauneuf-du-PapeはNew Castleの部分訳だけで
教皇の要素が抜ける。支持の誤り・指示対象の曖昧さ・回答不足を分け、Fを正答確率にしない。
Big BoyのReferenceは閉鎖年を2017とするが原文は1995であり、原文を優先した。
P700の励起状態の限定と、NCO/COの分野の曖昧さを含む2候補は判定不能のまま保持した。

| 経路 | 最終AI品質（20問） | 改善見逃し | Model呼出し |
|---|---|---:|---:|
| 修復なし | 可6・不可14 | 6 | 20 |
| 常時書換え | 可12・不可6・不明2 | 0 | 40 |
| 元順序の単回評価 | 可6・不可14 | 6 | 32 |
| Shuffle1の単回評価 | 可7・不可13 | 5 | 33 |

改善6問はNeon、Europe clocks、Council、Zidane、Tom Bombadil、Phoebe。
うちNeon/Europe/Phoebeの3問は拒否Fallbackによる見逃しで、順序効果と合算しない。
Grey's Anatomyの検索不足による妥当な拒否、NCO/COの分野の曖昧さ等も別に記録した。
全18既知ペアでは悪化0だが、少数Calibrationと単独AI採点の範囲であり、常時書換えの一般的優越は主張しない。

## GPU・予算・費用の検証結果

初回3Bと補助4Bの両方で37/37 LayerのCUDA Offloadを実ログと出力で照合した。
補助128 Taskすべての推論予算・終了・最終JSON文法を検証し、
実質問/固定Claim/本文/Schemaが順序比較で不変であること、書換えに元回答/元順序の根拠だけを使うことを
保存Promptから再検証した。Gold・内部Judge Feedbackを推論へ追加していない。

- 初回はContext4096/出力512。実最大出力363 Token、入力超過・打切り0。
- 補助はContext8192/予約3072/推論1536。Judge実最大1561、書換え全出力1592、最終回答261 Token。
- 3Bの初回引用表記は5問で不正が残った。Token・JSON制約の通過と引用・意味の正しさを区別する。
- 補助入力353,847/出力93,385 Token、Step和957.37秒（約15.96分）。
- Judge平均7.304秒、書換え平均8.426秒。初回生成和17.79秒、Context準備2.48秒、検索2.76秒。
- これらの保存Step和は計980.39秒。起動・Hash検査・外部AI採点込みの実運用応答時間ではない。
- GPU利用率・VRAM・電力・温度は`data/runs/lab/calibration-gpu-telemetry-v2.csv`へ保存。
  RAMの計測最小空きは初回約4.09GiB、補助約3.60GiB。現時点のDisk空きは約385GiB。

CPUとの倍率や品質改善率は計算しない。Cohortも補助推論予算も異なるためである。
固定モデルHashは不変で、旧CPU Runを新GPUコードで再開・上書きしていない。

## 最終固定の判断と本番計画案

`configs/phase11_gpu_freeze_decisions_v2.json`と既存の最終固定Validatorで確認した。
品質来歴・Parser・拒否方針の記録・CUDA Runtimeは通過。
**意味妥当性の採用判断と分析規模が未確定なのでGate 11はfalse、Phase 12は未開始。最終凍結Manifestは作らない。**
監査を全件行ったことと、そのJudgeを本番へ採用できることを分ける。

固定根拠がそろったのは、Source/Split/Index/モデルの同一性、Ubuntu/CUDA Runtime、
入力と順序の分離、再開・再試行0・失敗非補充、JSON/Token制約、匿名品質固定後の照合である。
追加修正が必要なのは、支持判定の誤帰属・限定の見落としと、拒否から改善できる場合の扱い。
推論予算やPromptを変えるだけで一般的な意味精度が改善したとはしない。

本番件数は**200問案、未凍結**。現候補の比較可能率60%なら約120問の完全比較を見込むが、保証ではない。
補助生成Step和の見積りは同率で約2.66時間、全問比較可能なら約4.12時間。検索・起動・採点は別で、
修正後のJudge/拒否方針へこの時間をそのまま転用しない。
順序は元/逆/Shuffle3種、同順序は元を合計5回、共通初回を共有し最大9 Judge/問を候補とする。

統計案は質問内の全有効判断ペアを一つの値へまとめ、順序群−同順序群の差を主比較とする。
質問/Titleの対応を保つTitle単位Bootstrap 10,000反復・Seed42・95%CI。
全ペアを独立標本とせず、完全比較QAの分母・全選定QAのFallback込み品質/費用・品質不明の上下限を併記する。
支持根拠位置/分散・文数等の少数の条件別分析と探索的分析を分ける。
本番IDはGate通過時に固定SplitのIDメタデータだけからSHA256順で選び、Evaluation本文や結果で調整しない。
分析実装・件数の最終凍結は追加検証後の作業である。

次は、既知Developmentと今回の使用済み20問を回帰診断へ利用し、
文ごとの独立支持検証等を別Versionで検証する。順序反転を増やす目的の変更・閾値変更は行わない。
拒否から一回書換えへ進める案も、保存候補の事後比較と未知QAでの検証を区別する。
未使用Calibrationは200問残っており、使用済み25問/Titleを除いた次の20問を
`phase11_additional_validation_selection_manifest.json`へ事前選定した。モデル呼出し0、条件/Health Gateは未確定。
今回の20問を再び未使用と呼ばず、新候補・停止条件の保存後にこの別バッチで確認する。

確認済みの成果物:

- `data/manifests/phase11_lab_preflight_manifest.json`: 結果前の条件・環境・既知診断。
- `data/manifests/phase11_gpu_quality_freeze.json`: 全40候補のLabel固定。
- `data/manifests/phase11_gpu_calibration_result_manifest.json`: 完了集計と生データHash。
- `data/runs/calibration/phase11-gpu-twenty-v2/semantic_audit_v2.json`: 全34単位の意味監査。
- `data/runs/calibration/phase11-gpu-twenty-v2/runtime_evidence.json`: 実Offload/Native/モデル/Runtimeの根拠。
- `scripts/summarize_lab_calibration.py`: 品質封印を照合してから入力不変性・全Task・費用・旧ファイル不変を再検証する。
