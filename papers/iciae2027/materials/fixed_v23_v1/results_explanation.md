# 結果の読み方・公開表への対応

主指標はQAごとのO=順序群の全判断ペア不一致率、R=同順序反復群の同率、D=O-R。必要な全試行が有効なQAだけでDを等重み平均する。qa_summaryとinputsのstatistical_comparisonから再確認できる。文/ペア/Callは独立QAではない。

主比較はMain/en16/20・ja13/20、Cal/en16/20・ja12/20。平均増分は順に0.0875、0.04615384615384615、0.125、0.08333333333333333。95%区間は[0,0.1875]、[0,0.13846153846153844]、[0.05,0.225]、[0,0.20000000000000004]。日英差はMain -0.041346153846153845、Cal -0.04166666666666667で区間は双方0を含む。

CIは元のNumPy2.5.3・Seed42・文書Group Bootstrap10000回・linear percentileによる結果をByte不変で保持する。標準ライブラリ検証器は点推定・Group/分母とCIの元コピー一致を確認し、別RNGでCIを生成して同一実装と主張しない。

順序で判断が分かれたQAはMain/en3/16・ja1/13、Cal/en5/16・ja2/12。同順序反復は比較可能QAの全てで0。対象外23 QAはstandalone refusal/no_claims22件と初回生成失敗1件であり、順序効果0として補完しない。

品質Y=1件数は修復なし/元順序評価/常時書換えの順にMain/en9/12/14、Main/ja5/10/14、Cal/en6/9/10、Cal/ja4/6/9（各20選定）。A/Bの改善・悪化は対応のある品質遷移で確認し、不明Yはunknownのまま保持する。policy_outcomesにmissed_improvement/harmful_rewriteとQA内の選択/費用を保持した。単に判断が反転しただけで品質が変わったと解釈しない。

公開quality_and_operational_cost.csvのbaseline_missingは、実装上20-そのrouteの記録数である。shuffle_2等では重複順列の省略もここに含まれ、初回生成失敗件数そのものではない。元CSVを直さず、この資料のpolicy_state=omitted_duplicate_order_aliasとinitial_unavailableで区別する。省略Trialを新規実行したことにせず、alias_ofで元対応を残す。

collection_cost.csvは全収集の試行、policy_outcomesは単一方策を運用した場合の保存済み経路費用、annotation_cost.jsonは外部AI採点の費用で、相互加算・混同しない。保存秒の和は実測応答時間ではなく、外的取消の最終Token不明は既知分の下限。意味監査は同じ固定文×試行の反復を含み、人手正解の独立標本精度ではない。

閾値感度は事前の0.5/0.6/0.7/0.8/0.9で全て同じ元結果を再判定した補助分析。閾値を選び直していない。図表と詳細値は[published_results](published_results/)・[analysis](analysis/)を参照する。
