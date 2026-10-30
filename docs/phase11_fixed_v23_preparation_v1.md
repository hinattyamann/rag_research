# v23固定実験の準備と研究室PCでの操作

2026-10-30 更新: 今回の続きは[書換え本文上限にも対応する復旧v2](phase11_fixed_v23_recovery_v2.md)を優先する。新入口は `fixed-v23-recover-v2.sh`。初回失敗1と書換え失敗1を保全し、同種の本文超過では再送せず次QAへ進む。

2026-10-29 更新: 今回のMainは日本語初回回答の512 token打切りで停止した。[停止原因と新しい途中再開手順](phase11_fixed_v23_recovery_v1.md)を優先する。元の結果と実験条件を保全し、既知失敗1問を欠測として残す新入口 `fixed-v23-recover.sh resume` を準備済み。以下の旧 `resume` は既存失敗を拒否するため、今回のRunには使わない。

2026-10-28 JST。ユーザーは旧改善作業の停止を完了済みとし、引継ぎ文書の順序2以降を開始するよう指示した。停止作業は再実施しない。
方針の正本は [固定実験の引継ぎ](phase11_v23_fixed_experiment_handover_2026-10-28.md)、利用の区切りは [操作手順](phase11_v23_user_runbook_2026-10-28.md)による。

## 固定した範囲

- Protocol: `fixed-v23-order-study-v1`、[登録設定](../configs/fixed_v23_study_v1.json)。Mainは元の選定順の英20・日20 QA、別のCal各20 QAは保全する。
- 専用Checkout: `/home/uchida/デスクトップ/code/rag_research/.tools/worktrees/fixed-v23-study-v1`。
- 推論の基準Commit: `f0b7c71c4375a617c7142c67e3aa0610f73edb14`。元の全Python Sourceを保存し、既存ファイルの変更は収集制御の `bilingual_runner.py` のみ。新しい制御モジュール・入口を追加し、全Source/設定/WrapperのHashを `fixed-v23-release.json` へ固定した。最新mainの推論Coreは持ち込まない。
- 追加制御・設定・実機確認証拠を保存したCommitは `37ea029`。専用CheckoutのHEADは元Commitのままで、追加ファイルの実体は準備Manifest内の全Hashと照合できる。
- Judge/書換えは元のQwen3.5-9B Q6_K、Prompt en/ja v12、Graph OFF・CUDA0全層、Context12288・温度0.2・seed42・batch128・推論4096・出力予約6144。初回生成は既存の3B/専用初回Promptを維持する。
- 根拠全文/Title/ID・初回回答・固定文をQA内で保持する。元/逆/Shuffle3と元順序5反復、初回共用の原則9論理試行、共通書換え一つ、主閾値0.7、Retry0を維持する。9試行は9モデル呼出しではない。
- Knownの非支持14/16=87.5%という旧基準未達を承認した固定研究であり、旧採用基準・結果・Gate11は変更しない。旧意味70/Known84の再実行はしない。

従来のMain準備・採用入口は保持する。新scope `fixed_v23_main_v1` は元Sourceの固定Releaseを必須とし、最新mainから同じ設定を流用することも拒否する。旧v3自律改善台帳を新しい合格証拠として流用しない。新経路の実費は各RunのRawから記録する。

## 単独実行の確認と限界

先頭1 QAの確認・残りの続行で、設定/対象20件/Manifestを変えない。部分的な内部Trace一覧は元のPrefixだけを延長し、QAごとの入力Bindingを保つ。合成テストで先頭QAの保存Byte不変、続行・完了後の再開による追加Call0を確認した。

別OS SessionのSupervisorと子プロセスを起動し、stdinを切り、ログへ出力する。短い合成子プロセスで独立完了、二重起動拒否、終了コード保存、所有Groupだけの期限停止を検証した。子入口は生存中Supervisorと所有PID/起動Token/段階の一致を要求する。

日英合成検索各Top5、3B/9Bの全層GPU起動、既知の日英入力について初回生成・Judge・書換えの入力収容を、**回答生成0回**で確認した。最終証拠は [準備Manifest](../data/manifests/fixed_v23_preparation_v1.json)と[生成0証拠](../data/manifests/fixed_v23_preflight_v1.json)。これは実QA推論・長時間GPU安定性・全Main入力の収容・科学的採用の保証ではない。新しい回答/根拠の実入力予算は実行時にも既存処理が検査する。

最初の準備では元Commitに存在しないテンプレートの補助配置が必要だった。また生成0監査v1/v2は、日本語テンプレートが旧Assets v1を指していたため開始前に拒否した。両言語を元の事前選定と一致するAssets v2へ明示的に結び直した。失敗Reportと制御改訂前のSource/設定/Releaseは専用Checkoutの `data/runs/model_screening` へ保全した。いずれも生成0。起動前状態のみの旧初期化記録も同所へ保存し、実Runを再生成していない。

## 時間・停止の登録

元の1660 Call/言語という上限を維持し、新規QAの前に必要な残りCall全体を予約する。新規段階は原則5 QAずつ。固定文を削ったり、失敗QAを補充したりしない。

今回の有限Wall上限は、先頭QAの各段階4時間、通常の5 QA段階12時間、Main全体の累積72時間。停止/再開でも消費時間を持ち越す。これらは停止上限であり、所要時間の保証ではない。上限到達・失敗・未知で停止し、予算を自動拡張しない。

