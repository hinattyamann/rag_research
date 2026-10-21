# Phase 11 9B直接照合v13の全診断と旧15 QA回帰v3

2026年10月22日。[v13の事前条件](phase11_qwen35_candidate.md)で固定した、
中間読解を除く方法を固定Commit `541d0d2`の専用Worktreeで実行した。
全診断に通過したが、主Development/未使用Calibrationの採用やGate 11の通過ではない。

## 全58条件の結果と監査

全29例/35固定文の2順序、全58条件/70 Callを完了した。
既知Critical4/4一致、人工英語24/24、日本語28/30・両言語の誤支持0で事前基準に通過した。
形式/Runtime/入力超過失敗0、未試行0、入力109350/出力198444 Token・Task秒和3220.362427秒（53.67分）。
Callsが少なくてもToken/時間が小さいとは限らず、別Model/推論予約の過去Runとの単純比較で優劣を断定しない。

92 Source Hashと全58集計/70子Taskの原入力・全文草稿/元根拠/ID/全分母・Native費用を照合した。
再開134 File不変・追加Call/Server0を確認し、原本136 Fileを同一Byteで正規保存した。
全Source/最終Label・理由/引用先を確認したAI監査1、生成0/準備5を含む全142 Artifactを
`data/manifests/phase11_direct_result_v13.json`へ結んだ。旧全Version/Expected/基準は不変。

日本語の2不一致は同じ「由来不明、一つの説だけが示される」1文書の断定Claimで、
Expected支持不足に対し両方矛盾となった。断定を明確な反証と同一視する残る誤りで、
Expectedを変えず28/30として記録する。同じSeed/実入力の2条件で、独立した2例ではない。
人工27例は全て1文書のため、人工54条件の順序対も独立した順序操作の証拠とは呼ばない。

Council c4は両順序でPope Pius Vの後の行為とCouncilの主体/時期/対比を区別し、
Zidaneは選手/監督・初期2季/後の3勝目と通算を区別した。その他の既知確定Labelは原資料の該当箇所と一致した。
曖昧c6は元S/逆NSでF6/7→5/7、閾値0.7で両採用。Expected null/全7分母を保持する。
反転はなく、既知一例から一般の順序感度を推定しない。

一部の理由は160文字で途中終了し、局所ID c1への言及、英日中の混在、青色をgreenと訳す箇所もあった。
原文/Claim/引用先は保持されており、Label一致を理由文の流暢さ/翻訳の独立した正確性認定には使わない。
監査はCodex AIでhuman_reviewed=false・厳密Model ID未取得・履歴共有。
既知例を反復した候補選定のため、通過率を独立した汎化精度として報告しない。

## 旧15 QA/全42文の回帰v3

全診断を保存/監査した後で、`phase11_known_trace_regression_v3.json`と
`phase11_known_trace_candidate_v3.yaml`を新生成前に用意した。
旧15 QA/全42文/30条件、全Expected・正負/曖昧分母・全基準と裸拒否8 QAの別保持は同じである。
変えるのは通過前提のReport/候補、直接方式による読解Call除去だけ。
Model/Runtime/Prompt/全予算/Sampler/Seedは通過v13と同じで、Study Version/Plan参照だけを変える。

明確な負例を持つ6 QA/12 Critical条件の全42 Callを先行し、全一致した場合だけ他9 QA/18条件へ進む。
全84 Call/Retry0、全体の確定Label/支持Label各90%以上、誤支持0と無失敗/全条件完了を要求する。
旧Source-readingの114から30読解Callを除くもので、QA/文/条件を減らさない。
事前Manifestは`phase11_known_trace_preregistration_v3.json`。既存9B実完了144込み累積最大228。

実Config/前提Report/計画Hash・Model/Runtime/Native Core・全旧Source/Expectedの照合を生成0で確認した。
次は新固定Checkoutで全84入力の資源確認をしてから実走する。回帰の通過はまだ確認していない。
全回帰の実Raw/採用基準が通る場合だけ、同じ主20問の新Policy/Configへ結ぶ。
主/未使用Calibration/最終N・条件・拡張Validator/凍結は未了で、Phase 12は開始しない。
