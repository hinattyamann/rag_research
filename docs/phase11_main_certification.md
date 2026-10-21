# Phase 11 主Developmentの証拠検証と保存

2026年10月22日。主Development各20 QAの実走後に使う入口を追加した。
実採用済みの候補や主Runはまだなく、現時点で実データの通過証明書は発行していない。
採用基準は[既存Policy](phase11_main_development.md)と[開始前Guard](phase11_main_adoption_audit.md)を保つ。

## 検証するもの

`scripts/certify_bilingual_main.py`はModelを起動せず、各言語のRun・匿名品質Packet/Label・固定文Packet/Labelを受け取る。
入力JSONは各言語1件、計2件の一覧で、Fieldは`run`、`quality_bundle`、`quality_annotations`、
`unit_bundle`、`unit_annotations`。全てRepository内のDevelopment Runに属する相対Pathを使う。

両言語の全品質Labelと全文単位のExpectedを封印した後だけ、内部Report/Manifest/Hashを調べる。
既知日英診断の全条件・原入力・子Task・費用・採用基準を再計算し、主開始前の完全な旧15 QA回帰も照合する。
通過Flagだけ、接続各1問、人工例だけ、部分実走を主採用の証明には使えない。

主Runでは事前選定の全20 QA/20 Group、旧Policy/採用済み候補/同一条件、全実行Healthと
意味基準・完全比較QA数を既存Validatorで確認する。匿名品質と内部Fを正解として同一視せず、
品質改善や反転の大きさ、有意差を成功条件にはしない。
全Native Leafを一度ずつ数え、初回生成と補助処理のCalls/Token合計が解析側と一致すること、
未知費用/中断/失敗がないこと、事前上限内であることも求める。

初回/内部の全SessionにServerログが対応し、実Context/Runtime/設定が一致し、
ログのCUDA配置と実際の全層数が保存Reportと一致することを調べる。
Step秒和は応答全体の遅延や独立したGPU Kernel時間とは呼ばない。
資源Sessionの原本と、採点秒数/実採点者表示/文単位Labelに記録されたModel IDの取得可否・履歴分離を保存する。
品質Labelの既存Schemaに厳密Model IDのFieldはなく、取得済みと推測しない。
人手確認false・履歴独立を仮定しないことを証明書へ明記する。

## 原本の保全と出力

既存のSource-reading再検証は派生集計を書き直すことがあるため、RunをLockし、
全Fileを同一Byteの隔離コピーへ複製してから再計算する。変更され得るRawをHardlinkしない。
終了時は原本/コピーの全Hash、外部Binding、入力JSON、検証Sourceの不変を確認する。
通常終了/例外/KeyboardInterruptでコピーとLockを解放し、原本を変更しない。

検証成功後だけ、新しい`data/runs/development_certification/`配下へ
`certificate.private.json`を保存する。全対象/条件・意味/統計・実費・採点負担・証拠File/Source Hashを含む。
これは主Developmentの証拠保存で、Calibrationの実行承認や最終凍結ではない。
`calibration_execution_allowed`、`gate11_passed`、`phase12_allowed`、規模固定は全てfalseを保持する。
Calibrationには別の事前Protocol/固定条件・対象/上限・実走・全Label封印・解析が必要である。

## 検証結果と限界

新規27 Testを含む全611 Test/Ruffに成功（最終回10.53秒）。CLIのHelpも確認した。
合成証拠の制御TestではModel再生/一部の上位Validatorを明示的に置き換えており、
その成功を実主Runや意味妥当性の通過に数えない。
既知診断の再計算では実際の判定集計/Checkpoint検証を使い、欠落・改変・偽通過・不明費用等を拒否した。
全採点前の内部Hash禁止、中断時の原本/Lock/コピー保全、実CUDA証拠の欠落/不一致も検査した。

実保存データでは不通過v12のReportを拒否し、全37 File不変/追加推論0を確認した。
日英の既知各1 QA接続の実Session計4件について、資源検査だけを追加推論0/原本不変で確認した。
最初の実Session照合で、合成Fixtureと実装が初回Contextを存在しない`runtime`から読んでいた不足を発見し、
実Schemaの`generation.context_tokens`へ修正した。Native Core26 Fileと形式Probe1 Fileの計27 Hashは不変。
合成Testの初回611件成功だけを根拠にせず、この修正後に全611件を再確認した。
実データでの証明書発行の成功側は、全意味採用と主Run/採点の完了後に確認する。

検証Manifestは`data/manifests/phase11_main_certification_validation_v1.json`。
全証拠がそろうまで主Development/Calibration・Gate 11を達成済みにしない。
