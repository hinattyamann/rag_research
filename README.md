# rag_research

根拠提示順序に対するRAG自己評価の感度と、修復判断・回答品質・処理コストへの影響を分析する卒業研究プロジェクトです。

2026年10月18日にこのテーマへ正式に方向転換しました。同じ質問・根拠本文・初回回答について、
評価器への根拠順序を変えた場合と同一順序で繰り返した場合を比較します。
より信頼できる自己修復の設計につながる知見を目指し、対策の開発は任意の追加成果とします。

2026年10月21日、CLAPNQと仕様をできるだけ近づけた別の日本語データセットを加え、
日英で順序感度と採用/書換え・品質・費用への影響を比較する方針を採用しました。
[日英比較の拡張方針](docs/english_japanese_expansion.md)に沿って、選定・日本語対応・予備検証・
両言語の条件固定をPhase 11で行います。翻訳対を主実験には使いません。
[候補比較](docs/japanese_dataset_selection.md)から日本語Sourceを選定し、固定版原QAを取得・構造監査しました。
本文Corpusは取得中です。日本語の文単位候補を実装し英語回帰を確認しましたが、
分割・検索/Model/品質の全Pipeline実走・予備検証・最終固定は未完了です。

**Phase 1〜10の開発確認、Phase 11のUbuntu/CUDA対応と追加20問・40候補のAI採点・34単位監査を完了しました。完全比較12問・実行Health Gate通過ですが、意味妥当性の採用と分析規模が未確定でGate 11未通過です。最終凍結・Phase 12は未実施です。**
固定回答の自己評価・判断に加え、元順序による一回書換え、採点画面、採点JSONのImport、経路比較を実装しました。
開発3候補は、ユーザーの委任により[AIが代行採点してJSONを保存](docs/phase9_ai_quality_review.md)しました。
ユーザーの委任により、以後は[AI品質採点Protocol](docs/ai_quality_protocol.md)を使います。
Gate 9はAI採点による開発確認として通過し、人手確認の達成とは区別します。
[Phase 10結果](docs/phase10_pilot.md)ではFの順序変化が1例、主比較11問の修復判断反転は0件でした。
主張抽出・Judge・書換え・出力予算を修正し、明確な15判定と5書換えを診断しました。
[修正後の結果](docs/phase10_recheck_results.md)では、Astrosの順序別判断反転と改善見逃しを1例確認しました。
v14の事前Gateは引用ID重複1件で不通過として保持し、後処理だけを修正した保存出力の再検証を別記録にしました。
[Phase 9の実走結果と採点手順](docs/phase9_answer_rewrite.md)を参照してください。
[フェーズ別の現在地・次の作業・完了条件](docs/research_roadmap.md)を最初に確認してください。
[別チャットからの再開用引継ぎ](docs/codex_handover.md)に、読む順番・生データの場所・GPU確認済み事項と残る作業をまとめています。
[Phase 11の結果とGPU側で残る作業](docs/phase11_finalization.md)に、CPU確認の限界・追加Calibration・最終固定の条件をまとめています。

研究内容と実装方針は、次の文書を参照してください。

- [研究計画 Version 7.14](docs/rag_research_plan.md)
- [実装計画 Version 8.16](docs/rag_implementation_plan.md)
- [多言語検索候補・本文Passage分割の実装と確認](docs/phase11_multilingual_retrieval.md)
- [Corpus本文欠測・英語分割と親参照保持の監査](docs/phase11_corpus_preparation.md)
- [日本語Datasetの選定基準・日英比較・Phase 11〜14の拡張方針](docs/english_japanese_expansion.md)
- [Dataset Guide Version 2.4](docs/clapnq_dataset_guide.md)
- [先行研究との関係・本研究の立ち位置と有用性](docs/related_research_positioning.md)

