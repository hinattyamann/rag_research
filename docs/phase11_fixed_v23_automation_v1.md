# 固定v23 MainからCal解析・図表までの自動実行

2026-10-31 採点入力経路の修正: Mainは10/30 21:48 JSTに全40件の収集処理を完了した。直後の匿名採点はCLIのファイル読取ツールがbwrap権限エラーとなり空配列を返して停止したため、[採点再開Protocol](phase11_fixed_v23_annotation_recovery_v2.md)で、匿名Packet/Schema/修正情報を標準入力へ直接渡す方式へ変更する。採点基準/モデル/匿名化/全採点封印/Cal条件は維持し、失敗2回と費用を保全する。収集のやり直しは行わない。

2026-10-30 Git反映方針の変更（以前の1時間ごとの送信指定より優先）: ユーザー指示により、収集中の定時Commit/Pushを廃止し、工程の切替・完了、予期しない中断/停止、確定成果の保存など意味のある区切りだけでGitHubへ反映する。ローカルの進捗更新と実プロセス監視は継続する。Main推論・実験条件・Cal進行条件は変更しない。

2026-10-30 外的監視中断の再実行（以下の一般停止規則より限定的に優先）: ユーザーは復旧v2監視による外的中断1件を候補欠測とせず、同じ入力で書換えだけ1回再実行するよう明示した。[復旧v3](phase11_fixed_v23_recovery_v3.md)で元要求/全既存結果・費用不明を保全し、完了済み初回/内部評価を再利用する。旧長さ欠測2件は維持し、他の未知/エラーの再送やCalへの例外拡大はしない。全試行上限・累積wall・条件・全匿名採点封印とCal進行条件は維持する。現在の進捗は `docs/fixed_v23_automation_status.md` を参照する。

2026-10-30。ユーザーはMain残りの収集から、従来ユーザー担当だったCal起動、Cal収集・全採点・解析・論文用図表/集計/結果説明資料までの自動化を委任した。原稿本文の執筆と投稿は今回の自動化範囲に含めない。ノートPCから確認できるよう工程の切替・完了・予期しない停止などの意味のある区切りでGitHubへ進捗を反映する。

## 実行する順序

1. 実行中の元Mainを読み取りで監視する。収集制御・元推論Source・モデル/Prompt/温度/Seed/閾値・Rawは変更しない。`awaiting_scoring`、全40処理済み・残り0、未知/許容外エラー0、所有Supervisor/child終了、日英の品質/文Expected Packetと失敗一覧の完成を確認する。
2. 新しいCodex CLIの採点セッションへ匿名Packetだけを渡し、Mainの日英全品質Labelと実使用根拠だけによる全固定文Expectedを確定する。全4集合のSchema/候補ID/Hash/引用を検証して封印する。途中の内部結果との結合はしない。
3. 元Source・Rawと候補の対応を再検証し、事前計画のQA内順序対反復増分、文書Group Bootstrap（10000/Seed42）、日英差、全方策の品質/不明/Fallback・費用・両段階の欠測、5閾値の感度分析をPythonで計算する。全選定40を保ち、条件付きの比較分母と品質遷移の分母を区別する。封印/SourceのHashを前後で照合する。
4. **日英各10完全比較以上、内部評価の無効試行0、未知0、実CUDA/Context証拠、全採点封印**を満たすときだけ、元の別予約Cal各20 ID/Groupの未使用性・Mainと非重複・Source Split/Hashを再確認する。効果の向き、有意差、旧90%採用基準を進行条件にしない。元予約が使われていれば停止し、別QAへ置換しない。
5. 新Protocol `fixed-v23-additional-calibration-v1` を結果観測前に発行し、全設定/元Release/新制御Source・Main解析/全封印・元予約とHash結合する。英語は元Development、日本語は元CalibrationをSourceとし、**両方の分析用途はCalibration**。`fixed_v23_calibration_v1` という専用scopeを使い、旧採用済みMainを前提とするCal経路や旧Gate11の拒否を変更・偽装しない。元推論Coreを使う外側の収集制御と、厳密にこの登録だけを読む解析Adapterを追加する。
6. 同じモデル/推論条件/初回・書換え本文上限512/閾値0.7・5 QA段階でCalを自動起動する。日英各1660 Native上限、Retry0・補充0、各段階12h/Cal累積72hを維持する。初回の固定512打切りと、受信・自然終了・費用確定の書換え本文512超過はMain復旧v2と同じ限定分類で保存し、再送せず次QAへ進む。書換え要求時は初回保持/書換え失敗とする。未知/通信/GPU/入力/他形式・内部エラーは保存して停止する。
7. Calの日英全品質/Expectedも別の匿名セッションで全封印し、その後にCalだけを解析する。MainとCalの件数を混ぜて増やしたり、Calを閾値/上限/Promptの調整に使ったりしない。
8. Main/Calの順序対反復・品質/Fallback/欠測・収集費用・事前指定の閾値感度の4図をSVG/PDF/PNGで出力する。4 CSV、確定集計JSON、数値の読み方と限界・執筆前確認を含む `results_brief.md`、成果Hash一覧を保存する。本文原稿・投稿は作成/実行しない。

