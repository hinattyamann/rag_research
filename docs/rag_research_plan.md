# 英語・日本語データにおけるRAG自己評価の根拠提示順序感度と修復判断への影響に関する研究計画

## Version 7.80 — 2026年10月27日 v24不採用保存と共同変更候補v25

11:38 JST現在、v24の生成0全90入力は通過したが、別入力の日英Judge Smoke2は両方NSをCと判定し、不採用とした。Health2/2・未知0だけでは意味採用に進めず、全意味90とKnown84は未実施のまま保存する。入力2383/出力7161 Token・Native141.556498秒、旧909を含む累積1079試行・未知3。結果と累積費用は`phase11_v24_smoke_result_v1.json`と`phase11_autonomy_cumulative_cost_v6.json`へ保存した。旧失敗・未使用枠は変更しない。

新候補v25は、原因の併存可能性を明示するJudge Prompt v14と、共通reasoning budget4096→1024の共同変更である。IDは`2044ad1b52556b4cfa8d16ba2667a2bfea77163e7fc4fca9bd032fc69c48df74`。Rewriteの指示は不変だが実推論予算も1024になるため、別の架空日英各1例の一回書換えSmokeと全文品質監査を追加する。Prompt単独の効果を主張しない。Core94/Model/Graph OFF Runtime/Schema/その他Sampler/全90入力・Expected・分母/元Known全84/F0.7/支持・非支持各90%/被覆/盲検条件は維持する。旧形式10の再利用はoverride後128/512の境界形式条件だけに限定し、新Judge・Rewriteの意味やHealthへ流用しない。全979 Test/Ruffは成功、新候補のNativeは0。次は別固定Commit/Checkoutで生成0→JudgeSmoke2→RewriteSmoke2→全意味90→新鮮Known84。Main/Cal・Gate11は未達、Goal active、Phase12未開始。

以下は各観測時点の履歴として保持する。

### Version 7.79 — 2026年10月26日 Known全84の不採用保存と関係照合候補

21:36 JST現在、Known v12は同固定f0/Handle17686で84応答・未知0/失敗0、全30条件を完了した。支持57/58＝98.28%、非支持14/16＝87.5%で不採用。曖昧10観測をFに保持し、三分類68/74・C↔NS3・誤支持2・支持見逃し1を保存した。全84 Native Schema/payload/費用/Source99照合・追加0再読と実Main準備Gate拒否を確認済み。原因に対応する汎用関係端点照合Prompt v13/候補v24を別保存し、旧70全入力/Expected不変＋新日英10文元逆20Callの全90意味検証と新Known84を必要とする。Model/Runtime/Sampler/Schema/Core94/Rewrite/F0.7/基準を維持する。新候補のNativeはまだ0、Main/Cal/Gate11は未達、Goal active・Phase12未開始。

21:12 JST追記: Known12はTar Heels固定c2の元逆両方で因果結合の誤支持があり、非支持16の最良値も14/16＝87.5%で採用不能。Health良好を意味問題の解消とせず、同Handleの全84/監査/費用を保存して別仮説の候補へ進む。Expected・支持/非支持90%・被覆・全分母・Main/Calの未使用枠を維持する。Main/Calは未開始、Goal active。

20:54 JST現在、固定f0b7c71のKnown v12は54応答＋1処理中・確定未知0/Task失敗0で継続し、全84の採用は未確定。Main開始前の初回生成証拠の橋渡しと強制入口、Graph OFFテンプレート、全単位Scope上界を生成0で検証・保存した。新入口の本番設定との不一致を実Main前に発見・限定修正し、実設定生成関数の日英Main→Cal統合を含む全944 Test/Ruff・独立再監査に通過。94 Core/実行中WT/研究条件は変更せず、実Main/Calは未開始。詳細は[自律継続v3](phase11_autonomy_v3.md)。支持/非支持各0.90・被覆・F0.7・全分母・全匿名採点封印・実証拠要件は不変で、Gate11未通過・Phase12未開始。以下は各時点の履歴として保持する。

19:42 JST現在、固定f0b7c71の専用Checkoutで新鮮Known v12全84 Callを実行中。全84入力の生成0/33層CUDA/Context確認と532資産再現、全条件・Expected不変の独立監査は完了した。Runは84 Call/21250秒・個別1200秒/Retry0へ事前登録し、全完走後のHealth/支持Recall・非支持Specificity各90%/最低被覆/全理由・費用監査まで採用を確定しない。実行Handle/Hash/監視は[自律継続v3](phase11_autonomy_v3.md)と[工程正本](research_roadmap.md)に記録する。Main/Cal/最終凍結は未実施、Goal active・Gate11未通過・Phase12未開始。以下は準備時点の履歴として保持する。

日英意味v21は固定d40で全70要求/58条件を終了し、Critical4/4・人工英語24/24・日本語30/30・未知0で通過した。原Raw133/固定Source98・全Native/理由/費用を独立監査し、追加0再読と正規コピーを完了。初回3BのGraph OFF生成0/既知日英2Smokeも固定479で完了・監査し、累積993試行/旧未知3を保存した。後工程のGroup欠落を非推論修正し、全889 Test/Ruffと実70のLock保持下再検証・最終Validator検証v5を通過。新94Coreの候補v23/Receiptv2へ旧証拠を明示的に結び、元15 QA/42文/30条件/84 CallのKnown v12を準備した。Known新Native、Main/Cal/最終凍結は未実施。Goalはactive、Gate11未通過、Phase12未開始。

初回生成3Bの旧Graph ON参照を事前点検で発見し、Model/日英初回Prompt/全generation値を保った新baseline設定（runtime_specだけGraph OFF）と検証入口を追加した。既知接続の日英各1例だけを対象とし、生成0/Smoke2・入力全文・Gold非注入・新出力排他・未知保全を厳密に検査する。新851 Test（29.60秒）/Ruffと実Contractの生成0照合に成功、core93/実行中d40は不変。新初回生成の実Runtime確認は未実施で、ソフトウェア確認を実Health/採用としない。

ユーザーが方向転換を決定したため、本書を今後の研究目的・実験方針の正本とする。
研究方針の採用と、自己評価・修復の実装や実験結果の完成は区別する。
実装は[実装計画 Version 8.83](rag_implementation_plan.md)、工程と現在地は[ロードマップ](research_roadmap.md)、
Source/Schemaは[Dataset Guide](clapnq_dataset_guide.md)による。
[旧計画 Version 6.11](archive/rag_research_plan_v6_11.md)は履歴として保存する。

ユーザーの週末無人運転依頼を[研究室用Goal](phase11_lab_weekend_goal.md)へ明文化した。候補数・追加188回/4時間の全体打切りと回復可能障害時のGoal停止は今後の新Protocolで置換可能とし、90%の採用基準・実行Health・全対象/分母・未使用性・全採点封印を維持する。純粋な資源枠は結果を見る前に別Versionへ必要量を登録し、失敗の再抽選へ使わない。Calを調整に使った後は同じ集合を未使用と呼ばず、追加の独立確認は非重複・未使用Groupで事前固定し、全失敗と反復選択の限界を報告する。Evaluationで調整せず、Gate11実証拠と最終Manifestまでを完了条件としPhase12は開始しない。研究目的とF閾値0.7は不変。旧v10の不採用・909試行/未知3件は保存し、今回はGoal文書だけの作成で新実装/実験/採用は未了。

[新基準v2の全回帰v10](phase11_known_trace_direct_result_v10.md)は固定903f4cfで56試行（55応答取得/未知1）後にCUDA launch timeout・Kernel Watchdog/Xid8で停止し不採用。元15 QA/42文/30条件・84 Callを保持し、12条件/28 Call未試行。非支持の予定16判定は全件取得したが14/16＝87.5%で基準0.90未達。C↔NS3件は二次診断、全予定率はHealth不適合でnull。全55理由/56入力・Schema/55実Sampler/96 Source/生成0再読79 File不変・830資源観測を監査し、Raw81/全123 Artifactを正規保存・WT照合した。新開発はSmoke2+Known56＝58、累積909/未知3、Task4310.915004秒・共有壁4381.357537秒で数値上限内。残130（Known28+未割当102）と旧未使用69・42/42/81/42は自動再配分しない。v2のKnown→Main→Cal→最終Validator実装と全782 Test/Ruffは成功し、実Main準備/最終凍結の拒否も確認。Main各20/予約Cal各20・独立品質/費用・最終N/条件/凍結は未了、Gate11未通過・Phase12未実施。Nativeは全終了。ユーザー指定の障害時一時停止条件に該当し、保存・Git同期後にGoalを一時停止する。再開にはRuntime診断と意味候補の追加枠または研究範囲の明示的判断が必要で、CUDA復旧だけでは意味不適合は解消しない。

研究目的/仮説/実QAの順序反復設計は維持し、採用の意味指標をScoreに対応させる設計改訂。支持Recall/非支持Specificity各0.90という新設計は今後の別Protocolへだけ適用し、旧の誤支持0・完全一致基準での不採用結果を保持する。全経路実装・Test/事前登録に加え、新鮮な全Known回帰のHealth・意味採用がそろうまでMainへ進めない。

[温度0.2旧全回帰v9のCUDA停止](phase11_known_trace_direct_result_v9.md)を監査・正規保存した。固定9727409/session72566は3条件/15記録試行・14応答取得/未知1、Zidane元順序の実LogにCUDA launch timeout/応答前切断があり不採用。取得した会議14判定は確定12/12/支持10/10・誤支持0だが、全74/58精度null・残27条件未試行/69枠未使用を保持する。95 Source/元23 File不変・追加0、全15提出Schema/取得14 Native Schema・実Sampler/7組/全14理由/193点資源/実Main準備拒否を確認し、Raw26/全110 ArtifactをWT照合した。全9B記録851（Q4 317/Q5 317/Q6 217）・未知計2、今回未使用69と旧42/42/81/42/累積上限920・Retry0を保持。72566/23121は終了済みで再起動しない。次はGPU/Driver/Kernelと旧停止Logの原因調査で、根本原因や温度効果は未確定。新候補/新Native未登録、Main/予約Cal/最終凍結は未了、Gate 11未通過・Phase 12未実施。

