# Phase 11 新チャットへの引継ぎ

2026-10-27 19:03 JST追記: v28完全90は18:25:49 JSTに失敗終端となった。48試行/47応答/未知1/未試行42、全90精度null・不採用・Known17不適格。[障害診断](../data/manifests/phase11_v28_semantic_disconnect_diagnosis_v1.json) SHA20688eb4355dd945faf342d0cf39381b56878798f2d757aa95209176cce2f7c1は実FAoff/Graph OFFでもserver PID467890のCUDA同期abortと同PIDのHost watchdog/Xid8を照合した。未知48は10.641596秒の切断でHTTP1200秒timeoutではなく、返却本文/出力tokenはnull。正確な原因や旧障害との原因一致は未証明。owned process終了を確認し旧固定WT/Raw89/未知/未使用42を保全、同条件再送0。

閉29Runの[累積費用v15](../data/manifests/phase11_autonomy_cumulative_cost_v15.json) SHA7c14c509b5456d98516100d563a66b33cd81fa9e06c43c0eab977c1624adba6eは新337試行/335返却/未知2、旧込1246試行/確定未知5、観測output1015308・総outputnull。全HTTP20496.807576秒は未知2件16.895423秒を既に含み、Task20436.771672秒・壁21073.548590秒と重ねて加算しない。部分47応答の機械検証は完了、全文/全thinkingのAI監査は進行中で候補採用には使わない。

次v29は研究Modelだけを既存Qwen3-8B-Q4_K_Mへ変更する別仮説で、実GGUF5,027,783,488B/SHA d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785を一度実Hash照合し実ID7d35156207fb6d4ef520412c43036d701c104b18145c13455a56c6e54d64f008を得た。Core94/Graph OFF b11433/FAoff/Prompt15/4096/Schema/Sampler/全90入力・Expected・基準は維持する。8BのTokenizer151667/151668と36block/必要37層はModel由来の新契約とし、新11witness/実全層ログへ照合する。旧8B不合格と旧9B形式・意味出力を採用再利用しない。v29は設定・形式入口/有限producer準備段階で新Native0、正式prereg/Commit/専用WT/生成0/形式10/日英Smoke/Rewrite品質/全90/新鮮Known84は未了。元Main/予約Cal/Gate11未達、Goal active、Phase12未開始。以下は各時点の履歴。

2026-10-27 17:43 JST追記: v28の[帰属C元逆2](../data/manifests/phase11_v28_attribution_smoke_result_v1.json)（SHA4d5a9abf0188f01933dce33e01eac92ed0f5c1eba7dc0199b221e71701cba91b）と[日英書換え2](../data/manifests/phase11_v28_rewrite_smoke_result_v1.json)（SHA08bb2563c5c885522eb485d3b0987f774cc2bd37b722fa0f2513791d27dd8b2b）は全実監査を通過。各Health2/未知0、帰属C2/2、新品質2/2を全Source/入力/回答/thinking/Raw/Native/FAoff/monitorへ結合した。[閉28Runの費用v14](../data/manifests/phase11_autonomy_cumulative_cost_v14.json) SHA99a029636e5746dee2069520db21cd566482eb8be0970f0451b463bb1fb77247は新289/返却288/未知1・旧込1198/未知4、totaloutputnullを保存し独立検算済み。固定291d017/候補0499の完全39QA・45文・78条件・90Callを2026-10-27T08:42:30.751860UTCからHandle3524/Plan cadaf9600feb3a8d36df298e3264fea6f1fd9bd68517a38eba695555eb90e567で初回実行中（壁22720秒/個別1200/監視5/Retry0）。候補全体の意味採用・新鮮な元Known84・元Main/予約Cal・Gate11は未了。支援AI設定のみユーザー申告6.1 Sol極高へ変更、厳密な提供Model IDは未取得・研究条件変更0。Goal active、Phase12未開始。