現在の到達点、研究室PCで確認する項目、Data再生成を含む引継ぎ手順は
[`docs/lab_pc_handover.md`](docs/lab_pc_handover.md)を参照してください。

## 基盤データセット

本研究では、Text-basedのFull RAG Pipelineを評価するため、CLAPNQを基盤データセットとして
使用します。CLAPNQはNatural Questionsの英語質問とWikipedia Passageから構築され、
Long-form Reference Answer、Gold Passage、Selected Evidence Sentences、および検索Corpusを
提供します。

- 公式Repository: <https://github.com/primeqa/clapnq>
- 論文: <https://aclanthology.org/2025.tacl-1.3/>
- Hugging Face Annotation: <https://huggingface.co/datasets/PrimeQA/clapnq>
- Hugging Face Retrieval Corpus: <https://huggingface.co/datasets/PrimeQA/clapnq_passages>

初期基準Revisionは`c508d78d8c5c2eecbf172fcf5f789004206e11fb`です。Raw DataはRepositoryへ
Commitせず、取得元、Revision、取得日、File Hash、件数、LicenseをManifestへ保存します。

CLAPNQはApache License 2.0として公開されています。一方、元Natural Questions Dataは
CC BY-SA 3.0で公開されているため、本研究では両方のLicense表示を保持し、CLAPNQ論文と
Natural Questions論文の両方を引用します。再配布、派生Data、論文・発表資料で必要な表示の詳細は
`docs/clapnq_dataset_guide.md`を参照してください。

公式Test 601件は非公開であり、2026年8月26日のAccess問い合わせに対して2026年9月10日時点で返信・
Data提供がないため、本研究では使用しません。公開Train/Dev 4,345件をWikipedia Title単位で
Development、Calibration、内部Evaluationへ再分割して研究を継続します。内部EvaluationはCLAPNQ
公式Testまたは公式Leaderboard相当の評価ではありません。

## CLAPNQ Raw Dataの取得

CLAPNQは、研究仕様で固定した公式RepositoryのCommitから次のコマンドで取得します。

```powershell
uv run python scripts/prepare_clapnq.py
```

取得先は`data/raw/clapnq/{revision}/`です。Raw Dataは`.gitignore`の対象で、GitHubへは保存しません。
このコマンドは40文字の固定Commit Hashだけを受け付け、一時Directoryへの取得が完了してから正式な
取得先へ移動します。既に取得先がある場合は上書きせず、Commitと必須Fileを検証して再利用します。

取得後、次のコマンドでFile Hash、件数、Schema、Gold Passage対応、License Lineageを検証し、
Source Manifestを生成します。

```powershell
uv run python scripts/build_clapnq_manifest.py
```

成果物は`data/manifests/clapnq_source_manifest.json`です。ManifestはGit管理し、Raw Dataを別PCで
再取得した場合の同一性確認に使用します。

固定Git配布の`passages.tsv`はHeader込み178,891物理行、実際のPassage Recordは178,890件です。
CLAPNQ論文の178,891 Passagesという記載とは1件差がありますが、公式Hugging Face配布の
`num_examples`も178,890件であるため、本研究では178,890件をCanonical Corpusの実Record数とします。

## CLAPNQ AnnotationとRetrieval Queryの確認

取得済みの最終Round Annotation 4ファイルとRetrieval Query 4ファイルは、次のコマンドでLoad、
Reference正規化、Gold Passage IDの1対1対応を確認できます。

```powershell
uv run python scripts/inspect_clapnq.py
```

LoaderはRaw JSON Recordを保持し、`skip=true`、`null`、空白のみ、`NA`のAnswerを評価Referenceから
除外します。Answerableは有効Referenceが1件以上、Unanswerableは0件であることを検証し、Answerと
Selected Sentencesの対応および元Output Indexを維持します。この確認処理はProcessed Dataをまだ
出力しません。Queryは`Source Split + Answerability + Source ID`でAnnotationへ結合し、質問文も完全一致
することを検証します。AnswerableにはGold Passage IDを1件、Unanswerableには空Listを付与します。

