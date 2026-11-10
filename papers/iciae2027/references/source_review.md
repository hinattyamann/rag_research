# 初稿の出典確認記録

確認日: 2026年11月4日。原稿の引用は一次資料の書誌・該当する本文/抄録等を根拠とする。
網羅的な最新研究調査や全原論文の精読が完了した記録ではない。精密な新規性・比較範囲は教員レビュー前に再確認する。

| 原稿番号 | 一次資料 | 今回の確認範囲と使用箇所 |
|---|---|---|
| 1 | [Lewis et al.](https://arxiv.org/abs/2005.11401) | 著者・題名・NeurIPS 2020採録表示・抄録。RAGの基本的な構成のみ序論で参照 |
| 2 | [Lost in the Middle](https://aclanthology.org/2024.tacl-1.9.pdf) | 公式書誌、抄録、入力位置を操作する導入。生成時の位置感度と本研究の評価時操作を区別 |
| 3 | [Wangら ACL2024](https://aclanthology.org/2024.acl-long.511/) | 2026-11-06追記。正式書誌/抄録、Fig.1、2.3.2節。候補回答の順序と校正を確認し、本研究の根拠順序操作と区別 |
| 4 | [Shiら IJCNLP-AACL2025](https://aclanthology.org/2025.ijcnlp-long.18/) | 同日追記。正式書誌/抄録、Fig.1、2.1〜2.2節。反復安定性は印刷p.294/PDF3頁。反復対照を新規としない。arXivでなく正式版を引用 |
| 5 | [ConsJudge](https://aclanthology.org/2025.findings-acl.301.pdf) | 公式書誌、抄録、3節の評価観点・一貫性と学習の説明。固定評価器の監査との相違を限定して記述 |
| 6 | [RAGVUE](https://aclanthology.org/2026.eacl-demo.35.pdf) | 公式書誌・本文冒頭と抄録の診断観点。詳細な実験比較や未確認の優劣は記載しない |
| 7 | [When the Judge Should Not Decide](https://arxiv.org/html/2608.07813v2) | 著者・v2日付・公開本文の固定候補と選択規則の位置付け。査読採録済みと扱わず、候補固定/下流影響自体を新規性としない |
| 8 | [CLAPNQ](https://aclanthology.org/2025.tacl-1.3/) | 公式書誌・抄録・論文冒頭。最初の2024年公開版と2025年TACL版を区別し、参考文献にはTACL版を使用 |
| 9 | [日本語Datasetカード](https://huggingface.co/datasets/baobab-trees/wikipedia-human-retrieval-ja) | 提供者・Dataset識別子。使用した固定版/加工はローカルのAssets/Manifestを根拠とする。追加のQAを研究結果として採点していない |
| 10 | [multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small) | 提供者のモデルカードと識別子。実使用の資産・検索条件はローカルの固定設定に従う |
| 11 | [Qwen2.5-3B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF) | 公式モデルカード。実ファイルの量子化・Revision/Hashは保存済み生成モデルManifestに従う |
| 12 | [Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B) | 公式モデルカード。Q6_K実ファイルはUnsloth提供の保存済みManifestに対応し、公式モデルカードを量子化ファイルの配布元と誤認しない |
| 13 | [保存資料と事後分析の固定スナップショット](https://github.com/hinattyamann/rag_research/tree/92ae5525a3a6a0e1046924b5d77f470a31098ad0/papers/iciae2027) | 2026年11月6日更新。自研究の資料で、関連研究の新規性の根拠ではない。元2資料は同日検証済みと同じTreeを保持し、事後記述集計と原文抜粋を追加した。末尾の資料同定段落から参照する。Wordの表示URLはRepository名まで、Hyperlink遷移先は固定Commitの論文フォルダ。無制限の公開アクセスは未確認 |
| 14 | [追加120問の固定スナップショット](https://github.com/hinattyamann/rag_research/tree/7beb396febd2842248af53a8ec39eda9fc153153/papers/iciae2027/materials/cal_extension_v1) | 2026年11月10日追加。自研究の別計画の追加Protocol、封印済み3Batch、追加集合のみの統合、オフライン検証器。Fetchした資料の全体/子検証に通過し、Tree0cc2339を保全。旧資料の文献13とは別に本文末尾で引用する。Wordの表示URLはRepository名、遷移先は固定Commit。第三者アクセスの保証や公開設定変更はしていない |

書誌本文とURLは日英原稿で共通とし、本文の引用番号は出現順の上付き丸括弧にした。
著者名と文献題名は翻訳せず、原書誌の識別に使う。
関連研究の具体的な数値は本研究の結果表へ混ぜていない。

初稿3の文献13は元2資料と保存入力の事後記述分析を含む92ae552へ更新した。引用英訳は推敲したが元日本語/文字区間は不変。無制限の公開アクセスを確認済みとは扱わない。本文の引用は日英で出現順1〜13。

初稿4は既存文献1〜13を保持し、追加資料の同定用として14を加えた。日英の出現順は1〜14で共通。
関連研究の新しい主張や文献の追加調査を行った改稿ではなく、自研究の検証済み追加結果を反映した。
