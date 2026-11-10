# 原稿掲載用の図表

2026年11月11日の初稿7では、図題・表題を短い句にし、必要な定義・分母・単位だけを表の下の注記へ分けた。図のPNG/SVGと結果値は初稿6から変更していない。

- experimental_design_en/ja.png・svg（図1）: 固定入力、順序変更と反復、共通A/Bからの選択、品質・費用の比較と、採用閾値0.7を説明する。
- order_increment_en/ja.png・svg（図2）: 事後統合した英語80問・日本語68問の判断不一致増分と、日本語平均−英語平均の95%区間を対象問数とともに示す。

図2の正本は[pooled_results_v1.json](../notes/pooled_results_v1.json)。定義・事後解析の位置付け・区間の計算方法は[再現案内](../notes/pooled_analysis_readme.md)を参照する。元の集合別解析と掲載前の元成果は変更せず、Git履歴とmaterials/reportsで保持する。

生成処理は[build_draft.py](../manuscript/build_draft.py)の--refresh-figures。Wordへは1段幅85 mmのPNGを配置し、SVGを編集・再利用用に保持する。設計図の生成寸法は3.35×2.85インチ、結果図は3.35×2.1インチ。フォントや区間の判読性は日英全ページの表示で確認した。

掲載表は別の画像にせずWord表として生成する。表1=標本・数値設定、表2=開発診断と結果、表3=対象・順序感度、表4=方策品質、表5=全品質遷移と選択、表6=判断変動26問の影響、表7=具体例、表8=費用、表9=意味監査、表10=閾値感度。現在の[生成Manifest](../notes/draft_build_manifest.json)と[最終検証](../notes/draft7_validation_20261111.json)で原稿と数値を追跡できる。