[温度0.2の旧全回帰v9](phase11_qwen35_q6_temperature_known_execution_v1.md)を開始した。全意味/登録を9727409へCommit・通常Pushしリモート一致後、同Commit固定WTへ1763 File Binding/57不変Hardlink/相対Symlink10・Offline58 Packageを再現。親202/新温度形式40/Core27不変、全84実入力生成0・最大3927 Token/全層CUDAと準備14 Artifact保存/WT照合に成功した。同じWTの回帰は観測付きsession72566で、元全15 QA/42文/30条件・最大84/全9B累積920/Retry0を維持する。負例12条件/42 Call全一致後だけ残18正例条件へ進む。全採否は未確定、全終了後だけ監査/正規保存する。旧未知/未使用と全Source/Expected/基準は不変。Main/予約Cal/最終凍結は未了、Gate 11未通過・Phase 12未実施。

[温度0.2の全意味診断と回帰v9登録](phase11_qwen35_q6_temperature_semantic_result_v1.md)を完了した。固定17d57c6/session89310は全58条件/70 Call・Critical4/4・英語24/24・日本語28/30・誤支持0で元基準通過。日本語NS→C2/曖昧Council両NS・F5/7/理由断片を保持し、全68確定Labelは旧T1と同じで改善を主張しない。95 Source/元133 File不変・追加0、全70 Native独立Schema/実温度0.2・主要Sampler/全理由・29全文根拠/772点資源を監査し、Raw136/全202 Artifactを正規保存・WT照合した。親136 Fileコピー上の再検証後、元全15 QA/42文/Source25/Expected/基準/裸拒否8へ新前提を結びv9を作成。正の準備12/登録検証8 Artifact・全761 Test（30.43秒）/Ruff成功。別v18は既存条件付き84だけ/全9B記録836・累積上限920/Retry0で、旧未知/未使用を保持する。新回帰Nativeは未実施。次はCommit・Push後の新固定WTで全84入力生成0/全層CUDA→回帰v9へ進む。Main/予約Cal/最終凍結は未了、Gate 11未通過・Phase 12未実施。

[候補v20の実機確認](phase11_qwen35_q6_temperature_execution_v1.md)で全70入力生成0/全層CUDAと新形式10 Call/全9 Strictを通過し、全10 Native実温度0.2・全監査/Raw16・40 Artifactを保存した。形式成功を意味採用へ読み替えず、同じ固定17d57c6で全意味session89310を実行中。全対象/Expected/基準と累積920/Retry0を維持する。実Main/Cal/最終凍結は未了。

[候補v20の別事前登録](phase11_q6_temperature_registration_v1.md)は記録試行756から新形式10/意味70/条件付き旧全84＝最大164・累積920/Retry0とし、旧未知/未使用と全Expected/基準を保持する。登録の算術/入力参照/親144・準備9 Artifact/実95 Sourceを検証した。新Native実走/採用・Main/Cal/最終凍結は未了である。

[低temperature候補v20](phase11_qwen35_q6_low_temperature_candidate.md)はStudy Versionと補助temperature1.0→0.2だけを変更する。Judge/書換え双方と同一順序の分散に影響し得るため日英で同じ候補を用い、採用した条件に結論を限定する。全154 Message/Model/Runtime/Prompt/予算/Seed/全Expected/基準は不変、全761 Test（29.32秒）/Ruffまで成功。新条件のNative形式/意味/旧全回帰は未実施で、採用や最終Nの確定ではない。

[Q6旧全回帰v8](phase11_known_trace_direct_result_v8.md)は12条件/42 Call・Critical8/12・誤支持3で不採用、残18条件未試行。確定34/40/支持23/24と全74/58精度nullを維持し、全監査/Raw62・144 Artifactを保存した。目的/Expected/全基準を緩和せず、temperatureだけを下げる別候補の準備を進める。実Main/Cal/最終N/資源/条件/凍結は未了。

Q6全意味/回帰登録を262ba08へCommit・通常Pushし、[固定WTの全84入力生成0と回帰v8](phase11_qwen35_q6_known_execution_v1.md)へ進んだ。全層CUDA/全入力収容と14準備Artifactを確認し、元全条件/基準・最大84/累積798・Retry0のままsession61821を実行中。採用/実Main/Cal/最終凍結はまだ未了である。

[Q6全意味診断](phase11_qwen35_q6_semantic_result_v1.md)は全58条件/70 Call・Critical4/4・英語24/24・日本語28/30・誤支持0で元基準に通過し、全終了後監査/Raw136・195 Artifactを保存した。NS→C2/曖昧/F/理由断片は維持し、全68確定Labelは旧Q5と同一で改善を主張しない。同じ旧全15 QA/42文・84 Callと全Expected/基準へQ6の新前提を結びv8を作成。新v16は既存条件付き84だけ/累積上限798・Retry0で、旧未知/未使用を維持する。全旧採用とMain/Cal/最終N/条件/凍結は未了であり、目的/閾値/成功条件は変更しない。

[Q6候補v19](phase11_qwen35_q6_candidate.md)は同固定Revisionの公開Size/Hashで取得し、v18のModel Manifest/Study Versionだけを分けた。全対象/Expected/基準・日英Prompt/12k/予算/Samplerは維持する。全154入力同一・全761 Test/Ruffに成功し、事前登録v15は新最大164/累積798・Retry0。実GPU配置/新形式/意味/旧全回帰は未確認で、取得やTest成功を採用としない。全旧失敗・未知1・未使用42/81/42を保持する。研究目的/閾値/全採用条件を変えず、Main/Cal/最終凍結は未了。

[旧全回帰v7](phase11_known_trace_direct_result_v7.md)は12条件/42 Call・Critical9/12・誤支持3で不採用。残18条件/全74・58分母を保持し、全精度はnullとする。全理由/Source、Native Schema、追加0再開、569点の資源を監査/正規保存した。元Expected/基準/全失敗と旧未知1を維持し、Main/Calは未開始。[Q6資源調査](phase11_q6_resource_feasibility_v1.md)は同固定Revisionの公開Size/Hashと試算だけであり、配置/精度の確認ではない。量子化を分ける候補でも別事前登録・形式/意味/旧全回帰が必要。目的・閾値・成功条件は変更せず、Gate 11未通過。






[12k全意味診断と旧全回帰v7](phase11_context12k_semantic_result_v1.md)を保存した。固定5c8b8b0/session74326は全58条件/70 Callを正常終了し、Critical4/4・人工英語24/24・日本語28/30・誤支持0で元基準を満たした。全58条件の判定/理由/引用/Fは元24kと同一で、意味改善を主張しない。限定なし由来主張の不一致2件/曖昧/理由断片を保持した。入力140500/出力181440 Token・Task秒和3301.218210秒、95 Source/再開133 File不変・追加Call/Server0、全70 Native JSONの独立Schema/35組不変・全理由確認を保存。資源663点/取得エラー0・観測最大GPU6926/8151 MiB/最小Host Available4344584 KiBを再計算し、連続Peak/因果/安定性保証としない。Raw136/全182 Artifactを正規保存・WTとByte照合した。親136 Fileのコピー上で全前提を再検証し、同じ旧全15 QA/42文/30条件・84 Call/Source25/Expected/基準/裸拒否8をv7へ結んだ。全750 Test（29.14秒）/Ruffも成功。事前登録v14は元v13の条件付き84だけで、記録試行592/累積上限676・Retry0/旧未知1・旧未使用81/42を保持する。固定5f4a6b6の新WTへ1065 File Binding/56不変Hardlink/内部相対Symlink10・Offline58 Packageを配置。全84実入力/生成0・最大3927 Token/12k/全層CUDAに通過し、Runtime一点6871/8151 MiBと短区間見逃しを含む資源観測も保存した。全9 Artifactを正規保存・WTとByte照合し、同じWTで旧全回帰を観測付きsession64437として開始した。[回帰実行記録](phase11_context12k_known_execution_v1.md)を再開先とし、採否は未確定。主/Cal採用・最終N/資源/条件/凍結は未了、Gate 11未通過・Phase 12未実施。

以下は各作業時点の履歴であり、稼働中Session・採用状況・次の操作は上の最新記録を優先する。

[旧15 QAのQ5直接回帰v5の不通過結果](phase11_known_trace_direct_result_v5.md)を保存した。固定9036182/session54967は12 Critical条件/42 Callを終了し、完全一致10/12・誤支持2で停止した。残る18条件は未試行、全74確定/支持58判定の精度はnull。Tar Heel c2は両順序で別伝承を結ぶ因果関係を誤支持し、c1逆順序は支持不足を矛盾とした。Tom c5は両NS、暖鋒c2は両Label/表の列対応が一致したが、c1元の余分な引用IDの非対応も保持。入力135658/出力166835 Token・3047.441637秒、95 Source/再開59 File不変・追加Call/Server0、Raw61/全73 Artifactと全42出力の独立Schema/AI確認を保存した。全9B実439（Q4 317/Q5 122）、旧84 Call枠の未使用42は保持する。全Source25/Expected/基準/曖昧/裸拒否8は不変。次は同じQ5/Runtime/予算で、別の説明間の因果・同一関係を根拠なしに補わない一般Prefixを日英の別Versionとして事前計画する。候補は未作成・未推論で、主/Cal採用・最終N/条件/凍結は未了。Gate 11未通過・Phase 12未実施。

