# 実験条件と各集合の役割

Mainは開発集合として日英20問ずつ、Calは調整に使わない追加確認として日英20問ずつ。英語CalのQA Sourceはdevelopment、日本語Calはcalibration。入力のqa_source、source_qa_split、provenanceの元Manifestで確認できる。未使用Evaluationの本文は含めない。

初回生成はQwen/Qwen2.5-3B-Instruct-GGUF Q4_K_M、評価/共通書換えはunsloth/Qwen3.5-9B-GGUF Q6_K。固定Revision、モデルHash、Sampler・Context・CUDA全層条件はprovenanceの各manifest.jsonとfrozen_filesのモデル/Runtime/Prompt設定を正本とする。モデルWeightsは同梱しない。

初回: Context4096、出力上限512、温度0、Seed42。補助: Context12288、Batch128、Threads6、温度0.2、Seed42、Top-k20/Top-p0.95/Min-p0、Presence penalty1.5、Reasoning予約4096、出力予約6144。実験のBudgetと停止規則は元Manifest、固定Release/Recovery/Cal登録を参照する。GPU Graph OFF・FA OFF・全層Offloadの実証は元解析resource_auditへ保存されている。

検索はBM25とmultilingual-e5-smallのHybrid、候補50、RRF定数60、Top-k5。Reference/Goldと通常検索の実使用文書はinputsで別Fieldに保持する。Referenceを生成やJudgeへ注入した設計ではない。

初回Aと実使用Context・文単位を固定し、元/逆/Shuffle3候補と元順序計5反復を比較する。originalは両群で共用し、原則9論理試行。重複順列はplan.duplicate_order_aliasesで省略する。試行ごとの再検索・A再生成・文再抽出・切詰め・同順序Cache代用は行わない。

Fは支持とされた固定文の割合。F>=0.7で採用、未満で一回書換え。F=nullの判断不能と、bare-refusal時のrewrite_once Actionを区別する。Bは元順序の同じ根拠/Aから一回だけ生成し、Judge Feedback/F/Goldを渡さず全方策で共用する。B失敗時はA保持で費用を残す。

外部AI品質Yは必須要点・重大な誤りなし・実使用文書による支持の3基準。Expectedは実使用文書だけで全文固定単位を評価する。条件/F/判断/段階を匿名採点時に遮蔽し、Main・Calそれぞれの日英全品質/Expected封印後に内部結果と結合した。基準全文とPrompt/Schemaはprovenanceとannotationsに同梱した。