2026-10-27 17:21 JST追記: v28日英因果NS2の[全実監査](../data/manifests/phase11_v28_smoke_result_v1.json)が通過した（SHA76c7e7a2efb230890d6c3e6f762d459fcd201a700f8cc530a82c7a42c9869d3e）。全Source/理由・Native・実FAoff・全monitor・原Raw9独立copyを照合し、Health2/未知0・両NS、AI実joint135.046183秒。思考反復・両forced4105/末尾断片は保存し、最終理由144/101字は完結した。終了26Run時点の[費用v13](../data/manifests/phase11_autonomy_cumulative_cost_v13.json) SHAfc13a4d6b1e45a957c599b1b363247fe68420ea50408b4aae5fb5391e63bb686は新285/旧込1194/確定未知4・totaloutputnull、全17guardと旧23行不変を独立検算した。現在同固定291dで帰属C2をHandle90305/Plan43179919916fe43a8562cecf7592d122068ca36712922e3625bcb8707e954f0b・2Call/壁3000秒/個別1200/監視5/Retry0で初回実行中。候補全体の意味採用・全90/新鮮Known84/Main/Cal/Gate11は未了、Goal active・Phase12未開始。

2026-10-27 17:08 JST追記: 固定291d017/v28の実再現378資産＋別copy4・専用uv58と生成0全90、さらに新形式10の全実監査が通過した。[実再現](../data/manifests/phase11_v28_checkout_reproduction_v1.json) SHA8a09d32575f8d26b00fa3e2a29ccead003f49e67800dd2e4bf95a2049b49b9b8、[生成0](../data/manifests/phase11_v28_preflight_result_v2.json) SHAa0f46a48c8cb71c5a2881a6021aef9516147c972c27cf56d3cb4dd626d7ea6f0、[新形式10](../data/manifests/phase11_v28_format_result_v2.json) SHA3fe0466f70b4de53ba736d7164ad0b2d72523765edf399b62f7dd654f92b3f18。実FAoff/Context12288/33層CUDA、全90最大3926＋予約6144、Strict9＋意図したlegacy失敗1・返却10/未知0を確認。現在同固定WTで日英因果NS2をHandle86697/Plan ea93f03a568800d968a5c212f35312395d28e8560227c7c88d155bb7fc465e24・2Call/壁3000秒/個別1200/Retry0で初回実行中。Kernel安定性・意味採用は未確定で、帰属/Rewrite/全90/新鮮Known84/元Main/予約Cal/Gate11は未了。Goal active・Phase12未開始。

2026-10-27 16:51 JST現在: 新v28はFAauto→offだけの計算条件変更で、実ID0499a611e9ec8369e5c1958b2ce0e4d25e9095e72aeca6fe13f769e593db982e。[正式事前登録](../data/manifests/phase11_semantic_v28_preregistration_v1.json) SHA e51661318468b95ad28e7689cfdee0b735c0f7ea21ca7481239141b09b3ef68fへ64監査成果・19入力・新形式10を固定した。[実行契約v2](phase11_cuda_execution_v2.md)はCore2/Sampler executionを新Hashへ結び、Model/Runtimeビルド/Prompt15/Schema/4096/batch128/全90入力・Expected・基準を保つ。全1107 Test（36.11秒）/Ruff、有限producer24 Test/実Guard1回、監査v2のmonitor/Source/witness拒否16 Testが成功。旧監査v1の不足は実新出力前に保存・修正し、旧形式出力の採用再利用0。固定Commit専用Checkoutの再現と、生成0→形式10→因果NS2→帰属C2→Rewrite2全文品質→全90→新鮮Known84はこれからで、新Native0・採用未証明。元Main/予約Cal・最終凍結/Gate11未達、Goal active・Phase12未開始。

2026-10-27 16:32 JST追記: v27失敗の[全72返却・部分監査](../data/manifests/phase11_v27_semantic_partial_result_v1.json)を正式保存した（SHA fc02f34714a8b0d303d8bf2764e8eb3df10dfecae06dbaa7e9e8993b189c29dc）。Raw139・224監査成果・旧6629保存証拠を照合し、全72全文/理由の実AI監査539.881375秒を結合。観測72中のExpected確定70に対しexact68、C–NS混同2・理由の範囲懸念を保存し、全90精度/未知outputはnull・Known16不適格を維持する。支援AI容量による最終通知失敗時点で全72レビューは保存済みで、追加timer/再採点/別モデル回避は0。次v28の実Identityは0499a611e9ec8369e5c1958b2ce0e4d25e9095e72aeca6fe13f769e593db982e、FAoff実行契約の関連86 Testと新全1107 Test（36.11秒）/Ruffは成功した。まだ正式事前登録/専用Checkout/新Nativeは未実施。Goal active・Main/Cal/Gate11未達・Phase12未開始。