[Q5の全意味診断と旧15 QA回帰v5](phase11_qwen35_q5_semantic_result_v1.md)を保存した。固定be6e6ac/session95591は全58条件/70 Callを終了し、Critical4/4・人工英語24/24・日本語28/30・誤支持0で事前基準に通過。日本語の記載のない選手時代の優勝を矛盾とした2件を保持し、精度改善を断定しない。入力118450/出力209629 Token・3781.233184秒、95 Source/再開133 File不変・追加Call/Server0、Raw135/全147 Artifactを照合。全70 Native最終JSONの独立Draft-7と35組のSchema不変、全理由/SourceのAI確認を保存した。Council c6の曖昧/観測NS・F5/7による採用相当と理由の断片も保持。親136 Fileのコピー上で全再検証する準備が成功し、同じ旧全15 QA/42文/30条件・84 Call/Source25/全Expected/基準/裸拒否8を回帰v5へ結んだ。事前登録v10は既存v9の条件付き84 Callを使い、既存397/累積上限481・Retry0を維持。Native27/新Q5形式24 Artifactは不変。全740 Test（26.07秒）/Ruffにも成功。固定9036182の新WTへ567 File Binding/56不変Hardlink/相対Symlink10・Offline58 Packageを再現。全84実入力/生成0・最大3612 Token/全層CUDAに通過し、VRAM7258/8151 MiBを一点観測した。準備/Preflight6 Artifactを保存し、同じWTで旧回帰v5をsession54967として開始した。全採否は未確定で、実主/Cal・最終N/資源/条件/凍結は未了。Gate 11未通過・Phase 12未実施。

[Q5の暫定資源見積り](phase11_qwen35_q5_resource_estimate_v1.md)も保存した。終了済み全70 Judge Call/147 Artifactを照合し、3781.233184秒・平均54.017617秒、既知16/人工54の群平均68.019841/49.868810秒を確認。各20 QA/平均5文/各9試行の仮定では主Judgeだけ24.9〜34.0時間、同規模Calを含むJudgeは49.9〜68.0時間で、初回/書換え/検索/採点等は別。観測群平均の幅であり時間保証/95%CIではない。1660 Call/言語を維持し、実行中旧回帰の費用や旧8Bの時間は混ぜず、新主Policy/最終Nの採用とはしない。追加Model Call0。

[9B Q5候補の取得と別事前登録](phase11_qwen35_q5_candidate.md)を保存した。同じ固定Repository Revisionの6577841376 Byte/公開SHA256を実ファイル全体で確認し、別Manifestへ取得した。取得CLIの量子化名Q4固定を修正し、誤った宣言は取得前に拒否/旧Q4既定を維持する。追加6件を含む全740 Test（28.29秒）/Ruffと実Config/Source/Identity契約に成功。候補v16はv15からStudy VersionとModel Manifestだけを変更し、Runtime/日英Prompt/予算/Sampler/全対象/Expected/基準とNative Core27を保持する。新事前登録v9は形式10+意味70+通過時の全旧回帰84=新規164/Retry0、旧Q4実317/Q5実0から全9B累積上限481。Model変更により新形式証拠が必要。固定be6e6acの専用WTへ389 File Binding/56不変Hardlink/相対Symlink10・Offline58 Packageを配置。全70入力/生成0・最大3478 Token/全層CUDAに通過し、VRAM7254/8151 MiBを一点観測した。新Q5形式10 Call/全9 Strict条件に通過、入力630/出力1802・生成34.964001秒、92 Source/再読14 File不変・追加Call/Server0、全24 Artifactを照合。同じWTで全意味58条件/70 Callをsession95591として開始し、全採否は未確定。[実行記録](phase11_qwen35_q5_execution_v1.md)に全証拠と再開先を保存。全旧基準通過前に主/Calへ進まない。Gate 11未通過・Phase 12未実施。 Q5通過後の旧回帰v5用準備Helperを別保存し、未完了/未監査の親を実際に拒否・出力未作成を確認した（`phase11_qwen35_q5_known_preparation_pending_v1.json`）。旧15 QA/42文/Source25/Expected/基準/裸拒否8は原版一致、追加推論0。正の再検証/登録はまだ未了。

[旧15 QA直接回帰v4の不通過結果](phase11_known_trace_direct_result_v4.md)を保存した。固定321adf3/session95270は42 Call/12 Critical条件を終了し、完全一致9/12・誤支持4で停止。残る18条件未試行、全74/支持58判定の精度はnull。Tomの媒体一般化1、Tar Heelの由来断定1/別逸話の因果接続2が誤支持。暖鋒は両Label一致でも両理由が表の列を誤読しており能力改善としない。入力135658/出力159626 Token・2529.175093秒、95 Source/再開59 File不変・追加Call/Server0、Raw61/全69 Artifactと全42出力AI確認・独立Schemaを保存。Q4実累積317。旧全Source/Expected/基準/曖昧/裸拒否8を保ち主/Cal採用しない。次は同じ固定Revisionの9B Q5_K_Mを、量子化だけを分ける候補として取得/Hash・VRAM資源調査する。取得/実走と意味改善はまだ未確認。Gate 11未通過・Phase 12未実施。

[v15の全意味診断と全旧回帰v4の登録](phase11_cited_decisions_result_v1.md)を保存した。固定55d031c/session77717は全58条件/70 Callを終了し、既知Critical4/4・人工英語24/24・日本語30/30・誤支持0で診断基準に通過。入力118450/出力194751 Token・3168.554393秒、95 Source/再開133 File不変・追加Call/Server0、Raw135/全142 Artifactを照合した。全70出力の独立Schema/AI確認と35組のSchema不変を保存。人工27組は1文書で同一入力、Council c6は曖昧のまま、F5/7による矛盾を含む回答の採用相当も保持する。親136 Fileのコピー上で全再検証する引継ぎに成功し、全旧15 QA/42文/30条件・84 Call/全Expected/基準/Source25/裸拒否8をv4へ結んだ。新事前登録v8はRetry0・既存275/累積上限359、Native27と新形式v4の25 Artifact不変を照合して再利用する。固定321adf3の新WTへ299 File Binding/55 Hardlink/相対Symlink10・Offline58 Packageを再現。全84入力/生成0・最大3612 Token/全層CUDA（VRAM6517/8151 MiBは一点観測）に通過し、7準備Artifactを保存した。記録包装のField参照失敗も保持してNative再実行0。同じWTで全旧回帰をsession95270として開始し、全採否は未確定。実主/Cal採用・最終N/条件/凍結は未了、Gate 11未通過・Phase 12未実施。

[引用状態Schema v3の実機形式検証](phase11_cited_decisions_native_result_v1.md)を保存した。固定55d031cの全70実入力/生成0・最大3478 Token/全層CUDAと、新Native 10 Call中の全9 Strict条件に通過。入力630/出力1679 Token・生成合計29.255313秒、92 Source/再開14 File不変・追加Call/Server0を確認し、Raw16を含む全25 Artifactを固定WTとByte照合した。包装時の既存File検査失敗も保存し、追加推論はない。形式は意味精度の証明ではない。同じWTで全58条件/最大70 Callをsession77717として実行中（10:37 JST観測で7/58条件完了、既知4条件のCritical基準を通過して人工条件へ進行）。開始時9B累積205/上限359・Retry0、全旧対象/Expected/基準を維持する。現行93 Sourceの最終Validator検証v2も保存し、全734 Test/Ruff・実未達拒否・30 Payload照合、Evaluation本文解析/追加推論0を確認。実主/Cal採用・最終N/条件/凍結は未了、Gate 11未通過・Phase 12未実施。

[9B直接判定の暫定資源見積り](phase11_qwen35_9b_resource_estimate_v1.md)を追加した。完了済みv13/旧回帰v3/v14の全121 Call（既知費用の失敗1を含む）と236 Artifactを再照合し、6323.312653秒/平均52.258782秒を確認。各9試行・日英40 QA・平均5固定文の仮定ではJudgeだけ23.0〜30.8時間、初回/書換え/検索/採点は別途。これは観測Run平均の記述的な幅であり、時間保証/95%CIではない。旧8B Policyを9Bの許可に流用せず、採用後に実費と新Policyを結ぶ。最終N/資源は未決で、文切捨て/QA補充/基準緩和を行わない。

[引用必須状態を生成時に拘束するv15候補](phase11_cited_decisions.md)を実装した。旧v2のSchema/Grammarと人工6 Caseの変更前Hashを保持し、v3だけでC/Sの実ID引用1〜2・NSの0〜2・両Boolean true禁止を表す。閉じたCompilerの選択肢/明示Protocolを対応し、新規33件を含む全734 Test（26.78秒）/Ruffと実v14失敗のClient=None再開Byte不変/追加0を確認。独立Draft-7検証器は開発依存だけに追加し、既存依存/別GPU Lockを維持。Core/Probe27 Binding中5 Fileが変わるため旧形式証拠は再利用せず、旧6+状態4の新形式10、全意味70、全旧回帰84=最大164/累積359 Call・Retry0を事前登録した。Model/Runtime/予算/日英Prompt・全旧対象/Expected/基準は維持する。Native実走/意味採用はまだ未了で、主/Cal/Evaluationを開始していない。

