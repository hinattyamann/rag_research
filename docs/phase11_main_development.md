# Phase 11 日英主Developmentの事前選定

2026年10月21日。現在の候補v8は固定Commitで意味診断中であり、主Development用に採用済みではない。
今回の成果は対象ID/選定規則の保存まで。新規対象への検索/生成/Judge/書換え/品質採点は行っていない。

## 選定規則と対象

各言語20 QA、各文書Groupから1問。20は予備検証20〜30問の下限で、全文読解/文ごとの多数Callを
伴う候補の費用と、異なるSource Groupの確認を両立するための開発規模である。
最終EvaluationのNや英語200問案を確定した件数ではない。

DevelopmentのSource-answered QAを母集団とする。本文欠測・引用位置不明・検索失敗・品質不明を
予測して選択から外さない。選定はIDのSHA256順位だけで行い、質問/Reference本文、Gold Coverage、
Model回答、品質Label、内部Fを順位や採否へ使わない。Seed42とMethod名/言語/IDから順位を決め、
既に選んだGroupの別QAは取らない。行順の変更で対象が変わらない。

- 英語: Development2824行のうちSource-answered1465。既知ID/Groupと旧文書露出を除いた候補1409 QA/1171 Groupから20問。
- 日本語: Development545 QA。初回Preview100問のGroup閉包で予約した142 QA（95 Group）と使用済みGroupを除いた403 QA/318 Groupから20問。
- 選定各20 Groupと使用済み/予約Groupの重複0。失敗を別のQAで補充しない。

全QAの構造/Hash確認は既存Assets v2で行う。最終EvaluationのQA行は読み込まず、既存AssetsのファイルHash照合だけを行う。
ID/Group/順位/母集団・候補数/除外来歴を
`data/manifests/phase11_main_development_selection_v1.json`へ保存した。
初回の選定Policy v1は旧ID欠測の処理を明示していなかったため選定前停止し、保持した。
実際の選定はPolicy v2を先に保存して行い、旧QA IDの欠測を隠さない。

## 使用済みの調査範囲と限界

Phase5/6、Pilot、Calibration、日英既知接続の`answers.jsonl`と`record.json`、計70入力をHash固定した。
成功だけでなく失敗/中断・Call前のJournalも除外する。内部F/品質/意味採点を開いて選別しない。
全62固有IDを保持し、Developmentで見つかる使用済みIDと同一文書Groupも除く。

初期Phase5の3つの手入力ログはQA IDがnullだった。旧質問とDevelopment質問を完全一致照合し、
3記録とも対応ID1件を確認した。IDを推測で発行せず、質問Hash/対応IDを記録する。
さらに、旧実使用/検索文書の英語TitleをNFC/casefoldで現行Groupへ対応し、保守的に候補から除外した。
これは新しい未知QAの評価結果の閲覧ではなく、既知の使用済み来歴の回収である。

「未使用」は、この明示的な保存Baseline履歴と日本語Preview予約に照らして、新しいModel回答を
まだ生成していないことを指す。全過去チャットやプロジェクト外の閲覧履歴まで未閲覧と証明するものではない。
選定後のUsage Inventory更新で、後から実行済みになった対象を未使用へ戻さない。

## 実行前に残る条件と見積り

現Runnerは既知1〜2問の接続専用で、今回の20問を実行できるようにはまだ変更していない。
拡大前に、次を別の実行Protocolへ固定する。

1. 新候補の日英意味診断と既知15 QA回帰の採用証拠。Model/Runtime/Prompt/予算/Seed/Coreの一致。
2. 全選定IDの保持、実Call/時間上限、Health/意味採用基準、最初の障害/予算到達時の停止と未試行の記録。
3. 初回生成・読解/固定文判定・一回書換えの全文保持/原子費用・中断/再開、初回失敗/裸拒否/品質不明の扱い。
4. 両言語の全匿名品質Labelを封印した後だけ内部F/対応を開く手順。AI実採点者/同一履歴の限界を保持する。
5. Source/Model等のHash差拒否、主20問を許可するGuard、旧接続設定/Calibration/Evaluationの境界と回帰Test。

9試行で読解を毎回生成し、固定文数をuとすると、概算は1 QAあたり`2 + 9(1+u)` Call。
日英40 QAでu=3/5/8なら1520/2240/3320 Callとなる。裸拒否・同一順序重複・失敗は別に記録する。
旧v6の128 Call/27.43分からの粗い換算は約5.5〜12時間。実入力長・出力・Runtime制約の差を保証せず、
検索/初回起動・外部80候補のAI採点/意味監査時間は追加である。実行上限は候補の診断/資源確認後、主結果を見る前に保存する。
20問の選定だけで、主Development完了や未使用Calibration・Gate 11通過にしない。
