# Phase 11 列挙項目・カテゴリーの完全支持を明確にする直接照合候補

2026年10月22日。固定8ea37e1の旧15 QA回帰v3を観測中に、完了済みのTom Bombadilのc5で
元順序に誤支持を確認した。逆順は事前Expectedどおり支持不足。
これは部分結果の診断であり、全回帰の最終Report/実費/採用を確定した記録ではない。
元のsession93865は中断・重複起動せず、事前の全Critical確認と停止規則を維持する。

## 観測した問題と保存

固定文は「radio and film versions」を例示する。使用原文にはラジオ版、Finnish miniseries、
ゲーム等の記載と、Jacksonの映画ではnot portrayedという記載がある。
元順序の理由はラジオと映像化の広いカテゴリーで映画の例まで支持した一方、逆順は映画の裏付け不足を保持した。
映画での言及を一切否定する文はなく、not portrayedをnot mentionedへ読み替えて矛盾にも変更しない。
旧Expected=not_supported、原回答/全5固定文/末尾の引用・角括弧、全使用文書を維持する。

同一Byteで保存した両順序の完了集計とc5 Native Task、元の全Case、AI診断と契約検証は
`data/runs/development_screening/phase11-known-v3-category-diagnosis-v1/`へ置く。
Fは元1.0・逆0.8で、閾値0.7の採用/書換え判断は両方採用のまま。
この既知1例を本研究の一般的反転率や独立した精度の推定に使わない。
確認者は同じ履歴のCodex AI、human_reviewed=false、厳密Model ID不明である。

## 次の開発候補v14

`phase11_semantic_candidate_v14.yaml`と日英Prompt v10を別に作った。
元のJudge指示の前に、次だけを共通して加える。

- 列挙されたAとBは各項目に肯定的な裏付けが必要で、Aや上位カテゴリーの支持ではBを補えない。
- 近い形式・役割・イベント・カテゴリーを、原文が同値と示さず置き換えない。意味が同じ言い換えは許す。
- 架空の展示品の木製道具/粘土の器から、石の器を追加して支持してはいけない例を示す。
  未言及は自動的な矛盾ではなく、矛盾がないことだけで完全支持にしない。

観測例の固有名・作品・映画/ラジオ等の媒体名・答え・Expected Labelを新Prefixへ埋め込まない。
Prefix以外の旧指示、Schema、抽出/書換え、Model/Runtime/量子化、24k Context、
推論4096/判定6144、Sampler/Seed、固定文方式、全29例/35文/58条件と元の全基準を変えない。
支持の取りこぼしが増える可能性もあり、改善は未実証である。
後続の旧15 QA/全42文/30条件・正例対照/曖昧5文/裸拒否8 QAの扱いも変えず、基準を緩めない。

主Development/予約Calibration/Evaluationの新規QAは開かず、既知例での方法調整として記録する。
同じ既知例を繰返し使う候補選択を独立した精度確認と扱わない。
候補の採用には、元の日英診断→全旧15 QA回帰→未使用主Developmentの実証拠が必要である。

## 事前登録と未実施の区別

Preregistration v6へ、追加最大70+84=154 Call・Retry0と変更理由を保存した。
稼働中の親Runの旧登録上限込み9B累積228に対し、新候補までの保守的上限は382。
旧RunのCall上限を延長せず、新候補の実行前に親の実完了Callsを別途照合する。
これはローカルでの別開発候補の資源枠で、主/Calibrationへの採用や実行許可ではない。

形式証拠は同じ固定人工Message、Model/Runtime/Context/予算/Native Core26+Probe1のものを明示再利用する。
新Promptは人工形式Messageに使われないため、追加の形式6 Callは実行しない。
新候補の全実入力で生成0のPreflightは改めて必要である。

親Runの終了・全Raw/費用/再開追加0と失敗/未試行の保存後だけ、新候補の固定Worktreeへ進む。
現在はConfig/Promptと同一条件・全旧Source25 Bindingの契約確認までで、
v14のGPU Preflight/意味診断/後続旧回帰は未実施。主Policy/Configは作らず、実主/Calも開始していない。
Gate 11未通過、Phase 12未実施。
