# Phase11 v31：生成0・NS通過、主体帰属の誤支持で不採用

2026-10-27 22:39 JST追記: [累積費用v19](../data/manifests/phase11_autonomy_cumulative_cost_v19.json) SHA399a40c962dfee50e8f4a01bca032f829cc6deac504761a00d8877ba3958c50aを実発行・独立検算した。閉38 Run/25Guard、新355試行・353返却・未知2、旧込1264試行・確定未知5、観測input724162/output1021409・総output null。Native20604.366958秒は未知HTTP16.895423秒を含む、Task20519.499901718635秒/wall21319.09550735884秒は別scopeで加算しない。旧35行/23Guard・旧未検証返却32をそのまま保存。Rootも全355/28binding等を0.040528225秒で追加検算し全禁止count0、証明74d7fea0へ保存した。v31意味不採用・未使用枠は不変、Main/Cal/Gate11未達・Phase12未開始。

記録: 2026-10-27 22:37 JST。固定実験Commit eb7967c9939d2ba5f8f04f6aada50a7faf8b853d。候補ID dbb9830fc366b8b1631ce8d1feab90403810ad9bb0086f655a08c4ba60ab12e3。

v31は日英Judge Prompt15→16へ、根拠の文法主体・行為/対象・時期/資格を先に結ぶ一般的指示を追加した候補である。Qwen3-8B Q4_K_M、GraphOFF b11433、FAoff、Context12288、共通reasoning4096、Sampler/Schema/Core94、全文Source・固定文・Expected・基準は不変。CUDA復旧やHealthだけで意味問題が解消したとは扱わない。

| 実段階 | 結果 | 正式証拠 |
|---|---|---|
| 専用Checkout再現 | 781資産/19 aliases/専用uv58/実Model・Runtime Hash/Core94一致、Native0 | [再現Manifest](../data/manifests/phase11_v31_checkout_reproduction_v1.json) `f4f6267b652f60d2c87f2b7af3d48c03d36979c5acff45b12e536d1e81af6c44` |
| 全90入力生成0 | 全90/95Raw、最大4218＋予約6144≤12288、余裕1926、37CUDA層FAoff | [生成0Manifest](../data/manifests/phase11_v31_preflight_result_v1.json) `79174e07d9209e9770244973e58a348cd685f8fcc88d6cccf934438f55b41e35` |
| 日英NS2 | Health2/未知0・意味2/2、全Source/理由/thinking監査 | [NS Manifest](../data/manifests/phase11_v31_smoke_result_v1.json) `c2db3ec66fe58e392650bd032530c4b6b2fdf9d77bc6e51495dd37a29cce9b4e` |
| 帰属C元逆2 | Health2/未知0でも両S、Expected Cとの意味一致0/2、二値も誤支持 | [C Manifest](../data/manifests/phase11_v31_attribution_smoke_result_v1.json) `12f18387fbd398bcee1a33e594e38dddc5012f3c6bd4567adbf6fce378f9f7d1` |

C2では、全10根拠・初回回答7固定文・根拠ID/Titleを保持した。1567年、Council閉会後にPope Pius Vが行った事項をCouncilに帰属させる誤りが元逆とも残った。原順のthinkingは閉会時期も1567年へ読み替え、逆順はPius Vの行為をCouncilの承認にalignすると説明した。Source主体の照合指示は実際の推論で履行されていない。実在する引用IDを挙げても理由の意味は正しくならない。自然reasoning548/453 Tokenで4096上限未到達、未知や形式破損による不合格ではない。

NS2は校正→試験合格と箱の塗装→日光反射から新しい因果関係を作らないことを正しく判定した。日本語thinkingには一時conflictと考えた揺れ/反復があり、最終的に別原因だけでは排他的否定にならないと修正した。この経過も全文保存する。NSだけの合格をCや全90/Knownへ外挿しない。

全新Runは正規v3 Guard/共有台帳に有限Planを登録し、Retry0・HTTP1200秒・監視5秒で一回実行した。Rootは実Handle53121/7313/68479の終了0と所有PID/create/group停止を確認してからRaw初読を認可した。NSは初読前Markerから全2件レビュー封印まで37.644845328秒、Cは106.248804439秒である。後者は全読・失敗診断・一般的な次候補案検討を含み、純読時間は未計測null、件別時間へ均等配分しない。

| 費用scope | 入力Token | 出力Token | Task秒和 | Native HTTP秒和 | Run wall秒 |
|---|---:|---:|---:|---:|---:|
| 全90入力生成0 | Native入力0（tokenize90） | 0 | 生成Taskなし | 0 | 20.771760929 |
| NS2 | 3786 | 1205 | 20.777593152 | 20.369618 | 35.704098291 |
| C2 | 7942 | 1233 | 25.023891730 | 24.550066 | 40.786267731 |

Task/HTTP/startup/wall/監査CPUは重なるため合算しない。生成0のtokenize/startup/監視資源を0費用とはしない。電気代・AI請求額・全対話wallは未計測null、外部従量API0。旧人工Tokenizer11/形式10は元v30のID/context/Rawを保持した厳格同値証明361222d4で再利用し、新Native10件へ加算しない。

Rootの追加小Hash検証はNS39＋C39、0.006385908秒。canonical `data/runs/lab/phase11-v31-finished-smokes-root-review-v1/review.json` SHAe5916240666e02e2dda204ed93716f1b6d64920454d750d7118a86a9da477109へ保存した。先のRoot小metadata helperはSmokeにも別schemaのartifactsを仮定してコピー前にKeyErrorとなり、失敗を保存、実schemaへ直した確認で成功した。実験再送0。

v31は不採用。未実行Rewrite2・全90・Known19・baseline・Main・Calを保全し、Expected/閾値/分母を変えて通過させない。旧v10/12/27/28/29/30、旧累積909試行/未知3、全失敗Raw/Manifest/Hash/未使用枠も保持する。Main/Cal/Gate11未達、Goal active・Phase12未開始。

次v32は、既存Coreが対応する`premise_then_claims`によりJudge入力を根拠→質問→初回回答→対象文とするレイアウトだけを別Identityで検証する。system/Extract/Rewrite/input_fields全文、QA内の回答・文書本文・ID・Title、各条件の根拠提示順、Model/Sampler/Schema/基準は不変。user JSONのkey orderは変わるため、旧systemだけ変更/user bytes不変という監査flagは流用せず、decoded内容同一・system同一・key orderだけ変更を別証明する。新鮮な入力0と意味検証が必要であり、改善は未確定。

採点はCodex AI、human_reviewed=false、履歴継承あり/非隔離、厳密な提供Model IDは取得不可null。UI設定はユーザー申告「6.1 Sol 極高」と記録し、旧記録を貼り替えない。
