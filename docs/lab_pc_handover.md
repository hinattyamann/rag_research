# 研究室PCへの引継ぎと実行手順

2026年10月18日更新: 正式テーマを「根拠提示順序に対するRAG自己評価の感度と修復判断への影響」へ変更した。
2026年10月21日更新: 現行は[研究計画7.14](rag_research_plan.md)、[実装計画8.16](rag_implementation_plan.md)、Dataset Guide 2.4。
英語CLAPNQに近い別の日本語Datasetで比較する方針を追加した。翻訳対を主実験に使わない。
[日英比較の拡張方針](english_japanese_expansion.md)の選定・日本語対応・予備検証と両言語の条件固定を
Phase 11で完了してからPhase 12へ進む。
[日本語Source選定](japanese_dataset_selection.md)と固定版原QA取得・構造監査は実施済み。
本文Corpusは固定Commitの専用Checkoutで取得中。日本語文単位のComponentを追加し全316 Test・Ruff成功。
分割・検索/Model/品質の全Pipeline実走・予備検証・最終固定は未完了。
QA Adapter/Group処理は実装済みで、実838件の取込み・暫定706 Group/開発予約142件を確認。全338 Test/Ruff成功。
正式Splitは取得完了とRedirect等の照合後に生成し、Gold Passage対応と意味妥当性は未確認。
[多言語検索候補とPassage分割](phase11_multilingual_retrieval.md)は既知開発1記事で実走し、全351 Test/Ruff成功。
英語3130 Passageに新Tokenizer上限超過があり、英語の分割・新Index・日英RAG接続とCalibrationは未完了。
英語の分割はその後183889 Passageへ作成し、元本文/親Gold対応を検証した。全365 Test/Ruff成功。
[Corpus準備](phase11_corpus_preparation.md)の欠測規則とGPU Probeを確認し、GPU正式接続・新Index・日英RAG実走へ進む。
Phase 1〜9とPhase 10初回20問・測定系修正・新規10問/20候補AI採点・集計を完了。
引用重複1件で元の事前Gateは不通過とし、後処理の修正・保存出力再検証を別に記録した。
[再確認結果](phase10_recheck_results.md)と[ロードマップ](research_roadmap.md)で結果と現在地を確認する。
Phase 11は本実装・CPU初期5問/10候補AI採点と集計まで完了。ただし全拒否で比較可能0、Gate 11未通過。
上記はCPU側の引継ぎ時点の履歴。Ubuntu側でGPU対応と追加20問/40候補採点・34単位監査を完了した。
完全比較12・Health Gate通過だが意味妥当性/分析は未確定で最終凍結を見送り、Gate 11未通過。
[最新の実機・GPU検証記録](phase11_lab_validation.md)を優先する。実測はRAM約7.5GiB、
RTX5060Ti VRAM8151MiB、Driver580.95.05。以下の購入仕様・未確認項目は当時の記録として読む。
Git運用は、確認済みの変更をCodexがCommit・通常のPushまで行う方針へユーザーが変更した。
ユーザーの委任により品質採点は[Codex AIのProtocol](ai_quality_protocol.md)へ変更し、人手確認とは区別する。
以下の日付付き実測・旧Versionの記載は、その時点の履歴として読む。

確認日: 2026年10月5日。対象はこの日の作業開始時点のCommit `9bfe8ac` と、研究計画Version 6.5、
実装計画Version 7.9である。以後の実装に応じて到達点と手順を更新する。

2026年10月6日時点: 研究計画はVersion 6.11、実装計画はVersion 7.15、Dataset GuideはVersion 1.10だった。
制御・比較・独立評価の仕様承認後、ノートPCでPhase 3〜6を実装し、Gate 6まで通過した。
先行研究との関係・貢献候補・有用性は[研究の立ち位置](related_research_positioning.md)へ記録した。
10月5日の実測値・Hash・Test結果はその日時の記録として保持し、Phase 3・4の結果を以下へ追記する。

