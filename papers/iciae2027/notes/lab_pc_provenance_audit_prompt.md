# 研究室PCで未取得情報の原因と回復可能性を調べるプロンプト

作成日: 2026年11月6日。以下を研究室PCのCodexへ渡す。
目的は、論文の出典確認・再現性に関わる3点を、既存記録でどこまで確定できるか調べること。
この文書は依頼手順であり、追加調査が完了した記録ではない。

---

ノートPCでICIAE論文の日英初稿を作成し、固定v23の既存80問資料はGitから取得・検証済みです。
残る3点について、研究室PCの元取得記録・生ログ・保存済み上流資料を調べ、確認結果と必要な証拠をGit共有してください。
情報を回復できない場合も、調べた範囲・取得不能理由・論文で開示する限界を確定してください。

## 1 作業範囲と保全

- 最新AGENTS.md、研究計画・実装計画、research_roadmap.mdを確認し、Git状態・Branch/Commit・remote・追跡先・実行中実験の参照Checkoutを確認してください。
- originをFetchし、最新origin/paper/iciae2027上の本指示書、notes/materials_handoff.md、notes/notebook_materials_review_20261106.md、既存資料のREADME/missing_information.jsonを読んでください。現在CheckoutへPullできなければgit showで読んでください。
- 最新執筆Branchから独立Worktreeを作り、paper/iciae2027-provenance-audit-v1等の専用Branchで作業してください。既存Branch/未完成変更を上書きせず保全してください。
- 元Main/CalのRun・Corpus・設定・採点封印・既存注釈・日英DOCX・進行中実験は変更しないでください。実行中CheckoutへのPullやサービスの停止も行わないでください。
- papers/iciae2027/materials/fixed_v23_v1/ は確定済み資料です。missing_information.jsonやManifestを含め変更しないでください。受領時の資料Treeは5fb236667f6e4411a730187dc1e6ce80f27c710fです。
- 新規の研究用モデル推論、再採点、Label変更、QA除外/補充、主結果・区間の再計算は行わないでください。モデル自身に実行モデル名を質問して識別根拠にしないでください。
- 未使用Evaluationや追加検証の未封印結果は閲覧・混入しないでください。上流資料も選定ID/Passageに必要なメタデータへ絞り、未選定QAの内容を調査対象にしないでください。
- 公開元の固定ファイルや歴史版を調べる読み取り通信は必要な範囲で可能です。取得日時・URL・版・応答・Hashを残し、大量の新規ダンプ取得や閲覧制限の回避はしないでください。

## 2 日本語1問の参照元本文が取得不能になった理由

対象はMain/jaのwhrja:02e85c8:answered:857、質問「ニューラルネットワークの歴史は？」、参照元jawiki-page:5273510です。
既存資料のinputs/main_ja_ae3cdc2b7e88b42e102ec4b2.jsonでは、参照本文はbody_available=false/raw_article_status=unavailable、Referenceと引用は保存されています。
実使用根拠5文書の本文は保存済みで、当該QAは主比較対象にも含まれています。参照側の欠落と実使用入力の欠落を混同しないでください。

1. 元の日本語Dataset取得・Snapshot取得のRaw記事記録、要求/応答ログ、Cutoff、Title/Redirect、Page ID、Revision IDと時刻を追跡してください。既存source_manifest.jsonと元取得Manifestを入口にしてください。
2. 「対象時点の版がない」「Namespace不適合」「削除本文の権限エラー」「通信/APIエラー」「元ログ未保存」「不明」等を、実記録で裏付けられる範囲で分類してください。
3. 別記事「出家」のPage13492/Revision95068750に関するpermissiondenied記録は別件です。Page5273510の理由に流用しないでください。
4. 保存済みの当時本文、または同じ歴史版の公開本文を回復できる場合は、新しい補足資料へ保存し、版同定の証拠・取得日時・Hashを示してください。今回取得した本文を、当時のCorpusや入力に存在していたと扱わないでください。
   oldidの一致だけで、テンプレート展開等を含む当時の描画本文と同一だと証明したことにはしないでください。取得応答と抽出方法を記録してください。
5. 現在版や別の歴史版で欠落を埋めたり、既存Gold/Reference/Labelへ追加したりしないでください。回復不能なら、確認できた原因と残る不明点を明記してください。
6. 保存済みの実使用入力・参照引用・外部採点の追跡がどこまで可能か、原典本文の欠落で何を確認できないかを説明してください。補助解析が望ましい場合は提案までとし、主解析から当該問を取り除かないでください。

## 3 外部採点モデルの実識別子

共有済み84 Jobのprovenanceはconfigured_model=gpt-6.1-sol、exact_model_identifier=null、event_model_identifiers=[]でした。
現行review.pyは実IDをNoneとし、イベントから主に使用Tokenを保存しています。これだけで「サービスが実IDを公開していない」とは断定できません。

