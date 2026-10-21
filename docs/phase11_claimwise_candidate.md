# Phase 11 固定文ごとの評価候補の次工程計画

作成: 2026年10月21日。初回の3候補（現4B、関係照合4B、同指示8B）は既知Criticalを通過しなかった。
その失敗/未試行と事前基準を保持し、Modelを大きくしたことや形式成功を採用理由にしない。
合理的な次の開発候補として、全固定文を一つのCompletionで評価する方式から、固定文を1文ずつ評価する方式を検証する。
この候補はまだ実装/Model実走しておらず、採用済みではない。

入力監査では、全3候補の元/逆Promptに主体Pius Vの本文が保持され、Runtime Truncationはなかった。
元/逆のSchemaも同一。誤支持したCouncilの推論が予算1536より前に終了した例（4B v2元462/8B元1109 Token）がある。
単に上限だけを増やす根拠とはせず、文ごとの検証で主体対応へ焦点を当てる候補にする。新方式の改善はまだ未確認。

## 変更する範囲と維持する条件

- 各QAの初回回答・全固定文集合と実使用根拠本文/ID/Titleを保持する。1文ずつ別Requestへ渡し、全単位を必ず評価する。
- 代名詞と文脈を失わないよう固定した初回回答全体を非信頼の文脈として渡す。正解/Reference・Expectedは渡さない。
  Target以外の文を事実の根拠にはしない。既存の質問/回答/Claim/文書のWhitelist内で入力を作る。
- 単位ごとのローカルClaim IDはc1へ写し、結果を固定した元Claim IDへ戻す。写像・Request/結果Hashを保存する。
  語句・文単位・ID/Title/本文は途中で再生成/書換え/再Packingしない。
- 各順序のFは、全固定文のsupported数/元の固定文総数。閾値0.7・9試行・共用初回・5反復・Seed・Samplerは維持する。
  1単位でもTask失敗なら当該試行を採点不能とし、成功単位だけでFを計算しない。
- 操作は根拠配列の順序だけとし、QA内の各単位でも同じ順序を使う。元/逆/Shuffle/反復間で本文を変えない。
- 比較の判断数は同じだが、Completion数は最大9×文数/QAとなる。全Raw呼出し・Token/時間を合算し、
  1 Completionと偽らない。1 QA内の全単位結果をそろえてから一つの判断を作る。
  これは旧方式と同じ費用とは扱わず、主実験へ採用するなら日英へ同じ変更を適用して未使用Calibration前に固定する。
- 初回/書換えのModel/指示・回数と匿名品質基準は変えない。裸の拒否は文を作らずnullの別経路とする。

## 検証と実行上限

1. Journal・Schema・元ID対応・F分母/失敗・費用・中断/再開0・正解漏洩防止をTestで検証し、旧共同評価を回帰する。
2. まず同じ8B/関係照合指示・Context12288/出力3072/推論1536を候補にする。入力形式の変更を結果前に固定する。
3. 旧Councilの全7文とZidaneの1文を元/逆で全て評価する（16 Completion）。Critical対象は旧c4/c1の4条件で、
   Expected・曖昧単位・全一致の採用/停止基準は旧Planから変えない。成功した文だけを選ばない。
4. Criticalが全一致した場合だけ、同じ日英人工27例/54条件へ進む。1候補最大70 Completion、Retry0。
   人工例の各言語90%以上/明確な非支持の誤支持0、形式失敗/Overflow0を維持する。概算5〜20分。
5. 通過後も旧Armisticeの誤時刻、暖鋒の時点/表、Tar Heelsの由来の限定と正例を事前に登録して回帰する。
   全文/文脈を保持したQA単位の意味監査・日英主Development・未使用Calibrationを少数人工例で代用しない。

この方法でも意味採用に至らない場合は、結果を保持して原因と残る実装/研究上の選択肢を整理する。
基準を緩めて最終Gateへ進めず、統計実装など依存しない工程も進める。Phase 12は開始しない。

## 19:10 JST 実装・事前契約の検証

`evaluation/claimwise.py`と共通Runner/品質検証/費用へ任意の`verification_mode: claimwise-v1`を追加した。
旧Configは`joint`のまま。各単位のRaw Taskを別保存し、元ID・全分母・Score・費用をRawから再構成する。
1単位の失敗で試行のFはnull、未試行単位も明示する。完了済みの単位は再呼出しせず、結果不明は再試行しない。
集計直前の中断は保存済みの子結果だけから復元し、その後に必要な未試行条件だけを実行する。
Server Reportより先にLogだけが残る中断でも、既存Log/Reportの最大連番から新Session番号を選び、旧Logを上書きしない。

新入力配置は、非信頼の固定初回回答→根拠配列→質問→Target Claim。
代名詞用の回答を先に置き、その後に根拠を読ませる。Target以外の回答文を証拠として扱わない。
この候補は呼出し単位と入力配置を一緒に変更するため、改善しても単位分離だけの因果効果とは言わない。
各QA/試行の中で操作するものは根拠配列の順序だけで、他の内容/配置は固定する。

入力は`phase11_semantic_diagnostics_claimwise_v2.json`、Configは`phase11_semantic_candidate_v4.yaml`、
日英Promptは`phase11_semantic_prompts_{en,ja}_v4.yaml`。旧Expected/曖昧単位/採用・停止基準は同じ、最大70 Completion。
Completion0のPreflightも全70の単位入力を実Tokenizerで測るよう共通入口を拡張した。
実GPUの新方式の意味診断はこれから。Test成功で意味妥当性を認定しない。
新規9 Testを含む全468 Test（ホスト6.43秒）/Ruff成功。共通の旧共同評価も回帰した。

## 固定4196aa5での実走結果

同じ8Bの全70 PayloadをCompletion0で測り、最大入力3322 Token・全層CUDA Offload・予算内を確認した。
GPU全体7082/8151 MiBは一点観測。事前確認Report Hashを保存後に、既知全8文を元/逆で実評価した。
16 Completion・4集計、入力49690/出力11432 Token、Task秒和183.19秒。
Criticalは2/4一致で不通過。Zidaneは両方で矛盾、Council c4は両方で誤支持のままで、人工54条件は未試行。
全16 Raw子Taskの元ID/全分母/費用と4集計を別照合し、再開27 File不変・追加呼出し/Server起動0を確認した。
結果は`phase11_claimwise_result_v4.json`。新方式も採用済みとせず、旧失敗と共に保持する。

並行して[QA内増分・Group Bootstrapの統計方法](phase11_statistical_plan.md)を結果を見る前の方法として実装した。
主Development/未使用Calibrationへは未適用で、主Model/条件/件数は未凍結である。
次の意味候補は[草稿を見ない根拠読解の先行](phase11_source_reading_candidate.md)として、別の事前計画へ分けた。
