# Phase11 自律継続Protocol v3と新Runtime・意味候補

2026年10月26日JST。[詳細要件](phase11_lab_weekend_goal.md)に基づく新規作業。
Gate11未通過、Main/Calibration/最終凍結は未実施、Phase12は開始しない。

## 引継ぎと生成0の確認

開始時はmain/50374e81f47a3683ad4edbf98678fec2478e4eef、origin/main。
Fetch完了後の履歴差は0/0、未コミット変更なし。Host側のProcess/GPU/Lockを確認し、
LLM/実験プロセスがないことを記録した。このチャットのGoalはactiveで、旧チャットのGoalは起動していない。
起動証拠は`data/runs/lab/phase11-startup-audit-v3/`、全資産照合は
`data/manifests/phase11_runtime_assets_audit_v2.json`と同名`.sha256`に結ぶ。

全6,761照合のうち6,759一致。欠落2件は旧Phase10不採用Qwen2.5-7Bの分割GGUFで、
現行入力を妨げない。現行Model/Runtime/Assets、Index/Embedding payload、v10関連証拠は一致。
旧Run等5,818ファイル640,340,713 bytesは別コピーとHash一致を検証し、Lock121件は未保持だった。
旧実験は再生成しない。旧909試行・未知3、v10不採用、非支持14/16=87.5%、
未試行28/旧未使用枠は過去の事実として保全する。

## 資源Protocolと実効Guard

`configs/phase11_autonomy_v3.json`、`experiments/phase11_autonomy.py`、
`scripts/phase11_autonomy.py`を別Versionとして使う。旧188回/4時間/候補1個の入口は変更しない。
新Protocolは全体の候補数・時間・Calls上限を置かず、各Runに有限な予算を必須にする。
仮説、変更、対象ID/QA/文/条件数、必要Calls/Token/時間、個別timeout、監視、停止/再開方法を
出力前に登録し、固定Commitと実行Config/Source/Model/Runtime/Prompt/Sampler/SchemaのHashへ結ぶ。
新台帳は`data/runs/development_screening/phase11-autonomy-v3/`へ累積する。

登録したプロセスだけにNative Guardのcontextを渡す。`/completion`送信前にCallを永続予約し、
Call数・timeout・出力Token上限を検査する。未知/失敗を成功や0費用にせず保存し、
同じ条件をRun名だけ変えて再抽選することも拒否する。外側の監視はProcess/Journal/資源を1〜60秒間隔で確認する。
有限timeoutに達した場合は自ら起動したProcess群だけを停止し、Raw/Log/未知/消費を保全する。
電力単価が不明なら金額を捏造せずnull、外部従量課金APIの使用は0として区別する。

Known→Main→Cal→Freezeでは、共通の`autonomy_protocol_version`、Protocol File Hash、
`candidate_identity_sha256`を照合する。支持Recall/非支持Specificity各0.90と最低被覆は
`support-binary-v2`のまま。Main/Calの旧1660枠は旧経路へ残し、新枠は結果前にHash固定した
有限の算定specへ結ぶ。全ID/全固定文/全分母・5QA単位・失敗時停止・補充なしは維持する。

`run_phase11_bilingual_collection_v3.py`は、各言語の初回生成4 Sessionと内部評価4 Sessionを
同じ固定条件で順次進める。5QAの正常終了でGoal全体を終了せず、実際のHealth障害は保存して停止する。
収集の終了は採用ではなく、両言語の全匿名品質/Expected封印後の意味・品質・費用照合と実証明書が別途必要。

## Runtime仮説と変更範囲

固定llama.cpp Source `50569eb87df530daff11afda229ceb9ab8e6cae8`から
`GGML_CUDA_GRAPHS=OFF`の隔離Runtimeをビルドする。Graphが根本原因とは断定しない。
配布版からのローカルCUDA12.9再ビルド・Architecture/Compiler差も条件差として保存する。
Driver/OS設定/GPU Reset/再起動は行わない。

