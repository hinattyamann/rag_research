# Phase11 自律継続Protocol v3と新Runtime・意味候補

2026年10月26日JST。[詳細要件](phase11_lab_weekend_goal.md)に基づく新規作業。
Gate11未通過、Main/Calibration/最終凍結は未実施、Phase12は開始しない。

## 21:12 JSTの意味不合格確認と継続

同Known v12/Handle17686は21:09時点65応答＋1処理中、Health失敗/確定未知0である。
独立意味監査でTar Heels c2が元順・逆順とも固定Expected NSに対してSupportedとなった。
別々の伝承に含まれる要素をつないで、固定文の結合した因果関係まで支持する誤読である。
非支持16観測中の誤支持が少なくとも2件のため、残り全正解でも14/16＝87.5%となり90%基準を満たせない。
全84取得/全監査を完了して不採用・費用・C↔NS・曖昧・順序差を保存し、原因に対応する別候補へ進む。
Expected/基準/分母は変更せず、同条件再抽選・Main/Calへの進行は行わない。Goalは継続する。

## 20:54 JSTのMain開始前準備

Known v12は同Handle17686/固定f0b7c71で継続し、20:53:48 JST時点54応答＋1処理中、確定未知0/Task失敗0。
全84完走前の採用は未確定。先行36葉の全文AI意味監査は支持24/24・二値非支持10/10、曖昧2を保持した。
Tom Bombadil逆c5の「非描写」から「非言及」への拡張はC↔NS誤読/理由の過剰解釈として保存し、
二値基準に影響しないからといって意味完全一致とは扱わない。理由の途中切れとCouncilの範囲問題も診断へ残す。

Main/Calの新実行入口は`scripts/run_phase11_bilingual_collection_with_bridge_v3.py`。
`validate_phase11_baseline_bridge_v2.py`で旧実2応答の限られたHealth証拠、旧Execution9aeb/現Adoption91f、
現94 Core/Native依存36、全698参照を検証する。旧WT内の20 Rawは封印済み同一Byte証明で正規コピーへ解決し、
696実物を新Checkoutへ再現できる。共有正規v3台帳のlive Run/固定Commit/自己PID・Process群/全config・資源・全Hash一致後だけ、
既存collectionを同じPID/環境で実行する。正式Main/CalのRunplan commandをこの入口へ固定し、全696依存と入口/元collectionを直接bindする。
既存汎用Guardが全ての旧直接入口を一律禁止したという主張ではない。

初版の全934 Test/Ruff成功後、独立監査で本番producerが追加する`decision.bare_refusal_policy=rewrite_once`を
consumerが拒否するP1を発見した。旧script/934ログ/実再現を保全し、期待decisionを候補全項目＋この必須項目だけに限定修正。
実Main設定生成→Cal設定生成の日英統合と8反証を追加し、新全944 Test（33.20秒）/Ruff、独立24 Test、
最終bytesの実canonical/旧WTなしportable2正例・4拒否を確認した。新Main/Cal本文参照・Native・collectionは0。
正式結果は`data/manifests/phase11_baseline_bridge_entry_result_v4.json`、SHA256
`12a9a18fd6b04b65aef50f1e3a9def236f3cb4d9d91ba9d07bd80cbf5c24cebb`。旧v3結果は上書きしない。
これらのTestを行った間のKnown Native時間は、並行ソフトウェア確認を含む観測時間で、隔離性能Benchmarkではない。

Graph OFFを指す正式Mainテンプレート日英2個を追加し、旧テンプレートとの差はbaseline_configの一行だけ。
別の単位Scope証明`data/manifests/phase11_initial_unit_scope_upper_bound_v3.json`（SHA256
`b2ba969d76b106a32671b106e4d499a0033d1b7e4dfc91800990a027a167586d`）は、
3B実GGUF metadata全151936語/455808候補片と65536合成byte組を生成0で照合した。
512出力Tokenから非空文131072/QA・5242880/40QAを計画Scopeの安全上界とする。
不正UTF8の置換で再UTF8化byte数は増え得るがcodepoint数は元piece byte数以下、非空文は非重複spanである。
実文数・F/精度/費用分母・必要Callをこの上界で置き換えない。実分母はまだnullである。
Main/Calの正式Policy/Resource/実config・Known前段証明と本収集は、実Known採用後に行う。

## 19:42 JSTの実行現在地

