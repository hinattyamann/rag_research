# 研究のフェーズ・現在地・次に行うこと

更新日: 2026年10月23日。正本: [研究計画7.67](rag_research_plan.md)、[実装計画8.70](rag_implementation_plan.md)。
テーマは「英語・日本語データにおける根拠提示順序に対するRAG自己評価の感度と修復判断への影響」。
本書を今後の作業順序とGateの正本とする。過去の日誌・Phase記録は当時の記録として保持する。
別チャットから再開する場合は [再開用引継ぎ](codex_handover.md)で、関連記録とローカル生データの場所を確認する。

## 1. 今どこまで終わっているか

[Q6旧全回帰v8の不採用結果](phase11_known_trace_direct_result_v8.md)を保存した。固定262ba08/session61821は12条件/42 Call・Critical8/12・誤支持3で終了し、残18条件未試行。媒体の元S/逆C、暖鋒逆c1のS→C、語源元c1のNS→C/両c2の誤支持を保持し、確定34/40・支持23/24、全74/58精度nullとする。95 Source/元59 File不変・追加Call/Server0、全42独立Schema/21組・全理由/6 QA Sourceと資源648点/エラー0・最大GPU7674/8151 MiBを監査した。Raw62/全144 Artifactを正規保存・WT照合し、Main準備CLIも早期拒否/出力0。全9B記録試行756/旧未知1/今回未使用42・旧42/81/42を保持。次はtemperatureだけ1.0→0.2の候補v20を別上限へ登録する。全154 Message/全旧条件/基準/Core27・実95 Source不変、全761 Test（29.32秒）/Ruffまで確認したが、新候補のNative実走はまだ未実施。Main/予約Cal/最終凍結は未了、Gate 11未通過・Phase 12未実施。

14:10 JSTに[Q6旧回帰v8](phase11_qwen35_q6_known_execution_v1.md)のTom元c5でNS→Sの確定誤支持1を確認した。radio/miniseriesをfilmへ広げており、現候補はMain基準未達。部分AI v3/元6 File不変をphase11_qwen35_q6_known_partial_failure_v1.jsonへ保存。同じ61821で残る負例条件を登録どおり継続し、全結果/実費は終了後に確定する。全Expected/基準/分母を維持し、Main/予約Calへ進まない。全終了後だけ全監査/正規保存を終えて次の候補を検討する。Gate 11未通過、Phase 12未実施。

[Q6旧全回帰v8の実行記録](phase11_qwen35_q6_known_execution_v1.md)へ、先行Council/Zidane4条件/16判定の部分AI確認と実Main準備の未完了拒否を保存した。全16 Message/Schema/最終判定は親Q6と同一、全理由/20 Source Passageを確認。実未完了Runは固定WTのMain準備関数がJSON入力/Lock/再検証/選定/Runner前で拒否し、ROOT Overrideなし・出力0・元20 File不変・実95 Source一致。全7 Artifact/Ruffを保存・WT照合し追加推論/未使用QA読込み0。曖昧/F/理由断片を保持し、全回帰採否は未確定。同じsession61821を継続観測し、終了後だけ全監査/正規保存を行う。

[Q6の暫定資源見積り](phase11_qwen35_q6_resource_estimate_v1.md)を完了70 Callだけで計算した。全195 Artifact/実95 Source・実費/算術/Ruffと全7 Artifactを検証し、平均54.566118秒/Call。各20 QA・平均5文・9試行の仮定ではJudgeだけMain24.5〜36.6時間/同規模Cal込み49.0〜73.2時間で、群平均の記述的な幅を上限/CI/総経過保証にしない。旧1660 Call/言語を維持し、稼働中61821の途中費用は含めない。追加推論/新Policy/新規QA読込み0、全旧回帰採用前にMainを開始しない。次は同じ61821の継続観測・終了後監査である。

[Q6旧全回帰v8の実行記録](phase11_qwen35_q6_known_execution_v1.md)を再開先とする。262ba08をCommit・通常Pushしリモート一致後、固定WTへ1404 File Binding/57不変Hardlink/内部相対Symlink10・Offline58 Packageを再現。全84実入力/生成0・最大3927 Token/12k/全層CUDAに通過し、全84 Token数も旧Q5と一致した。Runtime一点7582/8151 MiB、5秒6点/エラー0の観測最大7583 MiBで、連続Peak/安定性保証とはしない。全14準備ArtifactとCore27/新Q6形式37/親全意味195を照合し、同じ固定WTで観測付きsession61821を開始した。元Source25/全Expected/基準/曖昧/裸拒否8・最大84/累積798・Retry0を維持し、負例12条件の全一致後だけ残18条件へ進む。採否は未確定、同じHandleを観測し終了後だけ監査/正規保存する。Main/予約Cal/最終凍結は未了、Gate 11未通過・Phase 12未実施。

[Q6全意味結果と旧全回帰v8](phase11_qwen35_q6_semantic_result_v1.md)を保存した。固定cf489d9/session98160は全58条件/70 Callを正常終了し、Critical4/4・英語24/24・日本語28/30・誤支持0で元基準に通過。留保なし由来のNS→C2、曖昧Council c6の元C/逆NS・両F5/7、理由断片を保持した。全68確定Labelは旧Q5と同じで改善を主張しない。入力140500/出力189936・Task秒和3819.628270秒、95 Source/元133 File不変・追加Call/Server0、全70独立Schema/35組不変/全理由・Sourceを確認。資源766点/取得エラー0・観測最大GPU7672/8151 MiB/最小Host Available4134612 KiBを再計算し、Raw136/全195 Artifactを正規保存・WT照合した。親136 Fileのコピー上で全再検証後、同じ旧全15 QA/42文/30条件・84 Call/Source25/全Expected/基準/裸拒否8へ前提を結び、v8を実生成した。全761 Test（28.72秒）/Ruff成功。事前登録v16は既存v15の条件付き84だけで、記録試行714/累積上限798・Retry0、旧未知1/未使用42/81/42を保持する。次は新固定WTで全84入力生成0/全層CUDAと旧全回帰を実走する。Main/予約Cal/最終N/資源/条件/凍結は未了、Gate 11未通過・Phase 12未実施。