Source Archive SHA256は`10af4d51ee5c29566e1f2899752d12ea41004554ceff7a91ca931b0ace48bc93`。
初回ビルドは、Source Archive内のCMakeが親RepositoryのGit情報を拾い、表示Commitが
誤って50374e8になったため保全停止した。生成0、費用245.035230秒。
変更版v2へ`LLAMA_BUILD_COMMIT`/`LLAMA_BUILD_NUMBER`の明示を事前登録し、
実Sourceの全3,689ファイルと旧保存12 Sourceの一致を確認して再ビルドした。
旧部分Build/Logを上書きせず、変更版のログを`data/runs/runtime_build/phase11-cuda-graph-off-v2/`へ残す。

変更版Buildは619.089007秒で完了し、初回停止分を含め864.124237秒・Native0/外部API0、電気代はnull。
実`--version`はbuild11433/固定50569eb87df530daff11afda229ceb9ab8e6cae8、`--list-devices`でCUDA0を確認した。
全28RuntimeFile/3689Sourceと144 CUDA compile unitを照合し、Graph macro不在を確認。
結果は`data/manifests/phase11_cuda_graph_off_runtime_result_v1.json`と同名`.sha256`。
生成0の成功であり、CUDA障害の修復・意味採用はまだ主張しない。

順番は新Runtimeの生成0全入力/全層CUDA→2 Smoke→新形式10 Call→日英意味診断70 Call。
Smokeはv10停止入力のCamp David逆c5と暖鋒元c2で、全文/文書を保ち局所IDだけ通常処理と同じc1へ写す。
`configs/phase11_runtime_smoke_plan_v3.json`へ元入力Hash/対象2件を保存した。
Smoke成功をCUDA根本原因解消や意味採用と呼ばない。

## 意味候補v21と公平性

`phase11_semantic_candidate_v21.yaml`はQwen3.5-9B Q6_K、温度0.2、推論4096、
Context12288/判定出力6144などを維持し、新RuntimeとPrompt v12へ分ける。
一般的なSource→Targetの詳細監査を短い順序へ整理し、各Category/列挙要素/関係の正の根拠、
別事象を結ぶ未記載の因果、表の見出しと値の対応を確認させる。
診断例の固有名/ID/正解Labelは指示へ埋め込まない。文分割、Schemaの意味、Expected、F閾値0.7は不変。
小さな既知集合への適応である限界を保持し、未使用Main/Calで別に確認する。

Model/Runtime/Prompt条件が変わるため、旧意味70 Callをそのまま新条件の証拠へ流用しない。
日英の全27人工例と既知2例、全58条件/70 Callを新条件で確認する。
通過後に元15QA/42文/30条件/84 Callの新鮮な完全回帰・全理由/Native/費用監査へ進む。
不通過は保全して原因に対応する別計画へ進み、Expectedや基準を変えて合格を作らない。

## 次に取り組むべき内容

実装確認は実機全844 pytest（31.30秒）/Ruffに成功した。sandbox内の初回は832成功・ソケット権限1失敗で、実機側で全確認した。新旧Version境界、有限予算、実送信前拒否、未知・費用、複数timeout、Config/Manifest/Report/品質再読のHash改変拒否、5QA段階継続を含む。`phase11_autonomy_software_validation_v3.json/.sha256`へSource93File/実Log/各70入力の構造照合を結ぶ。これは実Main/Calや意味採用の成功ではない。

最終Validatorの現Source検証は`phase11_bilingual_finalization_validation_v4.json/.sha256`へ保存した。
全844Test/Ruff LogとSource Hashを結び、実v10のMain準備拒否・未達Freeze拒否/最終出力なしを確認した。
これも検証処理の証明であり、実Main/Cal/Gate11成功ではない。

1. 確認済みの今回Source/ConfigだけをCommit/通常Pushし、Remote先端一致を確認する。
2. ビルド完了とRuntime実物Hashの照合後、専用固定Checkoutで各Runを事前登録し、生成0と少数Smokeへ進む。
3. 日英形式/意味・全Knownの実採用後、元選定Main各20→全品質/Expected封印→実主証明書→予約Cal各20へ進む。
4. Main/Cal実測から最終EvaluationのN/条件/資源/統計/停止/欠測を固定し、実最終Validator/Manifest/Hashを照合する。
   実証拠がそろうまでGate11未通過を維持し、Phase12は開始しない。