全889 Test/Ruffと旧日英意味70 Callの明示的再利用証明を`f0b7c71`へCommit/通常Pushし、Remote先端一致を確認した。
候補v23/Known v12の専用Checkoutへ532ファイルを再現し、94 Core/Model/Runtime/旧Raw/SourceproofのHashを照合した。
再現Receiptは`data/manifests/phase11_known_v12_checkout_reproduction_v3.json`、
SHA256 `6288513be81af3dc05ccb8100fad8fd03faf8626ba002112ea48b16505500451`。
全84入力の生成0 preflightは25.518612秒で通過し、最大3305入力＋6144予約がContext12288以内、33/33層CUDA、完了要求0を実測した。
生成0結果は`data/manifests/phase11_known_v12_zero_preflight_result_v3.json`（SHA256 `43a654678220c871f2b1d16f89c17bac4f9c5bfc8992f7198a585673e7bc588d`）、
独立事前監査は`data/manifests/phase11_known_v12_prereg_independent_audit_v1.json`（SHA256 `063f061b6b2ff8c91080297099440536d32dc33dedd37ce3a785de204a61b956`）へ結ぶ。

新鮮な全Known回帰を同じ固定Checkoutで開始した。Run IDは`phase11-v3-v12-known`、実行Handle17686。
事前計画は`data/runs/development_screening/phase11-autonomy-v3-plans/v12-known.json`、
SHA256 `7639318280dc22b9e739e52b4f9b7b4a20f7202208ab8e574bea649849a7b3d7`。
全15 QA/42文/30条件/84 Call、支持58/非支持16/曖昧10の予定観測を固定し、旧Expected・最低被覆・F0.7を変更していない。
Native見積6707.988084秒は実意味診断の先行既知16 Call/1277.712016秒の外挿で、完了保証や母集団CIではない。
各Runの有限上限は84 Call/1032192計画Token/21250秒、個別1200秒/6144出力Token、監視5秒、Retry0。
上限はGoal全体の終了条件にしない。全完走後の独立Raw/理由/費用・追加0再読を経るまで採用を確定しない。
Main/Cal本文・Evaluation本文はこの準備と実行に使用していない。

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

## 固定Checkoutと最初の実走結果

固定Commitは`d40f927e24af8ad263fa4e12f21334f7b86388b6`（通常Push/Remote一致）。
専用WTは`.tools/worktrees/phase11-autonomy-v3-d40f927`。不変10590Fileはhardlink＋Hash、
可変Run13817Fileは別inodeコピー＋全Hashを確認し、Source731File/HEAD/cleanとGPU uv環境を再現した。
Receiptは`phase11_autonomy_checkout_reproduction_v3.json/.sha256`。
ONNX importが作った51Byte補助ファイルは保全し、公式の初期化前`ORT_DISABLE_TELEMETRY=1`で再発しないことを確認した。
これはプロセス限定設定で、Driver/OS/Source/科学Guardを変更していない。

| 実走 | 結果 |
|---|---|
| 旧Prompt/新Runtime preflight | 58条件/70入力、最大3793+6144<12288、33/33層CUDA、Call0、壁20.345749秒 |
| Runtime Smoke | Camp David逆c5と暖鋒元c2、2 Call/2成功/未知0、入力6874/出力8465、Task171.951885秒 |
| 改訂Prompt v21 preflight | 58条件/70入力、最大3171+6144<12288、全CUDA、Call0 |
| v21形式10件 | 厳密9件成功＋旧方式の失敗対照1。10応答/630入力/1729出力Token |
| v21日英意味 | 固定d40の同一候補で実行中。最大70 Call、全58条件、採否未確定 |

Smoke全9Rawは正規側へコピーし全Byte一致。全Payload/local c1対応、独立Schema、Native実Sampler/Grammar、
Source/Model/Runtime/費用/監視を照合し、コピー上の再読も追加Call0でRaw不変を確認した。
結果は`phase11_v3_runtime_preflight_result_v1.json`、`phase11_v3_runtime_smoke_result_v1.json`と同名`.sha256`。
Camp David c5のExpectedは曖昧のまま。暖鋒はLabelがCでも理由に表の誤読が残り、意味改善の証明に使わない。

費用の17:21:04JST時点snapshotは`phase11_autonomy_cumulative_cost_v3.json/.sha256`。
新2/成功2/確定未知0、旧込み911/確定未知3。処理中の予約を未確定として別に示し、正常返却の履歴を保存した。
旧未知の全出力Token/金額はnullのまま。Build864.124237秒・Test31.30秒・Native/Task/Runを別列へ残し、
並行処理の単純和をGoal全体の壁時計時間と呼ばない。このsnapshotに後続の形式/意味検証を実施済みとして含めない。

## 次に取り組むべき内容

