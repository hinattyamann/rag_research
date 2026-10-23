# Phase 11 Qwen3.5-9B Q6_Kの別候補v19

2026年10月23日11:54 JST。旧12k全回帰v7の不採用と全監査をd77e49cへCommit/通常Pushし、
リモート先端一致を確認した。同じPromptへの追記や採用基準の緩和は行わず、量子化を別候補へ分ける。

## 取得と条件

Unslothの同じ固定Revision `3885219b6810b007914f3a7950a8d1b469d598a5` からQ6_Kを取得した。
7458301152 Byte、SHA256 `91898433cf5ce0a8f45516a4cc3e9343b6e01d052d01f684309098c66a326c59`。
公開API/Pointerと全体Hashを照合し、旧Q4/Q5を保全した。取得session35864は終了Code0。
`phase11_auxiliary_qwen35_9b_q6_manifest_v1.json`へ別保存した。
公開来歴・License・資源試算の根拠は[Q6調査](phase11_q6_resource_feasibility_v1.md)を参照する。
変換元の正確なRevisionを独立検証済みとはせず、量子化精度の因果効果や精度向上を予告しない。

`configs/phase11_semantic_candidate_v19.yaml`はv18からStudy Version/Model Manifestだけを変えた。
日英Prompt v11、直接固定文判定v3 Schema、Context12288、Judge/書換え6144・推論4096、
Sampler/Seed、Runtime/全層CUDA、全文/固定文/引用ID、全対象/Expected/採用基準を保持する。
初回3B生成の条件も変更しない。

実LoaderとIdentityを確認し、意味70＋旧全回帰84の全154入力Messageが元Q5と同一だった。
全旧15 QA/42文/Source25/Expected/基準/裸拒否8とNative Core27は不変。
旧不採用93・親意味182・公開資源13・Main準備18 Artifactを再照合した。
全761 Test（29.18秒）、Ruff、実契約の確認に成功した。追加Model Call/Server0。
これは新Q6の実Tokenizer計測やGPU配置・形式/意味精度の確認ではない。

## 新しい事前登録と停止規則

`phase11_qwen35_9b_preregistration_v15.json`は、記録済み全9B試行634（Q4 317/Q5 317/Q6 0）から
新164 Call以下、累積上限798を保存した。内訳は新形式10＋全意味70＋通過時だけ旧全回帰84。
Retry0、旧未知1、旧回帰v7未使用42/v6未使用81/v5未使用42を保持し、埋合せや再配分はしない。

1. 条件・取得・検証をCommit/Pushし、新しい固定Commitの専用WTへModel/Runtime/Sourceを再現する。
2. 実意味入力を生成0で計測し、全文/予算の範囲内と全層CUDAを確認する。Q5のToken数や資源試算で代用しない。
3. Modelが変わるため、新しい実Native形式証拠を最大10人工Callで取得する。Q5形式をQ6の通過証拠にしない。
4. 同じ全58条件/70 Callの日英意味診断と全監査を行う。元のCritical完全一致・言語別精度0.9以上・誤支持0を保つ。
5. 全意味通過後だけ、同じ旧15 QA/42文・30条件/84 Callへ新前提を結ぶ。元/逆の12 Critical条件/42 Callが
   全一致した場合だけ残る正例9 QA/18条件を行い、全旧採用基準の通過を要求する。
6. 全旧基準通過後だけ新Main Policy/各20 QA・匿名採点/外部Expected封印/証明、予約Calへ進む。

資源/形式/意味/未知出力の失敗時は保存して停止し、同条件を再試行しない。
CPU fallback、Context/出力予算/全文の切捨て、都合のよいQA補充、Expected/基準緩和で採用しない。
5秒観測を実入力生成0・形式・意味の新Runへ添付し、取得欠測とNative失敗を分けて保存する。
単純なファイル差分試算や一回の配置成功を、連続Peak/長時間安定性へ読み替えない。

## 証拠と未了

登録検証は`phase11_qwen35_q6_candidate_validation_v1.json`、
取得Rawは`data/runs/model_screening/phase11-qwen35-9b-q6-v19`、
契約/Testは`data/runs/development_screening/phase11-q6-v19-registration-v1`に保存した。
モデル/Raw/環境はignoredで、Git Pushだけでは別PCへ転送されない。

新Q6の実GPU配置/形式/全意味/旧全回帰は未実施。Main/予約Cal/最終N/資源/条件/凍結も未了。
Gate 11未通過、Phase 12未実施、Goal継続中。