Q6のsession98160は12:35 JSTに6/58条件まで進み、既知Critical4/4完全一致を終えて人工条件へ進行中。全採否は未確定。[実行記録](phase11_qwen35_q6_execution_v1.md)に、全通過後だけ使う旧全回帰v8準備Helperと実未完了親の早期拒否を追加した。Config/Lock/再検証に入る前で停止し出力0、元15 QA/42文/Source25/Expected/基準/裸拒否8と実Native95 Sourceは不変。構文/Ruff・全7 Artifactを保存し、追加推論0。正の引継ぎ/実回帰v8・Main/Cal/最終凍結は未了である。

[Q6実機実行記録](phase11_qwen35_q6_execution_v1.md)を保存した。固定cf489d9の新WTへ1191 File Binding/57不変Hardlink/内部相対Symlink10・Offline58 Packageを再現。生成0の全70実入力/最大3793 Token/12k/全層CUDAに通過し、全11 Artifactを正規保存・WT照合した。同じWTの新Q6形式10 Callは全9 Strictに通過、入力630/出力1768・生成秒和37.804830秒。92 Source/元14 File不変・追加Call/Server0、独立Native JSON/Grammar/Token位置と資源を監査し、Raw16/全37 Artifactを正規保存・WT照合した。NativeはQ6_K/33層CUDA、Runtime一点7589/8151 MiB、形式13点の観測最大7601 MiBで、連続Peak/意味精度とはしない。全58条件/最大70 Callを同じWTで観測付きsession98160として開始し、採否は未確定。開始前全9B記録試行644/累積上限798・Retry0、旧未知/未使用を保持。実Main/予約Cal/最終凍結は未了、Gate 11未通過・Phase 12未実施。

[Q6の別候補v19](phase11_qwen35_q6_candidate.md)を登録した。同固定Revisionの7458301152 Byte/公開SHA256を全体照合して取得し、v18からStudy Version/Model Manifestだけを変更した。全154 Message・日英Prompt/Context12288/Task予算/Sampler/全対象/Expected/基準とCore27は不変。全761 Test（29.18秒）/Ruff、旧不採用93/親意味182/資源13/Main準備18 Artifactの再照合も成功。事前登録v15は記録試行634から新形式10＋意味70＋通過時だけ全旧回帰84＝最大164/累積上限798・Retry0で、旧未知1/旧未使用42/81/42を保持する。追加Model Call0、実Q6の生成0全層CUDA/新形式/意味/旧全回帰は未実施である。次はCommit固定の専用WTへ再現し、実入力生成0から確認する。Main/予約Cal/最終凍結は未了、Gate 11未通過・Phase 12未実施、Goal継続中。

[12k旧全回帰v7の不採用結果](phase11_known_trace_direct_result_v7.md)を保存した。固定5f4a6b6/session64437は12条件/42 Callを終了し、Critical一致9/12・誤支持3、残18条件は未試行。Tom元c5の媒体一般化1、Tar両c2の関係補完2が誤支持で、Tar両c1の支持不足→矛盾2と暖鋒元c2の理由の表誤読も保持した。確定35/40/支持24/24、全74/58精度はnull。入力148888/出力153689・Task秒和2827.888992秒、95 Source/再開59 File不変・追加Call/Server0。全42 Native JSONの独立Schema/21組不変・全理由/6 QA Sourceを確認し、Raw62/全93 Artifactを正規保存・WTとByte照合した。資源569点/取得エラー0・観測最大GPU6898/8151 MiB/最小Host Available4323548 KiBを再計算。全9B記録試行634（Q4 317/Q5 317）/旧未知1・今回未使用42/旧81/42を保持する。Main準備CLIも今回の正規ReportをQA読込み前に拒否した。[同じRevisionのQ6資源調査](phase11_q6_resource_feasibility_v1.md)は公開API/PointerのSize/Hash照合と試算までで、精度/実GPU配置は未確認。次は量子化だけを分ける別候補の取得/事前登録/生成0を検討する。Main/予約Cal/最終N/資源/条件/凍結は未了、Gate 11未通過・Phase 12未実施、Goal継続中。

[通過後専用のMain設定準備CLI](phase11_main_preparation_v1.md)を追加した。全旧30条件/84 Callの採用と終了後監査を先に要求し、コピー上のRaw再検証、元選定/使用済み来歴、現行Policyと日英Runnerの検査後に両設定を生成する。全761 Test（27.55秒）/Ruffに成功し、実行中v7/実不通過v5の早期拒否・出力なし・未使用QA読込み0、Native95 Source不変も確認した。実Main Policy/設定はまだ作成せず、下記session64437の全採否は未確定。Goal継続中、Gate 11未通過。

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

旧回帰v4の準備Helperをdata/runs/development_screening/phase11-known-v4-preparation-v1/prepare.pyへ保存し、未完了の親診断を実際に拒否/Versioned出力未作成を確認した（phase11_known_trace_preparation_pending_v1.json）。全58条件/70 Call通過・正規監査後だけ親の同一Byteコピーを全再検証し、旧全15 QA/42文/30条件・84 Call/全Expected・基準/裸拒否8を新Versionへ結ぶ。正の準備経路はまだ未検証で、既存の128 Call用入口を新候補へ無条件に流用しない。

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

[主Development採用Guardの監査](phase11_main_adoption_audit.md)で、Policy候補/通過回帰の直接一致と全事前基準の値/型・明示nullの開始前検査を補強した。新規23 Testを含む全584 Test/Ruff成功、故障注入の資源監視警告1件を保存。主20問や実採用成功側を達成した意味ではない。固定v11は終了済みで、不通過の全結果を保存した。

Calibrationの対象は[別予約Manifest](phase11_bilingual_calibration.md)へ保存済み。英語の元225問は検索調整済みのまま保持し、未使用Developmentの20 Groupを主20 Groupと分けて追加Calibrationへ予約した。日本語は元Calibrationから20 Group。全561 Test/Ruff・再計算/重複0を確認し、新規推論0。実行Protocol/専用Runner・採用/全Label封印/解析は主Developmentの確認後で、最終Gateは未了。