[v14の引用ID欠落による停止](phase11_category_coverage_result_v1.md)を保存した。固定f92298b/session54441は9 Call・1条件成功/1エラーで終了し、56条件未試行。支持判定なのにevidence_ids空で、既存検査が正しく拒否した。入力3339/出力4211のエラーは出力上限到達ではなく、v2の生成Schemaが後段の引用必須条件を表し切れていない。全入力29988/出力31378 Token・518.200587秒、95 Source/再開16 File不変・追加Call/Server0、原本18/全26 Artifactと8有効出力・1不正ObjectのAI確認を保存した。9B実完了累積195。旧v2/Raw/Expected/全基準を保ち、次は別Versionで支持/矛盾の非空引用とBoolean状態を生成段階でも拘束する。実装・新形式/意味/旧回帰は未実施で、主/Cal採用は未了。

[旧15 QA直接回帰v3の不通過結果](phase11_known_trace_direct_result_v3.md)を正規保存した。固定8ea37e1/session93865は42 Call・12 Critical条件を終了し、完全一致8/12・誤支持4（Tom元1/Warm front逆1/Tar Heel c2両2）とNS→Cの2不一致で不通過。残り18条件未試行、全74/支持58の精度はnull。入力130198/出力156604 Token・2584.749639秒、94 Source/再開60 File不変・追加Call/Server0、全68 Artifactと全42最終出力のAI確認を保存した。親終了時9B累積186。次のv14は固定f92298bで181 File Binding/相対Symlink10・Offline58 Packageを再現し、準備のリンク連鎖検査失敗も保全。全70実入力/生成0・最大3478 Token・24k/全層CUDAに通過し、VRAM6513/8151 MiBは一点観測。Native27/形式15 Artifact不変と準備/Preflight7 Artifactを確認し、同じWTの全58条件/最大70 Callを開始した（session54441）。全旧基準/Expected/分母・Retry0を維持、主/Cal採用は未確定。

[カテゴリー・列挙項目の完全支持を明確化するv14候補](phase11_category_coverage_candidate.md)を別登録した。実行中の旧15 QA回帰v3でTom c5が元S/逆NS（Expected NS、F1.0/0.8・両採用）となり、元順序の誤支持を確認した。固有名/答えを入れず、日英へ同じ一般Prefixだけを加える。全旧29例/35文/58条件・15 QA/42文/全基準/Native Core27とModel/Runtime/予算を維持し、契約と関連82 Test（2.61秒）/Ruffに成功。Python Sourceは全701 Testのe3c9fa0と同一。新規最大70+84=154 Call/Retry0、親の旧登録上限込み保守的9B累積382を事前記録したが、v14のGPU確認/推論は未開始。親session93865の終了・全失敗/未試行/Raw/費用監査保存後だけ次の固定Worktreeへ進み、主/Cal採用は行わない。

[日英の最終固定Validator](phase11_bilingual_finalization.md)を追加した。実主証明書と全採点封印済みCalibrationを再検証し、旧回帰/全Native/意味・統計・費用、両言語Assets/全Index/Embedding Payload、Evaluation本文を読まないID選定、最終N/資源/停止規則を照合する。未達時は最終Manifestを作らず、検証資料自身のSource一致も要求する。雛形のN/資源/実証拠は未決で、実主/Cal採用と最終凍結は未了。固定8ea37e1の旧15 QA回帰v3/session93865は継続観測し、重複起動しない。修正後の新規27件を含む全701 Test（25.15秒）/Ruff・実未達拒否・全30 Index/Embedding Payload照合に成功。母集団EN564/JA209のMetadata導出は最終Nの決定ではなく、Evaluation QA解析/追加推論0。

[固定v13の全診断と旧15 QA回帰v3](phase11_qwen35_direct_result.md)を保存した。全58条件/70 Callで既知4/4・人工英語24/24/日本語28/30・誤支持0、入力109350/出力198444 Token・3220.362427秒。全92 Source/再開134 File不変・追加Call/Server0、原本136/全142 Artifactと全最終出力のAI確認を保持。日本語の同一入力の支持不足→矛盾2と曖昧c6も保つ。次の旧15 QA/42文/30条件・最大84 Call/Retry0を全Expected/基準のまま新規事前登録し、実契約/前提を確認した。主/Cal採用は依然未了。固定8ea37e1の専用Worktreeで全84入力/生成0に通過し、最大3482 Token・Context24576/全層CUDAを確認した（VRAM6558/8151 MiBは一点観測）。準備/Preflightの5 Artifactを保存し、同じ固定Commitで旧15 QA回帰v3を開始した（session93865）。全結果/採用は未確定、最大84 Call/Retry0・負例12条件全一致時だけ残りへ進む。

[Calibrationの匿名採点・隔離解析](phase11_bilingual_calibration_analysis.md)を対応した。両言語の全品質/文Expected封印後だけ、同一Byteのコピーで意味/統計/全Native費用/実資源を照合する。各20 QA/Groupと比較数/費用の整合、単独Cal importとDevelopment偽装/品質QAのEvaluation本文読込みの拒否、Rubric/統計計画/CLIの固定を検証し、新規21件を含む全674 Test/Ruff成功。合成通過は実主/Cal採用の証明ではなく、実主証明書→実Cal Protocol/実走/全採点・採用と最終N/条件/拡張Validator/凍結は未了。

[Calibrationの準備・実行入口](phase11_bilingual_calibration_execution.md)を追加した。主の全証拠を再検証してから元の予約/未使用性と条件を結び、共通RAGを各20 QA/5 QAずつ・1660 Call上限/Retry0で収集する。元Runだけの再開・他Runの利用済み保持、Protocol Hashを更新しても実主条件と異なる設定の拒否を検証した。新規20件を含む全653 Test/Ruff成功。実未承認設定はQA読込み前に拒否/新規Cal推論0で、実主証明書/実Cal Protocolの成功側とCal匿名採点・意味/統計Adapterは未了。

v13は同じ9B/24k/推論4096/判定6144と全原資料/Expected/基準で、中間読解を除く直接固定文照合を別登録した。全58条件/35文は同じで最大70 Call、通過時の旧15 QA/全42文/30条件は84 Call。新規上限154/既存9B74込み累積228/Retry0。元方式も保つ採用/予算Guardを対応し、計画Hash/全対象/実Leaf Callsを照合する。新規22件を含む全633 Test/Ruff成功。Native Core26+Probe1 Hash不変でv12の形式証拠を再利用し、新固定Worktreeの全70入力/生成0から確認する。採用は未確定。固定541d0d2のv13は全70入力/生成0 Preflightに通過。最大3348 Token、Context24576/全層CUDA、VRAM6525/8151 MiBは一点観測。準備1+Preflight4の5 Artifactを正規保存し、Native26+Probe1不変/形式v3の15 Artifactを照合後、同じ固定Worktreeで意味診断を開始した（session11515）。固定v13は全58条件/70 Callを終了し、既知4/4・人工英語24/24/日本語28/30・誤支持0で診断基準に通過した。再開/全Raw/費用/2不一致の監査・保存を行い、完了後だけ旧15 QA/全42文/最大84 Callへ進む。主/Cal採用は未確定。

[主Developmentの証拠検証](phase11_main_certification.md)を実装した。全匿名品質/文Expectedの封印後に全診断/旧15 QA回帰・主各20 QA・意味/統計/Native費用・実CUDA Sessionを隔離コピーで照合し、原本を保全する。新規27件を含む全611 Test/Ruff成功。実不通過v12の拒否と既知接続4 Sessionの資源検査は確認したが、実主証明書の成功側は未了。

固定51b0559の意味v12は20 Call/既知4条件でCritical3/4、元順序Council c4のExpected矛盾に対する支持不足で不通過。誤支持0でも正確一致基準を維持し、人工54未試行・入力95316/出力85176 Token・1424.971683秒/全41 Artifact/再開追加0を保存した。大きな予約でも全基準を満たさず、主/予約Calibrationは未推論。

その後、既知回帰v1は読解が配列で始まり条件付きJSON制約が未到達となって5/30条件で停止した。21 Call/他25条件未試行・再開追加0を保持。
[終了Tag境界の別候補v7](phase11_json_boundary.md)を固定し、人工Runtime検証後に同じ128 Call診断から再確認する。主Development/未使用Calibration・最終Gateは未了。

境界v7の人工検証は旧制約で配列回避を再現し、新制約ではObject開始後の空白反復で上限に達した（2 Call/入力94・出力656 Token）。
この失敗を保持し、空白を各位置最大2文字とするv8を別保存した。Nativeが保存WORDを単一TOKENへ変換する処理も一次資料から確認し、Tokenizer実測ID/保存Token/全文Grammarの一致を要求する。全510 Test/Ruff成功。GPU再検証は未実施。

固定43ccf05のv8は人工6 Call（厳密5条件すべて）を通過。全128予定入力/生成0 Preflight・CUDA全層も確認し、新しい日英意味診断を実走中。全結果/意味採用は未確定で、旧Expected/基準と失敗Runを保持する。

並行して[主Developmentの事前選定](phase11_main_development.md)を行い、旧入力70 File/使用済み62 ID・日本語予約142 QAの除外来歴から日英各20問/20 Groupを保存した。全514 Test/Ruff成功、追加Model Call0。主20問のRunner拡張/実行Protocol・採用前提・実走は未了。

主Development用の採用/選定/Policy Guard・原子Call上限1660/言語・新規5 QA/段階Sessionと中断再開を実装し、全536 Test/Ruff成功。主結果前のHealth/意味採用/全Label封印基準も保存した。実設定/新規推論は既知15 QA回帰の通過後とし、まだ主実走を行っていない。

v8は固定43ccf05の全58条件/128 Call・Critical4/4/人工英語24/24・日本語28/30/誤支持0を完了し、全259 Artifact/読解11行の問題・曖昧c6によるF6/7/再開追加0を保存した。旧Expected不変の既知15 QA回帰v2は、この新しい通過Reportへ前提を結んで事前検証済み。実GPU回帰はこれから。