結合済みDataをStable ID付きの内部QA Schemaへ変換するには、次を実行します。

```powershell
uv run python scripts/build_clapnq_qa.py
```

成果物は`data/processed/clapnq/c508d78-base-v1/qa.jsonl`です。AnswerableではGold Passage IDと
Referenceを保持して`provided_passage=null`とし、UnanswerableではGoldとReferenceを空Listにしたうえで、
公式Annotation内のRandom Passageを`provided_passage`へ保持します。`research_split`はPhase 3で
Title単位の分割を行うまで`null`です。Processed Dataは再生成可能なためGit管理対象外です。

固定Retrieval Corpusを内部Document Schemaへ変換するには、次を実行します。

```powershell
uv run python scripts/build_clapnq_corpus.py
```

成果物は同じDataset Version内の`passages.jsonl`です。ZIP内のTSVを展開せずStreamingで読み、178,890件の
Passageを`passage_id`、Source情報、Title、Text、Text SHA-256へ変換します。生成時にはQA側の全Unique
Gold Passage IDがCorpus内に存在することも検証します。

## 研究用Splitの生成（Phase 3）

Phase 2で生成したBase QAから、次のコマンドで研究用Splitを生成します。GPUや追加Libraryは不要です。

```powershell
uv run python scripts/split_clapnq.py
```

Seed 42、Title単位Group、目標65%/10%/25%で分割します。大小文字・Unicode表記差を同じGroupとして
扱いますが、元のTitleやReference等は保持します。質問・回答内容やModel成績は割当判断に使いません。

| Split | QA数 | Answerable | Unanswerable | 正規化Title Group数 |
|---|---:|---:|---:|---:|
| Development | 2,824 | 1,465 | 1,359 | 2,277 |
| Calibration | 434 | 225 | 209 | 434 |
| Evaluation | 1,087 | 564 | 523 | 1,087 |

成果物は`data/processed/clapnq/c508d78-split-v1/`の`qa.jsonl`、`development.jsonl`、
`calibration.jsonl`、`evaluation.jsonl`、`split_report.json`と、Git管理する
`data/manifests/clapnq_split_manifest.json`です。Base QA・Corpusは変更しません。
欠損・重複・GroupのSplit間重複は0件、別出力先での再生成はManifestを含めByte単位で一致しています。

同じ条件での再実行は同一成果物を再利用します。既存Fileと内容が異なる場合は上書きせず停止します。
Seed等を変更する追加分割は新しいDataset Version、出力Directory、Manifestを指定してください。
ManifestのLF改行は`.gitattributes`で固定しています。分割AlgorithmとValidationの詳細は
`docs/clapnq_dataset_guide.md`第6.2節・第7.7節を参照してください。

## 検索Indexの構築（Phase 4）

BM25とEmbeddingの両方で、固定Corpusの全178,890件を検索します。検索APIへの入力は質問文字列のみです。
ノートPCで両Indexの構築・検索・Gold ID対応を検証し、Gate 4を通過しました。
設定・中断再開・検証結果は[`docs/phase4_retrieval.md`](docs/phase4_retrieval.md)を参照してください。
LLM生成はPhase 5、RRF統合はPhase 6で接続済みです。自己評価はPhase 8、保存回答からの一回書換えはPhase 9の実験層に実装済みです。

```powershell
uv run python scripts/download_embedding_model.py
uv run python scripts/build_retrieval_index.py --kind bm25
uv run python scripts/build_retrieval_index.py --kind embedding
uv run python scripts/validate_retrieval.py --kind bm25
uv run python scripts/validate_retrieval.py --kind embedding
uv run python scripts/build_retrieval_manifest.py
```

