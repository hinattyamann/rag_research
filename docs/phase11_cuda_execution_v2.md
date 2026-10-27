# Phase11 CUDA実行契約 v2：Flash Attention OFFの切分け

2026年10月27日。Phase11の自律継続Protocol v3に接続する、別Versionの実行条件である。Gate11未通過、Phase12は開始しない。

v27は固定Graph OFFビルドでも73件目で応答前切断となり、同一PID・時刻のCUDA同期abortとHost watchdog/Xid8を記録した。72応答・未知1・未試行17を保存し、不採用とする。特定kernelやDriverを根本原因と断定しない。詳細は[正式診断](../data/manifests/phase11_v27_semantic_disconnect_diagnosis_v1.json)に固定した。

実ログではFlash Attentionがautoからenabledになっていた。次のv28は同じ固定Source・ビルド・Model・Prompt15・共通reasoning4096・batch/ubatch128を保ち、Flash Attentionを明示offにする。計算経路を変えてHealthと意味への影響を検証する仮説であり、修復成功の保証ではない。checkpoint・cache・環境変数・OS・Driverはこの変更軸に含めない。

`execution`の旧4項目に、`version: cuda-execution-v2`と`flash_attention: off`だけを加える。旧契約と新契約を厳密に区別し、新契約の欠落・余剰項目・別値を拒否する。実行時には`--flash-attn off`を明示し、command・execution・検証結果をSessionへ保存する。Context実値と全層CUDAの既存検査も維持する。

固定Sourceでは明示disabledが`flash_attn=false`かつ`auto_fa=false`を設定するため、auto resolverの解決ログは出ない。実contextログの`flash_attn = disabled`を要求し、auto/enabledや有効化ログとの矛盾を拒否する。起動検査を通る前に推論を開始しない。ログの不存在を成功とみなさない。

この契約を実装するCore2ファイルのHashと、executionを含むSampler descriptorが変わる。Core94のファイル数が同じでも旧Byte同一とは扱わず、新候補Identityへ結ぶ。Model・Runtimeビルド・Prompt・Schemaの同一性と、全入力・Expected・基準の不変を別々に検査する。

新出力前に各Runの有限Planを共有v3 Guardへ登録する。専用固定CommitのCheckoutで、生成0の全90入力・資源確認、新形式10（意図したlegacy不合格1とstrict9）、因果NS2、帰属C2、日英Rewrite2と全文品質、全90完全回帰、新鮮な元Known84を順に検証する。形式・意味・Healthの旧実績を新契約へ無条件に流用しない。各段階の失敗・未知・未試行・実費は保存し、未知要求の再送や同条件を成功まで反復する操作は行わない。

元Knownの支持Recall・非支持Specificity各0.90、最低被覆、Health、全固定文と全分母、F0.7、順序変更・同一順序反復、一回書換え、未使用性と両言語全採点封印を維持する。実Known採用後だけ元Main・別予約Calへ進み、実測から最終条件・Validator・Manifest・Hashを固定する。

v27の返却72件にはC–NS混同と理由の過剰な範囲拡張もある。Runtimeの切分けだけで意味上の問題が解消したとは扱わず、Expectedや基準を変更して合格を作らない。支援AIのユーザー申告設定「6.1 Sol 極高」は研究用Modelとは別に記録し、厳密識別子不明・human_reviewed=false・実履歴隔離なしを保持する。
