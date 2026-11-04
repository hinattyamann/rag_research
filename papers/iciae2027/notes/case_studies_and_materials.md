# 論文の具体例と研究室PCから必要な資料

確認日: 2026年11月4日 JST。ノートPCの執筆BranchとGit履歴、登録済みの保存先を調査した。
実際の質問・根拠・回答・評価・品質を照合できた例だけを原稿へ用いる。
日本語版は英語版と同じ内容の翻訳とし、具体例の内容や数値も一致させる。

後続指示: ユーザーは必要な執筆資料をGitで共有し、ノートPC単独で参照できる状態を求めた。
現在の実行手順は [Git共有プロンプト](lab_pc_git_materials_prompt.md)を優先する。
元Run全体をGitへ入れず、選定済みQAに限定した必要な原文・確定結果・来歴を専用資料へ抽出・検証して共有する。

## 結論と所在

集計・図表・実験設定に基づく執筆はノートPCで進められる。
**最新の固定v23 Main/Calに対応する個別の結果例を確定するには、研究室PCから資料の書出し・転送が必要。**
ノートPCの登録済み配置にはMain/Calの個別Run・詳細解析・日本語の処理済みQAがない。
研究室PCの保存先は登録記録で確認したもので、今回リモートの現物を確認した意味ではない。

| 資料 | ノートPCで確認した状態 | 執筆上の用途 |
|---|---|---|
| 固定v23のCSV・Main/Cal公開集計・図表 | あり。reports/fixed_v23_order_study_v1/ | 主結果・品質・費用の集計 |
| 固定設定・事前選定ID・小さいManifest | あり。configs/、data/manifests/ | 方法、主要条件、来歴の説明 |
| 英語のDevelopment/Calibration QA | あり。Assets v2に記載された2ファイルのSHA-256一致 | 選定済みQAの質問/Reference/Gold構造の説明 |
| 日本語の使用版Development/Calibration QA | Assets v2の登録先にない | 日本語Datasetの具体的な質問・参照・来歴の確認に要転送 |
| 最新Main/Calの個別Run・全採点封印・匿名対応表 | 登録済みローカルRun配置にない | 質問→根拠→A/B→F/判断→品質の対応に要転送 |
| Main/Calのanalysis.private.json | ノートPCの自動化状態ディレクトリにない | 質問別の不一致、判断反転、改善見逃し/悪化、経路費用に要転送 |
| 採点CLI Jobのprovenance.json等 | 固定v23の状態ディレクトリがない | 実際の外部採点モデル・日時・来歴の詳細確認に要書出し |
| Phase 8/9等の古い個別Run | あり。旧order_sensitivity/answer_rewrite/pilot等 | 予備実験の説明例。最新Main/Calの結果には混ぜない |

公開集計は質問単位の統計行や個別回答・対応表を省略している。
公開値から特定質問のF、改善見逃し、原文引用を復元・推測しない。
確認根拠は [公開集計処理](../../../scripts/fixed_v23_automation/figures.py)、
[Assets v2](../../../configs/phase11_bilingual_assets_v2.json)、
[自動化準備記録](../../../data/manifests/fixed_v23_automation_setup_v1.json)。

## 実データの例を使う二つの目的

### Datasetや処理の流れを説明する例

実際の質問、Reference、Gold根拠と、通常検索で取得して実際に使った根拠の役割を説明する。
Reference/Goldは評価用であり、初回生成・内部評価・書換えへ正解として渡したと読める図にしない。
現時点で確認できる英語Main選定済みQAの一例は、record_id
clapnq:c508d78:train:1836182608890732134:answerable（Source TitleはNosebleed）。
元QA行はノートPCにあるが、このQAの最新v23生成回答・実使用根拠・判断はここでは未確認。
本文に使う場合は研究室Runと対応させ、Referenceを実際の生成回答や実使用根拠へ置き換えない。

### 主結果の意味を説明する例

最新Main/Calから、同じA/根拠に対して提示順序でFと判断が変わり、共通Bの選択・品質へどう対応したかを示す。
質問、実使用根拠のID/本文/順序、A、固定文、各TrialのF/判断、B、外部AIのY/理由/根拠を一つのQAへ結び付ける。
原稿には1～2例を短く載せ、例の全体中の位置付けと選定方法を記録する。
結果閲覧後の説明例選定であることを隠さず、全件の統計を説明例だけに置き換えない。
「順序で判断も品質も変わる例」「判断は変わるが品質は同じ例」は実データで確認できたものだけを使う。

## 履歴から確認できた古い実例

### Pradaの開発例

質問は what does prada mean in the devil wears prada。
旧Phase 8の保存Traceとreport.jsonで、固定2主張、全9試行F=1.0/acceptを確認した。
旧Phase 9の外部AI採点では、回答の数量主張を実使用根拠が十分に支持せず、Y=0と記録されている。
順序への安定性と意味上の妥当性を区別する説明には使えるが、**順序による判断反転の例ではない**。