**Phase 1〜10の基盤と、Phase 11の日本語Source/分割/全文Corpus・日英Index・共通RAGの既知接続を完了。v8の人工形式/日英意味診断は通過したが、既知15 QA回帰v2は誤支持6で不通過。別9B v9は生成0の資源確認に通過し、人工形式2 Callで推論未終了/出力上限に達した。全失敗/未試行を保持し、開始TagのPrefillを実入力とNative応答で照合するv10を追加、全555 Test/Ruff成功。固定v10は同じ人工6 Call/厳密5条件に通過し、監査追加0/全16 Artifact保存を完了。同じ固定Commitの意味診断は20 Call/既知4条件でCritical3/4となり不通過、人工54条件未試行。元順序Councilの矛盾/支持不足の不一致と全42 Artifact/再開追加0を保存した。指示の再述を減らすv11を旧全基準のまま固定bb11fc9へ保存。全128入力/生成0 Preflight後の意味診断も20 Call/既知4条件でCritical3/4・逆順誤支持1となり不通過。全41 Artifact/再開追加0を保存し、旧全基準を保つv12の大きな推論/出力予約を事前固定した。固定51b0559のv12は24k/全128入力生成0/全層CUDAと同じ人工6 Callの厳密5条件に通過し、同じ意味診断も20 Call/既知4条件でCritical3/4・元順序の矛盾/支持不足不一致により不通過。誤支持0でも基準を緩めず、人工54未試行/全41 Artifact/再開追加0を保存済み。日英主Development/未使用Calibration、規模/本実験条件、拡張Validator/最終凍結は未了。Gate 11未通過、Phase 12未実施。**

