# 論文本体

2026年11月10日、対話で合意した5項目を反映し、日英同内容の初稿5へ全面改稿した。[変更と検証](../notes/draft5_revision_status.md)を参照する。

| ファイル | 用途 |
|---|---|
| [iciae2027_manuscript_en.docx](iciae2027_manuscript_en.docx) | 公式テンプレートによる提出用英語版の正本 |
| [iciae2027_manuscript_ja.docx](iciae2027_manuscript_ja.docx) | 全本文に対応する理解用日本語版の正本 |

現在は両版7ページ、英語要旨217語、82対訳単位・7章・2図・6表・14文献。著者情報・教員確認・投稿は未完了。ページ番号は公式テンプレートに従い追加していない。

本文は英語100問・日本語100問を一つの固定評価器の実験として扱い、Main・Cal・Extの呼称を使わない。主比較可能なのは英語80問・日本語68問であり、段階的収集を結果確認後に統合した事後解析である。[統合集計の定義と再現](../notes/pooled_analysis_readme.md)と[結果JSON](../notes/pooled_results_v1.json)を参照する。元資料と旧集計は変更していない。

## 更新と確認

[draft_content.json](draft_content.json)が共通IDで日英を対応付けた本文入力、[build_draft.py](build_draft.py)がWord・図表の生成器である。日英の章構成・数値・条件・引用・主張の強さ・限界を同時に更新し、日本語版だけの補足や省略を加えない。Wordを直接編集した場合は生成入力も同期してから再生成する。

```powershell
uv run python papers/iciae2027/manuscript/derive_pooled_results.py --check
uv run --with python-docx python papers/iciae2027/manuscript/build_draft.py --build
uv run python -X utf8 -m pytest papers/iciae2027/manuscript -q
uv run ruff check .
```

図1・図2を意図して再描画する場合は--refresh-figuresを付ける。生成前に更新先Wordを閉じる。先に別ディレクトリで表示確認する場合は--output-dirを指定でき、日英DOCXと専用のdraft_build_manifest.jsonがそこへ出力される。原稿検査は環境変数ICIAE_DOCX_DIRとICIAE_BUILD_MANIFESTで、その作業用の一組も検査できる。

生成後はWord/PDFの全ページを表示し、本文・図表・段組・改ページ・文献を確認する。確認用PDF・PNGは内部QA用とし、提出は著者情報を確定した英語版から出力する。現在の[生成Manifest](../notes/draft_build_manifest.json)と[最終検証](../notes/draft5_validation_20261110.json)で正本のHashを追跡できる。

初稿4以前の到達点・旧集合別集計は[履歴](../notes/draft4_revision_status.md)として残す。[対話の合意事項](../notes/dialogue_revision_policy_20261110.md)と[構成](outline.md)は次の改稿時にも参照する。同じDOCXを複数PCで同時に編集せず、Commit・通常Push後に受取側でFetch・Pullする。