2026-10-27 16:20 JST追記: v27のCUDA同期abort/Host watchdog・Xid8を[正式診断](../data/manifests/phase11_v27_semantic_disconnect_diagnosis_v1.json)（SHA bf7f1c17a7a9243440041e3c155987cd1d36bdef68c3ecae6c0d0b359ebbd1f7）へ保存した。共有23 Runは全て終端、新273試行/272返却/未知1・旧込1182/未知4。[累積費用v12](../data/manifests/phase11_autonomy_cumulative_cost_v12.json) SHA09600144c3105e0acb2de8e031f3e57c1a495e574a8e49238de0051f33adbed5は全273予約/15Guardと旧22行不変を実照合した。台帳Native17404.773044秒には未知HTTP経過6.253827秒を含み、返却272のみは17398.519217秒、total outputはnullである。72返却の全文意味監査を分担中。次は実ログで有効だったFlash Attention auto→offだけを別execution-v2契約/新候補v28で切り分ける方針を選び、現在実装・検証中で新Native0。Prompt15/Model/4096/batch128/固定入力・Expected・基準を保つが、実行契約とCore2fileが変わるため旧Core不変や旧形式/意味の無条件再利用を主張しない。生成0/新形式/日英Smoke/Rewrite/全90/新鮮Known84を要し、根治や意味採用は未証明。Main/Cal/Gate11未達、Goal active・Phase12未開始。

2026-10-27 16:09 JST追記: v27全90はHandle65957が2026-10-27T06:58:30.535640UTCにfailed_or_unknownで閉鎖した。73試行/72応答/新未知1/未試行17、全90精度null・不採用。Native73は6.253827秒でRemoteDisconnected、同PID439676のserver CUDA launch timeout/abortと06:58:25UTCのGPU watchdog7秒/Xid8が一致し、HTTP1200秒timeoutではない。Graph OFFだけでは今回の障害は消えなかったが、旧v10との根本原因一致は未証明。現在のHost GPUは応答しowned processは終了済み。未知要求を再送せず、Raw139/台帳/旧証拠・成功72を保全し部分監査と原因に対応する別Runtime条件の調査を進める。Driver/OS変更/Reset/rebootは実施しない。全90/Known16/Main/Cal/Gate11は未達、Goal active・Phase12未開始。以下は時点別履歴。

2026-10-27 14:49 JST現在: v27の因果NS2・帰属C2・日英Rewrite2は全実監査を通過した。帰属結果0fc3964d57808d405d836b1a62915bc3dcce180bf56699dc2bbe63c126fdb2c7、書換え結果14cfdc0fdf3afb7a6026143abcc0eb3ac90f5c83ad05839b4f10ae13ba9629ef。新品質sealは全task/input/answer/Raw7/packet Hashと実時間順を結合し、旧補証を流用しない。終了22 Run時点の費用v11は新200/旧込1109/旧未知3（Manifest167f4acc61a332a88b91486ee0d0d771c0174c98868e29fd60288cb10efef745）。全90意味検証を固定9312e7d/Handle65957/Plan a282e5d64491d5e2468f49f6428a8652f401a26bb4a68a2799fa241a33dcc78bで初回実行中（90Call/22720秒/個別1200/監視5/Retry0、実開始UTC 2026-10-27T05:47:56.302783+00:00）。全90/新鮮Known84の実採用は未了、Main/Cal/Gate11未達、Goal active・Phase12未開始。以下は各時点の履歴。

2026-10-27 14:29 JST追記: 固定9312e7dのv27実再現（300資産＋alias2/専用uv58/実IDa0d7/clean）と生成0全90/33CUDAが通過した。最大3926＋予約6144/12288、余裕2218、結果Manifest f15ae1f7cb0da165e4ae5fee8706871c050144cc496e0f510ed395cbe2d13c38。因果Smoke2も全文Source/理由・機械payload/Schema/4096/全費用/追加0再読でNS2/2・Health2/未知0、正式結果c974606e108818c1fd6ad3a3af14f415b801749e629c93c92e79833d9fb8bfd4を保存した。両forced4105/最終reason160の末尾断片は留保であり、意味改善や原因解消を断定しない。終了20 Run時点の費用v10は新196/旧込1105/旧未知3。現在は同固定WTで別登録の帰属C2（元逆）をHandle88876/Plan acd76a2cd4a5f1641fe9a49b66a709c2dcad39667e87808fa93dc8908f0d8a82・2Call/3000秒/個別1200/Retry0で初回実行中。Rewrite/全90/新Known84/実Main/Cal/最終凍結は未了、Goal active・Gate11未通過・Phase12未開始。以下は各時点の記録。

