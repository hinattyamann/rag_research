# Phase11 v30：明示reasoning-prefillを共通Coreへ適用する候補

2026-10-27 20:16 JST追記: v30の[正式事前登録](../data/manifests/phase11_semantic_v30_preregistration_v1.json) SHAa10f5e2c4fa2b0c1ec651b37711dfa3b13f5868b552a45dfdafb3d7830fee4e5を発行した。新実ID87cf5942abf0652849246229c0b2550846c7c674aaa764c3489861e1baba8e6b・22formal入力/91canonical成果を固定し、共通Core3だけのprefill修正と非Core5成分不変、全1203 Test/39.11秒・Ruff、全90payload/Goldなしを結合した。有限producerは差分4 Test/.07秒・実Guard1回4.076925秒・実pending拒否2件が成功し、旧Guard変更/既存失敗の再送0。詳細は[v30条件](phase11_semantic_v30_preregistration_v1.md)。正式事前登録は実機合格ではなく、独立照合/Commit/専用WT実再現とTokenizer0→全90入力0→新形式10→NS/C/Rewrite品質→全90→新鮮Known84はこれから。将来full90監査のnotes/timer結合P1は旧版を保全して別新版で閉じる後段条件とした。Main/Cal/Gate11未達・Goal active・Phase12未開始。

記録時間: 2026-10-27 20:07 JST。実新Identity `87cf5942abf0652849246229c0b2550846c7c674aaa764c3489861e1baba8e6b`。正式Manifestの発行・固定Checkoutの実再現・実機各段階は未実施である。

v29の[失敗診断](../data/manifests/phase11_v29_tokenizer_preflight_failure_v1.json)は、実8Bテンプレートの末尾がbare assistantで、旧処理が既に `<think>\n` を含むと仮定していたことを示した。Native0の停止であり、CUDA生成安定性・意味適合は証明していない。人工形式入口だけを変更してもAuxTaskと一回書換えに同じ仮定が残るため、新候補v30で共通処理を修正する。仮説は「明示設定済みprefillを共通箇所で適用することで、元の科学入力と契約を保って実8B推論へ進める」であり、CUDA障害の根治とは位置づけない。

変更するCoreは `generation/auxiliary_config.py`、`evaluation/tasks.py`、`recovery/answer_rewrite.py` の3ファイル、全Core数は94のままである。既存mode `chatml_think_suffix_v1` で厳密bare末尾だけ固定THINK_PREFILLを追加する。既に正規suffixを含む入力とmode noneは元のtext/token bytesを維持する。未知suffixや追加による元token prefixの変化を拒否し、raw/effective全文・tokens・追加text/tokensを保存する。新形式入口v5と全入力preflightv2も同じhelperを使い、旧入口/旧固定WTのbytesを変更しない。Model Qwen3-8B Q4_K_M、GraphOFF b11433、FAoff/context12288/batch128、Prompt15、4096 reasoning/6144 output、Sampler、Schema、全39QA/45文/78条件/90calls、Expectedと採用条件はv29から保持する。

実ModelHash1回を含むIdentity構築は4.781564670秒で成功し、非Core5成分同一・Core3pathだけ差分・新IDを検証した。Source検証は全1203 Test/39.11秒とRuffが成功した。初回sandboxのloopback EPERMと、明示prefill設定なのにsuffixを持たない旧fake2の失敗も保存している。修正したfakeはSchema/cacheのassertionを変更していない。テストは実ModelのTokenizer/生成・意味性能の代替ではない。

| 段階 | 有限Native枠 | 壁上限秒 | 前段条件 |
|---|---:|---:|---|
| 新Tokenizer11witness | 0 | 1800 | 固定Commit/専用uv/資産再現・正式事前登録 |
| 全90入力preflightv2 | 0 | 1800 | 新Tokenizer全11実監査 |
| 新形式10（Strict9/意図したlegacy1） | 10 | 3000 | 全90入力の全文token収容・実GPU検査 |
| 日英因果NS | 2 | 3000 | 新形式全監査 |
| 日英帰属C | 2 | 3000 | 因果全監査 |
| 日英一回書換え/全文品質 | 2 | 1800 | 帰属全監査 |
| 全意味90 | 90 | 22720 | 全先行結果・書換え品質の実監査 |

各Runを通常v3 Guardへ別Planで登録する。合計有限Native枠106、個別HTTP1200秒・監視5秒・Retry0。全90の見積りはv28返却47件の実HTTP2567.091079秒を参考とし、未知1件の10.641596秒は除外して消さず費用へ残す。新8Bの速度保証とは呼ばない。全90の採用前に全文Source・reason・保存thinkingを実読し、実notes/timer/UTC/agent履歴を監査結合する。Rootの閉Handle・終了row・owned PID/create/group確認前はRawを読まない。障害時は自身のRunを停止・保全し、同条件を再送せず、原因に対応する別仮説へ進む。

全90採用後に限り、元15QA/42文/元逆30条件/新鮮84Callを別に実行し、支持Recall・非支持Specificity各0.90以上・最低被覆・Healthの全条件で採用する。全90やSmokeの合格だけではKnownを合格扱いしない。旧909/未知3と全後続失敗・未試行、旧v29生成0/費用v16、旧8B不合格を保持する。Core変更により旧最終Validator v6のSource証拠もそのまま採用しない。

実Known採用後は新3B baseline生成0/日英2、新Coreに結ぶ元Main20QAずつ・別予約Cal20QAずつを実行する。各段階で両言語の全匿名品質/Expectedを封印してから内部結果を開く。全文・固定回答/根拠本文/ID/Title・順序変更と同一順序反復・F0.7・一回書換え・未使用Group・全分母を維持し、Goldを推論へ渡さない。Evaluation本文/回答/結果で調整しない。実Main/Cal証明・独立品質/費用・実測N/資源/統計/停止/欠測・新最終Validator/Manifest/Hashが揃うまでGate11未達であり、Phase12を開始しない。

支援AIのユーザー設定は6.1 Sol 極高、厳密なserved Model識別子は取得不可/null、human_reviewed=false、実履歴継承はfork allで独立履歴ではない。AI監査者の差を独立Model実験とは呼ばない。
