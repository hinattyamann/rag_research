# 本文へ反映する記述案（日英同内容）

これは文案であり、日英DOCXは未編集。補足資料の調査完了を、元実験の再実行や再採点として扱わない。

## Japanese reference provenance / 日本語参照元

**EN:** One Japanese reference article was unavailable in the original corpus acquisition: the cutoff-based title lookup returned HTTP 200 but no pre-cutoff revision for page 5273510. A subsequent provenance audit traced a July 2026 page move and recovered public revision 98057227 (21 November 2023) from the moved history, page 56523. This body was acquired after the experiment and was not added to its inputs or grading. Equality to the historical rendered response is not established, and the complete saved reference quotation is not a verbatim match to the newly extracted text; documented partial quotations match. The five actual context documents, responses, and existing labels remain traceable and unchanged.

**JA:** 日本語の参照記事1件は元のCorpus取得時に欠落していた。Cutoffを指定したタイトル検索はHTTP200で応答したが、Page5273510のCutoff以前の版を返さなかった。後日の出典監査で2026年7月の記事移動を追跡し、移動先の履歴Page56523から公開版98057227（2023年11月21日）の本文を回復した。この本文は実験後に取得したものであり、実験入力や採点には追加していない。当時の描画応答との同一性は証明しておらず、保存Reference引用の全文も新たな抽出本文と逐語一致しないが、記録した部分引用は一致する。実使用根拠5文書、回答、既存Labelは引き続き追跡可能で、変更していない。

## Annotation model / 外部採点モデル

**EN:** All 84 retained annotation-job receipts, CLI events, and corresponding session logs were audited. They record CLI version 0.164.0-alpha.11.1 and the configured model alias gpt-6.1-sol with high reasoning effort. The observed model strings are client configuration or session metadata, not confirmed serving-snapshot identifiers. No exact serving-model identifier was established from these retained logs; this does not imply that the service never exposes such information. Anonymous packet mappings, rubrics, schemas, input/output hashes, job times, and format-repair provenance remain available. Human review and independence of model histories are not assumed.

**JA:** 保存された84採点JobのReceipt、CLIイベント、および対応するSessionログを全件監査した。当時のCLI版は0.164.0-alpha.11.1、指定モデル名はgpt-6.1-sol、推論努力はhighと記録されている。観測されたモデル文字列はクライアント設定またはSessionメタデータであり、確認済みServing Snapshot識別子ではない。これらの保存ログから厳密なServing Model識別子は確定できなかったが、サービスがその情報を一切公開しないという意味ではない。匿名Packet対応、採点基準、Schema、入出力Hash、Job時刻、形式修正の来歴は保持されている。人手確認とモデル履歴の独立性は仮定しない。

## English source revisions / 英語出典の版

**EN:** For the 40 selected English questions, retained upstream original-document records supplied explicit revision URLs for 36 original QA documents. This reference-document provenance is distinct from exact revision identification of the retrieval corpus. Among 222 distinct passages used or referenced by these questions, 199 had exact text matches in one or more retained upstream documents, while 23 had no match within the inspected sources. These matches are revision candidates, not established corpus-revision bindings, because the retained records do not preserve a direct corpus-to-revision construction ledger and unchanged text may occur in different revisions. Reproducibility of the saved input text relies on the fixed CLAPNQ revision, passage IDs, and text hashes; exact Wikipedia revision identity remains unresolved.

**JA:** 選定英語40問のうち、保存済み上流の元文書記録から36問の元QA文書について明示的な版付きURLを回復した。この参照文書の来歴と、検索Corpusの厳密な版同定は区別する。当該質問が使用または参照した異なる222 Passageのうち199件は1つ以上の保存上流文書内で本文が完全一致し、23件は調査した資料内で一致しなかった。Corpusと版を直接結ぶ生成台帳が保存されておらず、変更のない本文が異なる版に存在し得るため、これらは版候補であり、確定したCorpus版対応ではない。保存入力本文の再現性は固定CLAPNQ Revision、Passage ID、本文Hashに基づき、Wikipediaの厳密な版同一性は未解決である。
