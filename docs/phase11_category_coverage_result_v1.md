# Phase 11 v14の引用ID欠落による停止と次の修正対象

2026年10月22日。固定f92298bのv14/session54441は終了済み。
旧全29例/35文/58条件・最大70 Callを計画したが、2条件目の子判定で既存の出力検査が失敗し、
元の停止規則で9 Call・1条件成功/1条件エラー・56条件未試行となった。
新しい旧15 QA回帰84 Call、主/予約Calibration/Evaluationは実行していない。

## 実際の失敗

`known-council-reversed.claims/c2.json`は、局所c1で次を返した。

```json
{"has_explicit_conflict": false, "all_details_supported": true, "evidence_ids": []}
```

理由文には実在する`838915949_1389-1678`を記し、思考内でもそのIDを引用する予定としていたが、
最終`evidence_ids`が空だった。既存の`Supported/contradicted needs evidence`検査が正しく拒否した。
Rawを修正したり、理由文からIDを後付けしたり、支持不足へ読み替えて継続したりしない。

当該入力3339/出力4211 Token、Context24576/最大出力6144。
推論予算監査は4105 Token（予算4096とRuntime強制終了Message10等の許容内）、
Prefill・終了Marker・最終Grammarの実設定は確認済み。出力枠を増やす根拠となる上限到達ではない。
この失敗を意味診断や新候補の採用成功と扱わない。

## 保存した費用・未試行・監査

- Native実呼出し9、入力29988/出力31378 Token、Task秒和518.200587秒。未知費用なし。
- 全4 Criticalのうち実施2、完全一致1。両言語の人工54条件は全て未試行。
  失敗した逆順条件内にも5固定文の未試行を保持し、部分的な1文の支持からFを補完しない。
- 再開監査session64692も終了。95 Source Hash、2集計/全9子Taskの元入力・全草稿・全固定文・費用を照合し、
  再開16 File不変・追加Call/Server0。
- 監査2 Receipt込みの原本18 Fileを同一Byteで正規保存。8有効最終出力と1不正最終ObjectをAI確認し、
  追加記録1+準備/Preflight7を含む26 Artifactを`phase11_category_coverage_result_v1.json`へHashで結んだ。
  human_reviewed=false、厳密AI Model ID不明、履歴共有を維持する。
- 親終了時186+今回9で9B実完了累積195。形式証拠再利用で新しい形式6 Callを使った記録ではない。

正規Run: `data/runs/semantic_diagnostics/phase11-qwen35-9b-direct-v14`。
旧Run・全Expected/採用基準・未試行・Sourceを保持する。
開始時の`phase11_category_coverage_launch_v1.json`は当時の記録として変更せず、終了は結果Manifestで示す。

## 次に実装する内容（未実施）

既存`thinking_json_passage_ids_v2`のSchemaは両Booleanを自由に選べ、全状態で空の引用配列を許している。
後段の妥当性検査との間に表現上の差がある。出力検査を緩めず、別Versionで同じ必須条件を生成文法にも表す。

1. 旧v2を保持し、新VersionのSchemaを支持/矛盾/支持不足の互いに重ならない3状態で定義する。
   支持/矛盾は与えた実Passage IDを少なくとも1件、支持不足は0〜2件を許す。
   両Booleanが同時trueとなる状態は生成しない。真偽の正解をSchemaに埋め込まない。
2. 閉じたGrammar Compilerに必要な選択肢の処理を追加し、旧Schemaの生成物を保持する。
   どの文書順でもSchema/Grammarは同一で、引用候補はIDの安定順にする。
3. 空引用の支持/矛盾と両trueの拒否、支持不足の空引用許可、全単位/ID/順序/旧v2の回帰を確認する。
4. Code/Coreが変わるため旧Native形式証拠を再利用しない。新候補の事前登録・固定WTで形式・全実入力生成0を確認し、
   全旧日英診断/既知15 QA回帰を再実行する。拘束されたSamplingはLabel分布にも影響し得るため、意味妥当性の改善を仮定しない。

新VersionのCode/Config/事前登録・形式実走はまだ行っていない。
新たな形式6+意味70+全旧回帰84=最大160 Callという見積りは次の事前登録候補で、現在の実施記録ではない。
主/Cal採用、全実走・採点/証明、最終N/条件・凍結は未了。Gate 11未通過、Phase 12未実施。
