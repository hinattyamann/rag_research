# 研究室PCからノートPCへの資料引継ぎ

2026-11-06。既存固定v23 Main/Calの80選定QAを、元データの上書き・新規推論・再採点なしで抽出した。
論文本体の日英DOCX、元main、固定実験Checkoutは変更していない。

## 取込元と検証入口

取込元Branchは `origin/paper/iciae2027-materials-v1`。執筆Branchが開始時の基点から変わっていなければ同じ成果を `paper/iciae2027` へ通常Pushする。
資料本体のGit再取得・検証済みCommitは `7655c6b9852c7b7a8300601872e7256743df887f`、資料Treeは `5fb236667f6e4411a730187dc1e6ce80f27c710f`。この案内・検証記録を追加した最終取込Commitは終了報告を参照する。資料Treeは同一のまま保持する。

ノート側では未コミット変更と現在Branch・remote・追跡先を確認し、`git fetch origin`後の履歴差分を確認する。
未変更かつリモートだけが先行していれば `git pull --ff-only`。分岐や未完成変更があれば保全し、自動Merge/Rebase/force pushで解決しない。
DOCXは両PCで同時編集しない。

検証コマンド（Repository Rootから）:

```bash
uv run --no-project python -I papers/iciae2027/materials/fixed_v23_v1/verify_materials.py --audit-open
```

資料だけを別の場所へ移しても、同じPython標準ライブラリの検証が動く。
`--audit-open`は資料外へのデータ読取りとSocketアクセスを拒否する。元Runのパス文字列は歴史的来歴であり、開かない。

資料索引: [materials/fixed_v23_v1/README.md](../materials/fixed_v23_v1/README.md)

## 対応・分母・照合

- Main/en20、Main/ja20、Cal/en20、Cal/ja20を全て保持。主比較可能数は16/13/16/12。
- 初回A成功79、書換えB成功77、匿名品質候補156・固定文注釈460。
- 元の全706予定Trial（original共用・重複順列5省略・初回欠測1問は計画なし）。
- 方策880枠中、実記録864・初回欠測で未実施11・重複省略5。存在しない実行/不明Y/費用を0へ補完しない。
- F/閾値/Action/A-B選択/Y/改善見逃し・悪化/費用をQA内で結合した。
- 主増分・全品質/費用CSV・意味監査・閾値感度を元公開値と照合。Bootstrap CIはNumPy2.5.3/Seed42/10000回の元実装結果を保持し、別RNGで再現したと偽らない。
- 公開CSVのbaseline_missingにはshuffle重複省略も含まれる。元表は変更せず、新しいpolicy_state/alias_ofで初回失敗と区別した。

## 説明例

結果閲覧後の、条件を満たす辞書順先頭という規則で選んだ。説明例から頻度を推定しない。

| Case | 元ID/由来 | 型 |
|---|---|---|
| case_01 | Cal/en `clapnq:c508d78:train:6842134809914363415:answerable` | 順序で判断が変わり、A/B品質も異なる |
| case_02 | Cal/ja `whrja:02e85c8:answered:240` | 順序で判断が変わり、A/B品質も異なる |
| case_03 | Cal/en `clapnq:c508d78:train:-5607690022829878056:answerable` | 判断は変わるがA/BのYは同じ |
| case_04 | Cal/en `clapnq:c508d78:train:-588553238820942603:answerable` | 拒否・固定文なしで主比較対象外 |

各CaseのMarkdown/JSONから、質問・実使用原文・F/判断・A/B・Y・引用・QA別費用・元ファイルHashへ移動できる。
原baseline/trace/summary/rewriteの必要コピーもprovenanceに保存した。

## 利用条件と不足情報

CLAPNQ注釈のApache-2.0、NQ/Wikipedia本文のCC BY-SA 3.0、日本語注釈のApache-2.0とWikipedia本文のCC BY-SA 4.0を分け、URL/Revision/Title/本文Hash・帰属/変更表示を同梱した。Qwen3BのResearch Licenseも元文書を保存し、モデルWeightsを配布していない。

元から未取得の情報は[missing_information.json](../materials/fixed_v23_v1/missing_information.json)へ明記した。
Main日本語QA857の参照元記事本文1件、英語の元Wikipedia oldid、実採点Serving Model IDは補完していない。
保存済み実験の照合は資料内で完結するが、元から未取得の本文まで確認できるとは主張しない。
著者情報確認・関連研究全本文の精読・人手確認・教員確認・提出は残件。

## 次の作業

1. ノートPCでGit更新後に同じ検証コマンドを実行し、資料の数値・原文・限界を日英初稿へ同内容で反映する。
2. 著者情報と出典本文を確認し、原稿の図表/引用/主張を教員へレビュー依頼する。
3. 追加実験は別Protocol/Branchとして管理し、既存80問の結果へ混ぜない。

## Gitから取得し直したコピーでの実確認

GitHubから新規HTTPS Cloneし、資料ディレクトリだけをgit archiveで取得したコピーで、Python標準ライブラリ・資料外データ読取り禁止・通信禁止の検証に通過した。1043ファイルのHash、全80 QA、706 Trial、156候補段階対応、84採点Job、880方策枠（実記録864）、4具体例、元表との数値一致を確認。追加で内部引用2070件の原文一致を照合した。詳細は[検証記録](materials_validation_20261106.json)。

12反証Test/5.79秒・Ruff成功。元科学的記録2737ファイルは抽出前後不変、抽出に読んだ2627 SourceのHashもGit再取得後に再照合して不変。mainは5b866a9のまま、新規推論/再採点0。残る元資料不足は上記missing_information.jsonに記載した。
