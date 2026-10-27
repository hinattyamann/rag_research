# v26 Native0 メタデータ参照先修復 v1

2026-10-27 JST。今回の `phase11-v3-v26-smoke` に限定した、未開始登録の明示的な追加Protocol/入口である。旧Guard/Core94を編集せず、同じRun ID/condition fingerprintのまま、追加された完了証拠JSON2件のbinding.pathだけをignored locationへ移す。候補、Prompt、Model、Runtime、Sampler、Source、全targets/counts、予算、argv、output、固定HEADは変更しない。新しいRunの登録、Native実行、一般的なresume機能を提供しない。

Rootのexecute Handle64774は既存 `_fixed_checkout` が4untrackedを検出して終了した。v3 executeは `validate_plan → _fixed_checkout → monitor作成 → state=running` の順なので、今回の実登録行は7fieldだけのregisteredで、開始時刻/PID/snapshot/monitor/outputがまだない。この正確な条件だけを認める。既存登録Planや失敗記録を黙って変更・削除せず、新versionの修復履歴を残す。元失敗の全実行wallは未測定nullを保つ。

## 成果物と操作境界

- `phase11_zero_output_metadata_repair_v1.py`：正式 `scripts/` へ同byteでコピー可能。nearest pyprojectから実Guardと資産metadataを参照する。外部draft helper依存はない。
- `phase11_zero_output_metadata_repair_v1.json`：正式 `configs/` へ同byteでコピー可能。今回の旧Plan、登録row、共有台帳全Byte、固定HEAD61f56ad、候補d809、4file SHA、旧Guard SourceSHA、修復scriptSHA、失敗の正式Manifest+20artifactを固定する。
- `test_zero_output_metadata_repair_v1.py`：正式 `tests/` へ同byteでコピー可能。隣接draft sourceまたはPROJECT/scripts sourceを選ぶ。テストは架空metadataだけの/tmp小Git worktreeを作り、実v3 Guardを変更せず検証する。
- `read_only_guard_verification.py`：実v26WT/元Plan/登録状態の読み取り専用監査。実全identity/全bindingを既存 `validate_plan` で再検証した。適用入口ではなく、共有OSlock取得・WT移設・新Plan保存・台帳変更を行わない。

現段階ではRootの実WT/台帳を変更していない。実修復はRootだけが独立レビュー・正式化・検証・Commit/Push後に行う。生成済みJSONは追加Protocolであり、修復後のRun Planはまだ保存していない。

## commit が強制する順序

1. 実scriptと追加ProtocolのHashを固定し、同じcanonical v3 `run_lock` の非blocking OSlockを取る。Native実行context内からの修復、残存ledger.json.tmp、他のrunning行を拒否する。
2. 指定された共有台帳全Byte、registered7field行、旧Planの実Byte/contentHash、元runID/condition/candidate/fixedHEADを照合する。全monitor/output/native_guard/WT-local ledgerは存在もdangling symlinkも拒否し、Native予約・task journalが0であることを確認する。
3. Git汚れは指定JSON2とsidecar2の `??` だけを認める。tracked差分や余計なuntrackedは拒否する。WTとcanonicalの4fileの実Byte/Hashが一致し、移設先・新Plan・修復journalが新鮮かつignoredであることを検証する。各pathと親にsymlinkを認めない。
4. 既存の実 `validate_plan` を元Planに対して完全実行する。Planをdeep copyし、JSON2件のbinding.pathだけを置換する。並び、SHA、全他fieldを保持し、逆変換による全体一致と同じcondition fingerprintを照合する。
5. Run monitorとは別のcanonical ignored journalへ、immutable intent、旧台帳全Byte、旧row、旧Plan全Byte、追加Protocol/script、全失敗証拠、旧4file、新Plan予定Byte、台帳更新予定Byteをexclusive作成/fsyncする。この保存が終わるまでWT/台帳へ変更を加えない。
6. 4fileを `os.link` のexclusive作成→旧WT pathのunlinkで移設する。既存targetを上書きしない。canonical原本とjournalの旧Byteを保つ。新Planは別のfresh ignored pathへexclusive作成する。
7. 新Planで既存 `validate_plan` を完全実行し、既存 `_fixed_checkout` で同じ固定HEADとcleanを確認する。期限1800秒以内、元台帳Byte不変、monitor/outputなしを再確認する。
8. 同じ登録行のplan/plan_sha/content_shaと明示的 `zero_output_metadata_amendments` だけをatomic更新する。state/登録時刻/runID/condition、全他row、legacy909/unknown3、累積totalsは一切変更しない。読み戻し一致後にimmutable committed receiptを作る。Native実行は一切しない。

