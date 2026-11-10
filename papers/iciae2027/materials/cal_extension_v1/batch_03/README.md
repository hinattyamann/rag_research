# Cal拡張 batch_03 の確定執筆資料

選定40問（英語20/日本語20）。既存Main/Calと別の新規確認集合。
収集・採点の条件は固定v23、全文/採点は封印後に公開。欠測・拒否・判定不能・重複順列省略を区別する。

## 確認入口

`uv run --no-project python -I verify_materials.py --audit-open`

[質問別一覧](qa_summary.csv)のinput_pathから質問/Reference/実使用根拠全文/A/Bへ移れる。
[順序・反復](trials.jsonl)、[方策・費用](policy_outcomes.csv)、[元解析](analysis/cal.private.json)、[図表](published_results/)、[具体例](cases/index.json)。
[条件/封印](provenance/cal/protocol.json)、[採点来歴](provenance/annotation_jobs/)、[元ファイルHash](source_manifest.json)。

## 主比較

- en: 選定20、完全比較17、増分0.023529411764705882、95%区間[0.0, 0.07058823529411766]。
- ja: 選定20、完全比較13、増分0.06153846153846154、95%区間[0.0, 0.15384615384615385]。

## 限界と帰属

Fは固定文の支持率で正答率ではない。AIラベルは人手正解ではなく、モデル履歴の独立性も仮定しない。
Bootstrapは元実装/NumPy2.5.3/Seed42/10000回の値と元資料を保持し、別RNGで再現したと偽らない。
閾値/Prompt/上限を結果に応じて調整していない。新集合は最終の既知長さ欠測規則・引用選択手順を事前固定した。元Main/Calの途中変更と時期差は残る。
CLIモデルは指定gpt-6.1-sol/high、厳密なServing Snapshotは未特定。固定v23の旧非支持87.5%/旧90%基準未達は維持する。
公開経路表のbaseline_missingは重複省略も含む旧列。実際の初回失敗はcollection_cost.csv、状態別はpolicy_state/alias_ofを用いる。
原文の出典/本文Hash/変換範囲は各inputsのsource_metadata。CLAPNQ注釈Apache-2.0、NQ/Wikipedia英語本文CC BY-SA3.0、日本語注釈Apache-2.0/本文CC BY-SA4.0を区別する。
Wikipedia contributors、PrimeQA、Yusuke Oda/Baobabへ帰属する。抜粋/既存Passage抽出・JSON整形を行い、本文の意味は変更していない。派生本文は同じCC BY-SA条件を維持する。
英語はTitle由来URLであり、元oldidを推測しない。日本語は保存oldid/Revision/取得記録を保持。未取得参照本文は補作しない。
[ライセンス/NOTICE](licenses/source_notices.json)。採点Rubric/Schema/匿名対応/形式修正の証拠も同梱。全Corpus・モデル・認証・巨大イベントログは含まない。
収集/採点の費用はanalysisとprovenanceへ保持。source_manifestのnew_inference_calls=0は抽出処理が再生成しなかった意味で、新実験が0Callという意味ではない。
検証器は資料内だけを読む。原Run/GPU/ネットワーク/認証は不要。研究室の原稿は変更せず、著者の照合・日英更新・教員確認・提出は別工程。