CPU用の公式量子化ONNXモデルを固定Revisionで取得し、Batch 1・6 Threadsで生成します。
Embeddingは同じ条件のコマンドで中断後に再開できます。完成済みIndexは検証して再利用し、上書きしません。
モデル・Index本体はGit管理せず、`data/manifests/clapnq_retrieval_manifest.json`で条件とHashを管理します。
Developmentの固定50問を動作確認に使用し、Calibration/Evaluationでの調整・最終評価は実施しません。

```powershell
uv run python scripts/search_corpus.py "who does the voice of plankton from spongebob" --kind bm25
uv run python scripts/search_corpus.py "who does the voice of plankton from spongebob" --kind embedding
```

## 開発用Baseline RAG（Phase 5）

固定Embedding検索の上位5件を、ノートPC上のQwen2.5-3B-Instruct Q4_K_Mへ渡して回答を生成します。
llama.cppの公式Windows x64 CPU版をプロジェクト内へ置き、外部LLM APIを使わず実行します。
固定Development 5問で検索→生成→記録を確認し、Gate 5を通過しました。

```powershell
uv run --locked python scripts/prepare_generation.py
uv run --locked python scripts/run_baseline.py "who does the voice of plankton from spongebob" --config configs/phase5.yaml
uv run --locked python scripts/run_baseline.py --smoke --limit 5 --config configs/phase5.yaml
```

モデルは約2.1GBです。準備済みなら最初のコマンドは検証・再利用します。
回答・実Prompt・取得全文と使用Context・設定・時間・Memoryは`data/runs/phase5/`へ保存します。
実測では1問約19〜29秒、検索とLLMの合計Peak RSS約2.45GiBでした（固定5問、読込を除く）。
動作成功は回答の正しさを意味しません。独立品質評価や最終比較は未実施です。
条件と実行結果は[`docs/phase5_baseline.md`](docs/phase5_baseline.md)を参照してください。
Ubuntu/GPU向けRuntimeの導入・実行は未確認です。

## Hybrid検索を使うBaseline RAG（Phase 6）

既存のBM25/Embedding Indexを等重みRRFで統合します。Calibration Answerable全225件で
事前に定めた9組を比較し、候補50件/方式・RRF定数20・最終Top-10を固定しました。
Unanswerable 209件は検索正解Metricから除外し、Evaluationでの調整は行っていません。
現在のBaseline CLIの既定Configは`configs/phase6.yaml`です。Qwenと生成Prompt・Token予算はPhase 5と共通です。

```powershell
uv run --locked python scripts/calibrate_retrieval.py
uv run --locked python scripts/search_corpus.py "who does the voice of plankton from spongebob" --kind hybrid
uv run --locked python scripts/run_baseline.py "who does the voice of plankton from spongebob"
uv run --locked python scripts/run_baseline.py --smoke --limit 5
```

準備済みのReport/Manifest/Configは同じByte列だけを再利用し、異なる内容で上書きしません。
HybridのSuccess@10はEmbeddingと同じ78.22%ですが、nDCG@10は0.5317でEmbeddingの0.5519を下回りました。
検索精度改善を示す結果ではありません。全条件・評価定義・実測・再現手順は
[`docs/phase6_hybrid.md`](docs/phase6_hybrid.md)を参照してください。
固定Development 5問で各1回の生成・保存が完了し、Gate 6を通過しました。
平均約56.96秒、合計Peak RSS約2.528GiB。全135 Tests成功、ruff問題なし。
回答品質の改善は未検証です。Phase 9で開発2例を書き換え、独立品質確認とUbuntu/GPU実行は後続作業です。

## 今後の研究工程