既知回帰v2は形式/Runtime失敗0でも12 Critical中8一致・誤支持6により不通過。54 Call/残18条件未試行・再開追加0を保存した。日英全品質/固定文Labelの封印後にだけ内部と比較する監査入出力を追加し全545 Test/Ruff成功。次の[Qwen3.5-9B候補v9](phase11_qwen35_candidate.md)は条件固定/重みHash確認までで未推論。

9B v9は全128入力/生成0・CUDA全層の資源確認に通過したが、人工形式2 Callが推論未終了/出力上限で停止した。失敗/残4条件を保持し、意味診断は未実施。実入力に既にある開始TagをNative Budgetへ申告する[別候補v10](phase11_qwen35_candidate.md)を追加し、全555 Test/Ruff成功。Model/Prompt/Expected/上限/採用基準を保持して同じ人工検証から再確認する。主20問/未使用Calibration・Gate 11は未了。

固定645f193のv10は全128入力/生成0・全層CUDAと人工6 Callの厳密5条件すべてに通過。入力290/出力958 Token・生成16.712355秒、原本10 File/87 Source不変・監査追加Call/Server0、全16 Artifactを保存した。同じ固定Worktreeで日英意味診断v10を開始し、全結果/意味採用は未確定。旧Expected/採用基準と旧v9の失敗を保持する。

英語の元Calibration225問は全て検索条件調整済みのため再び未使用とせず、旧記録を保持する。[新しい日英Calibration用の別予約](phase11_bilingual_calibration.md)として、英語は未使用Developmentから主20 Groupとも分けた20問、日本語は元Calibrationから20問を結果非依存で保存した。元Source Splitと分析用途を区別し、Group/使用履歴/Hashを検証、全561 Test/Ruff成功。主Development採用後の専用実行Protocol/Runner・実走/全Label封印/集計は未了で、予約QAを方法調整へ使わない。

9B v10は4既知条件/20 CallでCritical3/4により不通過。元順序Councilの矛盾/支持不足の差、曖昧c6/Fの元逆差と全42 Artifact・再開追加0を保持した。新v11はJudgeへ再述を避け直接比較する一般Prefixだけを加え、旧Expected/全基準/予算等を保持して別登録。形式証拠は同一Model/Runtime/設定と27 Core/Probe Hashでv10を再利用し、新しい意味診断へ進む。主/予約Calibrationは未推論。

固定bb11fc9のv11は全128入力/生成0 Preflight・最大3887 Token/全層CUDAに通過。4 Artifact/形式証拠/27 Core HashとLaunchを固定し、同じ意味診断を実走中。全結果/採用は未確定、旧Expected/全基準を保つ。

主Developmentを実行する前の[採用Guard監査](phase11_main_adoption_audit.md)で、Policy候補と完全通過回帰の条件の直接一致、および全Health/意味/品質/判断の事前値・型/明示nullの検査を追加した。既存採用基準/入力は不変、新規23 Testを含む全584 Test/Ruff成功（既存の失敗起動時資源監視警告1件を保持）。実採用成功側/主20問・Calibrationの実走は未了。v11は固定bb11fc9のまま実走中。

固定v11も既知4条件/20 CallでCritical3/4・逆順の誤支持1により不通過。41 Artifact/旧Label/曖昧単位/全分母・再開追加0を保存した。[別候補v12](phase11_qwen35_candidate.md)は同じModel/指示/Expected/採用基準を保ち、推論4096・読解8192/判定/書換え6144・Context24576へ予約を増やす。費用が増える条件差を記録し、固定GPUの生成0/人工形式から再確認する。主/予約Calibrationは未推論。

固定51b0559のv12は24k Context/全128入力の生成0・CUDA全層と同じ人工6 Call/厳密5条件に通過。入力290/出力958 Token・16.687828秒、Source88 Hash/原本10 File不変/監査追加0・全15 Artifactを保存した。同じ固定Worktreeで意味診断v12を実走中、全結果/採用は未確定。

## 1. テーマと目的

現行候補は[固定文ごとの評価](phase11_claimwise_candidate.md)。初回回答全体を非信頼文脈として保持し、全固定文を個別評価して
元の全分母へ集約する。呼出し数と入力配置の変更を両言語で同じように扱い、費用と失敗を別に記録する。
旧共同評価/期待Label・採用基準を保持し、新方式の実GPU意味診断はこれから。
その後、同じ基準で固定文候補もCritical2/4と不通過を保存した。
主比較と欠測/文書Group Bootstrapの[統計事前計画](phase11_statistical_plan.md)を具体化・実装したが、件数/条件の最終凍結と新規Runへの解析は未了。
次は期待Label/採用基準を保持した[草稿なしの根拠読解候補](phase11_source_reading_candidate.md)を別計画で検証する。
その後、読解/全固定文・全分母/実費・中断再開と匿名品質への接続を実装し、全487 Test/Ruff成功。実GPU意味診断はこれからで、意味採用/最終凍結は未了。
その後、v5は読解1 CallでID/Quoteの対応不正を検出して停止した。v6へ一意ID/原文QuoteのDecoder制約を別保存し、Expected/意味採用基準を保持した。全488 Test/Ruff成功、v6実走はこれから。
その後、v6の既知Critical4条件は全一致し、人工54条件を実走中。意味Gate/採用は未確定。全Label封印後だけ内部を検証するDevelopment用統計接続を追加し全493 Test/Ruff成功。未使用Calibrationの実解析・最終件数/条件は未了。
その後、v6の全58条件が完了し、人工英語24/24・日本語28/30/誤支持0で診断通過。補助読解の誤り11行とF閾値による誤採用が残り、最終採用や品質改善は未実証。全旧GPU固定文と3旧誤りの回帰を事前固定し、全502 Test/Ruff成功。

現行の次工程は[意味判定・拒否Fallbackの診断](phase11_semantic_revision.md)。使用済み英語2例の4条件を先行し、
Critical全件一致した候補だけ日英の人工27例/54条件へ進める。採用・停止規則と最大58呼出し/候補を結果前に保存した。
期待Labelはモデル入力へ渡さず、主Developmentや未使用Calibrationの代わりにしない。今回のGPU診断はこれから。
その後、初期4BはCritical1/4一致・誤支持3/4で不通過、人工例へ拡大せず保存した。
予定した1つのPrompt改訂v2は主体・関係・時期・数の範囲を照合する指示へ変更し、旧Expected/基準・閾値・Model/予算は保持する。
その後、v2も2/4一致で不通過。計画内の8B公式固定版を取得/Hash照合し、同じPrompt/基準/予算の候補v3を用意した。
裸の拒否8問中3問の改善見逃しは保存候補による事後比較であり、Fallback候補の実装/未知QA検証はこれから。
その後、8Bも意味Critical2/4で不通過。初期3候補を不採用とし、基準を保持した[固定文ごとの次候補](phase11_claimwise_candidate.md)を計画した。
裸の拒否だけの一回書換えをnull Score/別経路で任意実装し、全459 Test/Ruffに成功した。事後再構成とProspective採用は区別する。

2026年10月21日追記: [日英共通RAG接続候補](phase11_bilingual_pipeline.md)を実装し、全441 Test/Ruffに成功した。
検索/初回/固定文評価/書換え/匿名品質の共通処理を再利用し、親Gold/欠測/参照来歴はOfflineに分離する。
親関連単位が英語元Passage・日本語記事と異なる点を明記し、Metricを意味支持の正解にしない。
現在は既知Development各1問の実機接続確認前であり、日英の意味監査・未使用Calibration・最終凍結は未了。
その後、日本語既知1問の11 Completion/全文固定/再開追加0を確認した。英語は生成前の旧Schema互換エラーを保持し、
条件を変えずFactoryを修正、全443 Test/Ruffに成功。英語再実走・匿名品質の照合と意味監査は次工程。
その後、英語も実走し、日英4候補をAI採点・固定後に内部照合した。各1問は全9試行で採用・品質1→1。
全3固定文は実Contextで支持と確認したが、既知肯定例の接続確認で、主Pilot・旧英語誤支持/拒否の解消を代替しない。
日英未使用Calibration・規模/統計・最終条件と拡張Validatorは未了。

**英語・日本語データにおける根拠提示順序に対するRAG自己評価の感度と修復判断への影響**

Evidence-Order Sensitivity of RAG Self-Evaluation and Its Impact on Repair Decisions
on English and Japanese Datasets

自己修復RAGでは、評価器の採点が回答を採用するか、書き直すかを決める。
質問・根拠本文・初回回答を固定し、評価器へ根拠を提示する順序だけを変えて、
評価値、修復の起動判断、最終回答の品質、処理コストへの影響を調べる。

2026年10月21日、英語CLAPNQに別の日本語データセットを追加し、同じ現象の再現性と
順序感度・品質・費用の差を比較する方針をユーザーが決定した。
翻訳した同一問題の比較は主実験に使わず、CLAPNQにできるだけ近い課題・長文回答・根拠・
検索Corpusを持つ日本語データをPhase 11で選定する。
同日、[候補比較と原QA構造監査](japanese_dataset_selection.md)により
`baobab-trees/wikipedia-human-retrieval-ja`を選定し、固定版の回答付き838件・回答なし433件を取得した。
記事全文Corpusは固定Commitの専用Checkoutで取得中。日本語の文単位候補と本文保持のTestを追加したが、
文書Group分割・検索/Model実走・予備検証は未完了であり、Source選定やComponent実装を条件固定とはしない。
内部QAへの取込みは838件で検証済み。全参照先と同文QAによる暫定706 Group・開発予約142件を得たが、
Redirect解決後の正式Splitは記事取得完了後に生成する。分割目標は英語と同じ65%/10%/25%・Seed42。
選定基準・比較上の制約・工程は[日英比較の拡張方針](english_japanese_expansion.md)による。
別Dataset間の比較なので、観測する差を言語そのものの因果効果とは断定しない。