2026-10-27 14:09 JST現在: v26は因果NS2通過後、帰属C2が元NS/逆CでExpected1/2のため不採用。全Raw/意味・費用監査を正式保存し、新194試行・旧込み1103/旧未知3を維持した。次v27はJudge Prompt14→15だけを変更し、Model/Graph OFF Runtime/共通reasoning4096/Schema/Core94/Rewrite・Extract/全90入力・Expected・基準を固定する。候補ID `a0d7d9a09eedc2182eb8443af0d5625012b4ab610c8fee040fec777cbdf18f2b`、正式事前登録[Manifest](../data/manifests/phase11_semantic_v27_preregistration_v1.json) SHA `e589422726c5d41a8bb83a0cfe5e3e297d80a1b950c8542fcd8eedde4f9514cd`。88監査成果・18入力・Core94とPromptのみの差を独立照合、全1065 Test（35.53秒）/Ruff成功。各Run有限予算・共有v3 Guardを維持し、300資産＋alias2の実Checkout再現、生成0→因果NS2→帰属C2→Rewrite2/全文品質→全90→新鮮Known84を必要とする。v27 Native0・意味未採用、Main/Cal/Gate11未達、Goal active・Phase12未開始。以下は観測時点ごとの履歴。

2026-10-27 13:44 JST追記: 実修復はRoot bcd42dbのCommit/Push後に適用・独立再監査し、同登録Runの初回Nativeを実行した。v26因果NS2は2/2通過（理由末尾の断片/両forcedは留保）。次の元c4帰属C2は元NS/逆Cで固定Expected1/2、Health2/2/未知0でも不採用。4Call以外のRewrite/全90/新Known84は未開始、全90精度null。全Raw/全理由/thinking/Native/費用/旧証拠を監査保存し、18終端Run/新194/旧込1103/旧未知3・費用v9を照合。次v27は4096を保つPrompt単一軸の最小案を独立査読中で、Identity/正式登録/Nativeは未了。Main/Cal/Gate11未達、Goal active・Phase12未開始。

2026-10-27 13:18 JST追記: v26実生成0とNative前停止証拠を保存し、同候補/全科学条件不変・Native未開始の2JSON参照先だけを直す別Protocol v1を正式化した。旧Guard/Core94は変えず、全1065 Test（34.49秒）/Ruffと実inspect（OSlock・Git読取8/Native0/WT・台帳無変更）に通過。旧Plan/失敗21証拠/台帳全Byteをpinし、重複・開始済・Native・出力・他の変更を拒否する。独立レビューも完了、Commit/Push後のRoot適用はまだ未実施、意味/新Known84/Main/Cal/Gate11未達、Goal active・Phase12未開始。

2026-10-27 13:02 JST最新: v25は16応答/4条件・Critical3/4で不採用、残74Call未試行・全90精度null。終端15 Run累積1099/旧未知3は保存済み。次v26はPrompt14等を固定して共通reasoning4096だけを変えたIDd809。固定61f56ad専用WTの278資産＋alias/uv58/実IDと全90入力生成0（20.625538秒、最大3644＋予約6144/12288、33/33 CUDA）を照合した。因果Smokeは登録済みだがRootが追加配置した未追跡の新実測Manifest4件をclean GuardがNative前拒否し、新Native0。元Plan/row/失敗ログを保全、配置だけを直す別Versionの厳格修復を検証中で、同条件再登録やGuard除外は行わない。Main/Cal/最終凍結/Gate11未達・Goal active・Phase12未開始。以下の記録は各時点の履歴。

2026-10-26 19:27 JST最新: 日英意味v21は固定d40で全70要求/58条件を終了し、Critical4/4・人工英語24/24・日本語30/30・未知0で通過した。原Raw133/固定Source98・全Native/理由/費用を独立監査し、追加0再読と正規コピーを完了。初回3BのGraph OFF生成0/既知日英2Smokeも固定479で完了・監査し、累積993試行/旧未知3を保存した。後工程のGroup欠落を非推論修正し、全889 Test/Ruffと実70のLock保持下再検証・最終Validator検証v5を通過。新94Coreの候補v23/Receiptv2へ旧証拠を明示的に結び、元15 QA/42文/30条件/84 CallのKnown v12を準備した。Known新Native、Main/Cal/最終凍結は未実施。Goalはactive、Gate11未通過、Phase12未開始。 以下の記録は各作業時点の履歴として保持する。

