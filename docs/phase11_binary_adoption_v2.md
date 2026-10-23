# Phase 11 支持対非支持の採用基準v2

2026-10-23。基準IDは`support-binary-v2`。設計理由は[見直し方針](phase11_evaluator_review_policy_v1.md)。
旧Version（Version欄なしを含む`three-label-v1`）のCritical完全一致・誤支持0の経路と、全旧不採用を保存する。
新基準の実装・事前登録であり、候補の実採用やGate11通過ではない。

三分類Expected/Raw/理由を変更せず、S対C/NSを派生集計する。支持Recallと非支持Specificityが各0.90以上を主採用とし、
C↔NSの誤りは三分類精度と取り違え数に残す。F、閾値0.7、裸拒否一回書換え、順序/反復設計は変更しない。
反転率、効果の有無、有意差、品質改善は採否に使わない。

Known全体とMain/Calの各言語に、同じ被覆下限を**新出力を見る前に**適用する。

| 被覆 | 下限 |
|---|---:|
| Expected Sの異なる固定文 | 10 |
| Expected C/NSの異なる固定文 | 5 |
| Sを含む異なるQA/文書Group | 3 |
| C/NSを含む異なるQA/文書Group | 3 |

異なる固定文はGroup/QA/Claimの組で数え、同じ文の元/逆/反復を増やしても被覆は増えない。
既知15 QAは元の異なるTitle選定に基づきrecord_idでGroupを識別し、主/Calは選定Manifestのdocument_group_idを使う。
10正例/5負例と各3 Groupは、片側クラスや一つのQAだけの検証を防ぐ最低限の実行可能性基準であり、精度保証や検出力計算ではない。
非支持5〜9文では0.90の離散性により少数の誤りでも通らない場合がある。分母0はnull、不足時は不通過とし補充しない。
各順序/反復は意味誤りの分母には残し、CIは同じQA/Groupを一塊で10000回・Seed42のBootstrapにする。
クラス欠落の再標本は有効回数/欠落回数を報告する。相関した試行を独立二項標本とは扱わない。

Knownは元15 QA/42文/30条件/84 Callの全回帰を一度行う。v2ではCritical誤Labelだけで正例対照を未実施にせず、
全結果とクラス指標で採否を決める。Runtime/JSON/入力超過/未知は直ちに停止し、全体率はnull、未試行・不明費用を保持する。
旧v1は従来どおりCritical不一致で拡大しない。全Expected、曖昧5文、裸拒否8問を保存する。

`semantic_adoption.py`をKnown・Main匿名封印後・Cal・最終Validatorへ接続した。
KnownのPlan/Manifest/Report、MainのPolicy/Config、CalのRules/Config、最終Decisions/主/Cal採点のVersionが異なれば拒否する。
Inference Core/Prompt/Samplerは不変で、既存の温度0.2の全意味70 Call・Native形式証拠を再利用できる。
旧結果を新Versionの実験結果へ書換えず、新鮮なKnown v10の結果を必須にする。

追加開発の登録は`data/manifests/phase11_review_development_preregistration_v1.json`。
旧851/未知2/未使用69・42/42/81/42を保存し、候補最大1個・新188試行/Task秒和14400・診断24内数の上限を引き継ぐ。
今回実行へ割り当てるのはSmoke2+Known84=86回。102回は未割当で自動使用しない。
Native全段階の壁時計時間（起動/生成0/処理を含む）を合計14400秒以内に制限する保守的運用でTask秒和を抑える。
外側Timeoutは15秒の終了猶予を確保し、停止後は未知を保全・生成0の監査だけを行う。

Main各20/予約Cal各20、各言語1660 Call/段階5新規QA/全固定文の原子予約、完全比較各10 QA以上、
両言語の全候補品質/Expected封印、品質・判断・費用の照合、最終N/資源/Manifestの実証拠は引き続き必要。
新基準による妥協範囲と三分類誤り、単独AI採点、少数観測の一般化限界を最終報告へ残す。

CUDA読取り調査では、旧v9の`llama-server` PID198938に2026-10-23 07:42:58 UTC（16:42:58 JST）の
RC Watchdog/Xid8を確認した。Xid8は「GPU停止」、初動はアプリ再起動と分類されるが、Xidだけで根本原因は決まらない。
[NVIDIA Xid Catalog](https://docs.nvidia.com/deploy/xid-errors/analyzing-xid-catalog.html)、
[NVIDIAの解釈上の注意](https://docs.nvidia.com/deploy/xid-errors/introduction.html)。
同日07:27:15 UTCにNVRM割当失敗もあるが、時間差があり停止の直接原因とは断定しない。
ホストではGPUを認識し、sandbox内の`/dev/nvidia*`非公開による接続失敗と区別した。
Driver/OS設定/Reset/再起動は実施せず、同じ条件の新プロセスで生成0→2 Smoke→完全回帰の順に検証する。

2026-10-23 18:03 JST追記: 固定9bfe78dの生成0で全84入力/最大3927 Token/全CUDAに通過。
Smokeの初回Zidane c1は正常終了（3793入力/4246出力/86.475462 Task秒）。
2回目の暖鋒c2はGlobal c2を単独で渡したSmokeコードの連番検証で、Native送信・Task Journal作成の前に停止した。
これはRuntime/意味不適合ではなくオーケストレーションの実装ミス。停止Run/Log/最初の成功/元Ledgerを保全し、
`phase11_review_smoke_recovery_v1.json`に消費122.924029壁秒・新Native1/未知0と未送信の証拠を固定した。
元と同じ全文/文書のc2を通常のclaimwiseと同じ局所c1へ写して、未送信分1回だけ新Commit/新Runで継続する。
成功済み初回を再生成せず、全Src91 File・候補/Prompt/Sampler/基準と188/14400/86の上限を維持する。
訂正用の共有Ledgerも元消費秒を差し引く。新鮮なKnown84の実採用は引き続き未了。

その後、903f4cfをCommit/通常Push・Remote一致し、新固定WTで未送信Smoke1回を正常終了した。
元成功1+新成功1=2 Call/未知0、入力7197/出力8500 Token、Task秒和173.264229秒。
全2 Native Schema/Sampler/全回帰と同じ全文Payloadを独立に照合し、12 Raw Artifactを正規保存した。
正本は`data/manifests/phase11_binary_smoke_result_v1.json`。共有消費225.012950壁秒を保持し、
同固定WTの新Known v10/84 Callを実行中。Smoke成功を完全回帰採用・Runtime根本原因解決とは扱わない。