既知84 CallのTask秒6538.850041914964から平均77.84秒/Call。平均5固定文・9試行を仮定するとMain40 QAのJudgeだけで約38.9時間。初回/書換え/検索/起動/採点・執筆は追加である。最初のQA後に観測Call/Token/Task秒から再見積りする。公開の残時間は途中処理を含む粗いTask時間の推定で、Wall保証や信頼区間ではない。

10/30 Main起動、11/2 Cal起動、11/5結果・図表、11/8教員版、11/9初稿、11/20投稿という目標を維持する。Main/Cal各40 QAでおおむね二日ずつの収集に加え採点が必要になり得るため、10/30起動後に着手が遅れれば余裕は小さい。実QAの文数・障害・採点量で遅れが見えた時点で原因と影響を報告する。背景・方法は収集中にも執筆する。

## 今、ユーザーが行う操作

通常の端末を開き、以下を実行する。このRunは起動前状態まで初期化済みで、`init` の再実行は不要。

```bash
cd '/home/uchida/デスクトップ/code/rag_research/.tools/worktrees/fixed-v23-study-v1'
./fixed-v23.sh pilot --run data/runs/bilingual_development/fixed-v23-main-v1
```

英語Mainの既存先頭1 QAについて初回生成、全順序/反復、共通書換えを収集する。別の追加QAではない。コマンドはSupervisor起動後に戻る。直後に次の状態確認を行い、`collecting` と `supervisor_alive: true` を確認する。

```bash
./fixed-v23.sh status --run data/runs/bilingual_development/fixed-v23-main-v1
```

その後は端末・Codexを閉じてよい。tmuxの切離し操作は不要。研究室PCの電源・OSセッション・ローカル環境・保存先を維持し、スリープや再起動、実行CheckoutへのPullは行わない。収集中にCodexのGoalを維持する必要はない。

`pilot_complete`、失敗/未知0、完了QA1/予定40を確認し、観測時間・費用を見てから同じRunを続行する。

```bash
./fixed-v23.sh continue --run data/runs/bilingual_development/fixed-v23-main-v1
```

`pilot_complete` は収集処理の完了であり、回答の正しさ・完全比較の成立を意味しない。拒否/固定文なしも保存され、後の解析で区別する。日英の全匿名品質/文Expectedを封印する前に、先頭QAだけ内部結果と照合しない。

続行後は事前登録した有限回の段階をプログラムが進め、Main日英全40 QAの収集・匿名Packet出力後に `awaiting_scoring` で終了する。正常な途中5 QA終了やexit0を全体完了と表示しない。公開状態は `status.public.json`、ログは `supervisor.log` / `session-*.log`、資源観測は `resources.jsonl`、所有プロセスと段階は `control.json` に保存する。

## 停止・再開と報告

```bash
./fixed-v23.sh stop --run data/runs/bilingual_development/fixed-v23-main-v1
```

停止要求は保存され、現在の処理を保存できる区切り/次の新規QA投入前で停止する。即時に全処理が終わるコマンドではない。状態が `stopped`、所有プロセス終了、失敗/未知0となった安全な停止だけ、次のコマンドで同じRunを再開できる。

```bash
./fixed-v23.sh resume --run data/runs/bilingual_development/fixed-v23-main-v1
```

既存の失敗・応答不明があれば再開を拒否する。`failed` / `interrupted` / 状態不明では起動を繰り返さず、公開状態と報告文をCodexへ渡す。Supervisor不在でも子が生きていれば再起動しない。停止・再開は成功済みNativeを再生成せず、未知を未実行へ変換しない。

採点待ち/失敗時の報告文は次に出力される。

```text
/home/uchida/デスクトップ/code/rag_research/.tools/worktrees/fixed-v23-study-v1/data/runs/bilingual_development/fixed-v23-main-v1/report_to_codex.txt
```

`awaiting_scoring` になったら、新しいCodexの会話へこのファイルの本文を貼る。品質Packetは `<Run>/en/quality/packet.json` と `ja/quality/packet.json`、実使用根拠だけの文Expected Packetはそれぞれ `quality/units/packet.json`。プログラムはこれらを生成するが採点やCodexの自動起動はしない。公開表示にF・判断・本文・Gold・候補対応を含めない。

Codexは両言語全品質/全文Expectedの封印後に内部結果と結合し、順序変更対反復、品質遷移、費用、欠測、Group単位の区間と既知限界を解析する。Calへの進行条件は実行Health・元対象/比較完全性・各言語10完全比較以上・採点封印・資源/期限の確認とし、効果の向きや有意差は条件にしない。旧90%基準への合格は要求せず、実際の意味誤りと分母は全て報告する。Cal用の新Protocol/実設定/コマンドは**Mainの採点・解析後**に作成し、ユーザーへ引き渡す。現時点でCal用の起動設定は未発行。Phase12は起動しない。

Git管理外の専用Checkout、モデル、Index、実Run、uv環境はPush/Pullでは転送されない。別PCではそのままこの絶対パスを使わず、元Commitと準備ManifestのHashを基準に再配置し、環境を別途再構築する。収集中のCheckoutは変更しない。
