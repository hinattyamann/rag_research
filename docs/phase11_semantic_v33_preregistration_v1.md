# Phase11 v33 部分GPU候補の正式事前登録

記録時間: 2026-10-28 06:32 JST。status=preregistered_waiting_checkout。正式Manifest [phase11_semantic_v33_preregistration_v1.json](../data/manifests/phase11_semantic_v33_preregistration_v1.json)、SHA `4f40971725f62293a430c4b4addac42ad31e4d022da695f94e77d061b4444296`。新Native0・実Run0で、意味採用/Main/Cal/Gate11は未了。

候補IDは `5466f860cb3731a946d0f351ea4dd374f5002d0a1eb8fb1045c7e4bd972d676b`。科学上の親v28の保存9BQ6/Prompt15/推論4096/出力6144/Context12288/batch128/GraphOFF+FAoffを維持し、全層99から厳密GPU16/33へ配置を変更する。Core6とSampler内の実行記述が異なり、Identity全体の単一軸同値やCUDA原因・修復を主張しない。旧47返却は新採用へ流用しない。Model/Runtimeの実Hash、全90入力byte同値、Source/Expected/全基準、形式v6/最終Validatorソフトウェアv8の限界は[実行前証拠](phase11_v33_preexecution_evidence_v1.md)を参照する。

正式事前登録は現94Core・22正式入力・70canonical成果を封印し、67独立copyと補助3成果を保存した。親v28・旧v32不採用・全失敗/未知/未使用枠・累積費用v20を結合する。Source-onlyの反証/独立レビュー・Root全文レビューと修正履歴を含み、新実Run前に元Guardを保ったまま使う。Source Publisher-v2とfresh releaseをRootが全67小Hash/全7段階/全ready条件を確認してから一回実行し成功した（tool ec4d1a、child0.364461996秒/tool wall0.341973647秒は別観測）。実GPU Health・新Tokenizer11・形式10・意味採用はまだ証明していない。

| 段階 | 新生成Call | Run壁上限秒 | 個別timeout秒 |
| --- | ---: | ---: | ---: |
| Tokenizer11実観測 | 0 | 1800 | 1200 |
| 全90入力のToken収容/資源 | 0 | 1800 | 1200 |
| 人工形式（厳密9＋既定legacy比較1） | 10 | 3000 | 1200 |
| 日英因果NS | 2 | 3000 | 1200 |
| Council元逆C | 2 | 3000 | 1200 |
| 日英一回Rewrite | 2 | 1800 | 1200 |
| 39QA/45固定文/78条件の全意味 | 90 | 22720 | 1200 |

形式だけ推論128/出力512、他の意味/Rewriteは4096/6144を使う。監視5秒・retry0・所有groupだけを停止し、失敗/未知/未試行/実費を消さない。Rewrite壁1800は2要求の最悪2400より短く、部分/未知でも保全し同条件を再送しない。既存Handle/Journal/Logを確認し、終了済みHandle・所有PID/Group停止・Root終端認可の後だけRawを監査する。最初のPlanは固定Checkout再現と空のcompleted認可、以降は全前段の実合格証明/終端認可を要求する。実v3 Guardは各固定Planで検証・登録し、初期のSource-only構築例を実合格扱いしない。

全90新規採用後にだけ、別Known21の入力0と元15QA/42文/30条件/84Callを新鮮に実施する。旧未実行Known20は保存。上記106＋Known84＝最大190新生成は今回候補の見積りで、Goal全体の上限ではない。旧47返却のHTTP平均54.618959秒/全90参考4915.706321秒は別配置の参考で、部分GPU速度を保証しない。新SmokeのHost RAM/GPU/時間を実測し、全90前に資源見積りだけを更新できる。

支持Recall/非支持Specificity各0.90、最低被覆、Health、全固定文・全分母、F0.7、提示順のみ操作、同一順序反復と一回書換えを維持する。元Main日英各20と別予約Cal各20、両言語全品質/Expected封印後の解析、最終N/統計/停止/欠測規則・実Validator/Manifest/Hash/Gate11はこれから。Evaluation本文/回答/結果を条件調整に使わない。全評価者はAI、human_reviewed=false・history_isolated=false・厳密Model ID null、設定はユーザー申告6.1 Sol 極高。別agentを独立Modelと呼ばない。Phase12を開始しない。

次の完了条件: 今回の変更のCommit/通常Push/Remote一致、新固定Checkoutの実資産/uv再現、全7段階の実検証・監査。

2026-10-28 06:38 JST追記: [出版後独立検算](../data/runs/development_screening/phase11-v33-preregistration-independent-postcheck-v1/postcheck.json) SHA `13b613ea9b9f6e282581f6ae2653d637ffb4153d845f03cbfb9432417beb1797` が全70成果/22入力/67＋3copy・Hash/stat/独立inode・六成分/全有限条件に通過した（実一回inner0.315780795秒/caller0.364567730秒、全禁止count0）。Rootの追加検算で出版用Hash一覧が自身を空SHAで含むP1を発見した。旧11ファイル/不備seal7f7aed11を変更せず、別[訂正記録](../data/runs/development_screening/phase11-v33-preregistration-independent-postcheck-v1/canonical-seal-erratum-v2.json)と訂正seal `SHA256SUMS-canonical-v2` SHA `21247c70d5ea07dce2f29c38696be096b227792937dbe324f05871249ad438d4`（全12成果、自身除外）を保存した。全70/22・旧11・新12のRoot再照合0.003890940秒、[Root証拠](../data/runs/lab/phase11-v33-preregistration-Root-postcheck-v2/review.json) SHA `e3e37d5468976a3981d37dcebc85439ea4eeefbb6c3ee58742985290cfe907ce`。最初のRoot照合はsealファイル名の取り違え、二回目は実自己混入を検出したもので、失敗を記録し、実験再実行・推論・Model Hash・postcheck本体再実行はいずれも0。正式Manifest/結果は変更していない。
