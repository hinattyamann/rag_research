# Phase 11 全旧回帰の通過後だけ行うMain設定準備

2026年10月23日10:31 JSTの記録。旧全回帰v7は固定5f4a6b6/session64437で実行中。
今回の成果は設定準備CLIと拒否/引継ぎ検証であり、実Main設定や新Main Policyはまだ作成していない。

`scripts/prepare_bilingual_main.py`は、新たに生成する候補設定を既存Runnerへ渡せるようにする。
モデルの起動・検索・生成は行わない。実行Policy自体は別の事前入力であり、このCLIでは採用しない。
既存Policy v1は旧8B/source-reading向けのまま保存し、Q5/12k向けに読み替えない。

## 検査と出力

1. 最初に正規保存された旧全回帰Reportだけを確認する。直接判定の全30条件/84 Call・通過・
   費用既知・未試行0と、終了後監査/追加Call0の再開確認が必要。未達時はPolicy、Template、選定、
   未使用QA、Raw再検証を読む前に止まる。
2. 既存Lockを取得し、Raw全体を専用一時Directoryへコピーする。全15 QA/42文の採用Guardを
   コピー上で実行し、全原本/コピーのByteが変わらないことを確認する。
3. 別保存の`preregistered`な実行Policyと候補を確認する。Model、Context、Prompt、Sampler、
   Task予算等が採用済み旧回帰と一致し、元の精度/誤支持/封印基準を保持する必要がある。
4. 元選定Policyで使用済み来歴を再調査し、元20 ID/20 Group/行順/未使用状態との一致を確認する。
   差があれば別QAで補充せず停止する。EvaluationのQA行は読まない。
5. 既存の日英接続Templateの初回生成・検索・書換え・匿名採点条件を保持し、採用済み候補の
   条件と両言語のPromptへ置き換える。両言語とも既存Main Runnerの読込み/検証に通過してから、
   新しい`data/runs/bilingual_main_protocol/<version>/`へ`main-en.yaml`、`main-ja.yaml`、
   `preparation.json`を作る。片言語の検証失敗時は両方とも出力しない。既存Directoryは上書きしない。

Receiptは全入力Hash、原本Raw一覧Hash、両設定Hash、コピー上の検証、追加Call/Server0を保存する。
設定準備の成功はMain実験・意味採用・最終凍結の成功とは区別する。
実行中断による部分的な出版が生じた場合も、そのDirectoryを上書き再利用しない。

実使用時は次の8引数を指定する。今の未通過v7を採用するCommandとしては実行しない。

```text
--known-report <完全通過・終了後監査済みの正規Report>
--known-config <その旧回帰Config>
--policy <同じ候補・実費見積りを結んだ新Main Policy>
--selection-policy configs/phase11_main_development_selection_policy_v2.json
--assets configs/phase11_bilingual_assets_v2.json
--template-en configs/phase11_bilingual_connection_en_v2.yaml
--template-ja configs/phase11_bilingual_connection_ja_v1.yaml
--output-dir data/runs/bilingual_main_protocol/<新Version>
```

旧日本語TemplateのAssets v1参照は、Hash照合済みの明示的なAssets v2引数へ置き換える。
初回生成は3B/4096、補助Judge/一回書換えは実際に採用した条件を使う。
各言語1660 Call/新規5 QAの原子予約・失敗時停止は既存Runnerで再確認される。
Main実行時は初回生成と内部評価を別Process/段階に分け、E5検索とQ5の同時保持を避ける。
これはコード経路の確認であり、新規Main入力の実GPU資源確認は未実施である。

## 実際に確認した範囲

- 新規11件を含む全761 Testが27.55秒で成功し、`uv run ruff check .`と補助ScriptのRuffも成功した。
  原本保全、Raw拒否、未完了/不通過/費用不明/未監査、旧候補・基準緩和、片言語失敗、
  既存出力上書き・QA補充の拒否を確認した。
- 新しい設定生成の正例は一時Fixture/検証Doubleを使う。実採用が済んだという証拠ではない。
- 実行中v7の固定WTをROOTとする早期Gate Probeでは、ReportがないためPolicy等へ進む前に拒否した。
  終了済み4条件のAggregate/Leaf計20ファイルは前後不変。稼働中全Inventoryは固定していない。
  このProbeのROOT切替は早期拒否だけに使用し、Raw再検証やMain Loaderへは一度も入っていない。
- 実不通過v5の正規Reportでも拒否した。両ProbeともMain出力なし、未使用QA行の読込み/追加推論0。
- 実行中Nativeの95 SourceはRootと固定WTの両方で一致した。親意味182・新形式32・登録4・
  生成0 Preflight9 Artifactも再照合した。新CLI/新Testは現行Native Source Inventoryの外にあり、
  `src`、日英Prompt、実験設定、Expected、採用基準は変更していない。

補助Probeの初回はimport Path不足で停止し、修正後に再実行した。旧stderr/stdoutを別名で保持する。
Test Fixtureの配置誤りによる途中の1失敗/5設定エラーも修正し、最終全件成功と区別して記録する。
どちらもNative再実行はない。
全証拠を`phase11_main_preparation_validation_v1.json`へ結ぶ。
ignoredの検証生データはGit Pushの転送対象ではない。

## 次に取り組むべき内容

1. 同じsession64437を継続観測し、終了後だけ全Raw・独立Schema・理由/根拠・追加0再開・資源を監査する。
2. 全旧基準通過後にだけ、実費を反映した新Main Policyを別Versionへ事前保存し、このCLIで両設定を生成する。
   未通過なら失敗/未知/未試行と全旧基準を保持する。
3. 実Main各20 QAと匿名採点封印/証明、予約Cal、最終N/資源/条件/凍結を実施する。
   Gate 11は未通過、Phase 12は開始しない。
