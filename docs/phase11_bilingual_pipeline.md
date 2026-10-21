# Phase 11 日英共通RAG接続の作業計画

開始: 2026年10月21日。旧Phase 6/Runを保持し、新しい候補設定で既存の質問専用Baseline、固定Trace、
文単位・順序/反復Judge、一回書換え、匿名品質採点の共通関数を再利用する。当初の作業計画に実施結果を追記する。

## 2026年10月21日 17:34 JSTの実装・検証

接続実装と全441 Test（5.36秒）・Ruffは成功した。実モデルでの接続確認はこれからで、意味妥当性は未認定。
候補Assetsは`configs/phase11_bilingual_assets_v1.json`。両言語のQA/Corpus/親対応/Index・E5/GPU uv条件と
共通CodeをHashへ結び付ける。EvaluationはファイルのHashだけを確認し、QA本文の読込みを拒否する。
旧Config/Runと旧Validatorの工程制約は保持し、共通Task制約だけを取り出して新Runnerへ適用した。

`run_bilingual_development.py`はDevelopment限定・既知例1〜2問の接続確認だけを許可する。
初回は既存の質問専用LangGraph/`baseline_once`、内部評価は`evaluate_traces`、書換えは`rewrite_once`を共用する。
元/使用本文・全Task Journal・Model/Runtime/QA/Code Hashを保存し、出力にはScore/判断/回答を表示しない。
本文切詰めは初回Packingでのみ記録し、Judgeでは全順序の本文/ID/Titleを固定する。
今回保存する検索順位は上位5件なので、親単位のSuccess/Recall/nDCG/MRRも@5だけを報告する。
取得不能な引用元の単位数と利用可能な親Gold数を分け、利用可能Gold0のQAも除外せずMetricをnullとする。
これは英語の元Passageと日本語の参照記事の関連性の違いを解消するものではない。

`bilingual_quality.py export/import`は既存の匿名化/品質基準/経路集計を利用する。
日本語のGold文書は検証済み引用位置と重なる子Passage、英語は元Gold親の全子Passage。
参照原文・人手要約・本文欠測・位置未一致はOffline来歴として明示し、生成/内部Judge/書換えには渡さない。
品質Labelを全件固定するまで内部対応を採点結果へ照合できない。採点者/モデルID可否/実際の分離は別途記録する。

新規9 Testは、Evaluation本文を開かないHash検証、親重複と欠測の分母、Gold漏洩なし、成功/失敗後の
再開追加0回・Server起動0、中断結果不明の保持、入力超過の無呼出し停止、匿名化/Label固定/改変検出、
旧Packet互換と同一候補の重複排除を確認した。実機でのToken/VRAM・意味支持・英語既知問題は別の検証が必要。

## 固定Commitで実行する接続確認

- 英語は既知Development例`clapnq:c508d78:train:-2421097959159398117:answerable`、
  日本語は既に開発予約した`whrja:02e85c8:answered:1`。未使用Calibrationとも主Pilotとも呼ばない。
- 設定は`phase11_bilingual_connection_{en,ja}_v1.yaml`。両言語共通の検索/Model/予算を使う。
  言語別初回/書換え指示と拒否文、固定文単位を対応させ、Judgeの英語指示・意味規則は同じとする。
- 事前上限は2 QA、各11 Completion以下、計22以下。決定的な文抽出はModelを呼ばない。
  重複順序は減らして保持し、実際のCalls・入力/出力Token・生成時間・ServerのGPU/RSSを保存する。
- 接続用Health確認は、固定Hash一致・CUDA全層Offload・Overflow/暗黙Truncationなし・全選定例と失敗の保存・
  匿名Packetの構成/来歴照合・再開追加0。失敗は保持し、別Versionで修正する。主Calibrationの採用Gateとは別物。
- Input OverflowはJournal保存後停止、Retry/QA補充なし。品質不明を成功に変えず、全Label前にF/判断を見ない。
- 固定Commitの専用Worktreeへ不変Data/Model/RuntimeをHardlink複製し、Run出力は独立にする。
  Symlinkで外のDataを参照しない。実行前にCommit・Config Hash・選定と上限をLaunch Manifestへ保存する。
- 規模拡大・英語既知誤支持/拒否診断・日英未使用CalibrationのHealth/意味採用基準はこの結果の後に別途事前登録する。

## 固定75d4787の日本語実走と英語Index互換修正

