# 先行研究との関係と、採用した研究テーマの位置付け

更新日: 2026年10月18日。現行テーマは[研究計画 Version 7.0](rag_research_plan.md)による。
旧原因別修復案の整理は[保存版](archive/related_research_positioning_before_pivot.md)を参照する。

## 1. 何を新しく明らかにしたいか

質問・実使用根拠・生成済み回答を固定し、評価器へ見せる根拠の順序だけを操作する。
同一順序の反復と比較し、その違いが採用/一回書換えの判断、独立品質、費用へ及ぼす影響と条件を調べる。
自己評価の不安定性や、それを制御へ使う一般論を最初に提案する研究とは位置付けない。

## 2. 最も近い研究と区別

| 文献 | 既に扱われている点 | 本研究で切り分ける点 |
|---|---|---|
| [ConsJudge（Findings of ACL 2025）](https://aclanthology.org/2025.findings-acl.301/) | RAG評価Promptへの感度・不一致と、一貫性を利用したJudge学習 | 評価次元を変えず、同じ根拠の順序を操作して修復起動へ接続する |
| [RAGVUE（EACL 2026 Demo）](https://aclanthology.org/2026.eacl-demo.35/)・[本文3.1.7](https://arxiv.org/html/2601.04196v1) | Model/温度による評価幅、各Judgeの説明、可視化 | Score幅や画面自体でなく、固定候補の選択と品質・費用を測る |
| [Stable-RAG（ACL 2026）](https://aclanthology.org/2026.acl-long.1188/) | 生成器の検索文書順序感度とその抑制 | 初回生成を固定し、評価器だけの提示順序を変える |
| [Doctor-RAG v2 Appendix D.2](https://arxiv.org/html/2604.00865v2) | 誤診別の修復率、診断訂正後の再振分け | 原因分類の正解化ではなく、同じ回答への評価条件による起動変化を調べる |
| [When the Judge Should Not Decide](https://arxiv.org/html/2608.07813v1) | 固定候補群でJudgeの選択を制限し、最終正答率と悪化を比較 | 固定候補や下流影響自体は既存。評価順序の操作と、単一回答の書換え起動に絞る |
| [AGO AI Quality Gate](https://arxiv.org/html/2610.01218v1) | Judgeの検証とSystem VersionのリリースGateの統計分析 | Version公開判断と、一質問内の回答修復を区別する |
| [Query Timing Produces Opposite Positional Biases Between LLMs and Humans](https://arxiv.org/html/2608.12387v1) | 証拠順序と途中/最後の判断の関係 | 証拠順序効果自体は既存。RAG修復の実害・費用に絞る |

Doctor-RAGと最後の三件は確認した著者公開版として引用し、会議採録確認済みとは扱わない。
全ての類似論文がないと証明したものではなく、投稿前に近接研究を再確認する。

## 3. 引き継ぐ基盤と、主貢献にしないもの

[Self-RAG](https://arxiv.org/abs/2310.11511)、[CRAG](https://arxiv.org/abs/2401.15884)、
[Adaptive-RAG](https://aclanthology.org/2024.naacl-long.389/)、
[RAG-Critic](https://aclanthology.org/2025.acl-long.179/)は、反省・適応・評価・修復の重要な先行である。
[ARES](https://aclanthology.org/2024.naacl-long.20/)は根拠性等の評価観点に関係する。
R/F/Aや根拠性Score、閾値、一回修復、小型LLM、ローカル実行、CLAPNQ適用、
評価器と品質Labelの分離、多数決・平均化のいずれかだけを新規性にしない。

## 4. 成果の示し方

主張の候補は、順序操作の効果が同一順序の反復と異なるか、どの条件で判断が変わるか、
その判断変化が書換えによる利益・害・費用のどこへ伝わるかという実証的知見である。
「閾値の近くは反転しやすい」という自明な帰結だけでは不足する。
現象が小さい場合も推定精度・対照・再現範囲を示し、単に有意でないことを不存在の証明としない。
対策は追加成果であり、そのために独立品質評価や本実験の対照を省かない。

単独採点、一Dataset・限定Model、固定書換え候補の制約を明記する。
参加者を集めないため、人の理解度や診断時間の向上は主張しない。
採択や性能向上を保証せず、実験で支持できる範囲へ論文の主張を更新する。
詳細な検討経緯は[ICIAE投稿可能性の調査](iciae2027_pivot_feasibility_review.md)を参照する。
