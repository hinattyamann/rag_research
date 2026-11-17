# 初稿17：論理接続と表6の分類行を明確化

記録：2026-11-17 15:30 JST。初稿16（16c9744）に対する教員の追加指摘3点を日英へ反映した。本文入力の変更は要旨、3.1節の反復対照説明、表6注の3箇所のみ。配置順、表の行名・数値、図資産、実験条件、元ラベル、集計結果、文献を保持した。新規推論・採点・区間推定は0。

## 1 要旨の論理の流れ

接続語を加えるだけでなく、各文の役割を次の順に整理した。

1. RAGと内部評価の背景。
2. “However, this decision may depend on evidence order.” で背景から研究上の疑問へ接続。
3. “To investigate this possibility” で疑問と順序変更・反復比較を対応付ける。
4. “To isolate selection effects” で共通書換えを生成する目的を明示。
5. 収集200問と比較可能148問を “of these” でつなぎ、対象の包含関係を示す。段階的収集と事後統合を保持。
6. “This analysis finds” で対象・解析から不一致の結果へ接続。
7. “Examining the quality consequences …” で順序判断の変化から品質上の帰結へ進む。
8. “Comparing policies” で26問の分類から方策別の品質比較へ切り替える。
9. “Despite returning fewer reliable answers” で品質と費用の結果を関連付ける。
10. “Together, these results indicate” で結果を結論へまとめ、最後の “However” で解釈の限界を明示する。

全結果数値、固定条件、品質判定不能、日英差の区間が0を含むこと、人手未確認・拒否除外・データセット差の限界を保持。Word標準232語、空白区切り230語。論理接続を削ってページ数を合わせる処理は行っていない。

## 2 反復対照の前提と帰結

“Across all trials” の文を先頭へ移し、全試行で固定する対象を根拠の「内容」まで明確にした。その後、反復対照では元の根拠順序とseedも変えないことを述べ、その帰結として同一入力・同一seedでの再現性を測ると説明した。

> Across all trials, retrieval results, A_i, sentence segmentation, and packed evidence content stay fixed. The repetition control also keeps the original evidence order and seed unchanged. It therefore tests repeatability with identical inputs and seed, rather than variation across sampling seeds.

日本語も「全試行の固定内容 → 反復対照で追加的に固定する順序・seed → したがって何を測るか」の同じ構造にした。直前の各呼出しseed42の説明と、後続の外部評価用の参照回答・根拠の扱いは保持。

## 3 表6の分類行

曖昧な “the three quality categories” をやめ、見出しを数えないこと、対象の行番号と各件数を表注で明示した。

> Excluding the header, rows 2–4 partition row 1's 26 questions: changed quality (14), unchanged quality (8), and indeterminate quality (4).

これにより、データ第1行が総数、第2行が品質変化14問、第3行が品質不変8問、第4行が判定不能4問と、次ページの本文を読まずに対応できる。Same Yの内訳も保持。表の値・行名・分類規則は変更していない。

## 出力と確認

- 日英WordとMicrosoft Word直接出力PDFを更新。英語8ページ・日本語9ページ、99対訳ブロック。
- 両版の全17ページを画像で確認。英語4・6・7・8ページ、日本語5・7・8・9ページは前版との画像Hash一致も確認。
- 英語要旨とKeywordsは第1ページ左段内。全12図表は段頭7件・段末5件で、check_pdf_layout.pyに合格。
- 現行公式テンプレートを再取得し、保存原本とSHA-256一致。最終英語Wordの公式セクション設定・余白・段組・書体・サイズ・著者欄・引用を保持。PDFの全本文・表注・14文献収録、全14文献リンク、フォント埋込みを確認。
- [変更前後全文](draft17_before_after_20261117.json) と [最終検証・対象Hash](draft17_validation_20261117.json) を保存。
- 最終検査は論文用pytest 29件合格、ruff check . 合格、git diff --check 合格。
- 公開要項への適合を確認。教員の投稿承認と投稿は未実施。

次は著者・教員による論理の流れと表注の再確認、投稿承認。その後、投稿画面の追加条件を確認して提出PDFを確定する。
