# rag_research

評価駆動型自己制御RAGによる回答信頼性向上手法を検証する卒業研究プロジェクトです。

研究内容と実装方針は、次の文書を参照してください。

- `docs/rag_research_plan.md`
- `docs/rag_implementation_plan.md`

## 必要な環境

- Git
- uv

Python 3.12とプロジェクトの依存ライブラリはuvで管理します。

## 初回セットアップ

リポジトリを取得した後、ルートディレクトリで次を実行します。

```powershell
uv sync
```

このコマンドにより、必要に応じてPython 3.12が用意され、プロジェクト専用の
仮想環境 `.venv` と依存ライブラリが作成されます。

## 動作確認

```powershell
uv run pytest
uv run ruff check .
```

## 日常のGit操作

作業開始前にGitHub上の変更を取得します。

```powershell
git pull --rebase
```

作業後は変更内容を確認し、コミットしてGitHubへ送信します。

```powershell
git status
git add .
git commit -m "変更内容を表すメッセージ"
git push
```

## 依存ライブラリの追加

通常の依存ライブラリは次の形式で追加します。

```powershell
uv add ライブラリ名
```

開発時だけ使用するライブラリは次の形式で追加します。

```powershell
uv add --dev ライブラリ名
```

`pyproject.toml` と `uv.lock` はGitHubで共有します。`.venv` は各PCで生成するため、
GitHubには保存しません。

## 秘密情報

APIキーなどの秘密情報をコードや設定ファイルへ直接記載しないでください。
秘密情報が必要になった段階で、Git管理対象外の `.env` と、項目名のみを示す
`.env.example` を用意します。