直接の目的は、**修復判断に使う自己評価の不安定性と、影響が大きい/小さい条件を明らかにすること**。
より効率的で信頼できる自己修復の設計に役立つ知見を、将来への意義とする。
揺れを発見しただけで、信頼性や効率を向上させたとは主張しない。
対策の考案・比較と可視化Viewerは追加成果であり、主研究は現象と影響の分析とする。
参加者の募集・操作評価は行わないが、独立した回答品質の確認は実施する。

## 2. 旧方針からの変更と引継ぎ

| 項目 | 旧方針 | 今後の方針 |
|---|---|---|
| 中心 | 原因別修復による品質向上手法の提案 | 評価条件から修復判断・結果への影響の分析 |
| 自己評価 | R/F/Aの加重Score C | まず固定Claimの根拠性Score F |
| 修復 | 再検索・制約付き再生成・回答書換え | 元質問・使用Context・初回回答から1回のAnswer Rewrite |
| 比較 | Baseline / Always Query Rewrite / Adaptive | 修復なし / 常時Answer Rewrite / 評価条件別の採用・修復 |
| Dataset | 四種類の失敗条件の専用Subset | まず通常検索で自然に得るAnswerable QAと回答 |
| 主な証拠 | 品質改善・原因分類・Confidence校正 | 判断不一致、品質遷移、改善見逃し、費用、条件別の再現性 |

旧C=0.25R+0.50F+0.25A、個別Failure閾値、原因分類Rule、旧H1/H2/H3、常時Query Rewrite、
四種類各150件のDataset、ECE中心の比較は主実験へ継承しない。
旧Aは質問適合性であり、今回の「評価器への根拠提示順」と同義ではない。
F単独では質問への不足を見逃し得るため、その限界も独立品質で測る。
Source、Title単位Split、Corpus、検索・初回生成の既存条件、過去の検証記録は引き継ぐ。

## 3. 研究質問

| 問い | 測る内容 |
|---|---|
| RQ1 | 根拠順序変更は、同一順序の反復より評価・採用/修復判断を変えるか |
| RQ2 | 判断変化は、品質の改善・悪化、改善機会の見逃し、費用へどれだけ伝わるか |
| RQ3 | 根拠位置・支持の分散等で影響は異なるか。別の評価器でも確認できるか |
| RQ-L（日英比較） | 英語CLAPNQと仕様を近づけた日本語Datasetで、順序による判断不一致の増分と品質・費用への影響は異なるか |
| RQ4（追加） | 限られた追加評価で品質と費用の関係を改善できるか |

主比較はRQ1の順序変更群と同一順序反復群の判断不一致の差を言語別に求めることと、
RQ-Lのその増分の日英差である。日英のQAは独立で、対応する翻訳対とは扱わない。
RQ2は主研究に必須とし、Scoreの揺れだけで結論を終えない。
影響が小さい結果も報告するが、未検出と不存在を区別し、信頼区間と測定範囲を示す。

## 4. 基盤と現状

以下は既存の英語CLAPNQ基盤と初期確認の条件。日本語へ対応済みの条件ではない。
日本語のSource・Split・検索等はPhase 11で選定・検証し、旧Manifestを上書きせず別Versionで保存する。

| 項目 | 維持する条件・確認済みの範囲 |
|---|---|
| Source | CLAPNQ公開Train/Dev 4,345 QA、Revision c508d78d8c5c2eecbf172fcf5f789004206e11fb |
| Corpus | 固定178,890 Passage Records。AnnotationのGoldを推論へ直接投入しない |
| Split | c508d78-split-v1、Seed 42、Wikipedia Title単位。Development 2,824 / Calibration 434 / Evaluation 1,087 |
| Answerable | Development 1,465 / Calibration 225 / Evaluation 564。主実験の母集団候補 |
| 検索 | BM25 + 固定MiniLM ONNX、等重みRRF、候補50件/方式、定数20、Top-10 |
| 初回生成 | Qwen2.5-3B-Instruct GGUF Q4_K_M、固定Revision、llama.cpp b11433 Windows CPU |
| 生成条件 | Context 4,096、出力512、本文各512 Token、温度0、Seed 42、6 Threads、既存英語Prompt |
| 実走 | 固定Development 5問のHybrid検索→生成→保存。平均56.96秒/問。品質比較ではない |

Hybrid Success@10はCalibration 225問で0.7822とEmbeddingと同じ、nDCG@10は0.5317で
Embeddingの0.5519を下回った。検索精度改善は主張しない。
5問のSmokeにはUnanswerableも含まれ、新しいAnswerable Pilot 20〜30問の完了ではない。
Ubuntu/GPU実行は第10節の別Versionで確認済み。自己評価器の最終採用、本実験規模の完走、
日本語対応は未確認。
詳細は[Phase 4](phase4_retrieval.md)、[Phase 5](phase5_baseline.md)、[Phase 6](phase6_hybrid.md)とManifestによる。

## 5. 固定回答による比較

```text
検索 → 元順序で初回生成 → 質問・実使用Context・回答を固定保存
                          ├→ 根拠順序を変えて評価 → 採用/書換え判断
                          └→ 固定の書換え候補を1回生成して保存
独立品質評価 → 各判断が選ぶ初回/書換え候補の品質と費用を比較
```

評価器へ渡すのは初回生成の`used_context`の同じ本文・Title・Passage IDと同じ回答。
取得全文Top-10と実使用Contextを区別し、順序ごとに検索・回答生成・本文切詰めをし直さない。
文書集合・本文Hashの同一性と全Promptの入力予算を検証する。
生成器の順序感度や情報欠落を、評価器の順序感度と混同しない。

Pilot初期条件は元順序、逆順、固定Shuffle 3通りと、元順序の合計5回の反復。
両群は各5回で元順序の初回を共用するため、実呼出しは原則9回/問/評価器となる。
少数文書で順序が重複する場合は異なる順序数を記録し、5順序あると装わない。
呼出し実行順はSeedで無作為化し、Model・温度・Seed方針を両群でそろえる。
最終の試行数・順序数はPhase 11で固定する。

### 5.1 評価器と判断Rule

初回回答だけから事実Claimを一度抽出・保存し、同じClaim列を全順序・反復で検証する。
初回Pilot後の修正候補は[文単位の固定主張](phase10_measurement_revision.md)である。
決定的な文分割によって本文の網羅性を保持し、LLMによる原子的な分解・言換えは行わない。
この候補ではFを「支持された文単位数/固定文単位総数」と定義する。複合文は全詳細の支持を要求する。
旧来の原子的Claimを目指した抽出とは分母が異なるため、新Versionとして比較範囲を区別する。
抽出へ根拠やGoldを渡さず、Claim抽出の揺れを主比較へ混ぜない。
Claim Labelは`supported / contradicted / not_supported`。
F = supported Claim数 / 固定Claim総数。支持割合であって正答確率ではない。
初回Pilotの評価器はGeneratorと同じ固定Qwen2.5-3B条件だった。修正では初回生成3Bを維持し、
Judge/書換えの7B候補を別Runで検証する。妥当性を確認してから本実験へ固定する。
7Bでも長文の意味判定・引用形式に問題が残ったため、Qwen3-4Bの補助評価候補を追加した。
文単位の評価、二つの支持/矛盾チェック、推論予算と引用IDの扱いは
[測定系修正記録](phase10_measurement_revision.md)に履歴・制約を含めて記載する。
自己評価はRAG内部の評価機構を指し、GeneratorとJudgeの同一Modelという条件は今回から外す。
別系統の評価器による確認は追試として区別する。Modelの最新性や規模だけを有効性の根拠にしない。

Phase 7の初期条件は[専用Protocol](phase7_order_protocol.md)、`configs/order_pilot.yaml`、
`configs/order_prompts.yaml`へ具体化した。補助TaskのContextは8,192、最大出力は
Claim抽出1,024・根拠検証1,536・書換え512とする。初回Baselineの4,096/512は変更しない。
保存済み3問の21入力Probeで6件が4,096を超え、最大入力+出力予約が5,748だったため、
本文を削らず比較するための予算として変更した。Phase 8で固定Trace・Claim抽出・Judge・順序/反復・判断を実装した。
実走で初期Promptの空Claim/不正JSON/引用表記の不備を確認し、元の設定を維持したまま
`configs/order_phase8_v5.yaml`と`configs/order_prompts_phase8_v5.yaml`へ開発版を分けた。
JSON形式と引用候補のDecoder制約を全順序へ共通適用し、そのSchemaも順序から独立して固定する。
この制約付きJudgeを測定対象とし、自由出力のJudge全般へ直接一般化しない。
出力の反復を避けるためClaimごとに引用最大2件・理由最大200文字とし、この上限も妥当性監査の対象とする。
変更理由・実走結果・意味上の監査範囲は[Phase 8記録](phase8_order_evaluation.md)による。
構造上有効なClaim/引用でも、網羅性・支持判定・質問への適合性が正しいとは限らない。
各実入力の予算を都度検査し、全文を保持する。全QAの収まりやJudge精度の検証は後続工程で行う。

