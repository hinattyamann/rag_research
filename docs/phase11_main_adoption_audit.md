# Phase 11 主Development開始前の候補・採用基準の照合

2026年10月22日。新規QAをまだ実行していない段階で、[主Developmentの事前条件](phase11_main_development.md)と開始前の実装を照合した。
実行中v11の専用Worktree/Source/Configや、旧Policy/結果/採用基準は変更しない。

## 発覚した不足と修正

既存の`validate_main`は主Configと通過済み既知回帰のModel/Runtime/Prompt/予算を照合していたが、
実行Policyの`candidate_config`自身をその通過条件へ直接結び付けていなかった。
また、PolicyのHashや一部の封印/件数/上限は調べていたが、意味採用・Health等の全事前値を
開始前に明示検査していなかった。実主20問は未実施で、採用基準を緩めたRunがあった意味ではない。

今回、Policy候補Fileのパス/Hashを照合して実設定を読み、完全通過の既知回帰と
`study_version`/`diagnostics`以外の全項目が同じであることを要求する。
両項目は候補診断と既知回帰で用途が異なるため除き、Model/Runtime/Prompt/予算/Sampler/全判断条件は保持する。
旧v8を指すPolicy v1を、新Modelや別Promptの採用へそのまま使えない。
今後の新Policyは、元の全採用値を保って採用済み候補へ結ぶ必要がある。

開始前と、両言語の全Label封印後に意味採用を集計する時点で、同じ関数が次の事前値/必須Fieldを検証する。これは既存Policyの値を実装へ反映したもので、条件の緩和ではない。

- 全20 QA、Task失敗/入力超過0、実使用Context、未知結果の停止と未試行保持。
- 確定Label/支持Label一致率各90%以上、明確な非支持の誤支持0、完全比較QA各10以上。
- 曖昧は精度だけから除きF分母を保つこと、正負/曖昧分母、全Expectedの封印後照合。
- 両言語全匿名品質の封印、人手確認false、品質不明の非補完、候補最大2。
- 閾値0.7、裸拒否一回書換え、文なしScoreの明示null。

型も照合し、件数0の代わりのfalseや、必須のnull Fieldの省略を許可しない。
比較可能QA数10の理由も空にしない。固定1660 Call/言語と新規5 QA/段階Sessionの検査は維持する。
このModuleは実行可否の検査で、Modelへ渡す入力や内部判定・Fを変更しない。

## 検証と現在の限界

新規23 Testを含む全584 Test/Ruffに成功した。開始前の補強後は8.25秒、封印後の採用へ同じ検査を接続した後は8.47秒だった。
Model/Seed/Prompt/判断条件/追加条件の異なるPolicy候補、意味/Health/品質/判断基準の弱化、
候補Binding/明示nullの欠落を、変更後のHashを与えても拒否した。
元の選定/履歴/QA/Core/上限/条件の変更拒否、分割実行/保存済み再開も回帰検証した。
実Policy v1は追加した事前値検査に通過し、推論を行っていない。

初回の全Testには1件の`PytestUnhandledThreadExceptionWarning`があった。
既存の起動直後にプロセスを終了させる故障注入Testで、`LocalServer._sample`が
`psutil.NoSuchProcess`を受けた。Test本体の起動失敗時Cleanup検査は成功した。
封印後の採用経路を変更したため再度全Testを実行し、その回は警告0だった。警告を消すためだけの反復は行っていない。現在のModel入力/Native Core27 Hashは不変。
この失敗起動時の資源監視の競合は未修正で、後続Testで出なかったことを修正の証拠や完全な資源監視の認定とはしない。

通過側Testは既知回帰の読込みを置き換えた単体検証で、実採用の証明ではない。
実際の新しい既知15 QA回帰/主20問は未通過・未実施であり、実Reportでの採用Guard成功側は依然として残る。
この補強を理由に採用やGate 11の達成を主張しない。
