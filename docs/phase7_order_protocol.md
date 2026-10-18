# Phase 7: 順序感度研究の開発用Protocol

作成日: 2026年10月18日。Study Version: `order-pilot-v1`。
本書はPhase 8〜10を実装・検証するための初期条件であり、Phase 11の本実験凍結ではない。
研究目的は[研究計画](rag_research_plan.md)、全工程は[ロードマップ](research_roadmap.md)による。

## 1. 今回できたものと、まだできていないもの

| 成果物 | 状態 |
|---|---|
| `configs/order_pilot.yaml` | 作成済み。対象・Model・予算・順序/反復・判断・失敗処理を指定 |
| `configs/order_prompts.yaml` | 作成済み。Claim抽出、根拠検証、一回書換えの英語指示文 |
| [独立品質の基準と練習例](order_quality_rubric.md) | 作成済み。2例はDevelopmentの既存Runから確認した基準案で、人手Labelはpending |
| `scripts/check_order_protocol.py` | 作成済み。Configと推論入力の境界、実Tokenizerによる予算を確認するCLI |
| Phase 8の評価器・実Trial実行 | 未実装。LLMの採点やClaim抽出はまだ実行していない |
| Phase 9の書換え・品質Export/Import | 未実装。新しい回答候補はまだ生成していない |
| 20〜30問のPilot/最終Evaluation | 未実施 |

## 2. 最初に確かめる研究上の問題

元の検索順位順を基準条件として必ず残す。順序を変えた結果だけで実運用上の害を結論づけない。
通常順位での評価の妥当性と修復結果を独立品質で点検し、順序操作を感度の切分けに使う。
関連性の順位と回答の支持は別であり、順序で判断が変わることと誤判断であることも区別する。
文章内の文順は変えない。文書間の照応や自然な論述順が重要な例では、
順序を変えても意味が同じという前提が妥当か監査する。単なるScore上昇を正しい評価と認めない。

