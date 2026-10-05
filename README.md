# rag_research

評価駆動型自己制御RAGによる回答信頼性向上手法を検証する卒業研究プロジェクトです。

研究内容と実装方針は、次の文書を参照してください。

- `docs/rag_research_plan.md`
- `docs/rag_implementation_plan.md`
- `docs/clapnq_dataset_guide.md`

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