2026年10月21日、英語CLAPNQに近い別の日本語Datasetを追加し、日英で順序感度と判断・品質・費用を
比較する方針を採用した。[日英比較の拡張方針](english_japanese_expansion.md)に従い、
選定・日本語対応・予備検証・両言語の条件固定をPhase 11へ追加する。
同日のGoal実行で[日本語Sourceの選定・原QA取得・構造監査](japanese_dataset_selection.md)を実施した。
Sourceは`baobab-trees/wikipedia-human-retrieval-ja`。記事取得・正式Group分割・全文Passage化は完了、QA参照対応・全Pipeline・予備検証と最終固定は未完了。
原QAの再取得/検証と歴史的な記事全文取得CLIを実装し、既知1記事でPreflightを確認した。
全2178 Titleの取得をCommit `61b4a5c`の専用Checkoutで行い、保存応答・本文/Source Hashを照合した。
独立して日本語の文単位候補を実装し、新規32 Testを含む全316 Test・Ruffに成功。
旧英語抽出65件は不変で、[実装計画第11節](rag_implementation_plan.md)に定義とFの分母への影響を記録した。
日本語の検索/Model実走、日英の意味監査・未使用Calibrationと最終固定は未完了で、Gate 11は通していない。
QA AdapterとGroup分割処理を追加し、実838件で原行Hash・引用/人手要約の区別・同一Byte再開を検証した。
全338 Test/Ruff成功。暫定706 Group・開発予約142件で、正式SplitとPassage/Gold対応は取得完了後に進める。
その後[多言語検索候補・全文保持のPassage化](phase11_multilingual_retrieval.md)を実装し、既知1記事で検索まで実走した。
全351 Test/Ruff成功。英語Corpusにも新Tokenizer上限超過3130件があり、英語の分割/新Index・新RAG接続と両言語の実走は未完了。
その後[英語Corpus分割・本文欠測の規則](phase11_corpus_preparation.md)を実装し、183889 Passage・全元本文/親Gold対応を検証した。
全365 Test/Ruff成功。正式日本語Splitは545/84/209 QA、706 GroupでGroup間Identity重複0。
取得成功2126記録・2118種類のPage、取得不能50・削除本文エラー2を保持し、全838 QAを除外しない。
新Index・日本語の全本文Passage/Gold対応と日英RAG/Calibrationは未完了。
[正式Encoder/CLIのCUDA入口](phase11_embedding_cuda.md)と専用uv Lockを追加し、合成数値/実演算・既知1記事の構築/検索を確認した。
全380 Test/Ruff成功。全Corpusの新Index・日英RAG/意味監査・未使用Calibrationと最終Gateは未完了。
[日本語全CorpusのPassage化](phase11_japanese_corpus.md)を完了し、2118記事・30065 Passageの全本文/Span/Hash/Tokenを独立検証した。
全392 Test/Ruff成功。原QA/Splitは保持し、親記事/引用/人手要約と欠測のQA対応は未完了。英語新CUDA Indexは固定Checkoutで構築中。
その後、[日英全CorpusのEmbedding Index](phase11_bilingual_indexes.md)を同じ固定Commit/GPU条件で構築・全件検証した。
英語183889/日本語30065 Vector・全ID/Offset/親対応、正規配置への同一Byte複製と再開追加0を確認。
新BM25/Hybrid、QA参照対応、日英RAG/意味監査と未使用Calibrationは未完了。
その後、日英BM25の全構築と合成Hybrid動作を確認し、日本語838 QAの[参照/引用/欠測の初期監査](phase11_japanese_evidence.md)を完了した。
全411 Test/Ruff成功、全原Field/Group/Splitを保持。引用元本文欠測25 QA・全引用元本文欠測9 QAを除外しない。
開発予約3例の脚注表示差を確認し、原HTMLから脚注位置を検証する別Version、Factory/RAG接続・未使用Calibrationはこれから。
その後、原HTML脚注の実位置と本文の全文字対応を検証するv2を実装し、引用位置1493/1741参照を確認した。
全432 Test/Ruffと別Scriptの全投影照合に成功。v1・全838 QA/Group/Split/欠測・Corpus/Indexは保持。
新Factory/RAG・品質/親単位Metric、Development意味監査・未使用Calibrationと最終固定は未完了。
その後、[日英共通RAG候補の接続](phase11_bilingual_pipeline.md)と匿名品質Packet・親単位@5 Metricを実装した。
新規9件を含む全441 Test/Ruff成功。両言語1問ずつの既知Development接続用設定を検証したが、実GPU実走はこれから。
再開追加0・失敗/中断の保持・Gold漏洩防止・全Label前の内部照合禁止はTestで確認した。
これは主Pilot・意味監査・未使用Calibration・Gate 11の合格ではない。
その後、固定75d4787で日本語既知1問の全経路を実走し、11 Completion・CUDA全層Offload・予算/本文不変を確認した。
再開22ファイル不変/追加0、匿名2候補のAI Labelは固定済みだが内部対応の照合は未実施。
英語は旧IndexのCLAPNQ Source省略Schemaで生成前停止した。失敗保持/Factory互換修正/実Index経由の回帰を追加し全443 Test/Ruff成功。
英語v2の別固定Commit実走と日英の意味照合、主Development/英語既知問題・未使用Calibration・最終固定が残る。
その後、固定5605bf8で英語1問も全11 Completion/再開追加0を確認し、日英全4匿名候補を固定後に内部照合した。
両言語で初回/書換えY1・全9 Judge F=1/採用、全3固定文のAI支持監査は27判定で相違0。
これは既知肯定例の接続確認に限る。日本語書換えの引用先不適合と英語の文数指示逸脱も記録した。
主Development、英語既知誤支持/拒否、日英未使用Calibrationと最終凍結は未完了で、Gate 11は未通過。
次の[意味診断計画](phase11_semantic_revision.md)として、既知英語2例と日英人工27例の入力/Expected・採用/停止規則を事前保存した。
専用Runnerと新規7 Testを追加。Critical4条件の全一致後だけ人工54条件へ進める。今回の実GPU診断結果はまだない。
その後、固定93c3611で初期4B候補を診断し、Critical正確一致1/4・誤支持3/4で不通過。人工54条件は未試行のまま保存した。
再開追加0を確認し、予定した主体/関係・時期・数量範囲のPrompt改訂v2を別設定へ事前保存した。v2の実走はこれから。
その後、4B改訂v2もCritical2/4一致で不通過。予定の8B公式固定版を取得/Hash照合し、同じPrompt/基準/予算の候補v3を用意した。
8B資源Preflight/意味診断はこれから。旧保存結果の裸の拒否8問中3問で改善見逃しを確認したが、新Fallbackは未実装/未採用。
その後、8B資源Preflightは58条件/Completion0/全層CUDAで合格したが、意味Criticalは2/4一致で不通過。
予定3候補の不通過を保持し、次の[固定文ごとの方法候補](phase11_claimwise_candidate.md)を事前計画した（未実装）。
裸の拒否だけの任意一回書換えを実装し、null Score/旧動作・失敗/費用/再開を含む全459 Test/Ruff成功。
保存候補による事後再構成では元順序Y1が6→9/Calls32→40、不明2。新規QAの効果とはせず、新方針はまだ未採用。
その後、固定文ごとの任意候補を共通評価/品質検証/実費/再開へ実装した。全分母保持・単位失敗時null・元IDと実Callを記録する。
旧Configの共同評価は保持。候補v4/最大70 Callの事前入力を検証し、固定Commitの新GPU診断はこれから。
その後、固定4196aa5で全70入力Preflight/Completion0と既知16実Callを完了したが、Critical2/4で不通過。
4集計/16子Taskの全分母・実費/再開追加0を照合し、人工54条件を未試行のまま保持した。
依存しない[QA内増分・Group Bootstrapと日英差](phase11_statistical_plan.md)を事前定義/実装し、全474 Test/Ruff成功。
統計は新規Run未適用。次の[草稿なし根拠読解候補](phase11_source_reading_candidate.md)は計画段階で、意味採用・主Development/未使用Calibration・最終凍結は未了。
その後、草稿なし読解を先行する任意候補を共通Task/評価/品質検証へ実装した。全ID/Quote・全分母/実費・中断再開を含む全487 Test/Ruff成功。
候補v5/最大128 Callの条件を保存した。実GPU意味診断と意味採用・日英主Development/未使用Calibration・最終凍結は未完了。
その後、v5は読解1 Callで文書ID重複/欠落と非一致Quoteを検出して停止した。固定文判定0、他57条件未試行・再開追加0。
旧v5/全失敗を保持し、v6だけID一意/完全一致QuoteをSchema制約へ追加した。全488 Test/Ruff成功、v6実走と意味採用はこれから。
その後、固定772d1a7のv6は全128入力の生成0 Preflightと既知Critical4条件全一致を確認し、人工54条件を実行中。全意味Gateは未確定。
全Label封印済みDevelopment用統計Adapter/CLIを追加し、全選定/失敗費用・文書Group・条件混在拒否を含む全493 Test/Ruff成功。
未使用Calibration対応・本実験規模/条件・全意味監査/拡張Validator・最終凍結は未了。追加Modelは公開Metadata/資源の調査だけで未取得/未採用。
その後、v6全58条件/128 Callを完了し、Critical4/4・人工英語24/24/日本語28/30・誤支持0で診断通過。再開251 File不変/追加0。
日本語の同一例での支持不足→矛盾2条件、補助読解11行の文書内非対応/過大一般化と、Council F5/7による採用を保存した。
次の[使用済み15 QA/42固定文の回帰](phase11_known_trace_regression.md)を最大114 Call/前提Hash/旧Expected保持へ固定し、全502 Test/Ruff成功。主Development/未使用Calibrationと最終Gateは未了。
固定2ae5133の既知回帰は生成0 Preflight後、5/30条件目の読解が配列で始まり旧Grammar Trigger未到達で停止。21 Call/他25条件未試行、再開37 File不変/追加0。
[JSON境界の別候補](phase11_json_boundary.md)をv7へ固定し、人工6 Call以下の実Runtime検証後、同じ日英意味診断を新Runで再実行する。未使用QAへはまだ拡大しない。

境界v7の人工検証は旧制約で配列回避を再現し、新制約ではObject開始後の空白反復で上限に達した（2 Call/入力94・出力656 Token）。
この失敗を保持し、空白を各位置最大2文字とするv8を別保存した。Nativeが保存WORDを単一TOKENへ変換する処理も一次資料から確認し、Tokenizer実測ID/保存Token/全文Grammarの一致を要求する。全510 Test/Ruff成功。GPU再検証は未実施。

固定43ccf05のv8は人工6 Call（厳密5条件すべて）を通過。全128予定入力/生成0 Preflight・CUDA全層も確認し、新しい日英意味診断を実走中。全結果/意味採用は未確定で、旧Expected/基準と失敗Runを保持する。

