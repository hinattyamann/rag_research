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