初期閾値τ=0.7、F>=τで`accept`、F<τで`rewrite`とする。
旧加重Cの0.7とは異なるRuleであり、Pilotの出発値である。維持/変更の理由と最終値をPhase 11で固定する。
Evaluationで判断が最も揺れる値を選ばない。事前の感度分析候補は0.5/0.6/0.7/0.8/0.9。
空回答、拒否、事実Claimなし、抽出/評価失敗は区別し、Fを1や0へ強制変換しない。
`unscorable`では初回回答保持のFallbackを記録し、品質上の採用とは区別する。

### 5.2 書換え

元質問・同じ使用Context（元順序）・初回回答から、誤りや不足を点検し回答全体を1回書き直す。
変動する評価Score/Feedback、並べ替え後のContext、Goldを渡さない。再検索はしない。
回答候補の生成は最大2回、修復後の再評価による選別・追加修復はしない。
同じ質問の全評価条件で同じ書換え候補を共用し、起動判断の影響を分離する。
既存の初回Promptも根拠限定なので、初回回答を点検・修正する入力を加えることを修復の差分とする。
固定Seed一つの書換えの効果であり、任意の修復方式・生成Seedへの一般化はしない。

## 6. 独立品質と比較方式

ユーザーの指示により、開発・本番ともCodex AIが条件名・Score・判断・回答段階を伏せた候補を固定基準で確認する。
人手の再採点を次工程の必須条件にしない。内部Qwen JudgeのFと外部AIによる品質Yを分ける。
詳細は[AI品質Protocol](ai_quality_protocol.md)。AI採点による品質推定であり、人手正解との一致を実証したとは扱わない。
Y=1は質問の必須要点、重大な事実誤りなし、事実Claimの実使用Contextによる支持を全て満たす回答。
それ以外はY=0、判定できない場合は`indeterminate`。理由・根拠箇所を残す。
Referenceとの表現一致は必須でない。自己評価のClaimや判定を品質の正解に流用しない。
採点AIの誤り・指示文依存・単独採点の制約を明記する。人間同士の一致や完全な盲検を実証したとは扱わない。
採点資料はReference/Goldを含め、内部F/判断/条件/段階を除く。採点側のContext順序は元順序に固定する。
本番は専用セッション・モデル識別子・入力/出力の保存を準備し、固定できない条件は限界として報告する。
Pilotは新しい内部結果を伏せた同一作業セッションでの採点を許容するが、完全な履歴分離とは主張しない。

| 初回Y0 → 書換えY1 | 意味 |
|---|---|
| 1 → 1 | 正答維持。修復の追加費用を測る |
| 1 → 0 | 書換え起動による悪化 |
| 0 → 1 | 書換え見送りによる改善機会の喪失 |
| 0 → 0 | 今回の修復では正答化できない |

「初回が誤り」と「今回の修復をすべき」は同義ではない。
比較は修復なし、常時Answer Rewrite、元順序単回評価、各順序/反復の単回評価。
同じ初回/書換え候補から選び、採用/修復の判断による差として解釈する。
追加対策では同一順序反復集約、順序変更集約、閾値付近への追加評価、同件数の無作為追加対照を
共通上限予算と品質・費用で比較する。平均化自体を新規発明とはしない。

## 7. 指標・統計

- 主判断不一致: 固定した試行集合内の有効ペアで`accept/rewrite`が異なる割合を質問ごとに集計し平均。
  順序変更群と同一順序反復群の差が主比較。全ペアを独立標本とは数えない。
- 判断反転例率: 少なくとも一度両判断が現れた質問の割合。試行数依存なので回数・有効数を併記。
- 品質: 最終信頼可能回答率、Y0→Y1の四遷移、正答悪化、改善可能例の修復見逃し。
  悪化は全対象あたり/初回Y0=1あたり、見逃しは全対象あたり/Y0=0,Y1=1あたりを区別。
- 費用: 初回、抽出、評価、書換え、補助・再試行を含むCalls/Input・Output Token/Latency。
  実験全体の収集費用、各方式の運用経路費用、独立採点の費用を分ける。Cache再利用を修復費用0としない。
- 失敗: 全対象、両群が有効なQA、採点不能、実行失敗、品質判定不能の件数と理由。

主判断比較は両群の必要試行が有効な共通QA。条件ごとの有効例への偏りを明示する。
Fallback込み品質・費用は全対象でも集計し、共通判定可能QAの対応比較を併記する。
品質不明は分母・理由と未知を良い/悪い側へ振った感度分析を示す。分母0は適用対象外。
元質問単位の対応を保持し、同一Titleの依存がある場合はTitleをまとめた再標本化で95%信頼区間を出す。
Evaluationは現行Splitで1 QA/Titleだが、Developmentにも同じ独立性があるとは仮定しない。
主比較・検定・少数の条件別分析を事前に固定し、有意な条件だけ選ばない。
閾値付近で反転しやすいこと自体はRuleから予想されるため、それだけを新知見にしない。

日英比較では、上記の質問内不一致率の差の言語別平均と「日本語 − 英語」の差・95%信頼区間を示す。
各Dataset内のTitle/文書Groupの依存を保ち、日英の独立な質問同士を対応Bootstrapの対にしない。
片方だけの有意差を言語間の差とは解釈しない。品質・費用・欠測も言語別に集計する。
回答長・文単位数・根拠数・検索品質等の差を記録し、条件別分析・統計手法・主比較の多重比較の扱いは
Phase 11で固定する。詳細は[日英比較の拡張方針](english_japanese_expansion.md)第5節による。

## 8. Data運用・対象範囲

Development Answerable 20〜30問でPilot。本実験100〜200問程度は作業量の候補で、必須件数や検出力の保証ではない。
IDの選定Rule・Seedを結果を見る前に固定し、Calibrationで設計を確定した後に内部Evaluationを実施する。
検索Calibrationへ同じCalibration Splitを既に使った履歴を残す。内部EvaluationはCLAPNQ公式Testではない。
UnanswerableのCorpus-level監査、人工Distractor、原因分類Datasetは主実験の必須工程から外す。
元LabelをCorpus全体の回答不能と解釈しない。正解情報は評価器・修復器へ渡さない。
条件別分析候補は支持根拠位置・分散、回答/Claim数、元順序Scoreと閾値の距離。
Selected SentencesはReferenceごとの代替根拠を保持し、欠損と代替支持を監査してから位置Labelを確定する。
Gold未取得だけで根拠不足を確定しない。詳細なSource/License/SchemaはDataset Guideによる。

日本語データの候補比較・取得・Split・日本語対応・少数予備検証とCalibrationもPhase 11で行う。
調整用と未使用Evaluationを分け、同じ内容・順序のみの操作と独立AI品質採点を日本語でも検証する。
既存の英語200問案を日英合計/各言語の件数へ読み替えず、言語別の有効比較数・精度・費用から決める。
両言語の対象・設定・統計を固定してからPhase 12の本実験へ進む。

## 9. 新規性・限界

[関連研究](related_research_positioning.md)と[投稿可能性調査](iciae2027_pivot_feasibility_review.md)を参照する。
評価の揺れ、順序感度、Judgeの誤りから結果への影響、固定候補による比較自体は既存。
貢献候補は、評価器側の根拠順序のみを操作し同一順序対照と比べ、一回修復の起動・品質・費用への影響と
発生条件を再現可能に示す実証的知見である。新規性・有効性は未実証。
現時点の実測は英語一Datasetのみ。拡張後も各言語で選定したDataset、限定したGenerator/評価器、
固定書換えSeed、単独品質採点の範囲を明記する。日英で別Datasetを使うため、
言語と課題・文書・回答形式等の差を完全に分離した実験ではない。日本語追加だけで新規性を実証したとはしない。
Viewerは点検と説明の補助。参加者なしで使いやすさや理解度向上を主張しない。

## 10. 投稿と現在地