日本語の既知1問は`phase11-connection-ja-v1`で初回1/Judge9/書換え1を完了した。
実使用5文書、固定文2単位。初回入力3584/出力138、Judge各入力4790/出力698〜1456、
書換え入力4036/全出力1390・最終回答174 Token。GeneratorとAuxのTokenizerは異なる。
初回Packingは1文書を短縮したが、内部評価では全順序の同じ本文/ID/Titleを保持し、Input Overflow/暗黙Truncationは0。
両ServerはCUDA全層Offload、Combined RSSの標本最大は初回3484721152/Aux4133298176 Byte。
GPU全体使用量5143 MiBの一点観測もあるが、最大値の計測とは扱わない。
別の照合Scriptが入力Whitelist/実Token予算/本文不変/呼出し上限/原Journalを確認した。
再開で22ファイルのHash不変・追加呼出し0・Server起動0。匿名2候補を出力し、AI Labelを固定した。
同じCodex実装セッションの採点でhuman_reviewed=false、厳密なモデルID取得不可・履歴分離なしを記録し、
英語側の採点前なので内部F/判断/候補段階の照合はまだ行っていない。

英語v1はRetriever初期化で`KeyError: source_dataset`により停止し、Completion/Server起動とも0。
旧`CorpusStore`はCLAPNQの場合だけSource Fieldを省略するSchemaだが、新Factoryが明示Fieldを必須としたためだった。
初回失敗は`phase11-connection-en-v1/failure.json`と元Launch/Manifestで保持した。
既存と同じ`.get("source_dataset", "CLAPNQ")`へ修正し、日本語は明示Identityが一致する制約を維持した。
実BM25/Dense Indexを構築してFactoryから日英それぞれ検索する新規2 Testを追加した。
全443 Test/Ruff成功。Source/Corpus/Index自体、検索/生成/Judgeの条件・品質基準は変更していない。

新候補Assetsは`phase11_bilingual_assets_v2.json`、英語再実走は`phase11_bilingual_connection_en_v2.yaml`。
v1は元Commitの履歴として保持し、新Codeを同じAssets/Runへ混ぜない。
別固定Commit/Worktree/Runで同じ既知英語1問・最大11 Completionを行う。
正規配置のローカル保存は`data/runs/bilingual_development/`。実走原本は専用Worktreeに保持した。

1. Data/Corpus/親対応/Index・Model/専用uv Lock/関連CodeをHashへ結び付けるAssetsとFactoryを追加する。
   読込みはDevelopment/Calibrationを明示し、Phase 11でEvaluationを開く入口を用意しない。
2. モデル入力は質問文字列と実使用文書だけに限定する。Reference・親Gold・欠測・GroupはOfflineに保持する。
   同じ親の複数子は検索Metricで重複加算せず、Goldなし/欠測の状況を全選定QAの分母と分けて報告する。
3. 初期候補は両言語共通のE5/Subword BM25・RRF候補各50/定数60・上位5文書。
   初回は既存Qwen2.5-3B/温度0/出力512、Context4096・文書上限1024 Token。
   Judge/書換えは既存Qwen3-4Bと推論1536/全出力3072を使い、入力差に対応する候補Context12288を実機確認する。
   実Tokenizerで初回の使用本文・切詰めを保存し、その後は全順序で本文/ID/Titleを不変にする。
4. 初回/書換えの回答言語と拒否文、固定文単位だけを言語に対応させる。
   Judgeの意味比較規則・閾値0.7・9試行・書換え1回・再試行0を共通にし、予算超過は記録して止める。
5. まず少数Developmentで検索・実入力Token・起動/VRAMを確認し、両言語の全経路へ進む。
   GPUメモリは8GBで、起動・Prefix予算の確認前にModelが同時に収まるとは扱わない。
   1 QAにつき最大で初回1/Judge9/書換え1の11 Completion。少数接続確認は各言語1 QAから始め、
   主な20〜30問のDevelopmentと未使用Calibrationは対象・Health/停止規則を別途事前固定する。

成果物はAssets/候補Config/Prompt、接続Code/Test、実入力・出力・Runtime/Token・失敗と再開の記録。
小さい接続確認は1〜30分、RSS1〜4GB程度を仮見積りとし、実機で測り直す。
長時間実走は検証済みCommitの専用Checkoutで行う。匿名品質の全Labelを固定するまで新規内部F/判断/対応表を開かない。
意味上の正しさ・品質・英語既知問題の解消はTest成功やJSON形式と区別する。
両言語のDevelopment/意味監査・未使用Calibration・統計/条件固定/最終Validatorが残っており、Gate 11未通過・Phase 12未実施。
