# Cal拡張の出典資料出力の復旧 v2

2026-11-09 10:43 JST。ユーザーは追加収集の状況確認、停止原因の特定・改善・再開と、同種の停止の予防を依頼した。

## 確認した状態と原因

11/8 17:01 JSTにBatch 02の収集・全匿名採点封印・解析が完了した後、論文用資料の出力が `Missing selected passage provenance` で終了した。Batch 01は資料化とGit再取得検証まで完了。追加120問のうち80問（日英各40）の処理が完了し、Batch 03の40問は未着手だった。初回80件成功、書換え78件成功・日本語2件は固定した512 Token本文上限による既知欠測。未知Nativeによる停止ではない。

原因は英語QA `clapnq:c508d78:train:-8402235505568929376:answerable` のGold親Passage `830268006_10409-12873`。固定Corpusには512 Token以内の子Passage `21285419333013253506675306384_0-1820` と `21285419333013253506675306384_1820-2464` があり、元QAは親IDを保持している。旧資料出力はすべてのGold IDが検索用CorpusのIDと一致すると仮定していた。実験側の親子対応と匿名採点には問題がなく、資料出力だけのID解決不足だった。

## 修正と予防

- 固定CorpusとParent Mapの全体Hash、子本文Hash、親ID/親本文Hash、文字範囲の連続性、Title/出典の一致を検証し、元親の全文Hashと一致する場合だけ正確な連結で復元する。親IDと子IDを別々に残し、実使用Contextは元の子Passageのまま保持する。
- 資料には親子対応・全文・文字範囲・Hash・出典・変換内容を保存し、標準ライブラリの検証器も親子の全文再構成を再検証する。元Runや外部Corpus、認証、ネットワークを不要とする。
- 再開前に選定済み120問（日英各60）のGold IDをすべて点検した。英語60/日本語98種類のGold IDを解決でき、再構成が必要な親は上記1件だけだった。未選定Evaluation本文/正解は読み込まない。今後の実検索で得る根拠は固定Corpus自身の子IDであり、既存の本文Hash検査も維持する。
- 元の固定Helper/Config/Batch Protocolを変更せず、独立Helper `scripts/cal_extension_v2/` と `config-recovery-v2.json` を準備する。失敗した非推論の資料出力だけ再実行可能にし、成功済み工程は元Receiptを再利用する。モデル要求/採点を再送しない。
- 元の失敗Receipt/ログ/経過時間・失敗した派生資料を退避保全する。未知の障害を成功扱いにしたり、出典不足を空欄で通したりしない。
- Codeを再度開いた場合のGPU不足も扱えるよう、復旧版の通常終了要求を別Receiptへ保存する。既存の有限GPU待機/生成前だけの限定OOM復旧・イベント単位Git反映・全採点封印を引き継ぐ。

条件Fingerprint `c01efa41304147a6973f401a352b4cfaf8bc23c289e32fec680a6e57d3b4d5cd`、元推論Commit f0b7c71、120問の選定、モデル/Prompt/Token上限/閾値/予算/欠測規則/統計/採点は変更しない。親の復元はオフラインReference用資料の抽出であり、当時の検索Corpusやモデル入力への追加ではない。科学的な比較や評価方法の変更はない。

## 検証と残工程

関連18テストに成功。全体1425 passed・6 skipped/44.46秒、`uv run ... python -m ruff check .`に成功。Skipは専用Worktreeに元Raw/Group Fixtureがない既存6件。最初の制限環境では既存Socketテスト1件が権限不足になったため、同じ全体テストをホストで再実行して成功した。

実Batch 02の資料抽出と `verify_materials.py --audit-open` は40 QA/357 Trial/80候補/40採点Job/440方策枠・437実記録/510ファイルに成功。原文・採点・F・品質・費用・公表値を照合した。修復中の研究生成0/追加採点0、既存の研究/採点/工程等4293ファイルと元Main/Cal2785ファイルが不変だった。Batch 01の確定資料も再検証成功。根拠は[復旧前検証](../reports/cal_extension_v1/recovery_v2_validation.json)、[準備/全選定出典点検](../reports/cal_extension_v1/recovery_v2_preparation.json)。

この記録時点で再開準備と実資料検証が完了した。Commit/Push後に独立サービスを起動し、Batch 02のGit再取得検証を経てBatch 03の新規正常応答を確認する。実際の再開証拠は `reports/cal_extension_v1/recovery_v2_resume.json`、現在地は [自動実行状況](cal_extension_status.md)。残り40問→全採点封印→解析→Batch資料→追加120問の統合図表/全文資料→Git再取得検証を自動実行する。11/14の新規QA締切・11/17の資料化期限を維持し、研究室側でDOCXを編集しない。

ノートPCの取込元は `research/cal-extension-v1`。各Batchは `papers/iciae2027/materials/cal_extension_v1/batch_XX/` に保存し、同ディレクトリの `uv run --no-project python -I verify_materials.py --audit-open` で検証できる。全体の `verify_collection.py` は最終統合資料の完成後に使う。
