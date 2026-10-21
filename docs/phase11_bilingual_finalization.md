# Phase 11 日英の最終固定Validator

2026年10月22日追加。旧英語用`finalize_phase11.py`は過去の検証経路として保持し、
拡張後のGate 11には`finalize_bilingual_phase11.py`を使用する。
本処理は新規推論やPhase 12の実行を開始しない。

## 確認する実証拠

1. 主Developmentの実証明書と日英の全採点を再検証する。既知15 QA回帰と前提となる日英意味診断の
   全Raw再照合、各20 QA/Group、意味基準、有効比較数、Native費用、全Layer CUDA記録も既存の証明処理を使う。
2. 専用Calibration解析を原本の同一Byteコピーで再実行する。両言語の全匿名品質・固定文Expectedを封印してから
   内部F/対応・保存済み解析・主証明書を読む。保存レポートの通過Flagだけでは採用しない。
   保存結果と再解析の比較から除くのは作成日時・解析所要時間・Checkpoint自身のDigestのみ。
3. Calibrationを許可したProtocolの主証拠と最終判断の主証拠が同じで、主/Calibrationの日英共通条件Hashが一致することを確認する。
   実主証明書または実Calibration解析が未完了/不通過なら、この経路を通過できない。
4. 実主に使用したAssets、Source選定Manifest、比較文書、両言語のCorpus/QA/Parent Map/固定資料をHashで確認する。
   Index Manifestだけでなく全Index PayloadとEmbedding Modelの実ファイルも検証し、CUDA Sessionは起動しない。
5. Validator自身の全Test/Ruff・実未達拒否の検証Manifestと、現行Source/検証ArtifactのHash一致を確認する。
6. 本実験の両言語N、採否と無関係な規模理由、資源枠、採点/比較の限界、停止・欠測・統計を確認する。
   既定の英語200問案を日英件数へ自動転用しない。Thresholdや統計を結果に応じて変更する経路は設けない。

通過側の自動テストでは主/Calibration証明・Assets検証の代替を明示して使う。
これを実データの成功、実主証明書やCalibrationの成功側の実証と扱わない。
実ファイルで判明したEmbeddingのRevision別ディレクトリ参照を修正し、初回の失敗記録と初回699件のTestログも保持した。
修正後の追加27件では、検証資料自体のSource/Artifact変更も拒否する。

## Evaluation本文を読まない対象選定

英語は固定Split ManifestのEvaluation IDからSource-answeredを選ぶ。
日本語は固定した838 Source IDのGroup Metadataと元の分割仕様から同じGroup割当を再現し、
Evaluationの209 Source IDを導く。質問・Reference・評価結果・Gold被覆は開かない。
元MetadataのパスとHashは実装へ固定しており、判断ファイルのHashだけを書き換えて差し替えることも拒否する。

選定は`digest(["phase11-bilingual-evaluation-id-selection-v1",42,language,record_id])`の昇順で各言語N問。
異なるDatasetのQA間に対応を仮定しない。最終対象はSource-answeredのIDから選び、文書の利用可能性や生成成功で補充しない。
文書Groupを独立標本としたBootstrapは事前統計計画に従う。最終標本が必ずN個の異なるGroupになるとは主張しない。
既知の主/Calibration IDとの重複や、`data/runs/bilingual_evaluation`に実行証拠がある場合は凍結を拒否する。

## 規模と費用

判断ファイルに最終Nと資源の計画枠（Native Calls、合計Native Step秒、品質/文採点秒）、
1以上のSafety Factorを明示する。各言語の実主20+Calibration20の費用から
`N * factor / 40 * 合計実測値`を計算し、Callsは切上げる。計画枠を超える場合は凍結できない。
Calibrationの完全比較率から期待有効数も保存する。

これは入力長・文数の違う本実験の最大費用や所要時間の保証ではない。
各QAの全文・全固定文を保持し、計画枠または未知結果/失敗で停止しても失敗・未試行を全件の分母に残す。
Native Step秒はGPU Kernel専用時間やEnd-to-end時間ではなく、検索/起動/人手時間とも区別する。
CI幅や検出力の保証も行わず、Group依存と比較可能例への条件付き推定の限界を規模理由へ記す。

## 操作と保存

`configs/phase11_bilingual_freeze_decisions_v1.json`は未決の雛形であり、N/資源枠/実証拠はnull。
日英の実主・Calibration採用後、根拠を確認して別Versionの判断ファイルを作る。
実験結果がない状態でstatusだけを変更しても採用されない。

```sh
uv run python scripts/finalize_bilingual_phase11.py review \
  --decisions configs/phase11_bilingual_freeze_decisions_v1.json
# 実証拠と最終件数を確定した新判断Versionだけに対して実行する:
uv run python scripts/finalize_bilingual_phase11.py freeze \
  --decisions configs/phase11_bilingual_freeze_decisions_vN.json \
  --output data/manifests/phase11_bilingual_final_freeze_vN.json
```

`review`は未達理由・検査状況を返す。未達時はconditions=null、Gate 11/Phase 12許可はfalse。
`freeze`は全検証を再実行する。呼出し側から通過Flagを渡す方式ではなく、未達なら最終Manifestを作らない。
既存の最終Manifestは上書きしない。確認中のSource・判断・採点/Raw/外部証拠・Index Payloadの変更も末尾で拒否する。

成功時だけSchema 2の最終Manifestへ、両言語の全対象ID、実主の全設定、Assets、統計/停止/品質方針、
実証拠/Index/Source Hashと計画値を保存する。主設定の用途・IDはDevelopmentの来歴として保持し、
本実験対象は別フィールドの`evaluation_record_ids`に明示する。Phase 12 Runnerの実装や実走をこの処理で前倒ししない。

## 現在地

固定8ea37e1で旧15 QA回帰v3を実行中（session93865）。まだ結果の採用は確定していない。
実日英主20 QA、実主証明書、実Calibration Protocol/40 QA/採点/解析は未了。
最終N/条件と最終Manifestは未凍結で、Gate 11は未通過、Phase 12は未開始。

検証: 新規27件を含む全701 Test（ホスト25.15秒）/Ruff成功。実雛形のreview/API freeze/CLI freezeは全て未達を返し、最終Manifest未生成。実Assetsの全30 Index/Embedding PayloadのHash一致、Evaluation母集団EN564/JA209のMetadata導出とQAファイルの前後Hash不変を確認した（2.73秒・新規推論/Server0・Evaluation QA解析0）。これらの証拠は`phase11_bilingual_finalization_validation_v1.json`へ保存する。
