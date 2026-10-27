# Phase11 意味候補v32の実結果

記録時間: 2026-10-27 23:32 JST。固定Commit `81563f7aefe0ca3a659ba0677a74d6d71e05d1bd`、Identity `73d9ac7d429e11129a8c5faceee6d8d50a48b196ccea3d45b85fc631f10512af`。

v32は不採用。Judgeの入力キー順だけを根拠→質問→回答→固定文に変えても、Councilの主体・時期の誤帰属は解消しなかった。本文・ID・Title・全固定文・Expected・採用基準を変更していない。旧v31/累積費用v19・失敗/未知を保持し、同条件の再送は0。Phase12未開始、Main/Cal/Gate11未達でGoalを継続する。

|実段階|実証拠|結果|
|---|---|---|
|全90入力・生成0|[Manifest](../data/manifests/phase11_v32_preflight_result_v1.json)、SHA `8a56f9ff578273fd5fb441287f7b651a8d0ffca9b7e886c6bbbe9a6d46f0d408`|95 Raw、90完全message/prefill、Core94、37層FAoff、監視5点が一致。4218＋6144≤12288、余裕1926。Native0。|
|日英の因果NS2|[Manifest](../data/manifests/phase11_v32_smoke_result_v1.json)、SHA `9bb5b74727ed2aaa77c7a3581a68c7d069af3fc9a21ec251cdca7262014aa480`|Health2/2、三値/理由2/2、未知0。校正による合格と銀色塗装からの因果補完を拒否。|
|Council c4元逆2|[不採用Manifest](../data/manifests/phase11_v32_attribution_smoke_result_v1.json)、SHA `a3bbc4aa742b7da7e94b9187cc3bbbbb394091d74a49332cb4a88453a7cf01c4`|Health2/2、三値0/2、二値非支持0/2、未知0。両方S、原Expected C。|

全10根拠/7固定文を含む回答・引用理由・保存thinkingを実読した。根拠はCouncil終了後1567年にPius VがTrentを越えて承認/非難したと記載し、Councilの年限1545–1563/1563年閉会も別根拠が示す。元順では主語をCouncilへ置換し、逆順ではPius Vと認識した後にその行為をCouncilの支持へ流用した。実在IDを引用しても命題の主体・時期は一致しない。thinkingは元326/逆345生成Tokenで自然終了し、4096予算の強制終了ではなかった。

NSの実全文読解区間19.732229150948秒、レビューSHA `2494ce3b936a3839c917586b38b25746376c59234a8e6246c8f42b1a191c7050`。Cの区間44.732378054992秒、SHA `b3fbff2bc061adf6fb2d89b6cdcc9c040d515750e21f67dd87a7d78b4217f16e`。C区間にはRoot表示補助が `Input JSON:` 接頭辞をJSONとして読んだエラーと修正を含み、純読解時間は未分離/null。初読markerと既存packetは維持し、推論再送・Expected変更は0。表示エラーtool `0dbbc0` と修正 `28e833` はレビューに保存した。

|成分|入力Token|出力Token|Native HTTP秒|Task秒|supervised wall秒|
|---|---:|---:|---:|---:|---:|
|全90入力0|生成なし|生成なし|生成なし|別途台帳|20.765735204099|
|NS2|3786|1034|17.655691|18.086213359958|30.642761261086|
|C2|7942|875|18.580015|19.027128805872|35.691249307012|

各列は重なる別scopeで加算しない。v32計4試行/4応答/未知0、観測input11728/output1909、Native HTTP36.235706秒。電気代・AI採点実費は未計測/null、外部従量API0。[累積費用v20](../data/manifests/phase11_autonomy_cumulative_cost_v20.json) SHA `e24b9e4335ad73a8cd608fb032fae0c2f54d41472f083520addcacc556e58ee7` は別の全41閉行監査・独立検算で実発行した。旧込1268試行/確定未知5、総output nullを維持する。

実Handle80602/92744/24326の閉exit0、Root認可とowned PID/create-time/group停止をRaw前に確認した。C実験の認可SHA `2f1669c689a187b0135419d5980f3cc37f692ebf1630276ebb72bf88eef9586b`。C監査のCPU Handle82580は正式出版後のpollでUnknown process idとなったため、観測済みexit0とは記録しない。正式出版された全39小Hashと全41閉台帳行をRootが追加照合した。これは実験Handle24326の閉/所有停止の観測とは別である。

[Root追加照合](../data/runs/lab/phase11-v32-stage-evidence-v1/attribution-smoke-Root-small-artifact-and-terminal-check.json)は全41 Run終了・v32の3段階/4 Call・未知0・未使用枠を確認した。Rewrite2/全90意味/新鮮Known20元84/Main/Cal/Freezeは未実行であり、成功や費用0に補充しない。

Source準備は必要差分8 test/Ruff・5pending拒否、親共通9関数ASTと不変補助SourceのHashを再利用した。独立Sourceレビュー `f2f2b050…` に未解決P1/P2はなく、Rootでも全90入力104小成果、NS/C各39小Hashを追加照合しRuffが成功した。採点AIは/root、human_reviewed=false、history_isolated=false・継承あり、ユーザー申告6.1 Sol 極高、厳密Model識別子null。

次は8BのPrompt/レイアウトだけを反復せず、保存済み9Bの意味精度とCUDA障害を分けて実行条件を検討する。原因は未確定で、別候補/Protocol/有限Planの変更範囲を事前登録してから実験する。旧Runの再生成とPhase12開始は行わない。
