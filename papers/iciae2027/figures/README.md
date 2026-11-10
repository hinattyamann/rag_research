# 原稿掲載用の図表

2026年11月10日の初稿5では、固定評価器による全選定200問を一つの評価実験として扱う本文に合わせ、掲載図を日英同時に更新した。

- experimental_design_en/ja.png・svg（図1）: 固定入力、順序変更と反復、共通A/Bからの選択、品質・費用の比較を説明する。
- order_increment_en/ja.png・svg（図2）: 事後統合した英語80問・日本語68問の判断不一致増分と、日本語平均−英語平均の95%区間を示す。

図2の正本は[pooled_results_v1.json](../notes/pooled_results_v1.json)。定義・事後解析の位置付け・区間の計算方法は[再現案内](../notes/pooled_analysis_readme.md)を参照する。元の集合別解析と掲載前の元成果は変更せず、Git履歴とmaterials/reportsで保持する。

生成処理は[build_draft.py](../manuscript/build_draft.py)の--refresh-figures。Wordへは1段幅85 mmのPNGを配置し、SVGを編集・再利用用に保持する。設計図の生成寸法は3.35×2.85インチ、結果図は3.35×2.1インチ。フォントや区間の判読性は日英全ページの表示で確認した。

掲載表は別の画像にせずWord表として生成する。表1=開発診断、表2=順序感度、表3=方策品質、表4=品質遷移と選択、表5=具体例、表6=費用。現在の[生成Manifest](../notes/draft_build_manifest.json)と[最終検証](../notes/draft5_validation_20261110.json)で原稿と数値を追跡できる。