| Phase | 作業 | 状況 |
|---|---|---|
| 7 | 新テーマのProtocol・専用Prompt/Config・採点基準 | 完了。入力予算を確認、採点・生成0回 |
| 8 | 固定Trace、評価器、根拠順序と反復 | 完了。開発2件、Judge 9回、再開の追加Completion 0回 |
| 9 | 一回書換え、品質のExport/Import | AI採点委任に合わせた開発Gate通過。人手評価とはしない |
| 10 | Development予備実験 | 初回20問、測定修正、新規10問の実験/採点と事後検証を完了 |
| 11 | 日本語Dataset選定・対応、日英Calibrationと条件凍結 | 英語GPU検証済み。日本語Source選定/原QA取得済み、本文Corpus・実対応/検証と最終固定は未了。Gate未通過 |
| 12 | 日英の内部Evaluationと独立採点 | 未実施 |
| 13 | 言語別統計・日英比較・条件別分析、任意の対策 | 未着手 |
| 14 | 日英比較を含むICIAE原稿・投稿準備・卒論 | 未着手 |

詳細とGateは[ロードマップ](docs/research_roadmap.md)を参照してください。
実評価CLIと実出力を比較するMarkdown生成を実装しました。手順・既知の課題は[Phase 8記録](docs/phase8_order_evaluation.md)によります。
書換えと品質Export/ImportのCLIは[Phase 9記録](docs/phase9_answer_rewrite.md)を参照してください。新規Pilotと本実験は後続工程です。
[Phase 7の記録](docs/phase7_order_protocol.md)と[品質採点基準](docs/order_quality_rubric.md)を参照してください。
入力予算だけを確認するCLIは実行できます。新規の出力先を指定してください。

```powershell
uv run --locked python scripts/check_order_protocol.py --output-dir data/runs/phase7/your-preflight-run
```