根拠性Metricの文書順序感度自体は、[Wan et al., NAACL 2025](https://aclanthology.org/2025.naacl-long.442/)でも扱われている。
本研究では通常順位の判断、同一順序の対照、一回修復の品質・費用と、条件別の影響へ問いを絞る。
これで新規性が保証されたとは扱わない。

## 3. 対象Dataと選定Rule

- Sourceは既存CLAPNQ固定Revision・Title単位Split・Corpus。既存ManifestとBaseline条件を上書きしない。
- Phase 7の入力確認は既存Development SmokeのAnswerable 3問を使用した。新規Pilotではない。
- 基準作成用の2例はConfigへIDを保存し、独立品質基準で理由を説明した。
- Phase 10の新規PilotはDevelopment Answerableから最大30問を出発目標とする。
  既存Preflight Runの全Record IDと、基準作成用IDを除外してから選ぶ。
- 選定KeyはUTF-8文字列`42:{record_id}`のSHA-256の16進表現、昇順、同点はRecord ID昇順。
  Model出力や自己評価の結果を見る前にIDと選定Manifestを固定する。追加除外・不足は理由を記録する。
- 同一Titleの依存を記録し、反復や順序を独立QAとして数えない。
- Calibration/Evaluationは今回読んだり生成したりしない。対象選定に使う正解MetadataはInferenceから外す。

## 4. 指示文とModelへの入力境界

| Task | 入力Field | 出力 |
|---|---|---|
| `extract_claims` | answerのみ | Claim IDと本文のJSON。引用だけ/拒否等は空配列 |
| `verify_claims` | question、answer、固定claims、documents | Claim別Label、根拠ID/引用、短い理由のJSON |
| `rewrite_answer` | question、answer、元順序documents | 英語の修正回答全文と引用ID |

documentsはPassage ID・Title・本文のみ。Gold/Reference/Answerability/Y/評価条件名を入れない。
検証のLabelはsupported/contradicted/not_supported。数値Fと判断はプログラムで算出する。
空ClaimのFはnullで、満点としない。書換えにはJudgeのScore/理由/順序変更したContextを渡さない。
独立品質の採点ではJudgeのClaim分解や理由も表示しない。

## 5. Runtime・Token予算の決定

初回Baselineは既存のContext 4,096/最大出力512を維持する。
補助Taskは同じ固定Qwen2.5-3B Q4_K_MとWindows CPU Runtimeを使い、次の予算を初期採用する。

| Task | 補助RuntimeのContext | 最大出力予約 |
|---|---:|---:|
| Claim抽出 | 8,192 | 1,024 |
| 根拠検証 | 8,192 | 1,536 |
| 一回書換え | 8,192 | 512 |

温度0、Seed 42、6 Threads、batch 128、repackなし。外部LLM APIは使わない。
変更理由: 保存済みAnswerable 3問に対する21入力Probeで、入力+出力予約が最大5,748 Tokenとなり、
6 Probeが4,096を超えた。8,192では全Probeが収まり、実際のServer Contextも8,192だった。
初回回答・採点指示を加えても同じ本文を削らず渡すための補助予算であり、
初回の検索・生成・根拠本文は変更していない。Task/条件間で共通に適用し費用へ計上する。

この確認では回答全体を一つの仮ClaimとしてToken計測した。実際のClaim抽出出力長や、
全QA/全順序の収まりを保証しない。Phase 8で実Claimと実Promptを都度計測し、超過時は本文を切らず記録する。
Decode成功、採点精度、速度の一般性を検証した結果でもない。

## 6. 順序・反復と起動判断

初期の順序群は元順序、逆順、Shuffle 3通り。同一順序群は元順序の合計5回。
共通初回を共有し、原則9回/問/評価器の実呼出しとする。Shuffle Seed 42、実行順Seed 43。
全Trialの生成Seedは同じ42。温度0でも同一入力反復を測る。
文書が少なく異なる順序が5種類ない場合、有効な異なる順序数を保存し、同じ順序を別順序として水増ししない。
同一Promptでも反復は実呼出しを行い、Prompt Hashだけで結果をCacheしない。

F=supported数/固定Claim数、初期τ=0.7。F>=τは初回採用、F<τは固定書換え候補を選ぶ。
初回Claimは1回抽出して共用。書換えも元順序Contextと初回回答から1回作って共用する。
事前の閾値感度候補は0.5/0.6/0.7/0.8/0.9。本実験前の最終値の固定はPhase 11で行う。

## 7. 失敗・品質・分母

自動再試行は初期0。不正JSON、未知ID、Claim欠損、入力超過、timeout等を有効Scoreへ変換しない。
Claimなしはnot_applicable、処理失敗はerrorと分け、採点不能の経路は初回保持Fallbackとする。
書換え失敗時も初回を保持しrewrite_failedを記録する。採用の正解認定とは区別する。
既存成功結果を再抽選せず、未実施Trialだけ再開する。Hash差なら上書きせず停止する。

主要比較は両群が有効な共通QAの質問内ペア不一致の差。
元順序での判定と独立Yの対応、四遷移、悪化、改善見逃し、費用を主研究として確認する。
全対象/有効Trial/共通QA/品質確定/未知の分母を明記する。品質未知の感度分析も示す。
実験収集、運用経路、Offline採点の費用を分ける。共用候補も各経路へ必要な費用を計上する。

## 8. 実行できる確認コマンドと成果物

Repository Rootで次を実行する。これはModelのToken計測で、採点・回答生成・Pilot実行ではない。

```powershell
uv run --locked python scripts/check_order_protocol.py --output-dir data/runs/phase7/your-preflight-run
uv run --locked pytest
uv run --locked ruff check .
```

出力先は新規Directoryにする。既存の報告やServer Logを上書きしない。
今回の最終Preflightは`data/runs/phase7/protocol-preflight-v2/report.json`へ保存する。
Protocol資産・ReportのHashと要約は`data/manifests/phase7_protocol_manifest.json`で管理する。
Raw Runと本文はGitへ追加しない。

確認結果: 全142 Tests成功・Skipなし、`uv run --locked ruff check .`は問題なし。
新規7 Testは入力境界と比較条件の検証であり、評価器の採点精度を検証した数ではない。

## 9. Gate 7と次の作業

Gate 7の対象は専用指示文・設定・基準案・入力境界・Runtime/予算の確認である。
LLMが正しくClaim抽出/採点できること、書換えで改善することは含めず、Phase 8以降で検証する。
次は固定TraceとClaim抽出・Judge実行・順序と反復の実記録を実装する。
既に確認した練習例で少数の実応答を点検し、その後にPhase 9の固定書換えと品質入出力へ進む。