原記録:

- Trace: data/runs/order_sensitivity/phase8-development-two-v5/453b8ed6a8fd228581e56c5c/trace.json
- Trial集計: 同Runのreport.json
- 品質: data/runs/answer_rewrite/phase9-development-two-v1/quality-v2/ai-review-20261019-v1/
- [Phase 8の記録](../../../docs/phase8_order_evaluation.md)
- [Phase 9のAI品質確認](../../../docs/phase9_ai_quality_review.md)
- [AI採点Manifest](../../../data/manifests/phase9_ai_quality_review_manifest.json)

上の品質記録のannotations/review_manifest/analysis.ai/review_reportの4ファイルは保存ManifestとSHA-256一致。
この所見は旧モデル・旧Promptによる使用済みDevelopment例で、完全な盲検や人手正解ではない。
固定v23 Main/Calの実例や統計対象として掲載しない。紙幅が限られる場合は最新Runの例を優先する。

### 原子説の開発例

旧Phase 8では初回回答が引用IDだけで固定主張0、F=null/採点不能となった。
旧Phase 9では文章へ書換えたが、外部AIの品質は判定不能で、改善済みとは扱われていない。
採点不能・Fallbackの説明に使えるが、最新Main/Calの成功・改善・順序効果の証拠にしない。
履歴は [Phase 9の記録](../../../docs/phase9_answer_rewrite.md) と上記AI品質確認を参照。

## 研究室PCの記録上の保存先

Repository Root:

/home/uchida/デスクトップ/code/rag_research

固定v23 Checkout:

/home/uchida/デスクトップ/code/rag_research/.tools/worktrees/fixed-v23-study-v1

そのCheckout内の対象:

- Main: data/runs/bilingual_development/fixed-v23-main-v1/
- Cal: data/runs/bilingual_calibration/fixed-v23-cal-v1/

Root側の自動化状態:

- .tools/fixed-v23-automation-v1/main/analysis.private.json
- .tools/fixed-v23-automation-v1/cal/analysis.private.json
- .tools/fixed-v23-automation-v1/config.json と登録された改訂設定・Job来歴

保存先が変わっていた場合は、元登録とHash・来歴で対応を確認する。同名の別Runを推測で採用しない。
英語Calの元QA SourceはDevelopment、日本語CalはCalibrationで、分析用途は両方Calである点を維持する。

## 必要な書出し内容

以下はこれから研究室PCで作成する書出し仕様であり、既存コマンド・完了成果として扱わない。
モデルや巨大Indexを転送せず、執筆用の読取専用資料をまとめる。

1. Main/Calの元analysis.private.jsonをByte不変で複製し、公開summaryのsource_analysis_sha256と照合する。
2. 両Runのall_annotations.seal.json、日英manifest.json、report.private.json、Cal protocol.json、固定Release等の来歴を保存する。
3. 日英quality/packet.json、mapping.private.json、annotations.json、units/packet.jsonとannotations.jsonを保存し、全封印と照合する。
4. 選定済み80 QAに限定した質問・Reference/Gold・文書Groupと、実使用根拠・A/B・固定文・各順序/反復ID・F/判断・Y・費用をQA単位で対応付ける。
   根拠のURL/Title/Passage ID、本文Hash、日本語の過去Page/Revision・引用来歴等も保持する。
5. 全件の判断反転、改善見逃し/悪化、各方策の品質/判定不能/欠測/費用を、分母と不明を保持して整理する。
6. 説明候補について、元baseline/record.json、internalのtrace.json・summary.json・rewrite.json、必要なTask/応答を添付し、原文・Label・対応を検証する。
7. 外部採点のRubric/指示/Schema版、実モデルIDの取得可否、Job日時・provenanceを保存する。未特定のモデルを推測しない。
8. 複製した全ファイルの相対パス・SHA-256・元パス・元Commit/Release・採点封印HashをManifestに記録し、元成果不変と新推論0/再採点0を報告する。

元Rawを上書きせず新しい書出し先へ保存する。今回ユーザーが指定した専用資料に限り、選定済みQAと必要な根拠等を
出典・利用条件・帰属表示とともにGit共有する。実際の掲載抜粋は出典・版・必要な表示を確認してから原稿へ反映する。
転送前後でManifest/Hashを照合する。未使用Evaluationや追加検証の未封印資料を混ぜない。

## 研究室PCの会話へ渡す依頼文

[Git共有プロンプト](lab_pc_git_materials_prompt.md)を使用する。
書出しだけで終えず、ノートPCで元Run/GPUなしに確認できる資料集・検証入口・Git反映と取得後の検証までを完了条件とする。
現時点でこの依頼は研究室PCへ送信・実行しておらず、資料も未共有である。
その間もノートPCでは、背景・関連研究・方法・既存集計に基づく結果の英日同内容原稿を進められる。
