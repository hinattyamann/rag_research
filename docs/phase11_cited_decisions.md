# Phase 11 引用必須状態を生成Schemaに表すv15候補

2026年10月22日。v14は支持判定の`evidence_ids=[]`を既存検査が拒否し、9 Callで停止した。
失敗/未試行/Raw/費用は全26 Artifactとして保存済み。今回、その失敗を後付け修復せず、
同じ既存条件を生成段階でも表す別Versionを実装した。現在は実装・契約/単体/回帰確認までで、Native実走は未実施。

## 変更と保持するもの

`thinking_json_passage_ids_v3`だけが新しいSchemaを選ぶ。旧v2のSchema/Grammarは維持する。
各固定文に対して、全てを許す独立したBooleanではなく次の3状態の選択肢を作る。

| 状態 | has_explicit_conflict | all_details_supported | 実際に与えたPassage ID |
|---|---|---|---|
| 矛盾 | true | false | 1〜2件 |
| 支持 | false | true | 1〜2件 |
| 支持不足 | false | false | 0〜2件 |

両Booleanがtrueの状態は含めない。引用IDの候補は実入力のIDを安定順に並べ、
正しいLabel/文書/Reference/GoldをSchemaへ埋め込まない。引用候補の文書順を変えてもSchema/Grammarは同じ。
全固定文の順序とID、160字の理由、引用の安定重複除去、3状態のLabel変換、Fの全分母と閾値0.7は保持する。
支持不足を空引用で表現できることも維持する。

閉じた`closing_tag_grammar` Compilerへ明示的な`anyOf`選択肢の処理を追加した。
支持/矛盾の生成では空配列へ抜けられず、理由中のIDを後から抽出する補正も行わない。
後段の既存の型/引用/妥当性検査は引き続き働き、ProviderがGrammarを破れば失敗として記録する。
新Versionは直接固定文照合・既存Boolean定義・最終Grammarを有効にしたProtocolだけに限定する。

生成時拘束はSamplingのLabel/引用分布へ影響し得る。定義を保持しても意味精度の改善を証明しないため、
全旧日英診断と旧15 QA回帰、未使用の主Development/Calibrationの確認を省略しない。

## 検証

開発依存へjsonschema 4.26.0をuvで追加し、標準Draft-7検証器でBoolean4組×引用0/1/2件を検査した。
与えていないID、件数超過、固定文ID/順序/欠落、余分なField、整数のBoolean偽装も拒否する。
Code既定の旧v2について、変更前e4af281のSchema/Grammar Hashと一致することを確認した。
従来の人工6 Caseも変更前Hashと一致する。

実際のv14失敗TaskをClient=Noneで再利用し、失敗状態・Raw/CheckpointのByte不変と追加生成0を確認した。
Task/Cache/Parserのテストでは、Native監査を明示した代替で置き換えている。
これらのテストを実GPUの強制生成の証明とは扱わず、次の実機Probeを必要とする。

新規33件を含む全734 Test（ホスト26.78秒）/Ruffに成功。
Rootの開発依存5 Packageを追加し、既存依存のVersion/ArtifactとGPU用独立Lockは変えていない。

## 次の実機確認と資源の事前登録

候補Config v15は、v14からStudy Versionと明示的なOutput Constraintだけを変更した。
日英Prompt v10、Model/Runtime/量子化、Context24576、推論4096/判定6144、Sampler/Seed、
全29例/35文/58条件・元Expected/採用/停止条件を維持する。主/予約Cal/Evaluationの新規QAは使っていない。

Native Core26+Probe1の27 Binding中5 Fileが変わったので、旧形式証拠は再利用しない。
従来の人工6 Caseに、支持/矛盾/空引用の支持不足/全3状態のUnionを敵対的な指示で確認する4 Caseを加える。
状態固定Caseは生成形式の検査であり、Research QAの正解を指定した精度検査ではない。
旧Legacy比較1件を除く全9 Strict Caseの成功を必要とする。人工Probeは推論128/出力512という専用上限を明記する。

Preregistration v7で、人工10+全意味70+通過時の全旧回帰84=新規最大164 Call/Retry0を保存した。
旧160という見積りに対し、実装した4状態検査を追加した正式な実行前の上限である。
既存9B実完了195からの累積上限359。途中失敗/未試行を保持し、後から上限/基準/Expectedを緩めない。

固定Commit/専用WTで不変資源を確認し、全70実入力の生成0確認→新Native形式→全日英意味→通過時のみ全旧15 QAの順に行う。
形式やTestの通過だけでは主/Cal採用、最終N/条件固定やGate 11通過にならない。
以前の8Bの時間見積りを9B主実走へ無条件に流用せず、採用前の実費から主実走の時間/費用を更新する。

Code Sourceが変わったので、最終Validatorの検証Manifestも新Sourceの全Test/実未達拒否へ更新してから最終固定へ渡す。
実主/Cal全実走・全採点/実証明書、最終N/条件/凍結は未了。Phase 12は実施しない。