並行して[主Developmentの事前選定](phase11_main_development.md)を行い、旧入力70 File/使用済み62 ID・日本語予約142 QAの除外来歴から日英各20問/20 Groupを保存した。全514 Test/Ruff成功、追加Model Call0。主20問のRunner拡張/実行Protocol・採用前提・実走は未了。

主Development用の採用/選定/Policy Guard・原子Call上限1660/言語・新規5 QA/段階Sessionと中断再開を実装し、全536 Test/Ruff成功。主結果前のHealth/意味採用/全Label封印基準も保存した。実設定/新規推論は既知15 QA回帰の通過後とし、まだ主実走を行っていない。

v8は固定43ccf05の全58条件/128 Call・Critical4/4/人工英語24/24・日本語28/30/誤支持0を完了し、全259 Artifact/読解11行の問題・曖昧c6によるF6/7/再開追加0を保存した。旧Expected不変の既知15 QA回帰v2は、この新しい通過Reportへ前提を結んで事前検証済み。実GPU回帰はこれから。

既知回帰v2は形式/Runtime失敗0でも12 Critical中8一致・誤支持6により不通過。54 Call/残18条件未試行・再開追加0を保存した。日英全品質/固定文Labelの封印後にだけ内部と比較する監査入出力を追加し全545 Test/Ruff成功。次の[Qwen3.5-9B候補v9](phase11_qwen35_candidate.md)は条件固定/重みHash確認までで未推論。
翻訳対は主実験に使わず、別Dataset間の差を言語単独の因果効果と断定しない。

基盤に加え、固定回答のClaim抽出、根拠順序/反復ごとの自己評価と採用/書換え要求の保存を実装した。
自己評価による採用/修復や、回答信頼性の改善を実証した段階ではない。
既存基盤と英語の完了工程は保持し、日本語に必要なデータ準備・実装・検証をPhase 11で追加する。

| Phase | 内容 | 状態 | 完了を判断する成果物・Gate |
|---|---|---|---|
| 1 | CLAPNQ取得とSource検証 | 完了 | 固定Revision、取得/検証Script、Source Manifest |
| 2 | Loader・内部Schema・Corpus変換 | 完了 | QA 4,345件、Corpus 178,890件、ID/Gold対応検証 |
| 3 | Title単位Split | 完了 | Development/Calibration/Evaluationと固定Manifest、Split間Group重複0 |
| 4 | BM25/Embedding検索 | 完了 | 共通Corpusの両Index、質問検索CLI、固定Manifest |
| 5 | 開発用Baseline RAG | 完了 | Embedding→Qwen CPU生成、Development 5問の実入力/回答保存 |
| 6 | Hybrid Baseline固定 | 完了 | 検索Calibration 225件、固定Hybrid、Development 5問の生成・保存、Gate 6通過 |
| 7 | 新テーマのProtocolとPilot仕様 | 完了、Gate 7通過 | 専用Prompt/Config・採点基準・入力検証CLI・Hash Manifest。21入力のToken計測、Completion 0回 |
| 8 | 固定Trace・評価器・根拠順序実験 | 完了、Gate 8通過 | 開発2件、Judge 9回、固定内容/Schema同一・再開追加0回・182 Tests/ruff成功 |
| 9 | 一回書換え・品質採点の入出力 | AI委任後の開発Gate通過 | 2回書換え、3候補AI採点、候補・判断・品質・費用の対応を照合。人手確認とはしない |
| 10 | Development予備実験 | 修正・再実験・事後の形式検証を完了 | 15診断・5既知書換え、新規10問/20候補。v14事前Gateの失敗を保持し、後処理再検証を別記録 |
| 11 | 日本語Dataset選定・対応、日英Calibration・最終条件凍結 | 日英Data/参照・既知各1問の全経路接続済み。主Development/既知英語問題・意味採用/規模・未使用Calibrationが残りGate 11未通過 | 選定比較表、日本語対応/意味監査/英語回帰、両言語の対象・条件・統計の凍結Manifest |
| 12 | 日英の最終Evaluationと独立採点 | 未実施 | 両言語の事前選定全対象のRun/品質/欠測/費用が対応し、条件を事後変更しない |
| 13 | 言語別統計・日英比較・条件別分析、任意の対策 | 未着手 | 不一致増分の日英差と不確実性、品質/費用、Dataset差の限界。対策は同予算で比較 |
| 14 | 日英比較を含むICIAE原稿・投稿準備・卒論 | 未着手 | 方法・結果・比較考察・限界、再現手順、引用・図表、指導教員レビュー |

完了済みの根拠は[Phase 4](phase4_retrieval.md)、[Phase 5](phase5_baseline.md)、
[Phase 6](phase6_hybrid.md)と`data/manifests/`にある。
Phase 6の全135 Tests成功は当時の検証実績であり、新機能のTestを済ませた意味ではない。

## 2. Phase 7: 新テーマのProtocolとPilot仕様

目的は、何を固定し、何を変えて比較するかを実装可能な形にすること。

- [x] 主テーマの正式採用と研究目的・RQ1〜RQ3の明文化。
- [x] 原因別三修復から、一回の固定Answer Rewriteへ研究範囲を変更。
- [x] 旧仕様の保存、研究/実装計画とこの進捗表の更新。
- [x] 専用Promptを作る（回答のみのClaim抽出、固定Claimの根拠検証、初回回答の書換え）。
- [x] `configs/order_pilot.yaml`等へPilot初期値を実ファイル化し、Model/Runtimeの利用条件を検証。
- [x] 少数のDevelopment例で独立品質の必須要点・重大誤り・判定不能の例を作る。
- [x] 初期の主比較、順序/反復・Seed、適用不能/Fallback、保存Schema、Test条件を確認。

Gate 7: 専用Prompt/ConfigとProtocolのVersionがそろい、Goldを使わない実装の入出力を説明できる。
本実験の最終凍結とは別であり、Pilot結果による変更は履歴を残してPhase 11までに確定する。
2026年10月18日にGate 7を通過した。記録は[Phase 7 Protocol](phase7_order_protocol.md)、
品質基準は[独立採点の基準案](order_quality_rubric.md)、固定情報は`data/manifests/phase7_protocol_manifest.json`。
確認したのはModelの起動・入力予算までで、採点精度や書換え品質を検証したものではない。
練習例の人手Labelはpendingであり、本実験の正解Annotationへ数えない。
Phase 8の実装は[実走・実装記録](phase8_order_evaluation.md)を参照する。

