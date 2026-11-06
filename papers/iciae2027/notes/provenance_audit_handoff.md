# 出典・再現性追加調査の引継ぎ

2026-11-06。`origin/paper/iciae2027`の基点`aff72fd74c1e2e5b8561675573b5534fbea6006c`から、独立Worktree/Branch `paper/iciae2027-provenance-audit-v1`で実施。
元main/固定実験Checkout/日英DOCX/既存Label/元主結果と区間/確定資料fixed_v23_v1を変更せず、新規研究推論0・再採点0。実験サービスは開始時inactive/MainPID0で、停止や再開操作はしていない。

## 取込元と資料

取込元は`origin/paper/iciae2027-provenance-audit-v1`。執筆Branchが基点から変わっていない場合だけ、同じ成果を`paper/iciae2027`にも通常Pushする。最終CommitとPush先は終了報告を参照。

資料は`papers/iciae2027/materials/provenance_audit_v1/`。[README](../materials/provenance_audit_v1/README.md)から証拠・表・日英記述案へ移れる。確定済み80問資料はTree `5fb236667f6e4411a730187dc1e6ce80f27c710f`のまま保持しており、そのmissing_information.jsonを書き換えていない。

Repository Rootから、ノートPCでも実行する:

```bash
uv run --no-project python -I papers/iciae2027/materials/provenance_audit_v1/verify_audit.py --audit-open
uv run --no-project python -I papers/iciae2027/materials/fixed_v23_v1/verify_materials.py --audit-open
```

どちらも元Run/認証/GPU/ネットワーク不要。追加資料の検証は補足フォルダ内のファイルだけを読む。検証成功は残る未取得情報の解決ではない。

## 回復と未解決

1. **日本語QA857**: 当時のHTTP200/空の履歴応答を回復。現在のPage5273510の履歴開始はCutoff後で、2026年7月の記事移動を公開ログから追跡した。旧Page56523のRevision98057227（2023-11-21）の本文を今回補足取得した。当時の入力にはなく、当時の描画応答との同一性は不明。保存Reference全文も逐語一致せず、確認できた部分引用だけを示した。実使用根拠5件・A/B・採点・主比較対象状態は保持。
2. **外部採点**: 対象84 JobのCLI/Sessionを全件確認。当時CLI `0.164.0-alpha.11.1`、指定モデル`gpt-6.1-sol`/effort `high`を回復。クライアント記録と厳密なServing Snapshotは区別し、実Serving版IDは未特定。「サービスが非公開」とは断定しない。Job別の匿名Packet/QA・段階・Hash/イベント位置を保存。
3. **英語版対応**: 選定40問の元QA文書URLは36件同定、4件は元example_idが保存original_documentsにない。対象222 Passageでは199件に完全一致本文を持つ上流文書の版候補があり、23件は確認範囲で候補なし。Corpus生成時の直接対応記録がなく、厳密なCorpus版同定は0件。数字やTitleから補完しない。

英語の掲載候補case_01/case_03/case_04はenglish_case_passages.jsonから該当Passageへ進める。元Dataset版/本文Hashによる再現と、Wikipedia版を厳密に同定することを混同しない。

本文の加筆には[日英文案](../materials/provenance_audit_v1/paper_wording_en_ja.md)を使用できる。原稿は日英同内容で更新し、今回取得した本文で過去のReference/採点や結果を訂正しない。著者確認・文献精読・人手/教員確認・投稿は別工程。

## ノートPCのCodexへ渡す文

Git状態・Branch・remote・追跡先を確認してoriginをFetchし、履歴差分を確認してください。未完成変更を保全し、安全に早送りできる場合だけ更新してください。取込元はorigin/paper/iciae2027-provenance-audit-v1、最終Commitは研究室の終了報告参照。資料はpapers/iciae2027/materials/provenance_audit_v1/です。READMEとfindings.jsonを読み、上記2検証を実行し、回復情報と未解決を区別して日英原稿へ反映してください。DOCXの両PC同時編集は避け、候補oldidを確定版や今回回復本文を当時の実験入力として扱わないでください。