実装確認は実機全844 pytest（31.30秒）/Ruffに成功した。sandbox内の初回は832成功・ソケット権限1失敗で、実機側で全確認した。新旧Version境界、有限予算、実送信前拒否、未知・費用、複数timeout、Config/Manifest/Report/品質再読のHash改変拒否、5QA段階継続を含む。`phase11_autonomy_software_validation_v3.json/.sha256`へSource93File/実Log/各70入力の構造照合を結ぶ。これは実Main/Calや意味採用の成功ではない。

最終Validatorの現Source検証は`phase11_bilingual_finalization_validation_v4.json/.sha256`へ保存した。
全844Test/Ruff LogとSource Hashを結び、実v10のMain準備拒否・未達Freeze拒否/最終出力なしを確認した。
これも検証処理の証明であり、実Main/Cal/Gate11成功ではない。

1. 固定v21の日英意味Run/Handle/Journalを監視し、終了後に全Raw/理由/Schema/Sampler/費用を監査する。
2. 日英意味通過後だけ、全15 QA/42文/元逆30条件/84 Callの新鮮な完全回帰を別Runへ登録し実行する。
3. 全KnownのHealth/意味実採用後、元選定Main各20→全品質/Expected封印→実主証明書→予約Cal各20へ進む。
4. Main/Cal実測から最終EvaluationのN/条件/資源/統計/停止/欠測を固定し、実最終Validator/Manifest/Hashを照合する。
   実証拠がそろうまでGate11未通過を維持し、Phase12は開始しない。

意味開始前の終了済みRunは新12 Call（Smoke2＋形式10）・旧込み921/確定未知3。
形式10は汎用Task checkpoint対象外のNative返却で、台帳の標準成功2と区別する。
独立形式監査は全9Strict/旧方式対照1・Grammar/Schema/Sampler/Tokenizer証拠/全Costを確認し、
`phase11_v3_v21_preflight_format_result_v1.json/.sha256`へ保存した。意味精度の証明ではない。
意味Runの有限予算は70 Call/個別1200秒/壁17810秒/5秒監視、同じ入力の自動再送0。
見積りNative6012.06秒は旧Promptの長いSmoke2要求からの条件付き目安で、完走保証ではない。
壁上限は70×6144出力Token÷25 Token/秒＋600秒の保守的計画から登録し、Goal全体の上限にしない。


## 初回生成3BのRuntime確認を分離する

Main/Calの旧baselineはGraph ONを参照していた。補助9Bの実Healthと区別し、
`configs/phase11_bilingual_baseline_graph_off_v3.yaml`へruntime_spec一項目だけを分けた。
初回Model/日英Prompt/温度0/seed42/Context4096/出力512・全generation値は保持する。
Runtime間の数値同値は仮定しない。新しい各QAの初回回答と実使用Sourceを一回固定し、以後は提示順だけを変える。

`scripts/probe_phase11_baseline_v3.py`は、旧known connectionのみの日英各1例をHash固定した
`configs/phase11_baseline_probe_inputs_v3.json`を使う。Main/Cal/Evaluationの本文・結果・Expectedは使わない。
補足生成identityは`phase11_baseline_graph_off_identity_v3.json`、有限資源は
`configs/phase11_baseline_runtime_resource_v3.json`。上位v3の別生成0/Smoke2 Run登録がさらに必要である。
各Runはtimeout300秒/壁900秒/自動再送0/5秒監視、Native前にlive ledgerと全入力Hashを照合する。
生成0ではprepared-*.jsonに実Token/全文を保存し、Smokeは実baselineのbuilder/Tokenizer/Model/Runtimeを使う。

追加7件を含む実機全851 Test（29.60秒、wrapper30.163459秒）/Ruffと実Contractの生成0照合に成功。
`phase11_baseline_probe_software_validation_v3.json/.sha256`へ全ログ・93Source・新入力を結んだ。
実GPUのbaseline確認はまだ未実施で、このソフトウェア検証はRuntimeの採用ではない。
補足生成identityは補助9Bの6component identityを置換せず、Main/CalのConfig/実Run/最終条件で別にbindする。

Baseline journalは標準Task checkpoint形式ではないため、返却2件はNativeのunvalidated_returnedに残す。
別の独立監査で全入力/制約/受信/費用を確認し、台帳の標準Task成功へ数を混ぜない。
未知/中断時はRawと不明総費用nullを保持し、同条件再送しない。


## 全70の実結果と初回生成の実Health

v21の全29例/35文/58条件/70要求は固定d40で正常終了した。Critical4/4、人工EN24/24・JA30/30、
入力96960/出力254333 Token、Task5059.542909秒/NativeHTTP5057.123585秒/Run壁5080.031970秒。
原Raw133/実Source98と全Native/Schema/理由/引用を監査し、58条件のコピー再読は追加Call0。
曖昧Council2、writer/translatorの排他性を仮定するC理由2、理由末尾切れ2も保持する。
実Known84の採用や小集合外の精度保証とはしない。正本は`phase11_v3_v21_semantic_result_v1.json/.sha256`。

