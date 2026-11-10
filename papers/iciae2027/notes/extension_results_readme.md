# 追加集合の原稿用照合集計

`manuscript/derive_extension_results.py` は封印済み追加3バッチを読み、`extension_results_v1.json`を作る。
原資料・ラベル・元区間は変更せず、推論、再採点、新しい区間推定は行わない。

```powershell
uv run python papers/iciae2027/manuscript/derive_extension_results.py --check
uv run pytest papers/iciae2027/manuscript/test_extension_results.py -q
```

順序所属の正本は各inputsのtrial_plan.order_groupであり、重複aliasとrepeat_2以降を含めない。
既存derive_order_effectsのValidatorを各バッチへ適用し、文書順、選択A/Bの本文Hash、保存Y、失敗時初回保持を検証する。
既存80問とのrecord ID・文書Group重複がないことも照合する。旧記述集計は変更しない。

## 表4の定義

主比較可能91問内の判断変動15問を、保存済みAI品質ラベルで排他的に分類する。

| 言語 | 比較可能 | 判断変動 | 同じ既知二値Y | 異なる二値Y | 未知Yを含む |
|---|---:|---:|---:|---:|---:|
| EN | 48 | 6 | 0 | 4 | 2 |
| JA | 43 | 9 | 1 | 6 | 2 |

未知が一つでもあれば未知分類を優先する。10異Yは改善10問ではなく、基準順序に応じた改善/悪化を含む。
同Yは文章の同一性や真の品質の完全な同一性を意味しない。費用範囲は観測経路の最小/最大で、CIではない。
判断一定でも未知Yがある問を運用結果から除かない。判断変動15問すべてでCall/Tokenは変動する。

表1/2/3/6は保存統合CSVと各バッチ方策表から生成し、この記述分類の分母と混同しない。
統合の主区間はpooled_new_extension.jsonに保存された文書Group Bootstrap（10,000回/Seed42/NumPy2.5.3）をそのまま使用する。
Batch別の値、出典、全文、採点来歴と元費用は元資料に保持する。
