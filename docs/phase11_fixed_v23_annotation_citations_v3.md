# 固定v23 Calの匿名採点復旧 — 原文引用の選択方式 v3

2026-11-04。停滞の原因究明・再発防止・検証後の再開というユーザーの依頼に基づく、採点出力形式の事後変更。モデル出力の再収集や、判定結果を見て好都合な採点を選ぶ操作は行わない。

## 停滞箇所と原因

11/1のGPU解放後、Calは全40選定の処理を完了した。初回40成功、内部評価・書換えは正常39/書換え長さ欠測1である。Main全採点封印・解析も完了済み。

11/1 21:31 JST、Cal英語の文単位Expected採点で、4候補/6注釈のcal-en-units-004-inline-v2が失敗した。初回は「Unit evidence must be verbatim actual used context」、許可済みの形式修正1回後は「Support/conflict requires actual context evidence」でValidatorが拒否した。CLI自体は2回ともexit0で、要求件数6も満たしていたが、検証済みJobとして確定できなかった。従来の自由文字列Schemaでは引用の逐語一致とLabelに応じた根拠必須を制約しておらず、形式修正が尽きてWorkflowが終了した。

今回はGPU不足やAPI接続ではなく採点の出力契約の不備である。Calの新しい収集障害・未知要求は発生していない。既知の書換え欠測1は元の収集結果として維持する。

## 出力契約の変更

- 匿名Packetの実使用文書から、候補ごとに資料番号eNNNNの引用カタログを決定的に作る。品質採点ではReference文書も別種として登録できるが、文Expectedでは実使用文書だけを登録する。カタログの引用は各Passage全文で、元文字列の0から全文長までの範囲をそのまま保存する。原文・周辺文脈・候補本文・採点基準は全文で渡す。
- AIは各aNNNスロットにLabel/理由/根拠資料番号を返す。品質採点では3基準とessential_pointsも返す。スロットと候補/文/Hashの対応は入力へ明示し、出力Schemaで全スロットを必須にする。プログラムが識別子とHashをその対応表から復元し、選ばれた資料の原文を無変更で引用へ展開する。引用内容や判定Labelをプログラムが創作・補完しない。
- 文のsupported/contradictedは同じ候補の実使用資料を1件以上選ぶことをSchemaとDecoderで要求する。not_supported/ambiguousは引用0件も許可する。資料を選べること自体は支持の証明ではなく、全詳細を同じ基準で評価するよう指示する。
- 品質のreliableは全基準passと実使用資料1件以上、unreliableは明確なfail、indeterminateはfailなし/uncertainありをSchemaと元Validatorで検証する。Referenceだけでreliableとはしない。
- 件数・ID/Hash・逐語一致・根拠必須・採点基準の元Validatorは緩めない。出力Decoderの形式エラーも最大1回の形式修正へ入り、エラーをReceiptの隣へ保存する。プロセス失敗や利用枠不足を形式エラー扱いで再送しない。

## 既存成果と予算の保全

- Mainの全採点封印・解析、Calの全収集、Cal英語品質の確定40注釈と検証済み文採点Jobはそのまま利用する。検証済みinline-v2 Jobは元の入力/Schema/出力/来歴を同じHashで再利用し、CLIを呼び直さない。
- 検証に失敗した6注釈のJob全体は未確定として、同じ匿名候補を別citations-v3 Jobで採点する。成功したLabelの選り好みをせず、元2回の出力・形式修正・来歴・利用量・55予約の台帳を保存する。新たな再開Jobも元の最大192予約に加算する。
- モデルgpt-6.1-sol/努力high、ChatGPT認証、APIキー課金禁止、4候補/Job、個別40分、修正1回、11/6 00:00 JSTのWorkflow期限は維持する。引用方式の人工検証2 Jobの利用量は別台帳へ保存し、研究採点の費用と混同しない。
- 日英の全品質・全文Expectedを封印するまで、Calの内部F/候補対応と結合・解析しない。新たなNative生成・QA補充・主閾値変更は行わない。

## 配置・検証と論文での説明

Calの元事前登録は旧Helper/品質ProtocolをHash固定しているため上書きしない。旧Revision6の全25入力を保存し、修正版7 Helperをfixed_v23_automation_v3へ追加配置する。Revision7設定と別復旧登録は元Cal Protocol、元/新入力Hash、Main/Cal元ファイル、失敗証拠を結合する。

通常のテストに加え、実際と同じsystemd・推論用uv環境・ChatGPT認証で人工英語文判定2注釈/日本語品質2注釈を検証した。双方とも元Validatorを通り、ツール実行0。最初の人工確認プログラムは推論環境にpytestがないためCLI起動前に終了した。そのログを残し、人工Packetを先に作って読み込む方式で実確認した。研究Nativeは0。

MainとCalの途中には採点入力レイアウトと引用粒度の差が残る。モデル/基準が同じでも採点手続が全件同一とは主張せず、事後変更と測定上の限界を明記する。方式別CLI回数をannotation_cost.jsonへ、変更理由をresults_brief.mdへ保存する。形式修正前後の出力/費用も保持する。

実テスト件数、元成果不変、実再開と新しい検証済み注釈数は[検証Manifest](../data/manifests/fixed_v23_annotation_citations_validation_v3.json)と[自動化状況](fixed_v23_automation_status.md)へ記録する。次はCalの未確定採点→全封印→Cal解析→図表/CSV/説明資料。原稿執筆と提出は未実施として残す。