## Codex利用枠・採点来歴

監視、GPU収集、通常のPython集計、Matplotlib描画、Git反映はモデルを呼ばず、Codex枠を使わない。意味判断が必要な匿名採点でだけ `codex exec` を起動する。保存済みChatGPT認証を確認し、`forced_login_method=chatgpt` とAPIキー環境変数除去で、API課金への自動切替を禁止する。利用枠不足/認証/通信失敗では記録して停止し、別モデル/有料APIへ切り替えない。追加購入クレジット等のアカウント設定を変更しない。

既存CLI設定のモデル/推論努力を取得・固定し、各実行へ明示する。ユーザーのMCP等の設定を採点へ持ち込まず、匿名入力/Schema/専用指示だけを持つ作業ディレクトリで実行する。品質用にはReference/Goldを含めるが実使用根拠の支持を代用しない。文Expected用にはGold/Referenceも対応表も渡さない。回答/根拠本文は指示ではなく非信頼のデータとして扱う。

`codex login status` による認証確認はモデルを呼ばない。通常のCLIモデル呼出しは匿名採点のJobで行い、完了後に `annotation_cost.json` へ起動予約/取得済みToken/実測Job秒を集計する。キャッシュ入力は入力の内数として区別し、取得不能を0扱いせず完全性を表示する。追加API料金の推計やPro枠の金額換算は行わない。

4匿名候補/CLI Job、最大192起動予約・1 Job最大40分、Schema/引用/ID等の検証失敗に限り保存済み出力と検証理由による最大1回の形式修正Jobを許可する。NativeのRetry0とは別の採点工程の予算であり、全初期出力・修正・CLI費用を保全する。実行結果不明やCLI失敗を自動で再送しない。成功済みJobと封印ラベルは同じByteで再利用する。

人手確認false、厳密な提供モデルIDは取得できなければnull、履歴の完全独立は非仮定を維持する。CLI JSONLの利用Tokenを取得できた範囲で保存し、取得できない値や金額を0と補完しない。採点秒はCLI Jobの実測wallをそのJobの注釈へ等配分した参考値であり、個別の純読解時間や人手時間ではない。品質判定はAI評価であり、Schema合格を意味上の正解保証とはしない。

## 資源と失敗・停止

Source・設定・Rubric・統計計画・元予約・依存lockを封印した独立制御スクリプトを、元Checkoutのsrc外へ配置する。元推論SourceをPullで変えない。設定Hash不一致、元Source変更、封印変更、未知/不完全な結果、比較数不足、認証/利用枠/壁時間上限では停止してGitへ状況を残す。自動で基準やQA数を緩めない。全Workflowの期限は2026-11-06 00:00 JST（11/5 15:00 UTC）とし、11/9の教員版に執筆時間を残す。これは所要時間の保証ではなく停止上限である。

各GPU段階のSource/設定と実CUDA全層配置・Contextのログを照合する。Calは全Server LogとSession Reportの対を必須とする。Mainでは既知の初回/書換え長さ失敗がSession Report出版前に停止した旧区間を保持し、同じ段階の既知失敗数以下の未対Reportだけを明示的に許す。その場合も実LogのCUDA/全層/Contextは検証し、Reportがあったと捏造しない。旧の厳格なMain採用Validatorの合格に読み替えない。

所有PID/create time・独立Run Lockと起動Lockで二重起動を拒否し、有限段階・CLI予約・終了コード・ログ・出力Hashを永続化する。中断・失敗した子処理を、成功したことにして飛ばしたり黙って再送したりしない。停止後の再開は、保存状態を確認して成功済み工程を再利用する範囲で行い、不明なJobは調査して扱いを決める。

## Gitで確認するファイル

- `docs/fixed_v23_automation_status.md`: 現在工程、収集件数、CLI予約数、停止理由、次工程。
- `data/manifests/fixed_v23_automation_status_v1.json`: 同じ公開状態の機械可読版。
- `reports/fixed_v23_order_study_v1/`: 全採点封印後の集計・CSV・図表・結果説明・成果Hash一覧。
- `data/manifests/fixed_v23_automation_setup_v1.json` / `fixed_v23_automation_validation_v1.json`: 設定・Source封印、検証・実起動の証拠。