[ICIAE公式投稿要領](https://www2.ia-engineers.org/iciae2027/paper-submission/)を2026年10月18日に確認。
通常初回は2026年11月20日、英語4〜8ページ、通知12月11日、最終原稿2027年1月8日。
会期は3月26〜30日。1月を初回要旨締切として計画しない。
作業・成果物・Gate・期限は[ロードマップ](research_roadmap.md)による。
**Phase 1〜10の開発確認、Phase 11のCUDA対応とGPU20問/40候補AI採点・34単位監査を完了。
完全比較12問だが意味妥当性の採用と分析規模は未確定。10月21日に日本語Dataset追加方針を採用したが、
日本語Sourceの選定・原QA取得・構造監査まで実施。本文Corpus・分割・実対応・検証は未実施。
Gate 11未通過、最終凍結・Phase 12は未実施。**
ユーザーのAI採点委任を受け、Gate 9はAI代行で候補・判断・品質・費用を照合する開発ゲートへ改訂した。
人手確認を達成済みへ書き換えず、採点方法を更新した理由と限界を別記録に残す。本実験は未実施。
2026年10月19日、ユーザーの委任により[開発3候補をAIが代行採点](phase9_ai_quality_review.md)し、
JSONを保存した。人手確認済みのYや本実験の成果には置き換えない。Yの意味上の3観点は維持する。
同日の[Phase 10結果](phase10_pilot.md)では、完全比較11問のうちFの順序変化1例、判断反転0例だった。
既知品質ペア18問では0→0が7、1→1が11、0→1/1→0は0。不明2問を改善へ数えない。
事実本文の空Claim、抽出漏れ、調印/発効時刻の誤支持があるため、このまま本実験条件を凍結しない。
Phase 10内で評価の妥当性・修復能力・出力予算を確認し直す。効果を作るための閾値変更はしない。
[測定系修正と新規10問の再確認](phase10_measurement_revision.md)を実施し、完了状況と残る制約を別記録に残す。
明確な判定15例、人工3例・自然2例の書換え、長い7主張の形式・予算を診断済みである。
新規10問の全品質Labelを固定してから内部F/判断を開いた。[結果](phase10_recheck_results.md)による。
元v14の事前Gateは引用重複1件のため不通過として保持した。後処理v15では同一IDの重複のみ整理し、
保存出力を事後に再検証した。元の完全比較3問・派生検証4問、順序判断反転1問・同順序反転0問だった。
Astrosの反転は元v14でも有効で、改善見逃しへ伝わった。品質改善3問のうち別2問は拒否Fallbackによる見逃しだった。
Phase 10の開発確認はこの区別を含めて完了とし、事前Gate成功や一般精度向上を主張しない。

2026年10月20日、[Phase 11の準備](phase11_calibration.md)を開始した。
Calibration Answerableから結果非依存で異なるTitleの5問を選ぶ初期バッチを設ける。
本番件数を5問に決めたものではなく、十分な意味妥当性や検出力を保証する件数でもない。
モデル・Prompt・閾値0.7・拒否FallbackはPhase 10修正後を候補として引き継ぎ、今回変更しない。
新しいSplitとRunへ分け、品質採点前の内部結果の非開示、失敗の非補充、再試行0を維持する。
Windows CPUの確認と、本番GPU環境の確認・最終固定を区別する。Evaluationは開かない。
候補Manifestの作成や実行面のHealth Gate通過だけでGate 11通過とはせず、
残る意味誤り・拒否・外部AI採点・実行環境・規模・統計の決定を終えてから最終固定する。

同日、ユーザーの指示で[最終固定の本実装](phase11_finalization.md)とCPU Calibrationを進めた。
本番は研究室PCのGPUを使い、実機情報・環境整備は研究室側のCodexで確認する方針をユーザーが指定した。
CPUの確認をGPUの確認に代用せず、GPU実Offload・実生成・Calibrationと件数/Runtimeの確定後にGate 11を判定する。
最終固定の検証処理は、未採点の内部結果を開かず、全品質固定後に候補・元Task・品質・集計を照合する。
実行Health Gateと意味妥当性を別に確認し、未達なら最終Manifestを作成しない。
本番対象IDは固定SplitのIDメタデータから結果非依存で選び、主比較・分母・欠測・統計とともに保存する。
CPU初期5問の初回は全て拒否で、新規Judge呼出し0・比較可能0となった。順序効果の有無を判定しない。
書換えでAI品質が改善した2問も現行Fallbackでは初回を保持した。元のHealth Gate不通過を保存し、
未使用の追加Calibration 20問を事前選定した。GPU側の実行条件・新しいHealth Gateは新規結果を見る前に固定する。
[Phase 9記録](phase9_answer_rewrite.md)に実出力・採点手順・検証範囲を示す。
全条件が採用/採点不能でも比較用書換えを1つ収集し、判断に応じて同じ二候補から出力を選ぶ。
初回と書換えが完全に同じ質問・回答・Contextの場合は、品質Labelを共用して重複採点を避ける。

同日、Ubuntu実機の転送・モデルHash照合とCUDA対応を別Versionとして実装した。
[研究室PCの検証記録](phase11_lab_validation.md)に実測と取得条件を保存する。
旧CPUと同じToken列のDevelopment入力でも過剰拒否が残った。初回Promptの変更候補は
既知例で重大な誤りも生成したため、Calibrationには採用せず、初回3B/元Promptを維持する。
GPUだけによる品質改善は主張しない。
補助Judgeの512 Token推論は既知例で途中終了し誤支持したため、推論1536/全出力3072を
候補v2で検証する。これは時間・生成分布が変わる変更で、旧CPU条件と混合した率を算出しない。
モデル・量子化・F・閾値0.7・文単位・順序/反復・初回保持Fallbackは維持する。
未使用20問は元の事前選定Manifestを保持し、Health Gateを実行前に保存してから使う。

2026年10月20日の[GPU追加Calibration結果](phase11_lab_validation.md)では20問/40候補の採点を固定し、
Judge108回・完全比較12問・Health Gate通過、全34固定文のAI意味監査まで完了した。
順序判断反転1/12・同順序反転0/12を確認したが、明確な誤支持が残り最終条件の採用は保留する。
本番200問・元/逆/Shuffle3種・同順序5回・Title対応Bootstrap10000回/95%CIは案で未凍結。
今回の20問を未使用へ戻さず、別の未使用20問を事前選定した。新候補の回帰診断と条件保存後に確認し、
意味妥当性・分析規模と最終ManifestがそろうまでGate 11を通さず、Phase 12は開始しない。

2026年10月21日、日英比較への拡張を決定した。Phase 11に日本語Datasetの選定・取込み・
検索/文分割/拒否/指示文/入力予算等の対応・予備検証・英語側の回帰確認・両言語の条件固定を追加する。
Phase 12で日英の本実験と独立採点、Phase 13で統計と比較考察、Phase 14で論文・卒論へ反映する。
今回は方針の文書化のみで、既存コード・設定・Run・Manifest・品質Labelを変更していない。

同日のGoal実行では[日本語Source選定](japanese_dataset_selection.md)と
`phase11_japanese_source_selection.json`を保存した。日本語Referenceは人手の段落・文ごとの引用対応を持つ。
引用断片のみのOracle条件へ切り替えず、全検索記録の記事全文から共通Corpusを準備する。
複数記事の引用を介する文書Group、引用と人手要約の違い、記事時点・規模・検索品質を確認する。
回答なし433件はCorpus全体の回答不能とは扱わない。これらの整備と日英実走・最終固定はこれからである。

同日、[日英共通の検索候補・本文分割の確認](phase11_multilingual_retrieval.md)として
固定版Multilingual E5 smallの公式FP32 ONNXとSubword BM25、512 Token以内の全文保持を実装した。
既知開発1記事の検索まで動作したが、検索品質や日英RAG全経路の検証ではない。
英語Corpusにも新Tokenizerの上限超過が3130/178890 Passageあり、元の参照IDを保持した別Versionの分割と
新Index・Development回帰・未使用Calibrationが必要である。旧英語条件・Runは保持し、最終採用を保留する。

同日の[Corpus準備・欠測/親参照の監査](phase11_corpus_preparation.md)で英語を183889 Passageへ分割し、
全親の本文保持と元Gold親2074種類の対応表欠落0を確認した。元の質問・回答・Split/Gold IDは変更しない。
子Passageが同じGold親を繰り返しても独立した関連文書として加算しない。実際の支持・品質は使用Contextで別評価する。
日本語の削除本文の権限エラーは原失敗を保持し、Identityと保存応答を確認した本文欠測として別記録する。
QAを除外・回答不能化せず、別時点の本文を補わない。正式Corpus/Index・新RAG接続と日英の実走はまだ完了していない。

その後、日本語の全2178 Title取得と正式Group分割を完了した。成功2126記録は2118種類のPageに対応し、
取得不能50・指定削除本文エラー2を保持した。全838 QAを706 Group、開発545/Calibration84/Evaluation209へ分割し、
Group間Identity重複0・開発予約142 QAの開発専用配置・原質問/Reference/行Hash保持を検証した。
全6494 Rawを正規配置へ同一Byteで複製した。根拠は`phase11_japanese_snapshot_group_manifest.json`。
記事Passage/Gold対応は未了で、Evaluation209件を本実験の確定件数とはしない。最終Gateも未通過である。

同日の[多言語Embedding CUDA監査](phase11_embedding_cuda.md)で、GPUを明示した正式Encoder/CLIと
専用uv Lockを整備した。合成入力の実CUDA演算とCPU数値差、既知1記事のIndex構築/再開/検索を確認した。
CPU既定・旧条件/Runは保持し、全Corpus Indexと日英RAG/Calibrationの確認までは最終採用を保留する。

同日の[日本語共通Corpus生成](phase11_japanese_corpus.md)で、全2118記事を30065 Passageへ分割し、
元本文22341944文字・全子のSpan/Hash/実Token上限・全Raw6494ファイルの保持を独立確認した。
QA/Referenceは入力にせず、全838 QAと元Splitは保持した。日本語の記事親と英語の元Passage親は粒度が異なり、
各子の完全な支持を仮定しない。Corpus規模などのDataset差も報告する。QAとの親記事/引用/人手要約と欠測の対応は次工程。

その後、同じ固定Commit・専用uv Lock・GPU条件で日英の全Corpus Embedding Indexを構築し、
全Vector・ID/Offset/元親対応と再開追加0を確認した。[全件Index記録](phase11_bilingual_indexes.md)による。
これは検索基盤の動作/完全性の確認であり、QAの検索精度・日英RAG品質/意味妥当性・Calibrationの完了ではない。

同日の[日本語参照監査](phase11_japanese_evidence.md)で全838 QAの原Field/Group/Splitを保持し、
引用元の記事親と、実際に確認した引用Spanに重なる子を別々に保存した。欠測25 QA（利用可能な引用元本文0は9 QA）を保持する。
人手要約や未一致を回答不能に変換しない。開発予約3例の脚注表示差を確認し、原HTMLから位置を証明する別Versionは次工程。
日英のBM25全構築・同Corpusでの合成Hybrid動作も確認したが、アプリケーションRAG接続/検索品質/意味監査は未完了。

その後、[原HTML脚注の投影v2](phase11_japanese_evidence.md)で脚注の実位置と本文の全文字対応を検証し、
引用位置確認は1493/1741参照になった。未一致116・原文なし102・原文引用あり本文欠測30も別保存した。
原838 QA/Group/Split、欠測25 QA/全引用元本文欠測9 QA、Corpus/Indexとv1を保持する。
原文形式の来歴確認であり、意味支持/品質の認定ではない。新RAG接続・意味監査・未使用Calibrationは次工程。