旧研究/実装計画とDataset仕様は`docs/archive/`へ保存しました。今後は現行計画を使います。
ICIAEの通常初回締切は2026年11月20日のフルペーパーで、2027年1月8日は最終原稿締切です。
詳細は[公式投稿要領](https://www2.ia-engineers.org/iciae2027/paper-submission/)を参照してください。

## 開発環境の基本方針

このプロジェクトでは、Python本体、仮想環境、依存ライブラリをuvで管理します。

- Pythonに関係するプログラムやツールの実行には、原則として `uv run` を付ける
- ライブラリの追加には、原則として `pip install` ではなく `uv add` を使う
- `.venv` は各PCで作り、GitHubには保存しない
- `pyproject.toml` と `uv.lock` をGitHubで共有する

この方針により、ローカルPCと研究室PCで同じPython環境を再現します。

## 必要なツール

- Git
- uv

Windowsにuvをインストールする場合は、PowerShellで次を実行します。

```powershell
winget install --id=astral-sh.uv -e
```

インストール後はPowerShellを開き直し、次のコマンドで確認します。

```powershell
uv --version
```

## 初回セットアップ

GitHubからリポジトリを取得します。

```powershell
git clone https://github.com/hinattyamann/rag_research.git
cd rag_research
```

続いて、プロジェクトのルートディレクトリで環境を構築します。

```powershell
uv sync
```

`uv sync` は、主に次の処理を行います。

1. `.python-version` に指定されたPythonを確認または用意する
2. プロジェクト専用の仮想環境 `.venv` を作る
3. `uv.lock` に記録されたバージョンのライブラリをインストールする

`.venv` はこのPC専用の実体です。GitHubには保存せず、それぞれのPCで
`uv sync` を実行して作成します。

## Pythonプログラムやツールの実行

Pythonに関係するコマンドは、原則として先頭に `uv run` を付けます。

```powershell
# Pythonファイルを実行する
uv run python main.py

# Pythonモジュールを実行する
uv run python -m rag_research

# 自動テストを実行する
uv run pytest

# コードを検査する
uv run ruff check .
```

`uv run` を付けると、PC全体のPythonではなく、このプロジェクトの `.venv` にある
Pythonとライブラリが使用されます。

### `uv run` を付けないコマンド

Git、uv自身、PowerShellの一般的なコマンドには `uv run` を付けません。

```powershell
# Git操作
git status
git pull
git push

# uvによる環境管理
uv sync
uv add ライブラリ名
uv remove ライブラリ名

# PowerShellのファイル操作
Get-ChildItem
```

## ライブラリの追加・削除

### 通常のライブラリを追加する

実行時に必要なライブラリは `uv add` で追加します。

```powershell
uv add ライブラリ名
```

例えば、LangGraphを追加する場合は次のように実行します。

```powershell
uv add langgraph
```

このコマンドにより、次の処理がまとめて行われます。

1. ライブラリを `.venv` にインストールする
2. `pyproject.toml` に必要なライブラリとして記録する
3. `uv.lock` に正確なバージョンを記録する

### 開発用ライブラリを追加する

テストやコード検査など、開発時だけ使用するライブラリには `--dev` を付けます。

```powershell
uv add --dev ライブラリ名
```

例：

```powershell
uv add --dev pytest
uv add --dev ruff
```

### ライブラリを削除する

```powershell
uv remove ライブラリ名
```

ライブラリを追加または削除すると、通常は `pyproject.toml` と `uv.lock` が更新されます。
この2ファイルはコードと一緒にコミットしてください。

```powershell
git add pyproject.toml uv.lock
git commit -m "依存ライブラリを更新"
git push
```

## `pip install` を原則として使わない理由

`pip install` は現在の環境へライブラリをインストールしますが、プロジェクトの
`pyproject.toml` と `uv.lock` には自動的に記録されません。そのため、別のPCで
同じ環境を再現できなくなる可能性があります。

このプロジェクトでは、次のように使い分けます。

```text
ライブラリを追加する       → uv add ライブラリ名
Pythonプログラムを実行する → uv run python ...
環境を再構築する           → uv sync
```

`uv pip install` というコマンドもありますが、通常のプロジェクト開発では
依存関係を記録する `uv add` を優先します。

## 仮想環境の有効化について

次のコマンドで `.venv` を手動で有効化することもできます。

```powershell
.venv\Scripts\Activate.ps1
```

ただし、このプロジェクトでは有効化忘れや環境の取り違えを防ぐため、基本的に
手動で有効化せず `uv run` を使用します。

## 日常の作業手順

### 作業開始時

GitHub上の変更を取得し、Python環境を同期します。

```powershell
git pull --rebase
uv sync
```

### 作業中

必要なコマンドを `uv run` で実行します。

```powershell
uv run pytest
uv run ruff check .
```

### 作業終了時

変更内容を確認し、コミットしてGitHubへ送信します。

```powershell
git status
git add .
git commit -m "変更内容を表すメッセージ"
git push
```

## よくある間違い

### PC全体のPythonを実行してしまう

避ける操作：

```powershell
python main.py
```

推奨する操作：

```powershell
uv run python main.py
```

### `pip install` でライブラリを追加する

避ける操作：

```powershell
pip install langgraph
```

推奨する操作：

```powershell
uv add langgraph
```

### `.venv` をGitHubへ保存する

`.venv` は各PCで再作成するため、GitHubへ保存しません。`.gitignore` により
Gitの管理対象から除外されています。

### `uv.lock` を手作業で編集する

`uv.lock` はuvが管理するファイルです。直接編集せず、`uv add`、`uv remove`、
`uv sync` などのコマンドを通して更新します。

## 秘密情報

APIキーなどの秘密情報をコードや設定ファイルへ直接記載しないでください。
秘密情報が必要になった段階で、Git管理対象外の `.env` と、項目名のみを示す
`.env.example` を用意します。

2026年10月20日の[Ubuntu/CUDA検証と追加Calibration](docs/phase11_lab_validation.md)を完了。
20問/40候補のAI採点、完全比較12問、実行Health Gate通過。意味妥当性と分析規模が未確定でGate 11未通過。
最終凍結・Phase 12は未実施。再開時はロードマップと最新の実機検証記録を優先する。