購入PCはUbuntu 24.04 LTSと判明したため、そのPCでは[第6節のUbuntu手順](#6-購入pcの仕様とubuntu向け手順)を
使用する。Windows手順は現在のPCでの参照用として残す。

## 1. 現在の到達点

| 工程 | 状況 | 確認できる成果物 |
|---|---|---|
| 研究テーマ・仮説・比較条件の設計 | 作成済み | 研究計画・実装計画・Dataset Guide |
| Phase 1: CLAPNQ取得・Source検証 | 完了、Gate 1通過 | 取得Script、固定Revision、Source Manifest |
| Phase 2: Loader・内部Schema変換 | 完了、Gate 2通過 | QA 4,345件、Corpus 178,890件のJSONL生成 |
| Phase 3: Title単位の研究用Split | 完了、Gate 3通過 | Split Script、割当済みQA、Split Manifest、再現検証 |
| Phase 4: 共通Corpusの検索Index | 完了、Gate 4通過 | 全178,890件のBM25/Embedding、質問検索CLI、固定Manifest |
| Phase 5: 開発用Baseline RAG | 完了、Gate 5通過 | Embedding→Qwen CPU生成、質問/Development CLI、Prompt/実測ログ |
| Phase 6: Hybrid Retrieval | 完了、Gate 6通過 | 候補50件/方式、RRF定数20、Top-10、Calibration/固定Manifest、Development生成 |
| Phase 7: 新テーマのProtocol具体化 | 完了 | 専用Prompt/Config・品質基準案・入力予算検証・固定Manifest |
| Phase 8: 固定評価・根拠順序/反復 | 完了、Gate 8通過 | 開発2件、Judge 9回、再開追加0回、182 Tests成功。精度・品質改善の実証ではない |
| Phase 9: 一回書換え・品質採点入出力 | AI委任後の開発Gate通過 | 3候補AI採点と経路照合済み。人手確認達成とはしない |
| Phase 10: Development Pilot | 修正・再確認完了、事前Gateの失敗履歴を保持 | 初回20問、15診断/5既知書換え、新規10問/20候補。元完全比較3問、後処理検証4問。判断反転1問 |
| Phase 11: 条件固定 | 進行中、Gate 11未通過 | GPU20問/40候補採点・監査済み。比較可能12、意味妥当性/分析の採用と最終凍結が残る |
| Phase 12以降: 本実験・分析 | 未実施 | 詳細は現行ロードマップ。旧四条件Datasetは必須工程から外れた |
| 比較実験・結果分析・卒業論文の完成 | 未実施 | 提案手法の性能向上を示す実験結果はまだない |

現在のPCには次の生成物が存在し、2026年10月5日に研究日誌のHashと一致することを再確認した。

| File | 件数 | Byte数 | SHA-256 |
|---|---:|---:|---|
| `data/processed/clapnq/c508d78-base-v1/qa.jsonl` | 4,345 | 9,954,217 | `233800e4cafadec8ebfdf185e28f4e7eb26efa924d68e592735b24cb8b937209` |
| `data/processed/clapnq/c508d78-base-v1/passages.jsonl` | 178,890 | 156,262,889 | `c847751985c2f95987628800a3a8a12aa274da37dee088310f74b6bddb1ea103` |

QA側の2,074 Unique Gold Passage IDは全件Corpus内に存在する。Base QAの`research_split`は全件未割当のまま
保持し、別Versionの`c508d78-split-v1`へ全件割当済みQAを生成した。
Unanswerable 2,091件のCorpus全体に対する回答不能監査も未実施である。

同日に`uv run pytest`は43件成功、Skipなし、`uv run ruff check .`は問題なしだった。
Manifest生成とAnnotation確認CLIも実データで再実行し、既存Manifestの10 FileとHashが一致した。
研究室PCでの実行はまだ行っていない。

2026年10月6日にPhase 3を実装・検証し、Development 2,824件（1,465/1,359）、Calibration 434件
（225/209）、Evaluation 1,087件（564/523）へ割り当てた。括弧内はAnswerable/Unanswerable。
原文Titleは3,799種類、casefold・NFC正規化Groupは3,798件で、Split間重複・欠損・重複QAは0である。
別出力先で全5成果物とManifestがByte単位で一致し、Base QA・Corpusの上記Hashも維持した。
Phase 3時点の全Test結果は61件成功・Skipなし、ruff問題なしだった。

Phase 4ではBM25とCPU用の固定MiniLM ONNX ModelでEmbedding Indexを全178,890件生成した。
両IndexのCorpus/ID順一致、全2,074 Unique Gold IDsの欠損0、同じDevelopment 50問の検索を確認した。
BM25は別DirectoryでByte再生成一致、Embeddingは60,349件のcheckpointから再開して完了した。
固定Manifestは`data/manifests/clapnq_retrieval_manifest.json`。条件と実測値は
[`phase4_retrieval.md`](phase4_retrieval.md)による。Phase 4時点の全Testは86件成功・Skipなし、ruff問題なし。

公開Train/Devのみを使用し、非公開Test 601件は主実験に使用しない。Test Accessの返信は研究再開の条件に
しない。最後のAccess状況の記録日は2026年9月10日であり、その後のメール状況はこの確認の対象外である。

Phase 5ではQwen2.5-3B-Instruct GGUF Q4_K_Mとllama.cpp b11433 Windows CPUを採用した。
固定Embedding Top-5から実回答を生成し、Development 5問が各1回の生成で完了した。
実測は1問18.77〜28.96秒、合計Peak RSS 2.453GiB。全116 Tests成功、ruff問題なし。
条件/実行手順は[`phase5_baseline.md`](phase5_baseline.md)、固定情報は
`data/manifests/phase5_generation_manifest.json`、実測要約は`phase5_smoke_report.json`。
これはWindowsノートPCでの確認であり、Ubuntu用Runtime/GPU、独立品質評価・比較実験は未実施。
生成Moduleへの切替えは別条件として記録し、最終比較の3方式へ共通適用する。

## 2. 研究室PCで確認する項目

特にGPUの型番・枚数・専用Memoryの総量と空き容量、RAM、OSを持ち帰る。

| 優先度 | 項目 | 確認する値・条件 | 使用目的 |
|---|---|---|---|
| 最優先 | OS | Windows/Linux、Version、64bitか | 実行環境とコマンドの選択 |
| 最優先 | GPU | メーカー、型番、枚数 | ローカルLLMとEmbeddingの実行方法を決める |
| 最優先 | GPU Memory | GPUごとの専用VRAM総量・空き容量、他の利用者の使用状況 | モデル規模、量子化、同時起動、Batch Sizeを決める |
| 最優先 | RAM | 総容量と使用可能容量 | Corpus、Index構築、CPU処理の計画 |
| 高 | CPU | 型番、物理Core数、Logical Processor数 | BM25と前処理の並列化・実行時間の見積り |
| 高 | Storage | 保存先、空き容量、SSD/HDD | Data・Model・Index・Logの保存 |
| 高 | NVIDIA環境 | Driver Version、`nvidia-smi`の出力、Toolkitが既にある場合は`nvcc --version` | 後で導入する推論Libraryとの互換性確認 |
| 高 | Network | GitHub、Python Package配布先、Hugging Faceへの接続可否、Proxyの有無 | Source・依存Library・将来のModel取得 |
| 高 | 運用条件 | Software導入権限、GPU利用時間、連続実行可能時間、Sleep設定、Remote利用可否 | 長時間のIndex構築・比較実験を継続する |
| 中 | 既存Software | Git、uv、WSL、既存のLLM実行環境とVersion | 環境の再利用可否を判断 |

現在の前処理とPhase 3のSplit作成にはGPUは不要である。Modelの必要VRAMは、Model Revision、精度・量子化、
Context Length、Batch Size、同時起動するModel数によって変わるため、現時点で一律の必須容量は定めない。
生成済みJSONLだけで約166 MBだが、Raw Checkout、仮想環境、将来のModelとIndexは別途容量を使う。

### Windowsでの確認コマンド

PowerShellで実行する。導入済みでないコマンドのErrorも、環境確認の結果として記録する。

```powershell
# OS
Get-CimInstance Win32_OperatingSystem |
    Select-Object Caption, Version, OSArchitecture

# CPU
Get-CimInstance Win32_Processor |
    Select-Object Name, NumberOfCores, NumberOfLogicalProcessors

# RAM: 単位はGiB
Get-CimInstance Win32_OperatingSystem |
    Select-Object @{Name='TotalRAM_GiB';Expression={[math]::Round($_.TotalVisibleMemorySize / 1MB, 1)}},
                  @{Name='FreeRAM_GiB';Expression={[math]::Round($_.FreePhysicalMemory / 1MB, 1)}}

# GPU型番: NVIDIA以外も表示
Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion

# Driveの容量: 単位はGiB
Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' |
    Select-Object DeviceID,
                  @{Name='Size_GiB';Expression={[math]::Round($_.Size / 1GB, 1)}},
                  @{Name='Free_GiB';Expression={[math]::Round($_.FreeSpace / 1GB, 1)}}

# Storageの種類: MediaTypeが不明の場合はPCの仕様等で確認
Get-PhysicalDisk | Select-Object FriendlyName, MediaType, Size

# NVIDIA GPUがある場合
nvidia-smi
nvidia-smi --query-gpu=index,name,memory.total,memory.free,driver_version --format=csv

# Toolkitが既にある場合。未導入なら今すぐ導入する必要はない
nvcc --version

# 開発用Tool
git --version
uv --version
```

`nvidia-smi`が見つからなくても、NVIDIA GPUがないとは断定しない。GPUの有無とDriver/Pathの状態を分けて
確認する。NVIDIA以外のGPUではタスクマネージャー等で専用Memory容量を確認する。
`Win32_VideoController.AdapterRAM`は`uint32`なので、大容量VRAMの確認値には使用しない。
[Microsoftの仕様](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-videocontroller)

`nvidia-smi`のCUDA Version等はDriver側の対応情報であり、Toolkitの導入Versionと同一とは限らない。
[NVIDIAの仕様](https://docs.nvidia.com/deploy/nvidia-smi/index.html)

### Linuxだった場合

```bash
cat /etc/os-release
uname -m
lscpu
free -h
df -h .
lsblk -d -o NAME,MODEL,ROTA,SIZE
nvidia-smi
nvidia-smi --query-gpu=index,name,memory.total,memory.free,driver_version --format=csv
git --version
uv --version
```

OSが異なってもPython Scriptは同じものを使う。以下の`Get-FileHash`などPowerShell固有の確認は、Linuxでは
`sha256sum`等に置き換える。Softwareの導入方法はOSに合わせる。

## 3. 引継ぎ前に現在のPCで行うこと

コード、仕様書、`pyproject.toml`、`uv.lock`、Source ManifestをGitHub経由で引き継ぐ。
確認済みの作業単位でCodexが `git add`・`git commit`・通常の `git push` を行い、研究室PCで取得する。
ユーザーはこの運用を継続的に許可している。詳細はAGENTS.mdに従い、Pushの成否を報告する。

```powershell
git status --short
git diff
git rev-parse HEAD
```

未Commitの変更がある場合は、内容と必要な検証を確認してCodexがCommit・Pushする。研究室PCでは
引き継いだCommit Hashが一致することを確認する。`.venv`、`data/raw/`、`data/processed/`、
`data/indexes/`はGit管理対象外であり、`git clone`だけでは移らない。

`.venv`は各PCで再作成し、Dataは固定Revisionから再取得・再生成する。Git管理対象外のDataをUSB等で
運ぶ場合、Raw Checkoutの`.git`も必要である。既存の取得・検証ScriptはRawのCommitを検証するためである。

## 4. 研究室PCでのセットアップ

以下はWindows PowerShell向け。各コマンドの終了を確認し、Errorが出た場合は次の工程へ進む前に原因を確認する。

### 4.1 Gitとuvを準備する

未導入の場合に実行する。インストール後はPowerShellを開き直す。

```powershell
winget install --id Git.Git -e
winget install --id astral-sh.uv -e
git --version
uv --version
```

uvのWinGet導入は[uv公式の導入手順](https://docs.astral.sh/uv/getting-started/installation/)でも案内されている。

### 4.2 RepositoryとPython環境を取得する

保存先のDirectoryへ移動してから、初回のみ次を実行する。

```powershell
git clone https://github.com/hinattyamann/rag_research.git
cd rag_research
git rev-parse HEAD
uv sync --locked
uv run --locked python --version
```

Pythonは3.12系を使用する。`uv.lock`は依存Libraryを固定するが、PythonのPatch Versionは固定していない。
今回の検証環境はPython 3.12.14だった。最終実験ではPythonの具体的なVersionも記録する。
`--locked`はLock FileとProject設定に不整合がある場合に、Lock Fileを更新せずErrorにする。
[uv公式の環境同期の説明](https://docs.astral.sh/uv/concepts/projects/sync/)

既にRepositoryがある場合は、そのRootへ移動して`git status --short`を確認する。作業中の変更がなく、
取り込むBranchが正しいことを確認してから`git pull --ff-only`、`uv sync --locked`を実行する。

### 4.3 CLAPNQを取得する

```powershell
uv run --locked python scripts/prepare_clapnq.py
```

固定Revisionは`c508d78d8c5c2eecbf172fcf5f789004206e11fb`である。
取得済みDirectoryは上書きせず、Commitと必須Fileを検証して再利用する。

**改行設定の注意:** 現行Source Manifestは`core.autocrlf=true`のWindows環境で取得したRaw Fileから作られた。
Source取得時の改行設定は現行取得Scriptでは固定されていない。別PCでRaw Hashが違う場合は、件数が同じでも
同一Sourceの確認完了と扱わず、Git改行設定とFile差分を確認する。

新しいPowerShellセッションで、初回取得前に既存Manifestの改行条件を明示して取得する場合は、上の取得コマンドを
次に置き換えられる。これらのEnvironment変数が既に設定されているセッションでは、既存設定を確認してから扱う。

```powershell
$env:GIT_CONFIG_COUNT = '1'
$env:GIT_CONFIG_KEY_0 = 'core.autocrlf'
$env:GIT_CONFIG_VALUE_0 = 'true'
try {
    uv run --locked python scripts/prepare_clapnq.py
    if ($LASTEXITCODE -ne 0) { throw 'CLAPNQ取得失敗' }
} finally {
    Remove-Item Env:GIT_CONFIG_COUNT, Env:GIT_CONFIG_KEY_0, Env:GIT_CONFIG_VALUE_0
}
```

Gitの設定Fileは変更せず、取得Processにのみ設定を渡す。
[GitのEnvironment設定仕様](https://git-scm.com/docs/git-config#Documentation/git-config.txt-GITCONFIGCOUNT)
既に取得したDataの改行はこの操作では変わらないため、不一致時に既存Dataを無条件に削除・上書きしない。

### 4.4 Sourceを検証し、保存済みManifestと比較する

既存Manifestを保持するため、検証結果をGit管理対象外の別Fileへ出力する。

```powershell
uv run --locked python scripts/build_clapnq_manifest.py --output data/processed/clapnq/source_manifest_lab.json
```

次に、固定Revisionと10 FileのHash・Size・件数を比較する。取得日時はPC間で異なるため比較しない。

```powershell
$baseline = Get-Content data/manifests/clapnq_source_manifest.json -Raw -Encoding UTF8 | ConvertFrom-Json
$actual = Get-Content data/processed/clapnq/source_manifest_lab.json -Raw -Encoding UTF8 | ConvertFrom-Json
if ($baseline.dataset.revision -ne $actual.dataset.revision) { throw 'Source Revision不一致' }
if ($baseline.files.Count -ne $actual.files.Count) { throw 'Source File数不一致' }
foreach ($expectedFile in $baseline.files) {
    $matchedFiles = @($actual.files | Where-Object { $_.relative_path -eq $expectedFile.relative_path })
    if ($matchedFiles.Count -ne 1) { throw "Source File対応不一致: $($expectedFile.relative_path)" }
    $actualFile = $matchedFiles[0]
    if ($actualFile.sha256 -ne $expectedFile.sha256 -or
        $actualFile.size_bytes -ne $expectedFile.size_bytes -or
        $actualFile.record_count -ne $expectedFile.record_count) {
        throw "Source不一致: $($expectedFile.relative_path)"
    }
}
Write-Output 'Source Revisionと全FileのHash・Size・件数が一致'
```

### 4.5 内部Dataを生成する

```powershell
uv run --locked python scripts/inspect_clapnq.py
uv run --locked python scripts/build_clapnq_qa.py
uv run --locked python scripts/build_clapnq_corpus.py
```

順に、AnnotationとQueryの対応確認、QA JSONL生成、Corpus JSONL生成を行う。CorpusはZIPを全展開せず、
Streamingで変換する。QA・Corpus生成コマンドは成功時に既存の生成JSONLを置換する。

確認する値はQA 4,345件、Answerable 2,254件、Unanswerable 2,091件、有効Reference 3,142件、Corpus
178,890件、Unique Gold Passage ID 2,074件である。

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath data/processed/clapnq/c508d78-base-v1/qa.jsonl
Get-FileHash -Algorithm SHA256 -LiteralPath data/processed/clapnq/c508d78-base-v1/passages.jsonl
uv run --locked pytest
uv run --locked ruff check .
git status --short
```

Hashが本書の表と一致し、86 Testsが成功、Skipなし、ruffが問題なしなら、Phase 1・2のDataと
現行Testの再現確認が完了する。続いて第5節でPhase 3の成果物と固定Manifestの一致を確認する。
Raw Data未取得では実データを使う4 Tests、Base QA未生成ではPhase 3の実データTestがSkipされ得るため、
単に失敗がないだけで完了としない。
別出力のManifestはGit管理対象外なので、Data再生成だけなら追跡Fileに変更は生じない想定である。

## 5. 次に研究として行うこと

2026年10月21日の現行工程は[ロードマップ](research_roadmap.md)と[日英比較方針](english_japanese_expansion.md)。
日本語候補の仕様比較・選定、取得/Split、検索/文分割/拒否/指示文等の対応・英語回帰、
少数予備検証と両言語の未使用Calibration、対象・条件・統計の最終固定をPhase 11で行う。
英語の既知の誤支持と拒否方針の検討も継続する。Phase 12は日英本実験と独立AI採点、
Phase 13は言語別統計と日英比較、Phase 14は原稿・卒論。既存の英語用Validatorだけで凍結しない。

現在の再開依頼例:

> AGENTS.md、現行計画・ロードマップ、docs/english_japanese_expansion.mdを読んでください。
> 英語GPU20問の検証済み記録を保持し、日本語Datasetの選定・対応と日英検証をPhase 11で進めます。
> 両言語の意味妥当性・比較条件・対象/件数・統計を固定するまでPhase 12へ進まないでください。
> 各工程の成果と未実施事項を説明し、確認済みの変更はCommit・通常Pushの成否まで報告してください。

### 移行前の引継ぎ手順（履歴）

以下は旧CPU/移行前時点の手順。現在地と次工程は上記の2026年10月21日方針を優先する。

新テーマは自己評価の根拠順序感度と修復判断への影響の分析である。
**Phase 1〜9、Phase 10初回Pilot・測定系修正・新規10問の実験/採点・事後の形式再検証を完了。次はPhase 11のCalibration。**
元v14の事前Gate不通過と後処理の派生検証を区別する。詳細は[ロードマップ](research_roadmap.md)、
[初回結果](phase10_pilot.md)、[修正後の結果](phase10_recheck_results.md)を使う。
旧四条件Failure Dataset、全R/F/A、原因別三修復を次工程の前提にしない。

研究室PCでは既存Data・Split・Indexを固定Manifestと照合し、少数DevelopmentでBaselineを再現する。
既存Windows用Baseline CLIの既定Configは`configs/phase6.yaml`、旧Embedding条件は`configs/phase5.yaml`。
Windows用RuntimeをUbuntuでそのまま起動できるとは扱わない。Ubuntu/GPUの実装と実測は未完了。
Model/Runtime/量子化条件を変更した場合は、既存Manifestを上書きせず別Versionで条件と差を記録する。

```powershell
uv run --locked python scripts/split_clapnq.py
uv run --locked python scripts/download_embedding_model.py
uv run --locked python scripts/build_retrieval_index.py --kind bm25
uv run --locked python scripts/build_retrieval_index.py --kind embedding
uv run --locked python scripts/build_retrieval_manifest.py
```

Ubuntu用Runtime対応後に検索→初回生成→保存を確認する。新実験の評価器・書換えPromptも入力予算を検証する。
最終条件を凍結する新Phase 11より前に実行環境を確定する。
生成条件を変えた場合は旧5問のRunと混ぜず、全比較条件へ共通適用する。
Hybridが検索精度を改善したとは主張しない。Source/基盤の詳細はPhase 4〜6記録による。

専用Prompt/Configと[Phase 7 Protocol](phase7_order_protocol.md)は作成済み。
固定TraceとClaim、Judgeの順序操作・反復・判断はPhase 8で実装した。
この後は一回Answer Rewrite、独立品質Export/Import、Development Pilotの順で進める。
Fの初期閾値0.7は旧加重Cとは別のRuleであり、旧R/F/A個別FailureやQuery Rewriteは実装対象から外す。
実評価CLIは`scripts/run_order_evaluation.py`、現行の開発用設定は`configs/order_phase8_v5.yaml`。
実出力確認は`scripts/render_order_example.py`。詳細は[Phase 8記録](phase8_order_evaluation.md)による。
書換え・盲検品質採点・新規Pilot選定CLIは後続工程。実装計画の仮名を既存コマンドとして実行しない。

Codexへの引継ぎ例:

> AGENTS.md、現行研究/実装計画、docs/research_roadmap.md、研究日誌を読んでください。
> Phase 1〜9とPhase 10の開発確認は完了済みです。既知のJudge誤りと制約を読んでください。
> Phase 11は本実装・CPU初期5問/10候補のAI採点と集計まで完了しています。
> 全5問が拒否で比較可能0、Gate 11未通過です。docs/phase11_finalization.mdを読んで続きへ進んでください。
> 旧原因別三修復ではなく、固定回答に対する評価器の根拠順序感度と一回書換えの判断を検証します。
> 研究室PCではOS/RAM/VRAM/Driverを確認し、固定Source・Index・Baselineを小工程で再現してください。
> Runtime変更は別Versionで記録し、Phase 11の本実験凍結前に共通条件を確定してください。
> 各工程の成果と未実施事項を説明し、確認済みの変更はAGENTS.mdに従ってCommit・通常のPushまで行ってください。

持ち帰る情報はOS、CPU、RAM、GPU型番/枚数/VRAM、Driver、Disk空き容量、Network条件、連続利用可能時間である。
## 6. 購入PCの仕様とUbuntu向け手順

2026年10月5日にユーザーから次の購入仕様を受領した。これは実機計測結果ではない。

| 項目 | 購入仕様 | 研究での見通し |
|---|---|---|
| OS | Ubuntu 24.04 LTS、64bit | LinuxのTerminalからGit・uvを使用する |
| CPU | Intel Core i5-14400 | 前処理、Split、BM25実装を進める構成として使用する |
| RAM | 8GB | 現行前処理は試せるが、Index構築とLLM実行のMemory予算に注意が必要 |
| Storage | 500GB M.2 NVMe SSD、500GB Partition | 実際の空き容量を確認する。初期のData・Model保存先として使用する |
| GPU | GeForce RTX 5060 Ti | VRAM容量、Driver、実際の認識状態は未確認 |

RTX 5060 Tiの公式Memory構成は16GB/8GBの2種類であり、型番だけでは判断できない。
[NVIDIA公式仕様](https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5060-family/)
RAM 8GBと専用GPU Memoryは別の容量である。

Model選定の見通しは次のとおり。いずれも実機での実行成功を保証するものではない。

- VRAM 16GBの場合: Qwen2.5-14Bの4bit量子化を生成用候補として検証できる。ただし、RAM 8GBでのLoad、
  Context用Memory、評価用Modelとの切替を確認する。生成・評価Modelの同時常駐は前提にしない。
- VRAM 8GBの場合: 7Bの4bit量子化を先に試す候補とする。14B Q4_K_Mの重みは約8.99GBで、全重みと推論用
  Memoryを8GB VRAMへ収める構成は想定できない。CPUへの一部退避もRAM 8GBでは余裕が少ない。
- RAM: ローカルLLM実験に向けた構成上の推奨は32GB。16GBもModelと処理方法次第で検討できるが、必須条件
  として確定したものではない。増設する場合はMotherboardの対応規格と現在のModule構成を先に確認する。

公式GGUF配布のQ4_K_Mの重みSizeは、7Bが約4.68GB、14Bが約8.99GBである。これはModel FileのSizeであり、
実行時のRAM・VRAM要件そのものではない。推論ではKV Cacheと作業領域等も必要となる。
[Qwen公式7B配布](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF)、
[Qwen公式14B配布](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-GGUF)

研究室PC用Model・量子化・推論基盤はまだ固定していない。変更が必要なら研究仕様と実装条件を合わせて更新し、
Baseline、Always Rewrite、Adaptiveの全方式へ共通に適用する。

### 6.1 実機で先に確認する

```bash
nvidia-smi
nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version --format=csv
free -h
swapon --show
df -h .
```

これらの出力に加え、Network接続と導入権限を確認する。SwapはRAMと同等の性能を持つMemoryとして見積もらない。
`nvidia-smi`が動かない場合は、そのErrorとGPU/Driver認識状態を先に調べる。前処理にはNVIDIA Driverは不要である。
Driverを導入する必要がある場合は[Ubuntu公式手順](https://ubuntu.com/server/docs/how-to/graphics/install-nvidia-drivers/)
に従い、購入時のDriver構成を確認してから行う。

RTX 5060 TiはBlackwell世代なので、LLM実行基盤を導入するときは対応するDriver・CUDA Backendを確認する。
今はToolkitや推論Libraryを一律に導入しない。
[NVIDIA Blackwell互換性ガイド](https://docs.nvidia.com/cuda/blackwell-compatibility-guide/)

### 6.2 Gitとuvを準備する

未導入の場合に実行する。`sudo`が必要なPackage導入は、このPCで導入権限がある場合に行う。

```bash
sudo apt update
sudo apt install -y git curl ca-certificates
curl -LsSf https://astral.sh/uv/install.sh | sh
```

uv導入後はTerminalを開き直し、`git --version`と`uv --version`を確認する。
[uv公式Linux導入手順](https://docs.astral.sh/uv/getting-started/installation/)

### 6.3 RepositoryとDataを再現する

今回の手順書を含む変更のCommit・Push成功を確認した後、保存先のDirectoryで初回のみCloneする。
各コマンドが成功してから次に進む。

```bash
git clone https://github.com/hinattyamann/rag_research.git
cd rag_research
git rev-parse HEAD
uv sync --locked
uv run --locked python --version
```

現行ManifestのWindows取得時のRaw Hashに合わせるため、初回Data取得にはProcess単位で改行設定を渡す。
Project全体やPC全体のGit設定は変更しない。既に取得済みのRaw Fileは、このコマンドでは改行変換されない。

```bash
GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.autocrlf GIT_CONFIG_VALUE_0=true \
  uv run --locked python scripts/prepare_clapnq.py

uv run --locked python scripts/build_clapnq_manifest.py --output data/processed/clapnq/source_manifest_lab.json
```

Source比較はLinuxでもuv経由のPythonで実行できる。取得日時は比較しない。

```bash
uv run --locked python - <<'PY'
import json
from pathlib import Path

baseline = json.loads(Path('data/manifests/clapnq_source_manifest.json').read_text(encoding='utf-8'))
actual = json.loads(Path('data/processed/clapnq/source_manifest_lab.json').read_text(encoding='utf-8'))
if baseline['dataset']['revision'] != actual['dataset']['revision']:
    raise SystemExit('Source Revision不一致')
expected = {item['relative_path']: item for item in baseline['files']}
observed = {item['relative_path']: item for item in actual['files']}
if (len(expected) != len(baseline['files']) or len(observed) != len(actual['files'])
        or expected.keys() != observed.keys()):
    raise SystemExit('Source File対応不一致')
for path, item in expected.items():
    for field in ('sha256', 'size_bytes', 'record_count'):
        if item[field] != observed[path][field]:
            raise SystemExit(f'Source不一致: {path}: {field}')
print('Source Revisionと全FileのHash・Size・件数が一致')
PY
```

一致後に内部Dataを生成し、検証する。

```bash
uv run --locked python scripts/inspect_clapnq.py
uv run --locked python scripts/build_clapnq_qa.py
uv run --locked python scripts/build_clapnq_corpus.py
uv run --locked python scripts/split_clapnq.py
sha256sum data/processed/clapnq/c508d78-base-v1/qa.jsonl
sha256sum data/processed/clapnq/c508d78-base-v1/passages.jsonl
uv run --locked pytest
uv run --locked ruff check .
git status --short
```

完了条件は第4.5節と同じ。これらのUbuntuコマンドは手順として作成したもので、購入PC上では未実行である。
DataとSplit再現後にPhase 4のCPU Index手順を再現する。最新の全Testは135件成功・Skipなし、ruff問題なし。
Source/SplitのHash一致、両Indexの共通Corpus/Gold対応とEmbeddingの数値/Hash差を確認する。
ノートPC用GeneratorはPhase 5で具体化したが、Ubuntu側のRuntime/GPU設定とEvaluatorは未確定である。
Phase 6の検索条件・選定Reportも再現・移送して検証する。Embeddingの数値差で選定が変わる場合は
固定成果物を上書きせず、影響を確認して別条件として記録する。
実機のVRAM/Memoryを確認し、移行条件を新しく記録する。Windows用RuntimeをUbuntuで実行しない。

## 7. 開発用ノートPCの実測仕様

確認日: 2026年10月5日。ノートPC上でPowerShellの`Get-CimInstance`、`Get-PhysicalDisk`、Windowsの
`dxdiag`を実行して確認した。研究室PCの購入仕様とは区別し、次は実機で認識された情報を記録する。
確認による設定変更は行っていない。

| 項目 | 確認結果 |
|---|---|
| メーカー・機種 | HP Pavilion Aero Laptop 13-be2xxx |
| OS | Microsoft Windows 11 Home、64bit、Version 10.0.26200 |
| CPU | AMD Ryzen 7 7735U with Radeon Graphics |
| CPU Core / Logical Processor | 8 Core / 16 Logical Processors |
| 物理RAM | 16GiB（Memory情報上は4GiBのEntryが4件） |
| OSが利用可能な総RAM | 約15.21GiB |
| 確認時のAvailable RAM | 約4.70GiB |
| GPUのOS表示 | AMD Radeon(TM) Graphics、Status OK |
| GPUの種類 | Integrated（`dxdiag`で確認） |
| GPU Driver | 31.0.22048.7002、WDDM 3.1 |
| GPU Dedicated Memory表示 | 485MB |
| GPU Shared Memory表示 | 7,786MB |
| GPU Display Memory表示 | 8,272MB |
| 物理Storage | KIOXIA KBG50ZNV512G、SSD、NVMe、約476.94GiB（約512GB） |
| C Drive容量 | 約475.71GiB |
| 確認時のC Drive空き容量 | 約89.94GiB |

Available RAMとDisk空き容量は確認時点の値であり、固定仕様ではない。物理RAM 16GiBとOSが利用可能な
15.21GiBは区別する。差の全量をGPU予約分だとは断定しない。

CPUの[AMD公式仕様](https://www.amd.com/en/products/processors/laptop/ryzen/7000-series/amd-ryzen-7-7735u.html)
では内蔵GraphicsはRadeon 680Mとされる。OS上の一般名表示と公式仕様の対応として記録する。
NVIDIA GPUは今回のDevice列挙では認識されず、`nvidia-smi`もPATH上に見つからなかった。

内蔵GPUのDedicated/Shared/Display MemoryはWindows診断の表示値であり、独立した約8GBのVRAMが
搭載されていることを意味しない。Shared MemoryはメインRAMと共有する枠であり、常時その全量を使用している
ことも意味しない。専用表示の485MBも、独立GPU上の専用Memory Chipの容量として扱わない。

## 8. ノートPCと研究室PCの比較・役割

この比較は実機での速度Benchmarkではなく、ノートPCの確認結果と研究室PCの購入仕様に基づく見通しである。

| 観点 | ノートPC | 研究室PC | 研究上の判断 |
|---|---|---|---|
| CPU | Ryzen 7 7735U、8 Core / 16 Thread | Core i5-14400、公式仕様は10 Core / 16 Thread（P-Core 6 + E-Core 4） | 長時間の並列CPU処理は研究室PCが有利と予想。ただし処理内容、電力設定、冷却、RAM不足で変わるため実測する |
| GPU | 内蔵Radeon 680M相当、RAM共有 | 独立GPUのRTX 5060 Ti、VRAM 8GB/16GBは未確認 | 対応する推論基盤でLLM・EmbeddingをGPU実行する用途は研究室PCを優先する |
| RAM | 16GiB | 購入仕様8GB | RAM容量はノートPCが上。研究室PCのRAM不足がModel LoadやIndex構築の制約となり得る |
| SSD | NVMe、約512GB、確認時空き約90GiB | NVMe、購入仕様500GB、空き容量不明 | 公称容量は同程度。速度の優劣は仕様だけでは決めない |
| 想定する役割 | コード開発、Test、前処理、Split、文書作成 | GPU推論、Embedding生成、比較実験 | 開発と計算実験を分担する。実験設定の固定後は同一条件で比較する |

CPUに関する見通しは、Desktop向けi5-14400と省電力Notebook向け7735Uの仕様からの推測である。
Core数や「i5」「Ryzen 7」という名称だけで速度を断定せず、研究用処理で所要時間とPeak Memoryを測る。
[Intel公式仕様](https://www.intel.com/content/www/us/en/products/sku/236788/intel-core-i5-processor-14400-20m-cache-up-to-4-70-ghz.html)、
[AMD公式仕様](https://www.amd.com/en/products/processors/laptop/ryzen/7000-series/amd-ryzen-7-7735u.html)

研究室PCはGPUでのModel推論に適した構成と考えられるが、全項目でノートPCより上とは表現しない。
購入仕様のRAM 8GBはノートPCより小さいため、VRAMの実容量とRAM使用量を確認してからModel条件を決める。
現行前処理・Phase 3に加え、Phase 4のCPU検索とPhase 5の小型LLM生成をノートPCで確認した。BM25/Embeddingの実測は
[`phase4_retrieval.md`](phase4_retrieval.md)、LLM実測は[`phase5_baseline.md`](phase5_baseline.md)へ記録する。
両PCの速度差・研究室PCのGPU/LLM動作は未測定であり、Modelや閾値を本比較だけで固定しない。
