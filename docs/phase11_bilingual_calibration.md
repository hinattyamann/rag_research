# Phase 11 日英Calibrationの別予約と未使用性

2026年10月21日。主Developmentも意味採用候補も未完了で、ここでは次工程の対象IDだけを保存する。
未実施の実走/採点/採用を完了と記録しない。工程の正本は[ロードマップ](research_roadmap.md)。

## 旧英語Calibrationを再び未使用としない理由

`phase6_calibration_report.json`は、元の英語CalibrationのSource-answered全225問を
検索条件の調整に使用したことを記録する。QA File Hash/全225 IDを実Sourceと照合した。
その後の生成使用済み25問だけを除いた200問や既存の別20問は、生成履歴がなくても
研究全体で完全未使用とは呼べない。旧Split/Run/選定/検索条件調整の記録は保持する。

今回、英語はまだ実行していないDevelopment文書Groupから20問をCalibration用に別予約する。
元QA Fileの`research_split=development`は変更しない。予約Manifestでは
`source_split=development`と`analysis_split=calibration`を区別し、
この20問/全同一Groupを今後のPrompt/方法調整用Developmentへ使わない。
主Developmentの事前20 Group、既知使用済みGroupと重複しない。
日本語は元のCalibration84問/84 Groupから20問を選ぶ。

既存EvaluationのQA行や結果を開かず、旧Source Splitと凍結候補を保持する。
両言語ともSource-answered/異なるGroup/同じID順位方式だが、元のSplitの出所は異なる。
この違いもDataset/作成方法等の差とともに条件へ明示し、言語単独の因果効果とはしない。
この予約は本実験Evaluationの件数や対象を確定する作業ではない。

## 事前選定と確認結果

結果閲覧前のPolicyは`configs/phase11_bilingual_calibration_selection_policy_v1.json`。
Method名/Seed42/言語/QA IDのSHA256昇順で、各Groupから最初の一問だけを選ぶ。
質問/Reference本文、Model回答、内部F/品質、Gold Coverageや欠測を順位に使わない。
20は独立した文書GroupのHealth/意味妥当性/費用を確認する予備的な検証枠で、
最終検出力や有意差の保証ではない。失敗を補充しない。

| 言語 | 元の対象 | 使用/予約Group除外後の候補 | 予約数 |
|---|---|---|---|
| 英語 | Development2824 QA/Source-answered1465 | 1386 QA/1151 Group | 20 QA/20 Group |
| 日本語 | 元Calibration84 QA/84 Group | 84 QA/84 Group | 20 QA/20 Group |

Baseline使用履歴70 Fileと旧検索調整Reportを結び、計262固有の使用/検索露出IDを保持した。
失敗/開始前Journalと同一Group、日本語Previewの全予約閉包、主Development20 Groupを除外する。
旧ID欠測は既知Phase5質問の完全一致/文書Titleによる保守的な既存規則を維持し、IDを捏造しない。
記録された旧記事Preflightの独自日英2質問と英語Development質問の完全一致も0件だった。
全QA読込みはDevelopment/Calibrationに限定し、EvaluationはAssetsの既存Hash照合だけである。

元英語Calibrationの全Source-answered IDと旧225 IDの一致、元英語Calibration/Developmentと
日本語Calibration/Developmentの文書Group非重複、主20問のID/Group/Source一致を検証した。
予約各20問は主Development・既知使用/予約Groupとの重複0。
選定を再計算して同一結果と元ManifestのByte不変も確認し、追加Model Call0である。
結果は`data/manifests/phase11_bilingual_calibration_selection_v1.json`。

未使用性の主張は、明示した保存Baseline/検索使用履歴・日本語Preview閉包と主予約に対するもの。
未記録の外部利用やModel事前学習まで独立に証明した意味ではない。
将来の別Calibration Runの中断/失敗を含むJournalもUsage Inventoryへ取り込み、再び未使用へ戻さない。

## 実装と実行前に残す条件

`calibration_selection.py`と`scripts/prepare_bilingual_calibration_selection.py`を追加した。
既存のUsage Inventoryへ明示したRootを渡せるようにし、旧Developmentの既定動作は保持する。
新規6 Testを含む全561 Test（ホスト8.24秒）/Ruff成功。
行順/本文/Reference/品質/Gold差に不変、使用Group閉包、元Split/言語/重複/不足の拒否、
追加CalibrationのCall前Journal、Policy/Hash/主予約/検索露出の改変拒否を確認した。
選定だけで実行を許可せず、現行の主Development Runnerはこの別予約を実行できない。

主Developmentの全結果と両言語全匿名Label封印後のHealth/意味/品質/費用を確認してから、
次の項目を新しいCalibration結果を見る前に別Protocolへ固定する。

1. 同一候補の完全な意味診断・既知15 QA回帰と、主Developmentの日英両方の採用証拠。
2. 全予約ID/Group、元Source Split/QA Hashと分析用途、直前の新しい使用履歴照合。
3. 実Call/Token/時間の上限、Session分割、Health/意味採用・停止と修正後の扱い。
4. 初回/読解/全固定文/順序反復/一回書換え、裸拒否/失敗/不明の保存と再開追加0。
5. 両言語全匿名品質/文Labelの封印後だけ内部対応を照合する経路と、AI来歴/履歴共有の限界。
6. 言語別の有効比較/全予定分母、品質遷移、実費/採点負担、統計Adapterと最終規模の根拠。

新しい分析用途/元Splitを明示できる専用Runner/採用Guard・品質/統計Adapterは未実装。
予約のModel出力/品質採点は0で、Calibration/Gate 11の完了や最終凍結とは扱わない。
