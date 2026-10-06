# Phase 6: Hybrid Retrievalと検索条件の固定

実施日: 2026年10月6日。ユーザー承認に基づきノートPCで実装・検証し、**Phase 6完了・Gate 6通過**。
本節の選定規則はCalibrationを実行する前に固定した。検索条件の選定・実検索・LLM接続の確認は完了した。
検索品質改善やH1/H2/H3を示す最終比較実験ではない。最終Model変更時は影響する条件を再検証する。

## 1. 統合検索と条件

Phase 4の全178,890 PassageのBM25/Embedding Indexを再利用する。Index、Corpus、Embedding Modelは変更しない。
両方式で同じ質問を検索し、Passage IDで重複をまとめる。順位は1始まりで、
`RRF(d) = sum(1 / (rrf_constant + rank_i(d)))`とする。片方で未取得の文書の寄与は0。
両方式の重みは等しく、同点はCanonical Corpusの行順で決める。Rerankerは採用しない。
[RRF原論文（Cormack et al., SIGIR 2009）](https://doi.org/10.1145/1571941.1572114)
による順位統合を使用する。RRF Scoreは正解確率・Confidenceではない。

元順位と元Scoreは取得記録へ保存し、GeneratorのPromptには渡さない。
検索入力は元質問文字列だけで、Gold/Reference/LabelはOffline測定だけに使用する。

## 2. 事前に固定したCalibration手順

- 対象は固定Title SplitのCalibration全434件中、Answerable全225件。209件のUnanswerableは
  検索正解Metricから除外し、除外数を表示する。Random Provided PassageをGoldにしない。
- Split ManifestとのHash・Record ID集合・Split Label・件数の整合を確認する。
  Seed 42とRecord IDのSHA-256による固定順を使う。Evaluationの性能は測定しない。
- 各方式の候補数は20/50/100、RRF定数は20/60/100で、9組を比較する。
  最大100件の実検索を各質問で1回ずつ実行し、Prefixで候補数を変えて同じ検索結果を再利用する。
- 平均nDCG@10を最大にする組を選ぶ。同点は平均Success@10が高い組、候補数が小さい組、
  RRF定数が60に近い組、定数が小さい組の順で決める。比較値は小数点以下12桁へ丸める。
- 最終top-kは3/5/10から選ぶ。選ばれた組のSuccess@10との差が0.05以下になる最小kを採用する。
  5ポイントの許容は小型LLMの文書量を抑えるための設計上の基準であり、統計的同等性や回答品質維持の保証ではない。
- BM25単独・Embedding単独も同じ225件で比較する。Hybridが改善するとは事前に仮定しない。
  選定規則はHybridの9組内の選択であり、単独方式への優位性を保証するものではない。

## 3. 検索Metricの区別

- `success_at_k`: k件の中にGoldが1件以上あれば1。質問単位で平均する。Dataset Guideの取得成功定義。
- `gold_recall_at_k`: 取得したGold数/全Gold数。複数Goldがある場合は上記と異なる。
- `ndcg_at_10`: Goldを関連度1、その他を0とする二値nDCG。Gold数に基づく理想順位で正規化する。
- `mrr_at_10`: 最初にGoldを取得した順位の逆数。未取得なら0。

Phase 4の既存`recall_at_5/10`は取得Goldの割合であり、過去のReportは書き換えない。
Phase 6から成功率とGold Recallを別名で記録し、評価対象・分母を明示する。
検索Metricは回答の根拠充足・独立品質Yを代用しない。

## 4. 検証と成果物

統合検索Module、Calibration CLI、固定Config/Manifest、Hybrid検索CLI、Baseline接続を実装した。
候補再利用時の時間は探索作業の時間として記録し、方式ごとの実検索Latencyとは区別する。
選定後の条件で全Calibration Answerableを再検索し、Cacheのない逐次実検索の時間・再現一致を確認する。
LLMの動作確認はPhase 5と同じ固定Development 5問で行い、Calibration/Evaluationの回答は生成しない。
Qwen2.5-3B、生成Prompt、Runtime、合計4,096/出力512/本文各512 Tokenの条件は維持する。
top-kが増えた場合も実GGUF Tokenizerで全体予算を守り、取得全文と使用Contextの切詰めを記録する。

最終Model・Embedding・Prompt・Runtime・Context予算の変更時は影響を確認し、必要なCalibrationを
新条件でやり直して別Manifestを作る。全比較方式で同じRetrieverを使う。
自己評価・Recovery、独立回答品質評価、Ubuntu/GPU再現はこのPhaseに含めない。

## 5. Calibration結果（2026-10-06）

選定条件は各方式の候補50件、RRF定数20、最終Top-10である。
9組内のnDCG@10最大を選び、Top-5からTop-10へ取得成功率が11.56ポイント増えるため、
事前規則の許容5ポイント以内には収まらずTop-10が選ばれた。

| 方式 | Success@3 | Success@5 | Success@10 | nDCG@10 | MRR@10 |
|---|---:|---:|---:|---:|---:|
| BM25 | 0.4089 | 0.5067 | 0.6267 | 0.4013 | 0.3309 |
| Embedding | 0.5911 | 0.7111 | 0.7822 | 0.5519 | 0.4783 |
| Hybrid（選定条件） | 0.5556 | 0.6667 | 0.7822 | 0.5317 | 0.4526 |

対象225件はすべてGoldが1件なので、この測定ではSuccessとGold Recallの値が一致する。
HybridのSuccess@10はEmbeddingと同じ176/225件だが、nDCG@10・MRR@10は下回った。
成功件数が同じでも、成功する質問集合が同じとは限らない。
Hybridの検索精度向上を確認した結果ではなく、事前に定義したHybrid内の選定結果として保持する。
これを理由に追加候補を後付けして同じCalibration結果と混ぜない。
検索方式の採否を変更する場合は理由と実験条件を別途明記し、全比較方式へ共通適用する。

候補再利用による9組探索は6.52秒、読込・選定後の再検索を含む全処理は13.19秒、
Sampled Peak RSSは537,116,672 Bytes（約512.23MiB）だった。
選定条件の逐次実検索はP50=0.02247秒、P95=0.02535秒、225/225件で探索時の結果と一致した。
Index/Model読込後の時間であり、質問結果のCacheは使わない。OS File Cacheの無効化は行っていない。
探索の再利用時間を各条件の独立したLatencyとは解釈しない。

保存先:

- 事前規則: `configs/phase6_calibration.yaml`
- 選定後のBaseline設定: `configs/phase6.yaml`
- 固定Report: `data/manifests/phase6_calibration_report.json`
- 固定検索条件: `data/manifests/phase6_hybrid_manifest.json`
- 質問ごとの候補順位・実測: `data/runs/phase6/calibration-initial-v1/`

固定Report/Manifest/Configは同一Byteの再利用だけを許し、異なる条件で上書きしない。
推論時にIndex、Corpus、選定条件、Protocol、Report、Hybrid実装Hashを確認する。
Git改行変換でHashが変わらないよう、該当資産は`.gitattributes`でLFへ固定する。

## 6. 実行手順

Phase 4の両IndexとPhase 5のModel/Runtimeが準備済みのRepository Rootで実行する。

```powershell
uv run --locked python scripts/calibrate_retrieval.py
uv run --locked python scripts/search_corpus.py "who does the voice of plankton from spongebob" --kind hybrid
uv run --locked python scripts/run_baseline.py "who does the voice of plankton from spongebob"
uv run --locked python scripts/run_baseline.py --smoke --limit 5
```

Baseline CLIの既定ConfigはPhase 6である。従来のEmbedding Top-5を実行する場合は
`--config configs/phase5.yaml`を指定する。検索CLIの`--top-k`による手動変更は探索用であり、
固定したBaseline条件の変更とは扱わない。

UbuntuでのLLM生成は現行Windows Runtimeのままでは実行できない。
検索再現はIndex・依存Version・数値差を検証し、Runtime/Model変更時は実験条件を別に記録する。

## 7. DevelopmentのEnd-to-End結果・Gate 6

Phase 5と同じ固定5問（Answerable 3/Unanswerable 2）で、Hybrid検索→Qwen生成→保存が全件完了した。
各質問は初回回答1回、実生成要求は計5回で、自己評価・Recovery・暗黙Retryはない。
すべて10文書を取得し、10文書をToken予算内で使用した。本文512 TokenへのPrefix制限は維持し、
文書の省略は0件。入力1,741〜3,399 Token、出力14〜314 Tokenで、合計4,096の予算を守った。

| 固定順 | Pipeline時間（秒） | 入力Token | 出力Token |
|---|---:|---:|---:|
| 1 | 110.75 | 3,399 | 314 |
| 2 | 45.06 | 1,961 | 45 |
| 3 | 41.09 | 1,741 | 61 |
| 4 | 46.80 | 1,973 | 60 |
| 5 | 41.10 | 1,901 | 14 |

読込を除く平均56.96秒、全体291.61秒、Python/Serverの合計Sampled Peak RSSは
2,714,767,360 Bytes（約2.528GiB）、PC全体の最小空きRAMは約1.663GiBだった。
100msごとの同時点RSSの和を使い、個別Peakの単純合計とは区別する。
他アプリやOS状態は制御しておらず、この5問だけで速度の一般的な結論を出さない。
Phase 5の平均22.95秒より長かったが、取得文書数と入出力長も変わっており、RRF処理だけの速度差ではない。

観察された品質の課題:

- 2問目は根拠IDの引用だけで、質問への回答がなかった。
- 4問目はGoldを取得せず、Promptで与えたIDと一致しない末尾だけの引用も出力した。
- UnanswerableのCorpus-level監査は未実施であり、回答・拒否を元Labelだけで正誤判定しない。
- これらは開発観察で、独立Failure Labelや品質Y、Hallucination率として採点していない。

`status=ok`は実行成功を表す。Goldは生成後のOffline確認へ分離し、品質Labelは`null`のままである。
質問CLIも声優の例で検証し、Hybridの重複なし10件と元順位を取得できた。
全135 Tests成功・Skipなし（22.95秒）、ruff問題なし。終了後のllama-server Processは0件。

Runは`data/runs/phase6/development-five-v1/`、実測集計とHashは
`data/manifests/phase6_smoke_report.json`、検索CLI例は`data/runs/phase6/search-example.json`に保存した。
共通Corpus・両Index・Split・Phase 5のModel/Runtime/Prompt条件を維持し、Gate 6を通過した。

## 8. 次の工程

Phase 7で固定Retrieverを基にNormal/Unanswerable/Retrieval Failure/Distractorの評価用Datasetを
人手監査して固定する。自己評価・Recoveryの実装とは区別し、Evaluation成績で条件を調整しない。
研究室PCはPhase 6〜7の間にUbuntu用実行基盤を整備し、最終Modelを使うPhase 8の正式な
Calibration前までに動作確認する。現在のWindows用LLM取得・起動処理はUbuntu/GPU未対応である。