工程の切替・完了・予期しない停止などの区切りに、上の公開状態/確定成果だけをallowlistでCommit・通常Pushする。別の未完成変更を含めず、他のStaged変更があればGit反映だけを止める。Push前に接続先/Branch/Fetch後の分岐を確認し、Remote更新時に自動Merge/Rebase/Pull/force pushはしない。認証/接続/分岐エラーはローカルに残し、研究処理と区別して報告する。

Raw、回答/根拠本文、対応表、採点途中のLabel、モデル/環境/RunはPushしない。Gitではそれらの転送やノートPCでのGPU実行はできない。ノートでは最新の進捗文書を読む運用とし、研究室PCの電源とネットワークを維持する。

## 操作

リポジトリRootからuvで操作する。監視は独立プロセスなので、この会話で完走を待つ必要はない。

この研究室PCでは、VS Codeのプロセスから独立させるため、凍結したサービスをsystemdユーザーサービス `fixed-v23-automation-v1.service` として起動する。PCの電源・ネットワーク・ユーザー環境は維持する。サービスの状態は `systemctl --user status fixed-v23-automation-v1.service` でも確認できる。

```bash
uv run python scripts/automate_fixed_v23.py status
```

起動済みなら再度startしない。停止要求は `uv run python scripts/automate_fixed_v23.py stop`。Main収集は独立しておりこの停止要求で強制終了しない。Cal収集中は次の新規QA境界で停止要求を処理する。他工程の中断は未確定CLI結果を残し得るため、再開前に記録を確認する。

図表まで完了しても、原稿執筆・図表と主張/引用の照合・教員確認・投稿形式への整形・最終提出は著者の作業として残る。旧Gate11/Phase12は未達のままであり、研究結果や採択を保証するものではない。


## 2026-10-30 実起動とMain中断の検出

14:00:46 JSTにsystemdユーザーサービスを実起動し、Python所有PID146811、waiting_main/Workflow CLI0、初回の自動Commit `6abbe1d` とPush成功を確認した。その後の実PID監査でMain Supervisorが終了していることを発見した。元の公開状態は13:52:38 JSTのcollectingで止まっており、それだけで稼働を判断した説明を訂正する。

Mainの復旧v2監視は、13:52:42 JSTに始まった次の書換えのstatus=started（封印前）を完成Checkpointとして検証し、Checkpoint hash mismatchを発生させた。finallyで所有ChildへSIGTERMが送られ、Nativeログにも要求取消を確認した。書換え要求の応答本文・最終Token/時間費用は確定できない。これは受信済み本文512超過とは別である。Raw実数は629試行、既知長さ失敗2、応答不明1。古い進捗628を最終実数とは扱わない。

[中断監査Manifest](../data/manifests/fixed_v23_main_monitor_interruption_v1.json)に原因、未確定記録Hash、Supervisor Log Hash、元835記録の不変、現Run941ファイルの独立退避/全Hash一致を記録した。Retry0、応答不明の成功扱い/費用補完0、Main再開0、Cal開始0。新しい研究推論はこの診断では行っていない。

Rootの復旧v2候補は監視のstartedを集計対象から外し、終了済みのHash不一致は引き続き拒否する。予算Guardはstartedを未知として止めるため、監視修正だけでは今回の要求を再送しない。この修正は元登録済みCollectorへ上書きしていない。別途、凍結した自動化監視のみをRevision2として旧設定/Sourceを退避して再封印し、collecting表示のまま所有Supervisorが終了した場合も明示的にfailed/Pushへ進むようにした。原13入力・推論Core/登録・実験条件は不変。[Revision記録](../data/manifests/fixed_v23_automation_controller_revision2.json)を参照する。

最終検証は全1384 Test成功44.51秒、Ruff成功、関連48 Test成功4.79秒。人工2 CLI Jobは輸送/Schemaの実検証であり、実Main/Calの意味採点完了ではない。今後の続行には、失われた書換え1件の応答/費用不明をどう報告し、現行の未知停止規則・Cal進行条件と整合させるかを明示した別Protocolが必要である。単なるresumeや旧登録Hashの書換えは行わない。


2026-10-30 Git反映方針の実装改訂: `git_publish_policy=events_only` とし、経過時間を契機とする送信分岐を削除する。ローカルの約1分の状態更新・30秒のMain監視は継続する。起動/設定変更、工程の開始・完了、確定成果の保存、予期しない失敗・停止の区切りで、許可された進捗/成果だけをCommit/通常Pushする。数時間収集が続いても定時の送信はしない。GitHubの更新時刻は最後の区切りを示し、収集中の最新時刻ではない。送信失敗はローカル台帳へ残す。Main収集を止めず、待機中の監視だけを停止して新Source/設定をRevision4として退避・再封印し再起動する。