## 3. Phase 8: 固定Trace・評価器・根拠順序

- 既存Baseline結果を、同じ質問・初回回答・実使用Contextを持つ固定Traceへ変換する。
- 回答だけからClaimを一度抽出・固定し、全順序に共用する。
- 元順序、逆順、Shuffle 3通り、同一順序の合計5反復を初期条件として実装する。
  共通初回を共有するため原則9呼出し/問/評価器。重複順序の有効数を記録する。
- 表示配列だけを変更し、本文・ID・Titleを不変にする。Prompt全体の入力超過を検査する。
- F、採用/書換え、Claim判定、実Prompt、Hash、Token、時間、エラーを保存する。
- 再開・Hash差停止・Gold漏洩・不正JSON・Claimなし・閾値等号を確認する。

Gate 8: 少数のDevelopment実入力で全文保持と評価出力を点検でき、必要なTest/ruffが通る。
構造が正しいJSONでも意味上の判定が妥当とは限らない。品質監査は続ける。
2026年10月18日にGate 8を通過した。具体的な入力順序・JSON・失敗履歴・監査は[Phase 8記録](phase8_order_evaluation.md)へ保存した。
開発用の練習例2件のうち1件はClaimなし、1件は有効な9判定が全てF=1.0/採用だった。
これはソフトウェアの動作確認で、順序の影響がないことやJudgeの精度を示す研究結果ではない。
初期の自由出力は不正JSON/引用不一致/反復があり、現行は全条件共通のJSON/原文引用候補と出力上限制約を使う。
意味上の過大支持が疑われる例と、長い別例の抽出の見落としを記録し、Phase 9〜10で妥当性を監査する。
Phase 9でScore/Feedbackを渡さない元順序の一回書換えまで実装した。次は独立品質採点とGate 9照合である。

## 4. Phase 9: 固定書換えと独立採点

- 元質問、元順序の実使用Context、初回回答から一回の書換えを生成・固定する。
- 評価Feedback、順序変更後Context、Reference/Goldを修復へ渡さない。
- 条件名・Score・判断・初回/修復を隠す品質採点用Exportと、Hash付きImportを用意する。
- 初回Y0と書換えY1の四遷移、判定不能、書換え失敗Fallbackを記録する。
- 修復なし、常時書換え、各評価判断が同じ候補から選ぶことを検証する。

Gate 9（AI委任後）: 少数例で二候補と外部AI品質が対応し、判断・品質・費用を照合できる。
参加者募集・人手の再採点は必須にしない。AIの実採点者、制約、経過時間を記録する。

2026年10月19日現在、[Phase 9実装・実走記録](phase9_answer_rewrite.md)のとおり開発2件の書換えに成功した。
原子の例は文章へ変化、Pradaは初回と同一だった。全条件は既存の判断どおり初回を選ぶ。
HTML採点画面・JSON入出力・候補Hash照合・四遷移・経路費用の実装を確認し、全216 Testが成功した。
当初は人手確認をGate条件にしていたが、その後ユーザーが開発・本番ともAI採点への委任を決定した。
同日、ユーザーの委任で[3候補のAI代行採点・保存](phase9_ai_quality_review.md)を実施した。
結果はY=0が2候補、判定不能1候補で、既存Validatorに合格した。
原子の初回0→書換え不明、Pradaは同文0→0と、各条件が初回を選ぶ対応を照合した。
[AI品質Protocol](ai_quality_protocol.md)によりこの開発確認でGate 9を通過とする。人手確認を達成済みにしない。
旧Manifestの未通過記録は当時の人手必須条件の履歴として残す。既知例だけから品質改善や順序効果を結論しない。

## 5. Phase 10: Development予備実験

Development Answerable 20〜30問を目安に、結果を見る前にIDと選定規則を保存する。
新しいPilotを既存5問のSmokeだけで代用しない。
今回はCPU実測と監査負担から下限の20問とし、既知IDと同一Titleを除外して異なるTitleを選んだ。
`data/manifests/phase10_selection_manifest.json`へモデル実行前に固定した。失敗例は補充しない。
AI採点の資料・入力・結果と内部F/判断を分離し、本番の再現可能な固定方法も検証する。

- 順序変更群と同一順序反復群の判断不一致、採点不能・障害を測る。
- 初回/書換えを独立採点し、判断変化が品質・費用へ伝わるか確認する。
- 評価器の支持判定とClaim分解の誤り、Prompt予算、速度、再開、採点時間を監査する。
- 本実験対象数、別評価器の範囲、反復数、連続実行時間を見積もる。

Gate 10: Pilot Reportがあり、継続する主張・Protocol修正・本実験の規模を根拠付きで説明できる。
反転率の大きさだけで合否にせず、品質Labelと対照の妥当性も確認する。
効果が小さくても閾値を都合よく動かして現象を作らない。研究テーマ内で主張の範囲を再検討する。

2026年10月19日、[初回Pilot Report](phase10_pilot.md)を作成した。
20問すべての初回・書換えと40候補のAI採点を完了し、完全比較は11問だった。
Fの順序変化は1例、判断反転は0例、既知品質ペアの改善/悪化は0例。判定不能2問を別に残した。
事実本文が空Claimになる3例、重要情報の抽出漏れ、時刻の誤支持、出力上限1試行が見つかった。
**初回20問集計時点では、Gate 10は修正・再確認待ちとした。** 以下はその時点からの開発履歴である。

次の優先順位は、(1)回答本文に対するClaimの網羅性と拒否文の扱い、(2)支持/矛盾の意味判定、
(3)一回書換えによる明示的誤りの訂正能力、(4)出力予算である。
変更は新Version/Runへ分け、既知例の回帰確認と事前選定した少数の追加Development例を分ける。
反転を作るために閾値を動かさず、Evaluationへ調整に入らない。修正後の測定時間から本番規模を再見積りする。

修正の仕様・再確認前の完了基準は[測定系修正記録](phase10_measurement_revision.md)へ記載した。
当初は文単位による本文保持、意味比較後の判定、引用と出力予約、新規5問の再確認を開発した。

