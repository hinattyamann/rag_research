# Phase11 v32：根拠を先に提示するJudge入力レイアウト

2026-10-27 23:05 JST追記: v32正式事前登録09236fcaの出版後独立postcheck616d788e8bed2719ffd616ae20bd9c3aba3f25d04fd911664898aef1b73ba135が、全82成果/21入力/79＋補3コピーの全Hash・前後stat・独立inode、新3flag/二親/5段階予算/全6入口/元Guard/Cost19/旧人工contextを確認し通過した。inner0.155309365秒/tool0.109672721秒は別観測、全禁止count0/台帳操作0/新Native0。正規postcheckをcanonicalへ封印68865c1bで保存した。次はv32固定Commitと専用Checkout実再現、実GPU入力0・意味回帰・Main/Cal/Gate11は未了・Phase12未開始。

2026-10-27 23:02 JST追記: v32の[正式事前登録](../data/manifests/phase11_semantic_v32_preregistration_v1.json) SHA09236fcae9807a780eb175312ed8c2774b01843973defc05f3ae078be09bea1fを一回実発行した。全82canonical成果・21正式入力・79独立copy＋補3、実identity73d9/入力reviewd0ab/厳格人工再用b8f/実buildd07fと新3flags/二つの親/全5段階有限予算を結合した。旧v31不採用・費用v19・未実行Known19等を保全し、将来の新Known20は元15QA42文30条件84Call/全基準不変。Source2aa61365とreleasef6ce5658をRoot全文/全24封印・79小Hash照合後、finite120秒/Native0で実出版（child0.107444366秒/tool0.106460551秒は別scope）。新12差分test/Ruff・Root producer deltaレビュー4fdf/新actual header AST照合に通過、旧同一controlflowの構築証拠は条件付き再用とし新real Guardは初fixed Planで実検証する。専用Checkout再現・実GPU入力0・全意味/回帰・Main/Cal/Gate11は未了、Goal active・Phase12未開始。

2026-10-27 22:53 JST追記: v32の全90入力CPU監査d0ab6be18a2efcc545129d857fdd44e3cf0889e376d59644e5d0d3285a3c2edaが実成功した（child0.655508078秒/内部0.571735182秒、21正式入力/英50・日40、全禁止count0）。system同一・decoded本文/Expected/Source同一・キー順だけ変更とGold不在を全件検証し、Rootも21小Hashを追加照合した。旧v30のTokenizer11/人工形式10を元ID/contextのまま保持する厳格再用証明b8f40fe7ab3c6e76713dfbd2520bd71823d5c3f316ab307c1508ebcf388450ebを一回実発行（child0.305462073秒）し、意味Native再用0・重Hash0・新Native0を確認した。二つのchild観測とtoolwall0.927837302秒は別scope。新実Token生成0・意味検証・全回帰・Main/Cal/Gate11は未了。

記録: 2026-10-27 22:48 JST。研究の工程・現在地は[ロードマップ](research_roadmap.md)を正本とする。v31の[全実結果](phase11_semantic_v31_result_v1.md)は不採用のまま保全する。v32は別候補であり、同条件を成功まで反復しない。

仮説は、全根拠を初回回答より前に入力すると、回答に引かれた主体の読み替えを減らせる可能性がある、というものである。実意味改善は未確認。既存Coreが対応するjudge_layoutをdraft_sources_targetからpremise_then_claimsへ変える。JSONキー順はanswer/documents/question/claimsからdocuments/question/answer/claimsへ変わる。

科学上の変更はこのレイアウト一つである。日英Prompt17の全tasks/system/Extract/Rewrite/input_fieldsはPrompt16と同一。元と逆等の各条件における文書の提示順・本文・ID・Title、初回回答全文・全固定文、質問、Source/Expected、0.90の支持Recall/非支持Specificityと最低被覆/Health、F閾値0.7、同一順序反復、一回書換えを維持する。JSONのキー順が変わるためuser bytes不変とは主張せず、decoded全値同一・system同一・順序変更だけを各90入力で厳密に検証する。

