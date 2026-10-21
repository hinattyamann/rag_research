# Phase 11 日英の意味判定・拒否Fallbackの診断計画

開始: 2026年10月21日。前工程e802127の日英既知各1問は肯定例の接続確認で、旧英語の誤支持は未解決。
本工程は使用済み例と人工例のDevelopment診断であり、未使用Calibration/Evaluationを開かない。

## 実行前に固定する手順と成果物

1. 旧GPU20問の固定TraceからCouncil/Zidaneの質問・初回回答・全使用本文/ID/Title・固定文をそのまま取り出す。
   旧AI監査のExpectedを保持し、曖昧と記録された単位は先に採用集計対象外と明示する。
   生成への正解注入や、新Corpusでの再検索/初回再生成は行わない。
2. 旧人工英語12例と、新しい日本語人工15例（主体/時期、範囲付き回数、複合文、推測の限定、表の時点）を固定する。
   全文・期待Labelと理由を診断Planへ保存する。日本語人工例は主実験Datasetや日英翻訳対ではない。
3. 診断専用Runnerは既存`execute_task`/実Tokenizer/固定Schema/Journal/Model・CUDA検証を共用する。
   Expected/理由/ケースIDをModel入力へ渡さず、質問・固定文・実使用本文だけを渡す。
   元順序と逆順の本文集合とSchemaは同一、Seed42/温度0.6/推論1536/出力3072/Context12288を固定する。
   人工例が1文書の場合は両条件で同じPromptを実呼出しする。異なる2順序や独立した2標本とは数えない。
4. 候補ごとに既知2例×2順序を先行する。形式/Runtime失敗・入力超過は即停止、Retry0。
   明確なCritical単位が全4条件で旧Expectedと一致しない候補は残る人工54条件へ進めない。
   成功した候補だけ人工27例×2順序へ進む。最大58 Completion/候補。
5. 最大3候補を段階的に扱う。最初は接続確認と同じ4B/Prompt、次は主体・関係・時期・数量範囲を明示比較する
   一つのPrompt改訂、それでも不通過ならローカルGPUに収まる8B級の固定版候補を一次資料/Hash/資源で確認する。
   別候補は結果前に別Config/Commit/Runへ固定し、最大174 Completion。結果後の採用基準緩和や失敗例の補充はしない。
6. 人工例の採用基準は各言語の全予定条件で正確Label一致率90%以上、明確な非支持例への誤支持0。
   Critical全条件一致・形式失敗0・Overflow0も全て必要とする。実行を止めた未試行分は未試行として残す。
   基準は既知誤支持を除いて先へ進まないための開発確認で、一般精度の保証や主Pilot/最終Gateの代わりではない。
7. 拒否Fallbackは、既存の拒否→有効書換えの保存例を先に確認し、ScoreなしをF0に変換しない。
   明示的な裸の拒否だけを一回書換えへ回す候補を、通常の採用/書換え・障害Fallbackと区別して検証する。
   方針変更は採用条件・費用・主比較への影響を記録し、新規Calibration前に固定する。

必要成果物は、入力/期待Label/予算/停止・採用規則のPlan、専用Code/Test、候補Config/Prompt、
固定CommitのRaw Journal/Runtime・呼出し/Token/時間・全予定/未試行/誤判定のReport、拒否方針の診断と仕様である。
4Bの先行4条件は1〜2分、全58条件は約5〜15分、ピークCombined RSSは前実走の約4.2GBを仮見積りにする。
8Bは未取得/未検証なので収容可能と扱わず、取得容量・VRAM・予算を別途実機で確認する。
長時間実走はCommit固定の専用Worktreeと不変Data/Model/Runtime複製を用い、出力を分ける。

この工程でもGate 11未通過・Phase 12未実施。次の主Development・未使用Calibrationは対象/Health/意味監査・停止規則を別登録する。

## 事前実装の検証