2026-10-26 18:24 JST追記: 初回生成3Bの旧Graph ON参照を事前点検で発見し、Model/日英初回Prompt/全generation値を保った新baseline設定（runtime_specだけGraph OFF）と検証入口を追加した。既知接続の日英各1例だけを対象とし、生成0/Smoke2・入力全文・Gold非注入・新出力排他・未知保全を厳密に検査する。新851 Test（29.60秒）/Ruffと実Contractの生成0照合に成功、core93/実行中d40は不変。新初回生成の実Runtime確認は未実施で、ソフトウェア確認を実Health/採用としない。

2026-10-26最新: [自律継続v3](phase11_autonomy_v3.md)を全844Test/Ruffで確認し、d40f927をCommit/通常Push・Remote一致。固定専用WTで現行資産/可変Rawを再現し、Graph OFFの生成0全70入力・Smoke2成功/未知0・新v21生成0全70入力/形式10（Strict9成功＋旧方式対照1）を完了・監査した。終了済み分は旧込み921試行/確定未知3、固定v21の日英意味70Callを実行中。旧v10不採用と暖鋒理由の誤読を保全、Main/Cal/最終凍結は未実施。Goalはactive、Gate11未通過・Phase12未開始。以下の旧停止指示は10月24日の新許可で置換する。

2026-10-24の作業指示更新: [研究室向け開始文](phase11_lab_weekend_start.md)と[週末Goal](phase11_lab_weekend_goal.md)を保存。
旧の候補1個/188回/4時間/障害時Goal停止は新規の自律継続方針へ置換する。旧失敗/未知/台帳は保存し、意味基準は維持する。
研究室での新Protocol実装・実験開始はまだ行っていない。以下の不採用/停止結果は実績として有効である。

更新日: 2026-10-23。新チャットでは本書と[評価器・資源・テスト見直し方針](phase11_evaluator_review_policy_v1.md)から読む。
工程の正本は[research_roadmap.md](research_roadmap.md)。長い日誌/過去の引継ぎは履歴であり、必要な箇所だけ参照する。
新チャット用の貼付文は[phase11_next_chat_prompt.md](phase11_next_chat_prompt.md)。

2026-10-23再開後の最新: **[新Known v10は不採用・全終了](phase11_known_trace_direct_result_v10.md)**。
新基準v2の全経路実装と全782 Test/Ruff、生成0/全84入力/全CUDA、Smoke計2 Callは通過した。
固定903f4cfの全Knownは56試行（55応答/未知1）でCUDA launch timeout・Watchdog/Xid8再発。
非支持全16判定も14/16＝87.5%で0.90未達。全予定率null、28 Call未試行を保持。
正本は`data/manifests/phase11_known_trace_result_v10.json`、Raw81/全123 Artifactを正規保存・WT照合した。
**稼働中のNativeはない。** 現チャットSession68501/監査74660は終了。旧Runも新v10も再起動しない。
新開発58/188・累積909/1039・未知計3、Task4310.915004秒/14400秒、保守的壁4381.357537秒。
未使用130（Known28+未割当102）と旧69・42/42/81/42は自動再配分しない。
Main各20/予約Cal各20/品質・費用/最終N・凍結は未了、Gate11未通過・Phase12未開始。
ユーザー指定の障害時一時停止条件に該当する。保存・同期後にGoalを一時停止し、再開は下記第6節の判断から行う。
以下の初回移行時・実行中・新基準未実装の記録より、この追記とロードマップを優先する。

## 1. 今回の依頼と引継ぎの意味

ユーザーは、評価器の改善へ時間をかけすぎているため、研究目的と資源からテスト・妥協範囲・打切りを見直し、
別チャットの新しい`/goal`でPhase 11全体を完了したいと依頼した。
無制限の評価器最適化を再開しない。研究は順序感度・採用/一回書換え・独立回答品質・費用の日英比較である。

