# 保存済み順序試行と選択品質の事後記述集計

2026年11月6日。初稿レビュー後、既存80問から作成した追加の記述集計である。
主解析・既存区間・候補回答・AIラベルは変更せず、新規推論/再採点/区間推定を行っていない。

Repository Rootで再生成/確認する:

```powershell
uv run --no-project python -I papers/iciae2027/manuscript/derive_order_effects.py
uv run --no-project python -I papers/iciae2027/manuscript/derive_order_effects.py --check
uv run pytest papers/iciae2027/manuscript/test_order_effects.py papers/iciae2027/manuscript/test_case_excerpts.py -q
```

主対象は元から比較可能な57問で、80問からの除外23問は別に記録する。
順序群は各inputs/*.jsonのtrial_plan.order_groupを正本とする。共有originalは1回だけ数え、反復・重複順列aliasを数えない。
trials.jsonlの補助的なin_order_group/in_repeat_groupは正本と390/395件不一致であり、抽出条件に使わない。
元資料を改変して直したのではなく、正本の計画と実文書順を照合して回避した。既存資料検証器もtrial_planを用いている。

| 区分 | 全選定 | 比較可能 | 判断変化 | 同じ二値Y | Yも変化 | 判断変化中のY不明 |
|---|---:|---:|---:|---:|---:|---:|
| Main EN | 20 | 16 | 3 | 1 | 2 | 0 |
| Main JA | 20 | 13 | 1 | 1 | 0 | 0 |
| Cal EN | 20 | 16 | 5 | 4 | 1 | 0 |
| Cal JA | 20 | 12 | 2 | 1 | 1 | 0 |

最後の3列は判断変化のある質問内の排他的分類である。一つでも選択Yが不明なら不明を優先する。
Cal ENには判断変化がなく選択Y不明の別の1問があり、全57問の品質不明が0という意味ではない。
失敗書換えでAへ戻った場合は実際のAのYを使い、B成功・改善・有害へ補完しない。
Y変化4問は順序に応じた良化/悪化の両方向を含み、改善4問という意味ではない。
7/11と4/11という合計は記述的な件数の和であり、Main/Calを統合した効果推定や検定ではない。

[order_effects_v1.json](order_effects_v1.json)は84元ファイルのHash、全80問の対応、除外/未知/失敗/alias、各順序経路の既知費用と範囲を保持する。
判断変化11問すべてで記録Callと入出力Tokenが変動する。蛾/蝶の例の順序内範囲は5〜6 Call、31514〜40112 Tokenである。
これは単一QAの観測順序経路の最小/最大で、信頼区間、全収集費用、金銭費用、実配備遅延ではない。範囲外の中断要求の未知費用も0としない。

[case_excerpts_v1.json](case_excerpts_v1.json)は、日本語例case_02の実使用根拠/A/Bの短い原文と英訳、元入力Hash、文字区間を保持する。
引用箇所はGoldや後日取得本文ではない。Bが支持のある別箇所ではなく冒頭Passageを引用したずれも残す。
付属の原文照合テストは引用と保存Labelの不変を確認するもので、人手正解の検証ではない。
