# 提出版と提出記録

著者・教員の確認を終えた提出対象PDFと、その提出記録を保存する。
採択後の最終版は別の名前で保持する。

## 初回提出前の確認

2026年11月20日に、担当教員から投稿承認を得たとの報告を受け、[提出対象PDF](iciae2027_initial_20261120.pdf)を確定した。日英Wordに対応するCommitは `7cea1c2778700112c34dab02f8e9eb0227a4ccfb`。英語8ページ、要旨232語、Keywords 5件。提出用コピーと[検証済み英語PDF](../manuscript/iciae2027_manuscript_en.pdf)は同一で、SHA-256は `3d015dc3c7a2e81f7054b4a4a8e0b45dafc73f1c4fed77a0098072c697c9c786`。

[公開著者要領](https://www2.ia-engineers.org/conference/index.php/iciae/iciae2027/about/submissions#authorGuidelines)と同日取得の公式テンプレートを再照合した。PDF形式・英語・4～8ページの条件、公式書式、図表12件の配置、参考文献14件のクリック可能性を確認した。文献(2)(8)はHTTPクライアントで出版社転送後に403となったが、Edgeでは両方ともMIT Pressの該当論文ページを表示できた。他の12件はHTTP 200と接続先を確認した。[英語Word・PDFの詳細検証](../notes/draft18_validation_20261119.json)を参照。

投稿画面はStep 1まで確認した。Step 3で原稿と同じ著者順で全2名を登録する。投稿完了・受付番号・受領確認は未確認。

## 提出記録の方針

提出PDFは提出用英語版 `../manuscript/iciae2027_manuscript_en.docx` から出力する。
対応する理解用日本語版 `iciae2027_manuscript_ja.docx` も同じ内容の版へ更新し、両版の対応を確認する。
日本語版は理解用と明示し、投稿ファイルに混ぜない。

各提出について、対応する英語・日本語Word原稿のCommit、PDFのSHA-256、ページ数、
提出日時とタイムゾーン、受付番号、受領確認の有無を記録する。
未提出の原稿を提出済みと記録しない。
アカウントのパスワード・認証情報や個人情報を含むメール原本を公開Gitへ追加しない。