本チャットのGoalは実状態を確認して**paused**。完了ではない。
Goalsはチャット単位であり、新チャットに過去の内部履歴やGoalが自動継承されるとは仮定しない。
新チャットで新しい`/goal`を設定する。公式資料:
[Using Goals in Codex](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex)、
[Developer commands](https://learn.chatgpt.com/docs/developer-commands)。
長い詳細はファイルへ置き、4000文字以内のGoalから参照する。

## 2. 最初の安全な確認

Repository: `/home/uchida/デスクトップ/code/rag_research`、Branch: `main`、Origin: `https://github.com/hinattyamann/rag_research.git`。
最初にAGENTS.mdとGit状態/HEAD/接続先/追跡先を確認し、Fetch完了後の差分を調べる。
未Commit変更を保持し、CleanでRemoteだけ先行の場合のみ`pull --ff-only`。Force/Reset/Cleanを使わない。

記録済みCommit:

- `9727409eee7a3f8c1ca76f879234f32de0462bb9`: 全意味監査と旧全回帰v9登録。v9実験の固定Commit。
- `b75bd070efcfaeb83d4850736ce3ed0e48b07a84`: 回帰v9の生成0/開始記録。
- `f5edacb`: 温度0.2の実測Judge時間と資源見積りを保存。
- `c3f42dc`: 旧回帰v9のCUDA停止と未知応答の全監査を保存。

本書・方針を導入した最終Commitは`git log -1 -- docs/phase11_handover_2026-10-23.md`と実HEADから確認する。
自分自身のCommit IDを本文に埋め込むためにCommitを作り直さない。

**稼働中の実験はない。** Native session72566/監査23121/生成0の98818、親意味89310/監査60518は終了済み。
履歴にある「実行中」を見て再起動しない。新チャットのTool Handleへ過去の番号が移るとも仮定しない。
新しく開始する実験だけ、固定Commitの専用WTと新Run/上限/条件を事前保存する。

## 3. 完了済みの基盤――作り直さない

| 範囲 | 現在の実証拠・限界 |
|---|---|
| 英語Phase 1〜10 | CLAPNQ基盤・CUDA接続・旧開発確認を保持。旧修復3種類/Failure Dataset4種類へ戻らない |
| 日本語Source選定/取得 | `baobab-trees/wikipedia-human-retrieval-ja`固定Revision。838 Source-answered QA/706 Group、欠測も保持 |
| 日本語分割 | Dev545/Cal84/Eval209。開発Preview閉包142 QA/95 Groupを使用済みとして隔離 |
| Corpus/参照 | JA2118記事→30065子Passage、EN183889子Passage。全文保持、引用/脚注投影・欠測監査を完了 |
| 検索 | multilingual-e5-small固定FP32 ONNX/CUDA、日英全Index/BM25/Hybridを構築・検証 |
| 共通RAG | 日英の既知1 QAずつで初回→固定文→順序/反復→一回書換え→匿名候補品質→照合を実走。主各20 QAの代用ではない |
| 既知診断 | 人工日英27例/既知2例、旧全15 QA/42文、裸拒否8を保持。多数の失敗も保存 |
| Main/Cal入口 | 準備/実行/匿名採点封印/解析/証明の実装とTestはある。新基準への改訂と実成功側は未了 |
| 統計 | QA内の順序差−反復差、Group Bootstrap、日英非対応差を事前定義/実装 |
| 最終Validator | 日英・物理Payload・主/Cal/品質・N/資源/統計の検証を実装。未達時に凍結を拒否する。実凍結は未了 |

主な基盤資料:
`docs/english_japanese_expansion.md`、`docs/phase11_bilingual_pipeline.md`、
`docs/phase11_bilingual_indexes.md`、`docs/phase11_statistical_plan.md`、`docs/ai_quality_protocol.md`。
主なManifest:
`phase11_japanese_source_selection.json`、`phase11_japanese_snapshot_group_manifest.json`、
`phase11_japanese_reference_projection_v2.json`、`phase11_bilingual_connection_result_v1.json`、
`phase11_bilingual_connection_quality_freeze_v1.json`、`phase11_bilingual_finalization_validation_v2.json`。
いずれも`data/manifests/`内。現在のAssetsは`configs/phase11_bilingual_assets_v2.json`。

## 4. 評価器と直近の結果

初回生成はQwen2.5-3B固定/T0、補助候補はQwen3.5-9B Q6_K固定GGUF。
現在の候補`configs/phase11_semantic_candidate_v20.yaml`は温度0.2、Context12288、出力6144、
推論4096、Seed42、top_k20/top_p0.95/min_p0/presence1.5、6 Threads/Batch128、全層CUDA。
モデルGGUF SHA256は`91898433cf5ce0a8f45516a4cc3e9343b6e01d052d01f684309098c66a326c59`。
Model Manifest: `data/manifests/phase11_auxiliary_qwen35_9b_q6_manifest_v1.json`。
Runtimeはllama.cpp b11433/CUDA12.8配布物+system12.9。実機はRTX5060Ti/8151 MiB、i5-14400、RAM約7.7 GiB。

### 直近の全意味診断

固定17d57c6/89310の全58条件/70 Callは終了・全監査済み。
Critical4/4・人工EN24/24・JA28/30・誤支持0、確定66/68/支持28/28。
JAのNS→C2は保持。全68確定Labelは旧T1と同じで、温度による精度改善を主張しない。
人工27例の元/逆は1文書/同一入力。Council曖昧c6は両NS、両F5/7。
Raw136/202 Artifact、実70 Native Schema/Sampler/Source95/追加0再開を保存。
正本: `data/manifests/phase11_qwen35_q6_temperature_semantic_result_v1.json`、
`docs/phase11_qwen35_q6_temperature_semantic_result_v1.md`。

### 旧全回帰v9――停止済み、不採用

固定9727409/72566は3条件/15記録試行、会議14応答取得、Zidane元c1の1応答不明で終了。
LogはCUDA launch timeout/応答前切断。根本原因未特定。入力/出力不明を温度効果と断定しない。
会議観測確定12/12・支持10/10・誤支持0でも、全74/58精度はnull、27条件未試行/69 Call未使用。
失敗LeafにはNative応答/最終Label/出力Token数がない。過去の成功結果や途中Logから復元しない。
全15入力は親診断と同一、提出Schema15/取得14 Native Schemaと実Samplerを検証。
95 Source/元23 File不変・再開追加0、193資源観測/エラー0、Raw26/全110 Artifactを保存・WT照合。
実Main準備CLIも早期拒否し出力なし。

正本: `data/manifests/phase11_known_trace_result_v9.json`、`docs/phase11_known_trace_direct_result_v9.md`。
Raw: `data/runs/semantic_diagnostics/phase11-qwen35-9b-q6-temperature-known-regression-v9`。
固定WT: `.tools/worktrees/phase11-known-trace-regression-v9`。
監査: `data/runs/development_screening/phase11-q6-temperature-known-v9-audit-v1`。
Config/Plan: `configs/phase11_known_trace_candidate_v9.yaml`/`phase11_known_trace_regression_v9.json`。
旧事前登録: `data/manifests/phase11_qwen35_9b_preregistration_v18.json`。

旧Q6回帰v8は42 Call後に誤支持3/非支持16、支持23/24、NS/Cの取り違え2。
改訂する意味基準でも非支持Specificity81.25%で不適合。v9もHealth不適合。
どちらも旧失敗を新しい合格へ読み替えない。

全9B記録851（Q4 317/Q5 317/Q6 217）、応答不明は計2。
旧上限920、v9未使用69/旧未使用42・42・81・42を保持。次の新枠へ繰り越さない。

## 5. 新基準の実装済み範囲と未達

[基準v2](phase11_binary_adoption_v2.md)の実装/事前登録・旧v1拒否・Version整合・被覆/不足・Health境界を確認した。
推論Core/Prompt/Samplerは不変で、温度0.2の旧全意味70 Call/形式証拠をHash照合して再利用した。
全回帰のAI監査は55最終理由を読み、誤支持2/C↔NS3/表を誤読した正Label理由2を保存した。
Camp David逆の4保存応答を失わず、3支持を含む全Leafの観測34S/34とRoot有効条件の31Sを区別する。
失敗条件のF/判断・未知出力Tokenはnullのまま。全Run指標を観測部分だけで通過へ変更しない。

新Scopeで使ったModel候補は最大1個の最終v20、開発Native計58。旧851や未使用枠は保全する。
実Main/Cal/独立回答品質Yは未実施。Known意味監査をこれらの代用にしない。

## 6. 次に行うこと――再開に先立つ判断

1. 新v10の結果/Raw/Manifest/HashとGitを確認する。新規生成をせず、旧失敗と未知応答3件を保全する。
2. Runtime切分けの別計画（例: 固定SourceをCUDA Graph OFFで別Build/Hash化）を許可するか判断する。
   Root Causeは未確定で、Driver/Reset/再起動/OS設定は変更していない。システム変更は具体案/影響と明示的な承認を要する。
3. 意味候補を追加する候補上限/予算の改訂を明示的に認めるか、研究範囲を再設計するか判断する。
   CUDAだけを直しても非支持87.5%は未達。0.90/Expected/閾値0.7を自動変更しない。
4. 新たな許可/事前登録と完全KnownのHealth・意味実採用がそろって初めて、元選定のMain日英各20へ進む。
   全品質/Expected封印・完全比較各10 QA以上・実費用・主証明書→予約Cal各20→最終N/条件/統計/Hash/Gate11を維持する。

上限未到達を理由に未使用130を自動消費したり、失敗Runの残28を実行したりしない。
保存物と実装Testの完成だけでPhase11を完了にせず、Phase12は開始しない。

## 7. 実装入口と分割・統計・採点の重要事項

- Main: `scripts/prepare_bilingual_main.py`、`run_bilingual_development.py`、`certify_bilingual_main.py`。
- Cal: `prepare_bilingual_calibration.py`、`run_bilingual_calibration.py`、`analyze_bilingual_calibration.py`。
- Freeze: `scripts/finalize_bilingual_phase11.py`。`configs/phase11_bilingual_freeze_decisions_v1.json`はN/資源/証拠nullの雛形。
- Main選定: `data/manifests/phase11_main_development_selection_v1.json`（日英20 Groupずつ、使用済みを除外済み）。
- Cal予約: `data/manifests/phase11_bilingual_calibration_selection_v1.json`（各20、Main/Groupと非重複）。
  旧EN Cal225問は検索調整済みなので、新EN Calは未使用Devから別予約。JAは元Calから予約。
- QA内の質問/草稿/文単位/根拠本文・ID・Titleを固定し、文書提示順だけ操作。初回/書換えへGoldを漏らさない。
- 主量DはQA内の順序変更ペア不一致率−同一順序反復ペア不一致率。QA等重み、Group Bootstrap10000/Seed42、
  日英は非対応差/95%CI。別Dataset差を言語単独の因果効果としない。有効Group不足のCIはnull。
- 採点は内部Judgeから分け、条件/F/判断/初回か書換えかを隠す。実採点者/human_reviewed=false/
  Model識別子取得可否/実際の履歴隔離を記録。できなかった盲検や隔離を達成済みにしない。
- EvaluationはEN564/JA209のMetadata母集団からID選定だけ行い、質問/Reference/結果を条件調整に開かない。

## 8. ローカル資産と検証・Git運用

Python/工具はuv。基本: `UV_CACHE_DIR="$PWD/.tools/uv-cache" .tools/bin/uv run ...`。
GPU環境は`environments/embedding_gpu`、WTごとに`uv sync --project environments/embedding_gpu --frozen --offline`。
Nativeは対応WTをcwdにして`uv run --project environments/embedding_gpu --frozen --offline python ...`。
OSをまたいでvenvを使い回さず、大型Modelは全体をRAMへ読み込まずストリームHashする。

最後の全実装検証は**761 passed in 30.43s / Ruff成功**。新基準の実装Testはまだない。
機械的な監査証拠と、実研究での成功を区別する。新実装でSourceが変われば旧Validator検証資料も再照合する。

同じPC/Repositoryなら既存のdata/models・data/runtimes・data/indexes・data/runsが残る。
**Git Pushだけではこれらの未追跡実体は移動しない。** 別PCならManifestの参照先を別途転送/再取得し、Hash確認する。
Raw不足を理由に旧失敗やCalibrationを再生成しない。`phase11_chat_handover_v1.json`は重要証拠の照合目録であり、
全モデル/Index/環境を内包した移行Archiveではない。

各工程でユーザーへ成果・残る問題を説明する。意味ある単位で今回分だけCommit・通常Pushし、
Remote先端との一致/未Commit/未Pushと次工程を報告。研究日誌はJST時刻/決定/問題/到達点/次の完了条件を記録する。
引継ぎは最新状態を短く清書し、古い「実行中」記録を先頭へ際限なく積み重ねない。