`inspect` は上記の適用前検査をOSlock内で行い、変更予定Hashだけを返す。移設、新Plan保存、journal作成、台帳変更をしない。

## Rootでの正式CLI

```bash
uv run --frozen --offline python scripts/phase11_zero_output_metadata_repair_v1.py inspect \
  --root '<既存phase11-v26-61f56ad WT絶対path>' \
  --extension-protocol configs/phase11_zero_output_metadata_repair_v1.json \
  --extension-protocol-sha256 22e5c3b17e4e6adc62a0d7baf740f43b29420a6a6204278f8c84f552c1002c6c
```

独立レビューとinspect成功を確認したRootだけが、同じ全引数でactionを `commit` にする。修復ログは新しい別ファイルに保存する。その後もNative開始前に新Plan/明示amendment/全移設Byte/clean/共有台帳と新journalを照合し、既存v3 executeを同runIDへ適用する。失敗を隠すための旧Plan上書き・同fingerprint再登録・旧ログ上書きは禁止する。

## 中断と限界

一般的な自動resume/rollbackは提供しない。既存またはpartial journal、ledger.tmp、想定外stateがあれば再実行を拒否する。intentには変更前と変更予定後の台帳/row/Plan Hashがあり、中断位置を読み取り専用で特定できる。移設途中の停止では、旧台帳はregisteredのまま旧bindingが見付からず実Guardが停止する。台帳更新後receipt保存前の停止でも、明示amendmentとintent/予定台帳の一致から状態を監査できる。どちらも元資料を消さず、Rootが新たにレビューした別versionで扱う。同条件を成功するまで繰り返す入口ではない。

13:18 JST追記: 正式Root Source/config/testsは封印草案と同byte。新46件を含む全1065 Test（34.49秒）/Ruff、正式入口の実inspect成功を確認した。適用はまだ未了であり、Nativeの実Health/意味採用とは扱わない。

## 検証結果

46 tests passed / 3.79s、Ruff成功。実v3 Guard、実Git HEAD/status/check-ignore、実OSlock、実atomic ledger writerを用いた小Git WT fixtureで、正常inspect/commit、全他row/totals/旧Plan保存、4fileのByte移設、同fingerprint、実clean成功、Native0、foreign/tracked差分、全非registered状態、PID/snapshot、output/monitor/native_guard、各SHA/Plan/予算/argv/targets/HEAD相違、既存先/dangling symlink/親symlink、同時lock、意図的な途中停止と再実行拒否を検証した。

実v26WTの読み取り専用検証は6.010745秒で成功。元Planの実全Model/Runtime/Prompt/Sampler/Schema/Core/全bindingsのv3検証、8回の必要なGit読取、Core94/元Plan/台帳Byte不変、Native/Server/tokenizer/socket/予約QA0を確認した。修復後の実newPlanは適用時に初めて存在するため、その実 `validate_plan` とclean成功はまだ主張していない。fixture成功や読み取り専用検証はNativeのHealth/意味、Known84、Main/Cal、Gate11の通過証拠ではない。CPU/電力費は未測定、外部API費0。Phase12を開始しない。