`configs/phase11_semantic_diagnostics_v1.json`に29 Case/58条件を保存した。旧Trace/AI Expectedとの一致を
読込み時にも再確認し、曖昧とされたCouncil c6のExpectedはnullで保持、CriticalはCouncil c4/Zidane c1とする。
入口は`scripts/run_semantic_diagnostics.py`、初期候補は`phase11_semantic_candidate_v1.yaml`。
既存Task契約を使う診断専用入口で、Calibration/EvaluationのQA読込み・検索・回答生成は行わない。
新規7 Testは停止/拡大、期待Label漏洩防止、Runtime/中断の保持・追加呼出し/Server起動0、
入力/Expected・Protocol改変の検出、平均一致率が高くても誤支持があれば不採用となることを確認した。
全450 Test（ホスト5.99秒）とRuffに成功した。実Planの旧Source/Expected・日英Judge指示の一致も確認済み。
実GPUでの新診断結果はまだ得ていない。検証済みCommitに固定して実行する。

## 初期4B候補の実走と事前に予定したPrompt改訂

固定93c3611の専用Worktreeで`phase11-4b-current-v1`を実行した。
Critical4条件は全て形式有効だったが、Council c4を元/逆とも支持、Zidane c1を元順序で支持し、
逆順序のZidaneだけ期待する矛盾と一致した。正確一致1/4・誤支持3/4で不通過、人工54条件は未試行。
4 Completion・入力14162/出力5192 Token、Task秒和54.61。入力超過/Runtime失敗0。
再開10 FileのHash不変・追加呼出し/Server起動0を確認した。初回失敗を`phase11_semantic_current_result_v1.json`で保持した。
元/逆だけの既知2例で感度率を推定しない。

予定した1回のPrompt改訂は`phase11_semantic_alignment_system_v1.txt`と
`phase11_semantic_prompts_{en,ja}_v2.yaml`、設定は`phase11_semantic_candidate_v2.yaml`。
文の主体→動作/関係→対象、時期・数値の範囲・否定・推測の限定を先に照合させる。
部分期間の回数と通算、閉会した組織と後の別主体の行為を架空の一般例で区別し、実例の人名/正解はPromptへ書かない。
既知Source/Expected・採用/停止規則・閾値0.7・Model/Runtime/Seed/予算/Schemaは不変。
初回生成/書換えの指示と日英文単位も変更しない。両言語のJudge指示を同じものにする。
新指示の意味精度はTestでは未認定で、別固定Commit/Runで同じ先行4条件から診断する。

## 4B改訂v2の不通過と8B候補の準備

固定54f116e/別Worktreeの`phase11-4b-alignment-v2`はCritical2/4一致で不通過だった。
Zidaneは元/逆とも矛盾へ改善したが、Council c4は元/逆とも支持のまま。人工54条件は未試行。
形式有効4/4、入力12390/出力4239 Token、Task秒和43.71、入力超過/Runtime失敗0。
逆順Zidaneの理由は正しい3回判定に誤った2014〜2017年を付けており、Label一致だけで理由の正しさも認定しない。
再開10 File不変/追加呼出し/Server起動0、結果は`phase11_semantic_alignment_result_v2.json`。