同日16:39 JSTの再開確認で、`order_phase10_v14.yaml`の診断が裏で完了していたと確認した。
曖昧な1例を除いた明確な15判定は全件一致し、人工3件・自然2件の一回書換えと、旧7 Claimの出力を確認した。
最大出力946 Token、診断24呼出しに形式失敗・入力超過・出力打切りはなかった。
正しい日付のTrue結論を支持不足とする既知の誤棄却は残り、一般精度100%とはしない。
新規10問の再実験を開始した。両Cohortの全匿名品質Labelを固定するまで内部F/判断を開かない。
同日、新規10問の内部評価36回・書換え10回、全20候補AI採点と集計を完了した。
v14は引用ID重複1件で事前Gate不通過（完全比較3問）。その失敗と各Cohortの停止を保持した。
後処理v15で同一IDの重複だけを整理して全36保存出力を再検証し、完全比較4問を確認した。
既存有効35出力の意味判定は不変、追加Model呼出し0。事前Gate通過や新規Model実験へ置き換えない。
Astrosの判断反転1問は元v14でも有効で、書換えによる改善の見逃しまで対応づけた。
Phase 10は事後の形式修正を含む開発確認として完了とし、元の事前Gateは不通過として報告する。
[再確認結果](phase10_recheck_results.md)に分母・品質・費用・意味上の誤りを記録した。
上記のPhase 10作業時点ではPhase 11を開始していなかった。10月20日に下記の準備実装を開始した。

## 6. Phase 11: 日本語対応・日英Calibrationと最終条件凍結

2026年10月21日の拡張決定により、Phase 11の完了条件へ日英比較の準備を追加した。
以下の日付付きCPU/GPU記録は既存英語検証の履歴で、日本語対応を完了した記録ではない。

2026年10月20日、[Phase 11の準備実装](phase11_calibration.md)を開始した。
初期バッチはCalibration Answerableの異なるTitle 5問。結果非依存選定・候補条件のHash保存、
初回生成の件数制限付き実行、順序/反復と共通書換え、匿名AI採点と品質固定後の集計を実装した。
事前選定5問のうち初回生成1問が成功し、4問は未実施。Judge・書換え・品質採点は未実施。
全259 Test/Ruffが成功し、追加生成0回の保存回答再利用と旧834 ArtifactのHash不変を確認した。
CPU上の初期確認であり、GPU実機確認・意味妥当性の判断・最終条件凍結を達成済みとはしない。
候補ManifestやHealth Gate通過だけで本実験を許可しない。

上記は初期実装時点の記録。同日、残り4問の初回生成を終えて5問全て保存し、
共通書換え・全10匿名候補のAI採点・Label固定後の集計まで完了した。
初回は全5問が単独拒否でJudge呼出し0・完全比較0、元Health Gateは不通過。
書換えで改善した2問も現行Fallbackでは初回を保持した。順序効果を測れた結果とはしない。
[最終固定の検証処理](phase11_finalization.md)とGPU実機情報の収集CLIも追加した。
未使用の追加Calibration 20問を結果非依存で事前選定したが、GPU実行は未実施である。
本番はユーザー指定で研究室PCのGPUを使う。GPUでの実測・Calibration・最終件数の決定後に凍結する。
CPU側の完了状況と、研究室側で残る事項は最新日誌と専用記録へ残す。

同日、Ubuntu実機と転送・モデルのHashを検証し、明示的CUDA対応を別Versionとして実装した。
既知Developmentで3Bの全Layer Offloadと実生成を確認した。4Bの512 Token推論は既知誤支持を
再現し、1536 Token候補で事前診断を行う。初回Prompt変更候補は重大な誤りが残るため不採用。
[実機検証記録](phase11_lab_validation.md)に失敗・条件差・採用理由を保存する。
追加20問の実行・全品質固定・内部照合と最終固定は、この準備記録時点では未実施。

その後、GPU20問の初回・Judge108回・書換え20回・匿名40候補のLabel固定と集計を完了。
単独拒否8、完全比較12、事前Health Gate通過。品質は0→1が6、1→1が6、0→0が6、不明2問。
Zidaneで順序判断反転1/12、同順序反転0/12。誤支持・回答不足・拒否Fallbackを区別した。
全34固定文をAI監査し、全128補助TaskのNative制約とGPU37/37 Layer Offloadを検証した。
[GPU結果と次工程](phase11_lab_validation.md)のとおり、意味妥当性の採用と分析規模は未決で最終凍結を見送る。
本番は200問案、反復/統計案を記録したが未凍結。使用済み25問を除いた別の未使用20問を事前選定済み。
次は既知例でJudge/拒否方針を別Versionで検証し、新条件・Health Gateを保存してからその別バッチへ進む。
今回のGPU20問を再び未使用と扱わず、Gate 11通過前にPhase 12は開始しない。

### 日英比較に向けた追加作業（2026年10月21日追加）

