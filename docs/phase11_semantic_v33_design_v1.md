# Phase11 v33 部分GPU配置候補の設計

記録時間: 2026-10-27 23:39 JST。status=design_not_preregistered。新Identity・固定Commit・実Runは未発行で、生成0/Native0。

v30/v31/v32の8B候補ではCouncilの誤支持が残ったため、意味判定の参考となったv28のQwen3.5-9B Q6_K・Prompt15・推論4096へ戻し、別のGPU配置を検証する。v28の返却47は確定45/45一致でも未知1/未試行42を含む失敗Runであり、全90採用や新候補の意味証拠に流用しない。v32不採用/未使用Rewrite2・全90・Known20は保存する。

- Modelは保存済み `unsloth/Qwen3.5-9B-GGUF`、revision `3885219b6810b007914f3a7950a8d1b469d598a5`、Q6_K、7,458,301,152B、GGUF SHA `91898433cf5ce0a8f45516a4cc3e9343b6e01d052d01f684309098c66a326c59`。旧実験を再生成しない。
- 科学的参照はv28。Prompt15・Context12288・出力6144・推論4096・batch/ubatch128・Sampler/Seed・GraphOFF b11433/明示FAoffを維持し、GPU要求を全層99から16へ変更する。batch32は採用しない。旧ログはprefill完了後の逐次decodeでtimeoutしており、batch縮小だけの改善根拠が弱い。
- 新 `cuda-execution-v3-partial` を別契約として追加し、Q6 manifest/Model path/Jinja・block32・実GPU16/33・full=false・CUDA0・FAoff/context一致を要求する。旧v1/v2の全層条件を変更しない。Mainのbaselineは既存全層条件を維持し、internalだけ明示v3契約を認める。曖昧な部分offloadやCPU-onlyを合格へ読み替えない。
- 現Coreのprefill修正と、新配置/証明のCore変更もIdentityへ含める。v28から全Identityが単一成分だけ変わるとは主張しない。新Core/Model/配置を含む形式・意味・回帰を新鮮に検証する。旧意味出力の再利用0。
- 部分化はGPU常駐量と一部計算を変えるが、CUDA演算は残る。watchdogの原因・修復は未確定で、未知/異常なら停止・保全し、同条件再送をしない。Host RAM増加を生成0とSmokeの監視で必ず実測する。

各Runは正式な新候補Protocol・入力Hash・実行入口・共有累積台帳・Guardへ結合してから出力を生成する。予定段階はTokenizer0→全90入力0→人工形式10→日英NS2→Council元逆C2→日英Rewrite2→全90意味→新鮮Known21元15QA/42文/30条件/84Call。前段合格時だけ後段へ進み、未使用Known20は旧v32予約として残す。新候補の開発予定は最大190 Native Call（10＋2＋2＋2＋90＋84）で、全体Goalの上限ではない。段階ごとの有限Token/時間/個別1200秒timeout・監視5秒・停止/再開方法は、実設定・実測とともに正式事前登録へ記す。

旧47返却のHTTP2567.091079/47=54.618959秒は9B全層時の参考値。90 Callの参考4915.706321秒、係数2なら9831.412643秒で、部分GPUの速度保証ではない。新Smoke後、全90開始前に意味結果を選別せず資源/時間の見積りだけ更新できる。新費用・Model Hash・資源値は未計測。旧失敗費用と未知を保存し、電気代/AI実費はnull、外部従量APIへ切り替えない。

支持Recall/非支持Specificity各0.90・最低被覆・Health・全固定本文/全分母・F0.7・順序/反復・一回書換え・未使用Group・全採点封印を維持する。Evaluation本文/回答/結果を読まない。Main日英20ずつ、独立Cal20ずつ、最終N/統計/欠測/停止規則・実Validator/Manifest/Hash/Gate11は未了。Phase12を開始しない。