計画内3番目の候補は[Qwen公式8B GGUF](https://huggingface.co/Qwen/Qwen3-8B-GGUF)の
Revision `7c41481f57cb95916b40956ab2f0b139b296d974`、Q4_K_M/Apache-2.0。
`Qwen3-8B-Q4_K_M.gguf`の公式サイズ5027783488 Byte、SHA256
`d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`を取得後に照合した。
取得/検証122.33秒、Model Completion0。元の3B/4BとRuntimeは保持した。
固定Manifestは`phase11_auxiliary_qwen3_8b_manifest_v1.json`、設定は`phase11_semantic_candidate_v3.yaml`。
Prompt v2・Source/Expected・全基準/閾値・Sampler/予算/Schemaは変えず、Aux Modelだけを8Bへ変更する。
主実験に採用する場合はJudge/書換えのModel変更と費用を両言語で同じように扱い、新Calibration前に固定する。

`preflight_semantic_model.py`は固定Config/Model/RuntimeでServerを起動し、58条件を実Tokenizerで測る。
Completion0・CUDA全層Offload・全入力+出力3072がContext12288以内であることを先に確認し、失敗は保存して停止する。
GPUメモリの一点観測は最大値や長時間安定性と区別する。資源Preflightも意味精度の採用とはしない。
現時点では8Bの取得/Hash/Config契約まで確認済みで、資源Preflight/意味診断はこれから。

## 拒否Fallbackの保存候補による事後診断

旧GPU20問の保存済み・品質固定済み結果には裸の拒否が8問あった。
全8問で既存経路はunscorable/初回維持、初回Y0。共通の一回書換え候補はY1が3、Y0が3、不明2だった。
この3問の改善を現経路は見逃し、初回1 Callに対して常時書換え経路は2 Callsを使っていた。
`refusal_saved_comparison_v1.json`へ保存した。追加Model呼出し0の事後比較であり、未知QAでの新方針の有効性の検証ではない。
候補方針は決定的抽出の`standalone_refusal`だけをJudgeなしの一回書換えへ回し、Scoreはnullのまま残す。
その他の空Claim/抽出障害・Runtime失敗は初回維持の別Fallbackとして残す。方針は未実装・未採用である。

## 8B資源・意味診断の結果と次の方法候補

固定f8df5b5/専用Worktreeの資源Preflightは58条件・最大入力3257 Tokenで全予算内、Completion0、
CUDA37/37層Offload、KV1728 MiBだった。GPU全体7094/8151 MiB使用は一点観測である。
資源確認のReport Hashを先に記録してから意味診断を開始した。

8BのCriticalも2/4一致で不通過。Council c4は元/逆とも誤支持、Zidane c1は元/逆とも矛盾だった。
形式有効4/4・Overflow/Runtime失敗0、入力12390/出力4303 Token、Task秒和67.52。
Zidane元順序の理由には誤った優勝Seasonの追加があり、Label一致と理由の正しさを分けて記録した。
人工54条件は未試行、再開11 File不変・追加Completion/Server起動0。
原本/正規複製とPreflightは`phase11_semantic_8b_result_v3.json`へHash付きで保存した。

初回に予定した3候補はいずれも意味採用不通過で終了し、どれも主Pilot/Calibrationの採用候補にしていない。
次の合理的な方法候補は[固定文ごとの評価](phase11_claimwise_candidate.md)。
全文・全単位・既知Expectedと採用基準を保持し、複数文を一つのCompletionで判定する処理を検討する。
呼出し数・文脈・Fの集約/失敗処理・費用への影響を先に定義した。新方式はまだ実装/実走していない。

## 裸の拒否だけを一回書換えへ回す実装候補

`decision.bare_refusal_policy`を省略/`keep_initial`なら旧動作を維持する。
日英の別Development/Calibration候補で`rewrite_once`を明示した場合に限り、
決定的文抽出の`status=not_applicable`・`extraction_kind=verbatim_sentence_units`・
`unit_audit.exclusion=standalone_refusal`・空Claimの全条件を満たせば、Score null/decision unscorableのまま
actionだけを一回書換え要求へ変える。これは通常の支持率判断とは別の例外である。
その他の空/引用だけ/曖昧な本文・LLM抽出・障害は旧Fallbackのまま。F0を捏造しない。
共通の一回書換え候補を使い、Judge呼出し0、書換え最大1。失敗時は初回維持/rewrite_failed、Retry0。
品質Importは同じRuleを再計算し、経路は`bare_refusal_rewrite_once`と費用を別に表示する。

新規9 Testを含む全459 Test（ホスト6.11秒）/Ruffが成功した。
null維持・通常障害との区別・旧Protocolへの適用拒否・追加呼出し/Server起動0・実費・書換え失敗を検証した。
既存のConfigは初回維持のままで、まだ新方針を新しいQA/Modelへ採用していない。

変更したCodeで旧20問の保存候補を再構成した事後解析では、8 QA/72経路のactionだけが変わり、F/判断は不変。
元順序のY1は6→9、Y0は14→9、不明は0→2、対応する保存費用のCallsは32→40だった。
`refusal_policy_reconstruction_v1.json`へ保存した。旧4Bの候補/Label/費用の再利用・実Model追加0であり、
新Model/未知QAでの効果や新しい実Latencyとはしない。未知QAのProspective検証は主Development/Calibrationで別に必要。