- [x] CLAPNQに近い日本語候補を比較し、[人手検索・長文QA Sourceの選定理由と残る差](japanese_dataset_selection.md)、固定版原QAの取得・構造監査を保存する。本文Corpusの準備は下記へ残す。
- [x] 全検索記録の記事全文から[共通Corpus](phase11_japanese_corpus.md)を取得・検証し、[正式Group/ID/Seed分割](japanese_dataset_selection.md#8-全取得と正式group分割の完了)とManifestを保存した。Redirect・複数参照・欠測を保持し、[日英全文Index](phase11_bilingual_indexes.md)と参照対応v2をAssets v2へ結んだ。
- [x] 読込み・選定・検索・指示文・文分割/拒否・Token予算・匿名品質採点・言語別記録/集計の[共通接続](phase11_bilingual_pipeline.md)と単体/回帰Testを実装した。現行Sourceの全734 Test/Ruffと全30 Index/Embedding Payloadの照合を最終Validator検証v2へ保存した。これは実主/Calの意味採用ではない。
- [ ] 最優先: 現候補の全日英意味診断と全旧15 QA英語回帰を、全Expected/基準を保って通過する。形式成功や既知4条件の通過だけで採用しない。
- [ ] 日英の主Development各20 QAで全経路・全匿名品質/固定文Expectedの封印・意味/費用/有効比較数を確認する。既知各1問の接続結果と、使用済み英語の拒否/誤支持履歴は保持し、主20問完了へ数えない。
- [ ] 修正後の候補と停止条件を保存し、両言語の未使用Calibrationで意味妥当性・有効数・費用を確認する。
- [ ] 言語別件数・対象ID・条件・独立品質基準・日英差の統計と欠測の扱いを固定し、最終固定Validatorも追加要件へ対応させる。

詳細と各項目の確認内容は[拡張方針](english_japanese_expansion.md)第3〜6節による。
既存の英語200問案は日英合計/各言語の固定件数ではない。新しい件数は両言語の有効数と負担から決める。
日本語の選定前に英語側の既知例診断を進めることはできるが、両言語の準備前に本実験条件を最終凍結しない。

- Calibrationで評価器の妥当性、閾値・入力予算・品質基準を確認する。
- Source/Split/検索/Generator/Judge/Runtime/量子化/Prompt/Seed/試行数/採点基準を固定する。
- 本実験の選定規則・ID、主比較、少数の条件別分析、分母・除外/Fallback、統計を保存する。
- 本実験100〜200問程度は規模の候補。Pilotの率・Title数・採点負担・推定精度から決める。
- 検索Calibrationに225問を既に使った履歴を残す。最終Evaluationで調整しない。

Gate 11: 日本語Sourceの選定根拠、両言語の実対応・意味妥当性・英語回帰・条件/対象/統計の根拠があり、
Evaluationの結果を見ずに再現可能な条件と凍結ManifestのHashがそろう。
追加要件を確認する[日英用Validator](phase11_bilingual_finalization.md)を10月22日に追加した。実主/Calibrationの成功側・最終件数/条件は未了で、旧英語用Validatorや人工通過テストだけでは拡張後のGate通過としない。
ここを通過してから本実験を始める。

## 7. Phase 12: 日英の本実験と独立採点

両言語の事前選定した内部Evaluationで固定条件を一度実行し、未完了だけを再開する。
障害・不適格・採点不能を成功例に置換せず、事前Ruleに従って理由と費用を保存する。
外部AIが固定Protocolで品質を採点し、条件の有効数・Y0/Y1・最終出力・費用の対応を確定する。
別評価器の確認を行う場合は範囲と予算を事前に固定する。

Gate 12: 両言語の全対象IDの実施状況と品質判定状況が分かり、各言語内の採点済み共通QAと欠測を明示できる。

## 8. Phase 13: 分析と任意の対策

主判断不一致の差と95%信頼区間、反転例率、品質四遷移、悪化・見逃し、費用を整理する。
これらを言語別に示し、QA内の不一致増分の平均の日英差と95%信頼区間を事前計画に従って求める。
日英QA同士に対応を仮定せず、Datasetの仕様・回答長・文単位数・根拠数等の差を比較考察へ含める。
元質問/Titleの対応を保ち、条件ごとの有効例への偏りと判定不能の感度を報告する。
根拠位置などの事前条件と探索的分析を分ける。閾値付近の反転だけを新規性にしない。

対策やViewerは任意。対策を追加するならDevelopment/Calibrationで決め、
最終評価済みDataで調整して同じDataを新たな最終評価と呼ばない。
既にEvaluationを見た後の対策は探索的結果と明示するか、未使用の追加評価を事前に用意する。

Gate 13: RQ1〜RQ3とRQ-L（日英比較）へ証拠と限界付きで答えられる。対策なしでも通過できる。

## 9. Phase 14: ICIAE原稿と卒論

原稿の背景・関連研究・方法はPhase 7から並行して書く。結果待ちで執筆を止めない。
主図表は実験手順、判断不一致、品質遷移、条件別の影響・費用。
日英のDataset選定理由・仕様差、言語別結果と日英差、言語単独の因果へ帰属できない限界を原稿へ反映する。
実施していない対策や品質向上を結論へ加えない。新規性の表現と近接研究を再確認する。
指導教員レビュー、英語・引用・License・4〜8ページ・提出形式、再現手順を確認する。
Gate 14: 提出可能な原稿と成果物がそろう。投稿操作は別途ユーザーの指示で行う。
採否後の修正と卒論では、査読指摘・追加実験を別Versionで管理する。

## 10. ICIAEを見据えた目安

[公式投稿要領](https://www2.ia-engineers.org/iciae2027/paper-submission/)を2026年10月18日に確認。
初回フルペーパー11月20日、通知12月11日、最終原稿2027年1月8日、会期3月26〜30日。

| 目安 | 優先する工程 | 期限までに欲しい成果 |
|---|---|---|
| 10月19〜23日 | Phase 8〜9、執筆の背景・方法開始 | 最小の実評価・書換え・品質確認が動く |
| 10月24〜26日 | Phase 10 | Pilot Report、所要時間、主張と本実験規模の判断 |
| 10月27〜29日 | Phase 11 | 凍結Protocol/Manifest |
| 10月30日〜11月8日 | Phase 12 | 日英の本実験と独立採点。別評価器は実行予算に合わせる |
| 11月9〜15日 | Phase 13〜14 | 図表、英語原稿、指導教員レビュー |
| 11月16〜19日 | Phase 14 | 形式・引用・主張の修正、完成原稿 |
| 11月20日 | 通常初回締切 | 審査対象のフルペーパー |

この表は目標で、実施済み記録ではない。Pilotの時間から逆算して調整し、延長・採択を前提にしない。
日本語追加前の目標日程を引き継いでおり、選定・対応・両言語の予備検証の負担を踏まえPhase 11で再見積りする。
日程を優先して日本語検証を省き、Gate 11通過や本実験完了を記録しない。
遅れた場合は対策・Viewer・条件数を先に絞り、主比較と独立品質確認を削らない。

## 11. 旧Phaseとの対応

Phase 1〜6の番号と完了実績は維持する。Phase 7以降の番号は本書で再定義する。
旧Phase 7の四種類Failure Dataset、旧8の全R/F/A、旧9の原因診断、旧10の三修復は必須工程から外れた。
旧11〜14の比較固定・最終実験・分析・執筆という役割は、新Phase 11〜14へ引き継ぐ。
古い日誌の「次はFailure Dataset」等は当時の判断であり、今後は本書の未完了項目を使う。
