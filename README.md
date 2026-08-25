# rag_research

評価駆動型自己制御RAGによる回答信頼性向上手法を検証する卒業研究プロジェクトです。

研究内容と実装方針は、次の文書を参照してください。

- `docs/rag_research_plan.md`
- `docs/rag_implementation_plan.md`
- `docs/jdocqa_dataset_guide.md`

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
