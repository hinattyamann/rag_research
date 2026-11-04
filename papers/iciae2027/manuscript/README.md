# 論文本体

ユーザー指定により、本文はWord形式で提出用英語版と理解用日本語版を必ず同時に並行作成する。

| ファイル名 | 用途 |
|---|---|
| `iciae2027_manuscript_en.docx` | 公式テンプレートを用いた提出用英語本文の正本 |
| `iciae2027_manuscript_ja.docx` | 全本文に対応する理解用日本語原稿の正本 |

2026年11月5日、両DOCXの初稿1を作成した。Word描画では各6ページ、英語要旨は196語。
研究室資料を受け取る前の段階であり、[到達点・残件](../notes/draft_status.md)を参照する。
従来の単一ファイル名 `iciae2027_manuscript.docx` は使用しない。

先に [構成案](outline.md) と [投稿条件](../notes/submission_requirements.md) を確認し、
[未編集の公式テンプレート](../templates/official/ICIAE2027_template.docx) を基に英語版と日本語版を同じ作業で作成する。
著者名・所属・責任著者を推測で埋めない。

章・節ごとに両版を更新し、章構成・数値・実験条件・図表番号・引用・主張の強さ・限界を照合してから完了とする。
追加実験の結果、教員の指摘、訂正も両方へ反映する。
日本語版は英語版と同じ内容の忠実な翻訳とする。自然な日本語に訳し、独自の補足・省略・別の説明を加えない。
ユーザーへの詳しい解説は会話または原稿外の執筆メモで行う。
日本語版のページ数・日本語フォント等の体裁は理解しやすさを優先し、英語版の提出条件と混同しない。

原稿のレビュー版を残す場合は `reviews/20261109/` のような日付付きサブフォルダへ複製し、
両版を一組で残し、正本とレビュー対象の対応・Commitを記録する。提出PDFは英語版から出力して `../submission/` へ保存する。
Wordの一時ロックファイルはGitへ追加しない。

## 更新用の入力と確認

[draft_content.json](draft_content.json)は64単位のIDで日英を対応付けた生成入力。
[build_draft.py](build_draft.py)は未編集の公式テンプレートを使い、本文と公開CSV由来の表・掲載図を両版へ反映する。
Word正本を直接編集したときは生成入力も同期し、同期前に再生成して手動編集を上書きしない。
生成前には対象のWord文書を閉じ、両版を同じ作業単位で更新する。

```powershell
uv run --with python-docx python papers/iciae2027/manuscript/build_draft.py --build
uv run pytest papers/iciae2027/manuscript/test_draft_artifacts.py -q
uv run ruff check papers/iciae2027/manuscript
```

テストは生成済みの実DOCXから本文・引用・全表セル・両版対応と元成果の不変を確認する。
意味の一致を機械検査だけで保証しない。翻訳を読み合わせ、更新後はWord/PDF描画と全ページの表示確認も行う。
実験・GPU推論・外部再採点はこの生成処理に含めない。
