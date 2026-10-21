# Phase 11 日英Calibrationの準備・実行入口

2026年10月22日。対象の[別予約と未使用性](phase11_bilingual_calibration.md)を維持したまま、
主Developmentの証拠から専用Protocol/設定を作り、共通RAGで収集する入口を追加した。
現在、通過した実主証明書/実Calibration Protocolはなく、予約QAへの新推論は0。
匿名採点・意味/統計Adapter・最終証拠のCalibration対応は次工程であり、本書は実走完了の記録ではない。

## 事前条件と専用Protocol

`prepare_bilingual_calibration.py`は主の入力JSON・証明書、元の予約Manifest/Policy、
`phase11_bilingual_calibration_execution_rules_v1.json`を受け取る。
両言語の全匿名品質/文Expectedの封印と全主証拠を再検証してから私用証明書を開き、
原本/条件/実費/採点負担/Sourceの一致を調べる。通過Flagだけでは進めない。
保存済みの品質/内部結果を未封印状態でHashすることも避ける。

直前の全使用履歴から選定を再計算し、元の各20 ID/20 Groupが同じであることを要求する。
選び直して差し替えず、外部利用やSource/Groupの変化があれば止める。
元英語Calibration225問は検索調整済みのまま保ち、英語の予約は元Development、
日本語の予約は元Calibration、分析用途は両方Calibrationと記録する。
EvaluationはAssetsのHash確認だけを維持し、予約/Ruleの入力Pathを装ってQA本文を読むことを拒否する。

新しい`data/runs/bilingual_calibration_protocol/<name>/`へ未使用性の直前記録、
Checkpoint付き`protocol.json`と日英の設定を作る。主の全採用条件をコピーし、
変更するのは用途/Scope・予約ID/元Split・Calibrationの実行上限/Protocol Bindingだけである。
起動時も実主設定から照合するため、Protocol/設定のHashを更新しただけではModel/予算等を変えられない。
原資料/固定文/判断閾値0.7/裸拒否一回書換え/null Score・元の順序/反復/Seedを保つ。

事前Ruleは全20 QA、Task/Overflow失敗0・実使用Context、正確/支持Label各90%以上・
明確な非支持の誤支持0・完全比較10 QA以上、曖昧をF分母に保持、
全品質/文Expectedの封印後照合・品質不明の非補完を維持する。
20 Groupは実行/意味/費用の実現性確認であり、本実験N・検出力や有意差の保証ではない。
反転/改善の大きさを成功条件にせず、失敗を補充しない。

## 共通収集処理と資源・中断

`run_bilingual_calibration.py`からだけ専用Scopeを開き、既存の検索→初回→固定文→
順序/反復→一回書換えと同じ処理を使う。既存のDevelopment入口はCalibrationを拒否する。
全設定/Source Hash、元の対象/出力Run、主証拠と未使用性を各再開時にも照合し、
それが終わるまで予約QAを読まず、Modelを起動しない。

上限は主と同じ各言語1660 Native Call・新規5 QA/段階Session、Retry0。
直接方式とSource-reading方式の実Leafの場所から、欠けるCallだけを予約する。
予算不足はCall前に止め、全20対象と未試行を保持し、文を削って収めない。
Task失敗/不明結果も保存して停止し、再開でその試行を再生成しない。
公開出力は件数/状態だけで、回答・F・判断を表示しない。

Tokenは採用した各Taskの実入力検査/出力予約を保ち、1660 Callと最大予約から保守的な総予算を見積もる。
時間は採用した各CallのTimeoutを保ち、主の実Calls/Token/Step秒和を各20 QAの見積りへ保存する。
別QAの文数等で費用は変わり、総Wall-clock時間やGPU Kernel時間の保証にはしない。
起動/検索・採点時間は別である。総Wall-clock上限を実装したという主張はしない。
結果を見た後の上限/基準の緩和や条件調整には使わない。

Calibrationの収集はRootの共通Lockで直列化し、別Protocol間でも使用履歴照合と開始を重ねない。
再開用に利用履歴から除けるのは、同一Protocol/設定/対象のManifestを持つ元の日英2 Runだけ。
他のRunの開始前Journalや失敗は引き続き利用済みで、除外した元Runも新たな未使用QAとは呼ばない。
新しい出力先へ再開を装うことや、ManifestのないJournalを隠すことを拒否する。

## 検証と残る作業

新規20 Testを含む全653 Test/Ruffに成功した（最終15.61秒）。Protocolの通過側は完全な合成主証拠と
設定読込み/Model再生を明示的に置き換えた制御検証で、実主採用の証明ではない。
共通収集は直接/読解方式それぞれ合成20 QAで全8 Server Session・5 QAずつを完了し、
160/280個の合成Completion・再開追加0/公開情報/Reference漏洩なしを確認した。
実GPU/ModelによるCalibrationの推論ではない。

実データでは元の予約各20 ID/Group・全QA Hash/原Manifest Byte不変と現在の使用履歴を確認し、
未承認の専用設定は予約QA/Assetsを開く前・Server起動前に拒否した。新規実Model Call/Server0。
Native Core26+形式Probe1のHashは不変で、別Worktreeのv13実走を変更していない。
実主証明書→実Protocol発行→実収集の成功側と、Calibrationの全採点/解析・採用は依然として残る。

主実走を始める前にCalibrationの匿名品質/文Expected・意味/統計Adapterも対応し、
一連の処理を固定Checkoutで使えるようにする。主/Calの実結果を保存・採点・検証した後で、
最終N/条件・拡張Validator/凍結を進める。Gate 11/Phase 12は未達・未実施。
