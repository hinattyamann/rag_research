# Phase 11 日英の主比較・欠測・95%区間の事前計画

作成: 2026年10月21日。未使用Calibration/Evaluationの新結果を開かず、既存の質問内差/Title Bootstrap案を具体化する。
本実験の対象件数は未凍結。以下の方法を結果の反転率・有意差に合わせて変えない。

## 主比較と分母

QA iごとに、重複順序を除いた順序群の全判断ペアの不一致割合O_iと、同一順序反復群の全判断ペアの不一致割合R_iを計算する。
共用のoriginal試行は両群へ一度ずつ入り、両群の相関を保つ。同一順序群は元を含む5反復、順序群は元/逆/Shuffle3候補。
主なQA内増分D_i = O_i - R_i。QAごとの値を一つの観測とし、文・Call・判断ペアを独立標本にしない。
完全比較は全予定試行が有効な採用/書換え判断を持ち、両群に少なくとも1判断ペアがあるQAに限る。
本文1文書などで異なる順序が1種類しかない場合は主比較を作らない。部分的な有効ペアの差は探索値として別表示し、主値へ混ぜない。

言語別の点推定は完全比較QAのD_iの単純平均（QAを等重み）。日英差は平均D_ja−平均D_en。
日英QAを対応付けず、別Dataset・領域/課題・参照単位・入力長等の差を含む記述比較とし、言語単独の因果効果とはしない。
意味/形式/Runtime失敗・拒否・採点不能は主比較へ数値を補完せず、全選定QA/Group数と完全比較/欠測/理由を言語別に残す。
主推定の対象は比較可能なQAに条件付くため、比較可能率の差と選択の限界も併記する。
全選定QAの採用/書換え/Fallback・品質/不明・費用は別の全件集計で保持する。

## Group Bootstrapと区間

- 英語は既定NFC/casefold Title Group、日本語は参照先Identity閉包のdocument_group_idを使う。新しい都合のよい分割を作らない。
- 各言語で、完全比較QAを含む文書GroupをそのGroup数だけ復元抽出する。選ばれたGroup内の全完全比較QAを保ち、QA平均を再計算する。
  複数QAを持つGroupはその全QAを一緒に動かす。Group平均の等重みへ点推定をすり替えない。
- 10,000反復・Seed42。NumPy SeedSequence(42).spawn(2)をen/jaの順に割り当て、言語間で独立に復元抽出する。
- 同じ反復番号の平均D_ja−平均D_enを計算する。各言語と日英差の2.5/97.5 percentileを95%区間とする。
  QuantileはNumPyのlinear法。実装Version/NumPy Version・反復/Seed・対象/欠測数を保存する。
- 比較可能Groupが2未満なら区間はnull。点推定があっても不確実性を0と偽らない。2 Group以上でも少数Groupの不安定さは残る。
- QA/文書Groupの標本変動を対象とする区間で、Model/生成Seed/採点者を変えた変動や人手正解の精度を表すものではない。
  共通Corpus/Modelに由来するGroup間依存を完全に除いた保証もしない。

## 実装と検証

純粋な入力検証/集計Moduleを作り、基準どおりのQA内ペア分母・共用original・完全/部分/失敗・単一順序、
Groupを保った復元抽出/QA重み・独立言語・再現性・少数Group/null区間を人工データで検証する。
新規Runへ適用するCLI/Adapterは全匿名品質Label固定と実行Manifest/Rawの検証後に接続する。現時点では新規Calibration解析は行わない。
1言語200 Group/10,000反復なら復元抽出の主配列は約16MB、言語別の処理で数十MB程度を概算する。
規模/計算時間の最終決定は日英Development/Calibrationの実測と有効比較数の後、Evaluation本文を使わずに行う。

## 実装の検証範囲

`experiments/statistics.py`を追加し、人工データの新規6 Testを含む全474 Test（ホスト6.57秒）/Ruffに成功した。
実行定義の異なる根拠順序・5反復/共用originalと有効な判断/Scoreを検証し、QA内のペア分母と部分/構造的欠測を分ける。
Groupを一緒に動かすQA重みと、同じQA/Group名が日英にあっても独立に復元抽出すること、入力順に依存しない再現性を確認した。
比較可能Groupが2未満ならCI null。実Runへ適用する品質封印済みAdapter/CLIは未実装で、新規Calibration解析はしていない。

## 全Label封印済みDevelopment Runへの接続

`bilingual_statistics.py`と`scripts/analyze_bilingual_development.py`を追加した。
全入力Runの匿名Packet/候補/Labelを先に検証し、いずれかがpendingなら全言語の内部F/判断の検証へ進まない。
LabelのHashを保持し、封印後の変更を拒否する。全Label固定後に、Raw生成・読解/単位・集計/費用、Source/QA/実行Manifestと匿名対応を再照合する。
Quality Importも同じ純粋検証関数を再利用し、Label未固定の段階で内部を読む経路を前で止める。

元QAから既定の文書Groupを取得し、全選定IDを保持する。Baseline失敗は主増分null/欠測理由付きで残し、
成功した候補だけの品質/経路費用に加え、Baseline失敗/未知結果を含む全選定の初回生成費用を別に保持する。
品質不明は補完せず、初回/書換えのLabelと不明/品質遷移を保存する。判断の主比較は事前定義どおり内部判断の完全性で決め、Yの大小でQAを選ばない。
共有Model/Runtime・予算・閾値/試行/Fallback・Judge/読解Prompt/Schema・品質Rubricの異なるRunの混在を拒否する。
実験結果/品質Label・Source/RawのHashと事前計画Hashを付け、全選定数/完全比較/欠測と既定10000反復の出力を保存する。

入力は`[{"run":"data/runs/bilingual_development/...","bundle":".../quality","annotations":".../quality/annotations.json"}, ...]`。
現在のRunnerに合わせDevelopmentだけに限定し、Evaluationを拒否する。未使用Calibrationへの経路拡張は、その事前条件とRunnerの実装に合わせて別途検証する。
既存の旧Runは当時の固定Sourceで保持し、新Codeの検証を旧Source一致の代わりにしない。今回、新規QA/Calibrationの実解析は行っていない。

新規5 Testで両言語の封印前停止、全QA/失敗Group・結果不明費用、品質不明、条件混在/重複/Evaluation拒否を確認した。
全493 Test（ホスト6.65秒）/Ruff成功。テスト用の人工入力と既存品質経路を使い、新規QA結果や最終件数は使っていない。