実候補IDは **73d9ac7d429e11129a8c5faceee6d8d50a48b196ccea3d45b85fc631f10512af**。科学比較親はv31 dbb9830fc366b8b1631ce8d1feab90403810ad9bb0086f655a08c4ba60ab12e3。Rootが実builder460f0f6dを全文読後、有限120秒/見積5秒/ModelHash1/Native0のintentを保存して一回実構築した。子wall4.660438111秒/内部build4.459220423秒は別scope、GGUFHash1・他のprocess/socket/未使用data/WT/write違反0。実proofは`.tools/draft-artifacts/phase11-v32-identity-config-design-v1/identity-build.json` SHA d07ff7bcf98531b7dd238699aab27d1d74740638f0646ecc46c10a7a1f5a5037。

Qwen3-8B Q4_K_M、Model実Hashd98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785、GraphOFF b11433/FAoff/Context12288/予定37層（v32のGPU実行は未了）/共通reasoning4096、Sampler/Schema/Core94の5成分はv31実証拠と一致。旧identity descriptor bytesも保全した。Model/Runtime/Corpus/Index/Run欠落を理由に旧実験を作り直さない。

| 新Prompt | SHA256 |
|---|---|
| [英語17](../configs/phase11_semantic_prompts_en_v17.yaml) | 85b737599ff7a12a2a9eca8fc633ef6dc97b145bf1eeaabae7981fa3feeb5879 |
| [日本語17](../configs/phase11_semantic_prompts_ja_v17.yaml) | ac7ce7a165f6e4794de600c0bbbed21003cbfb955aee44078e71694f0491b9a8 |

独立review ce00e011は両全文/diffと、現build_messagesの実ASTによる人工日英×元逆4条件を確認し、全値・doc順・Extract/Rewrite出力不変を確認した。Source-firstでも誤支持が解消する保証はなく、全文・全thinkingで確認する。厳密Model識別子取得不可null、human_reviewed=false、履歴隔離なしを保持する。

新Protocol/producer/累積台帳/Guardはv3自律方針へ整合した別候補版で登録し、旧guardや旧失敗を書き換えない。不変の人工Tokenizer11/形式10は、実旧v30のID/context/全RawとModel/Runtime/Core/Sampler/Schema・人工messages/設定/Schemaが一致することを別証明した場合だけ再利用できる。人工実親v30と科学比較親v31は別の記録であり、意味Nativeの再利用は0。新Promptの全90実入力Token収容検証は省略しない。

実行順は新全90入力生成0→新日英NS2→新帰属C元逆2→新Rewrite2全文品質→全39QA/45文/78条件/90Callと全thinking監査→新鮮Known20で元15QA/42文/30条件/84Callである。旧v31の未実行Known19を保全するため別番号を使い、Source/Expected/全分母/採用条件は変更しない。有限Call/時間・個別timeout・監視・停止再開を各Runの新出力前に登録し、Health/意味不合格なら全失敗/未知/未試行/実費を保全して原因に応じた別計画へ進む。

実Known採用後だけ、fresh3B baseline0/日英2→元Main日英各20→別予約Cal日英各20へ進む。日英全品質・全Expected封印前に内部F/判断/候補対応を開かない。未使用・非重複Group、全文、全比較各10 QA以上、独立品質・費用を確認し、実測から最終N/条件/資源/統計/停止/欠測を固定する。実最終Validator/Manifest/HashとGate11の全証拠がそろうまでGoal active。Phase12を開始しない。

現時点は実identity/config5・新Protocolの全90入力CPU監査・人工再用証明まで完了。正式事前登録・固定Commit専用Checkout実再現・新GPU生成0/Native/全回帰・Main/Cal/Gate11は未了である。