1. 元84研究JobのReceiptと対応するCLI JSONイベント/生ログ、開始・終了記録、当時のCLI版/設定を読取専用で確認してください。人工検証Jobや追加実験Jobとは区別してください。
2. 各Jobを既存のcohort/language/kind、input/output Hash、匿名Packetと結び付けてください。元ログの所在は既存source_manifest.jsonのcopy対応とreview.pyのReceipt生成箇所から探してください。
3. model/model_id/model_slug/snapshot等の識別情報があれば、実際に観測した値、イベント型、行番号/JSON位置、元ファイルHashを保存してください。
4. 指定名・エコーされた設定・CLI版・処理を実行したモデルの識別子を区別してください。単にgpt-6.1-solと書かれた行だけから、厳密なServing Model版が判明したとしないでください。
5. 実IDが得られなければ、「ログに該当情報なし」「元ログ未保存」「識別情報はあるが意味を確定できない」等をJob別に記録してください。現在のCLIへの問い合わせ結果を過去Jobの実IDへ代用しないでください。
6. 確定できるモデル設定・日時・Rubric/Schema・履歴分離の限界を整理してください。今後の記録改善案は文書にとどめ、現行収集コードや元provenanceを今回の調査で書き換えないでください。

## 4 英語Passageの元Wikipedia版ID

現行CLAPNQ資産では、固定Dataset版・Passage ID・Title・本文Hashは保存されていますが、元Wikipedia oldidは記録されていません。
新たにDataset全体やCorpus全体を作り直す必要はありません。

1. 固定CLAPNQの元QA/Passageファイルと、保存済みNatural Questions由来メタデータに、元document_urlや版の対応が残っているか確認してください。
2. 対象は選定済み英語40問の実使用/参照Passageに限定してください。まず掲載候補case_01/case_03等に関係するPassageを優先し、既存メタデータで一括対応できる範囲を整理してください。
3. oldidを確定できるときは、対応する元ファイル/行・ID・URL・版・保存本文との対応方法を証拠化してください。本文正規化を介した照合なら、その処理と限界も示してください。
4. Passage IDの数字、Title一致、現在のlatest revision、検索結果の類似本文からoldidを推測して埋めないでください。
5. 「同定済み」「候補のみ」「確認範囲では回復できず」をPassage別に区別してください。回復できない場合も、固定Dataset版/Passage ID/本文Hashに基づく出典表記と、その制約を整理してください。

## 5 成果物と検証

新しい出力先はpapers/iciae2027/materials/provenance_audit_v1/とし、既存版があれば内容を確認して上書きせず別版にしてください。

- README.md：3点の結論、証拠への索引、調査済み範囲、ノートPCでの確認方法。
- findings.json：各項目の調査状態と解決状態を分離し、確認事実/推測/未確認・理由・元証拠への対応を記録。
- 日本語QAの取得理由、84採点Jobのモデル情報、対象英語Passageの版対応を追跡できる表/JSON。
- evidence/：必要な元メタデータと最小限のログ抜粋。元の相対/歴史的パス、Byte数、SHA-256、抜粋位置、複製/抜粋/マスキングの別を記録。原文や根拠の出典・利用条件を保持。
- paper_wording_en_ja.md：方法・限界へ反映できる短い日英同内容の記述案。未確認の識別子や因果説明を補わない。
- artifact_manifest.jsonと小さい標準ライブラリの検証入口：相対パス・全出力Hash・表と証拠の対応・状態の欠落を確認。検証成功と未取得情報の解決を混同しない。

認証ファイル、Token、Cookie、環境変数、巨大イベントログ全体や不要な推論本文をGitへ載せないでください。
元ログに秘密情報が混在する場合は必要な識別情報だけを抽出し、元Hashとマスキング位置を記録してください。

既存固定v23資料の指定verify_materials.py --audit-openを作業前後に実行し、元の全採点封印・固定入力と、元資料Tree/Hashが不変であることを確認してください。
Python処理はuvを使い、コード追加時は変更に応じたpytest/Ruffを行ってください。
Gitから取得し直したコピーで、元Run/生ログ/認証/GPU/ネットワークなしに、新しい補足資料の証拠とHashを検証してください。
新しい検証入口は補足フォルダ内の相対パスだけで動き、元ログ等の歴史的絶対パスを開かないようにしてください。
資料調査に必要な公開元取得と、取得後のオフライン検証は区別してください。

## 6 Commitと引継ぎ

今回の補足資料・検証処理・最小限の案内だけを確認してCommit・通常Pushしてください。force pushや元Runの一括追加は禁止です。
執筆Branchが作業開始時の基点から変わっておらず早送り可能な場合だけ、同じCommitをpaper/iciae2027へ通常Pushしてください。
執筆Branchが先行していた場合は自動Merge/Rebaseせず、共有Branchを保持して取込元を報告してください。

終了時は、3点それぞれの「分かったこと/回復できた情報/未解決と理由/論文への影響」、証拠パス、検証結果、元成果不変、新規研究推論0・再採点0を報告してください。
Commit ID・Push先・リモート一致・未コミット/未Pushの有無と、ノートPCへ貼れる取込元Branch/Commit・資料パス・検証コマンドを示してください。
研究室側ではDOCXの編集、会議投稿、追加実験は行わないでください。
