# Phase 9 開発例のAI代行採点

実施日: 2026年10月19日。確認者表示名: **リサーチャー01**。実際の採点者: **Codex AI**。
ユーザーが回答品質確認をAIへ委任し、採点JSONの保存を指示したため実施した。

**3候補を採点し、JSONを保存・検証した。人間が確認した独立品質Labelではない。**
Computer UseはブラウザURLを確認できず停止したため、HTMLと一致するPacketを表示順で読み、
同じ3観点・文章欄・根拠欄に対応する内容をJSONへ記録した。GUI操作を完了したとは扱わない。

## 1. 保存先と画面での確認

- [採点JSON](../data/runs/answer_rewrite/phase9-development-two-v1/quality-v2/ai-review-20261019-v1/quality-annotations.json)
- [理由・原文引用を含む採点レポート](../data/runs/answer_rewrite/phase9-development-two-v1/quality-v2/ai-review-20261019-v1/review_report.md)
- [AI代行・確認時間・検証の来歴](../data/runs/answer_rewrite/phase9-development-two-v1/quality-v2/ai-review-20261019-v1/review_manifest.json)
- [AI採点による経路比較](../data/runs/answer_rewrite/phase9-development-two-v1/quality-v2/ai-review-20261019-v1/analysis.ai.json)
- Git管理のHash記録: `data/manifests/phase9_ai_quality_review_manifest.json`。

採点JSONは元のHTMLと互換である。[採点画面](../data/runs/answer_rewrite/phase9-development-two-v1/quality-v2/採点画面.html)の
「保存したJSONから再開」でこのJSONを選べば、選択値・理由・根拠を表示できる。
元HTML、空の採点票、候補、既存の人手Import履歴は上書きしていない。
このJSONを人手Importへ流して人手確認済みと数えることは行っていない。

## 2. 確認した手順と結果

質問の必須要点を整理し、候補全文、実使用Context全10件、Referenceの代替表現とGoldを確認した。
事実主張を分けて原文との対応を調べ、質問への十分性と事実の支持を区別して3観点を採点した。
Referenceとの表現不一致やGold未取得だけで失敗とはしていない。
外部の知識で欠けた支持を補わず、自己評価ScoreやJudgeの判定を正解Labelとして流用していない。

| 表示順・候補 | 必須要点 | 重大誤りなし | 実使用Contextの支持 | 総合 |
|---|---|---|---|---|
| 1: 原子説の文章回答 `Q-09da4ac6a5c8d8210c87` | uncertain | pass | uncertain | indeterminate / Y=null |
| 2: Pradaの回答 `Q-47b98dde316abc059677` | uncertain | uncertain | fail | unreliable / Y=0 |
| 3: 引用IDだけの回答 `Q-d331e8ea413b8b76536f` | fail | uncertain | uncertain | unreliable / Y=0 |

### 原子説の文章回答

Daltonの1803年の近代原子説は支持される。古代の原子論に関する対比にも対応する根拠がある。
しかし質問が古代か近代かを指定せず、Referenceも一人を挙げないため、回答の十分性を確定しにくい。
反応物の重量比からの推論は根拠にあるが、回答の「科学的証拠と実験」という説明全体の支持には曖昧さが残る。
明確な失敗とは断定せず、判定不能とした。過去の説明例の結論を自動採用せず、全10件も確認した。

### Pradaの回答

根拠の「大半の市場では、英語使用か現地語訳使用」という記述から、回答の
「大半の市場で現地語へ翻訳された」という数量主張は導けない。全実使用Contextにも割合の裏付けはない。
イタリア語題名と英訳は支持されるが、回答全体の支持に明確な欠落があるためY=0とした。
これは数量主張が外部世界で偽であるという断定ではない。
質問意図とReferenceの対応はuncertainのまま残し、明確な支持の失敗を質問の曖昧さで隠していない。
短縮引用IDの不一致も記録したが、これ単独をY=0の理由にはしていない。

### 引用IDだけの回答

有効な引用先があっても、回答本文に人物名や説明がなく、質問への実質的な回答を欠くためY=0とした。
事実の命題がない2観点は適用対象外であり、現行フォームにその選択肢がないためuncertainにして理由へ明記した。
空の主張を満点に変換せず、一つの明確な失敗でY=0を確定する基準を適用した。

## 3. 検証と研究上の扱い

- HTMLのPacketと保存Packetの一致、Packet/Candidate Hash、全3IDの対応を確認した。
- 9箇所の原文引用の完全一致、3観点とLabel、要点・理由・確認者・時間・日時の整合を既存Validatorで確認した。
- 保存したJSONの読戻しも同じValidatorに通した。未採点は0、Y=0は2候補、判定不能は1候補である。
- AI確認の経過時間は108.34 / 51.78 / 33.99秒。ツール・記録の時間を含み、人間の作業時間とは扱わない。
- AI採点だけによる補助集計ではPradaが0→0で1問、原子の質問は0→nullで未知1問。
  不明を改善へ置き換えず、品質改善や順序効果の研究成果とは結論しない。
- この作業で新たな初回生成・Claim抽出・Judge・書換えの実行は0回。
- 採点者は既知の開発例について過去の会話で候補段階やJudge結果を知っており、完全な盲検ではない。
  モデル間/人間との一致率を測ったことにもならない。

今回の依頼範囲であるAI代行採点と保存は完了した。
原計画の「独立した人手確認済みY」や、それを含む正式Gate 9を完了したことには置き換えない。
今後、AI採点を研究の最終品質指標へ採用する場合の独立性・妥当性・Protocolの変更は、
この開発3候補の代行採点とは別の研究上の決定として扱う。Phase 10はまだ実施していない。
