# 追加120問資料の受領と検証

2026年11月10日。原稿Branch paper/iciae2027、開始Commit9799076、未コミット変更なし。
origin Fetch後に原稿追跡先との差0/0を確認した。別Branchを自動Mergeせず、研究室の確定資料のみを取り込んだ。

## 取込元と保全

- 取込元: research/cal-extension-v1、7beb396febd2842248af53a8ec39eda9fc153153。
- 追加資料Tree: 0cc2339a73efff938db8766269ea7b9daeb32852。原稿Branchの取込後Treeと一致。
- 対象: materials/cal_extension_v1全文、追加Protocol/復旧仕様/進捗、Plan/Preflight/Statusの3Manifest。
- 独立取込Commit: abff9af「検証済みの追加120問資料を原稿ブランチへ取り込む」。
- 研究室Branchの古い原稿や研究用src/設定を取り込まず、初稿3の本文を改稿の出発点として保持した。
- 元80問資料Tree5fb236667f6e4411a730187dc1e6ce80f27c710f、出典監査Tree2e9bc4cdd1a6eeb97698d426e291a6b604023ebd、元公開成果は不変。

## オフライン検証

`uv run --no-project python -I papers/iciae2027/materials/cal_extension_v1/verify_collection.py --audit-open` がexit0。
Root inventory/bytes/SHA-256、3バッチの各510資料、選定120問、既存ID非重複、保存統合値と元QAの平均を確認。
各バッチの独立検証も全てpassed。ネットワーク・認証・元Run・GPUを使わない。

| Batch | 選定 | 主比較EN/JA | 論理試行 | 候補段階 | 採点Job |
|---|---:|---:|---:|---:|---:|
| 01 | 40 | 17/16 | 358 | 78 | 40 |
| 02 | 40 | 14/14 | 357 | 80 | 40 |
| 03 | 40 | 17/13 | 357 | 80 | 40 |
| 合計 | 120 | 48/43 | 1072 | 238 | 120 |

初回120成功、書換え118成功/日本語2失敗、未収集・未封印0。29主比較除外は全て根拠不足の回答拒否であり、感度0へ補完しない。
失敗書換え2問は比較可能であり、書換え失敗を理由に主比較から自動除外しない。
原文29件とbare_refusal_rewrite_once/再書換え要求の対応を独立確認した。

## 執筆判断

追加3バッチのみの統合は収集前Protocolで指定済み。旧Main/Calと合算した200問推定は行わない。
全選定200問、主比較148問（Main29/Cal28/Ext91）、既知A/B品質遷移、方策分母は区別する。
保存済み区間は再利用し、新しい推論・採点・区間推定は行わない。新規派生集計は保存ラベルによる記述分析である。
日本語Ext2問の参照本文未取得、Serving版不明、人手未確認、旧手順改訂・採点時期差も保持する。
日英本文更新と全頁確認は[初稿4の対応](draft4_revision_status.md)へ記録する。
