# Phase11 v29: 研究Model変更候補の事前登録

作成日: 2026-10-27 JST。[正式Manifest](../data/manifests/phase11_semantic_v29_preregistration_v1.json) SHA `fa4f54ef17e7a4104d5b3a818f27a6409980af9ba0f5b5e414e888d92f044794` を発行済み。新Native0、候補採用・Gate11は未達。独立出版確認後の固定Commitと実再現・実測結果は工程正本・日誌へ追記する。

v28はGraph OFFかつFlash Attention offでも48試行・47返却・未知1でCUDA同期abortとなった。元の90要求の精度はnull、Known17は不適格のまま保存する。異なるModelの計算経路・量子化・資源使用を対照として調べるため、次の別候補を登録する。特定kernelの原因や修復成功は主張しない。

- Model: Qwen/Qwen3-8B-GGUF、revision `7c41481f57cb95916b40956ab2f0b139b296d974`、Q4_K_M、apache2。既存実物5,027,783,488B、SHA `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`。Rootの新Identity構築で一度全Hashを照合した。
- 候補ID: `7d35156207fb6d4ef520412c43036d701c104b18145c13455a56c6e54d64f008`。v28からのIdentity変更はModel componentのみ。Core94、固定b11433/CUDA12.9 Graph OFF Runtime、FAoff execution-v2、Prompt15、Sampler、Schema、共通reasoning4096、output6144、context12288、batch/ubatch128を維持する。
- Model由来の別metadata契約: `<think>`151667、`</think>`151668、block36、全GPU offload37層。GGUF metadataの確認だけでは実行証拠にせず、新serverのtokenize/render/round-trip/全層startup/FAoffを照合する。旧9Bのtoken248069・33層・11witnessは再利用しない。
- 元の全39QA・45固定文・78条件・90Callを不変に保つ。全質問・初回回答・全固定文・根拠ID/Title/本文を保持し、元/逆の提示順だけを操作する。Gold・Expectedは推論payloadへ含めない。過去8B-v3の4条件2/4不合格は保存し、旧出力を採用証拠へ再利用しない。

各Runは新出力前に専用固定Commit Checkoutと共有v3 Guard・Root絶対ledgerへ別登録する。個別HTTP timeout1200秒、監視5秒、Retry0、未知再送0。以下はRunごとの最大値でありGoal全体の停止上限ではない。

| 段階 | Native最大 | 壁上限秒 | 検証するもの |
| --- | ---: | ---: | --- |
| 新Tokenizer生成0 | 0 | 1800 | 人工10入力とタグ、計11witnessを実serverで新規保存 |
| 全90入力生成0 | 0 | 1800 | 省略しない全90payloadのtoken/context/資源・全GPU/FAoff |
| 新形式 | 10 | 3000 | 同じ人工Strict9＋意図したlegacy対照1。自身Sessionで11witnessを再捕捉 |
| 日英因果NS | 2 | 3000 | 因果関係の欠落を支持・明示反対と混同しない |
| 帰属C元逆 | 2 | 3000 | Council c4の全文・全7文・元逆を保持し両Cと理由の範囲を確認 |
| 日英一回書換え | 2 | 1800 | 固定の人工2入力、全回答/根拠の新AI品質・費用評価を封印 |
| 全意味回帰 | 90 | 22720 | 全39/45/78/90、全reason・保存thinking・Health・意味・費用を監査 |

時間見積りはv28の返却47要求の実HTTP2567.091079秒を47で割った偏ったproxyをCall数に掛ける。未知48の10.641596秒はその平均から除外するが累積費用に含める。新8Bの速度保証・旧90完走実測とは扱わない。生成0にもstartup/CPU/資源・監査費用があり、Native0を総費用0と記録しない。形式だけreasoning128/output512であり、意味/書換え4096を変更しない。

人工形式専用configはsemantic configからdiagnostics参照と用途metadataだけを変え、同Model/Runtime/Sampler/Prompt/Identity/token契約を厳密比較する。既存Guardの全診断domain規則を迂回せず、全90生成0は元semantic configで独立実行する。各次段のPlanは前段のRoot終端認可・実証明書をHash結合した後だけ生成する。

実験中は既存Handle、Journal、監視ログを確認し重複起動しない。実行中Checkoutを編集・Pullせず、通常失敗ではそのRunを停止・保全して原因に対応する別候補へ進む。全90不完了、unknown、Health不良、意味基準未達では採用しない。未知・誤りの再抽選、QA補充、Expected/閾値の変更はしない。driver/OS/security変更、GPU reset/reboot、他者process終了、有料外部API切替えは自動実施しない。

全90の実採用後だけ、新しいKnown専用生成0→元15QA・42文・30条件・84Callへ進む。支持Recall・非支持Specificity各0.90以上、最低被覆・各Group数、全文・全固定文・全分母・Healthを維持する。v28用Known17の未実行準備は不適格のまま残し、次候補の別Versionを整合させる。Mainは元選定日英各20、Calは別予約日英各20とし、両言語の全匿名品質/全Expectedを封印してから内部結果を照合する。F閾値0.7、同一順反復・順序変更、一回書換え、未使用/非重複Group、Evaluation本文を調整に使わない条件を維持する。

採点者はCodex AI、human_reviewed=false。ユーザー申告の支援AI設定6.1 Sol極高と厳密な提供Model ID取得不可/null、実際の履歴隔離を正直に記録する。これは研究Model8Bへの変更と別の設定である。Main/Cal実証、独立品質/費用、実測N・統計・資源・停止/欠測規則、実最終Validator・Manifest/HashがそろうまでGoalを完了しない。Phase12を開始しない。