3B用の生成0はEN1166/JA3584入力＋出力512でContext4096内。既知日英2Smokeは入力4750/出力191、
Task2.237472秒、EOS/非truncated/37層CUDA/未知0で終了した。原Raw20/実Source105を照合・正規コピーし、
保存actualTokenizer出力と固定479の実Client/GeneratorのHTTPなし再現に通過。再tokenizeはしていない限界を明記する。
標準Task成功0/Native未検証返却2を変えず、独立Health2と区別した。
`phase11_v3_baseline_runtime_result_v1.json/.sha256`が正本。これも新Coreへ自動継承せず、
Model/Runtime/日英Prompt/Native builder依存36ファイルのHash不変を照合して再利用する。

終了済み7Runの費用v4は新84要求（Runtime2＋形式10＋意味70＋初回生成2）、
標準Task成功72/Native未検証返却12/新未知0、入力109214/出力264718 Token。
旧909/未知3を保って累積993。旧未知の全Token/全費用はnull、Native/Task/Run和とGoal壁を混同しない。

## Group保存の修正と旧証拠再利用v1

実producer→二値consumerの生成0監査で、Main/Cal Manifest.selectionから文書Groupが落ちるため、
日英両経路の意味解析がKeyErrorになることを再現した。新Runでは元hashbound rowsの
`document_group_id`をselectionへ保存する。旧connection形式は維持し、欠落を推測補充しない。
修正はrunnerのselection代入だけで、生成/判定の全文・ID・Title・Prompt/Model/Samplerを変えない。

全srcを含む6component identityは非推論修正でも変わるため、旧9aebを新Coreへ偽装しない。
`evidence_reuse.py`の別Version `phase11-semantic-evidence-reuse-v1`が、旧70群と新群を別々に厳密検証する。
Model/Runtime/Prompt/Sampler/Schemaの全binding、全資料/Expected/基準/予算、旧93Source snapshot、
新94Source実物を照合する。差分はGroup登録・厳密な証拠読込み/閉包と追加helperだけを許可し、
登録した正確なAST追加以外やNative入力Core変更を拒否する。元Rawを変えずコピー上で全70を再読する。
Receiptは新config自身のHashを含めず、条件digest/新ID/新Plan/旧実Runと全Sourceをbindして循環を避ける。
Main証明のexternal閉包へ全Receipt/旧Source/条件を取り込み、Cal/Freezeでも再検証する。

初期のv22/Receipt file v1/Known11は、証明書の外側Lockに対する二重取得の見落としを修正する前の
未実行成果として保全した（Native登録0）。43.876913秒の生成0検証も消さない。
helperは外側Lockを再取得せず、常に同一Byteコピーで再読・原本前後Hash照合を行う。
修正版は全889 Test/Ruff・独立AST11負例/92Testと実外側Lock保持下の全70再読に通過した。
追加Native/socket/process0、実43.082430秒。`phase11_unexecuted_technical_supersession_v1.json`へ
旧版と理由・全Hashを保存し、同条件の再抽選にはしていない。

現行は`phase11_semantic_candidate_v23.yaml`と未実行条件view `phase11_semantic_diagnostics_v23.json`、
`phase11_semantic_evidence_reuse_v2.json`。新Identityは
`91f50601299a8e9b1399b3925acddc36ffb6af9a46032e2adad631770a12d1b5`、
旧Identityは9aebのまま。viewを新しい意味RunとしてNative実行する入口は拒否する。偽Reportは作らない。
Known以降は現行Identityへ統一する。新Known v12は元15 QA/42文/元逆30条件/84 Call・
全Expected/曖昧5文/裸拒否8を保持し、実load_configに通過したが、Nativeはまだ開始していない。

最終Validator検証v5は現94src＋validator/rubric/statplanの97Sourceと889実Test/Ruffをbindし、
実未達Freeze/失敗v10 Main準備の早期拒否・出力なし・QA本文/Native0を確認した。
`phase11_bilingual_finalization_validation_v5.json/.sha256`は現Validatorで受理済みだが、
実Main/Calの証明や最終Gate11通過ではない。

次は今回分をCommit/Pushし、固定CheckoutでKnown v12全84入力生成0→新鮮全84要求を実行・監査する。
Known実採用後に元Main各20/全匿名品質Expected封印→実主証明→予約Cal各20/全封印→
最終実Validator/Manifest/Hashへ進む。Phase12は開始しない。
