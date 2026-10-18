# Phase 8: 固定回答に対する根拠順序別の自己評価

本書はPhase 8実施時点の記録。2026年10月19日に[Phase 9の一回書換え・独立品質入出力](phase9_answer_rewrite.md)を実装した。
現在の次作業は3候補の人手採点とGate 9照合である。以下のPhase 9未実装という記載は当時の状態を示す。

## 1. この段階で動かす処理

```text
保存済みBaseline回答（Development）
  → 質問・回答・実使用根拠をHash付きTraceへ固定
  → 回答だけからClaimを一度抽出して保存
  → 元/逆/Shuffle 3通り + 元順序の合計5回の反復
  → Claimごとの支持/矛盾/未支持を検証
  → Fと採用/書換え要求、採点不能を保存
```

初回回答を再生成せず、実際の書換えも行わない。`rewrite_requested`はPhase 9へ渡す判断である。
並べ替えるのはJudge入力のdocuments配列だけ。Question/Answer/Claimsと各文書のID/Title/Textを固定する。
元の`used_context`をそのまま使い、検索・Packing・再切詰めは行わない。
全入力を実Tokenizerで計測し、入力+出力予約が8,192を超えれば`input_overflow`とする。

配置:

| 配置 | 実装した責務 |
|---|---|
| `src/rag_research/experiments/frozen_trace.py` | 推論FieldのWhitelist、Trace/回答/文書Hash、文書内容の同一性 |
| `src/rag_research/evaluation/claims.py` | ClaimのJSON/ID/本文検証 |
| `src/rag_research/evaluation/order.py` | 元/逆/Shuffle、同一順序反復、重複順序・共通初回・実行順 |
| `src/rag_research/evaluation/judge.py` | 全ClaimのLabel/根拠ID/原文引用一致を検証、Fを計算 |
| `src/rag_research/evaluation/schema.py` | JSON構造と出典引用候補の制約。文書順序から独立した同一Schema |
| `src/rag_research/evaluation/tasks.py` | 実Model呼出し、全文Promptと応答、入力予算、失敗・Token/時間 |
| `src/rag_research/experiments/decisions.py` | 閾値等号、採用/書換え要求/採点不能Fallback |
| `src/rag_research/experiments/order_runner.py` | Development限定、固定条件Manifest、実行と再開、記述的集計 |
| `src/rag_research/experiments/storage.py` | 原子的Checkpoint、Hash照合、OSが解放する排他Lock |
| `scripts/run_order_evaluation.py` | 実評価CLI |
| `scripts/render_order_example.py` | 実入力/出力を読む説明用Markdown。盲検採点Exportではない |

## 2. 順序と反復

原則、各問に異なる5順序と同一順序の合計5反復を用意する。
元順序の初回は両群で共有するので、Judgeの実Completionは9回/問。
文書が1件等で順序が重複すれば、順序群の重複だけを除きaliasを保存する。同一順序の反復は省略しない。
反復ごとに実Modelを呼び出し、`cache_prompt=false`、同じ温度0/Seed 42を使用する。

Shuffleの乱数Seedはcanonical JSONの`[shuffle_seed, record_id]`のSHA-256を整数化する。
同じ乱数器でShuffle 1〜3を順に生成する。実行順は別の`[execution_order_seed, record_id]`で無作為化する。
表の表示順と実際の呼出し順は異なる。実行順はManifest内の`plan.trials`へ保存する。

## 3. 採点と失敗

- Fは`supported`数/固定Claim数。Modelが申告したScoreは受理しない。
- F>=0.7は`accept`、F<0.7は`rewrite`。後者のactionは`rewrite_requested`。
- ClaimなしはF=null、`not_applicable`。初回回答保持は品質上の採用とは別のFallback。
- Claim抽出が空でも「本当に事実がない」とは保証しない。空抽出を含め意味上の妥当性を点検する。
- JSON不正、重複Key、Claim欠損/重複/順序違い、未知Label/ID、本文と不一致の引用、出力上限はエラー。
- 引用は空白・記号を含む原文の連続部分文字列と一致させ、曖昧な一致へ自動修正しない。
- 構造と引用が正しくても、意味上の支持、Claimの網羅性、質問への適合性を保証しない。
- 現行v5はJSON Schema制約付きDecoderを使用する。評価する対象はこの制約付きJudgeであり、自由出力Judge全般への一般化はしない。
- 自動再試行は0。失敗を0点や満点へ変換せず、失敗した試行も残す。

各群の`valid_trials/valid_pairs/disagreeing_pairs`は質問内の記述的確認用。
失敗やClaimなしを判断一致の分母に入れない。少数のSmokeから研究上の反転率や有意差を主張しない。

### v5の出力制約と公平性

`output_constraints: json_schema_source_spans_bounded_v2`を明示する。
Claim抽出はJSONオブジェクト/配列/Field型を制約し、IDの連続性や意味は後で検証する。
Judgeは文書をPassage IDでソートしてから、IDと引用候補を対応させたJSON Schemaを作る。
引用候補は本文中の`.`/`!`/`?`/`;`後の空白で区切った各区間、隣接2区間、全文をstripした連続部分文字列である。
引用の本文中の空白・引用記号を変更しない。これは言語学的な文分割やGold根拠抽出ではない。
文書本文はJudge入力に全て残り、候補を作るためにContextを切り捨てることはない。
Claimごとの引用は最大2件、理由は最大200文字にする。無制限の引用配列で同じ引用を繰り返す不具合を防ぐためである。
複数箇所の支持を示す能力に上限があるので、この引用予算も本実験前の監査対象とする。
同じ引用を2件返しても独立した支持を2票と数えず、Fは各ClaimのLabelだけから計算する。

全順序・反復のSchemaは同一で、Task JSONの`json_schema/json_schema_sha256`へ保存する。
入力PromptだけでなくDecoder制約まで変わる交絡を防ぐ。Labelや意味上の正解は制約に埋め込まない。
制約は「その文字列を実在する出典から引用できる」ことを助けるだけで、支持の正しさを保証しない。
SchemaのID順・候補粒度は一定の追加条件であり、後の比較で隠さない。
将来別の出力制約を比較する場合は、Development/CalibrationでProtocolを分ける。

固定Runtimeの[/completion仕様](https://github.com/ggml-org/llama.cpp/blob/b11433/tools/server/README.md)と
[Grammarの制限](https://github.com/ggml-org/llama.cpp/blob/b11433/grammars/README.md)を確認した。
`prefixItems`は使わず、固定Runtimeの[公式Test](https://github.com/ggml-org/llama.cpp/blob/b11433/tests/test-json-schema-to-grammar.cpp)で
対応を確認したDraft-7形式のtuple itemsでClaim順を固定する。Python側でも順序・全件対応を検証する。

## 4. 保存と再開

Runごとに`manifest.json`、`report.json`、Session/Server Logを保存する。
質問ごとのDirectoryに`trace.json`、`claims.json`、各Trial JSON、`summary.json`を置く。
Task JSONには入力Messages・実Chat Template適用後Prompt・Token ID列・Raw Response・検証結果・費用を残す。
最終応答を残していない中断Journalは`interrupted_unknown_outcome`として保持し、自動で再抽選しない。
その場合の費用は不完全として示す。別の成功Runへ失敗を置き換えない。

再開時はProtocol/Prompt/入力QA/Baseline/Model/Runtime/実装SourceのHashを照合し、
異なれば停止する。同じ条件なら未実施Taskだけを呼び、成功・失敗とも既存結果を再利用する。
同一Promptの別反復には別Trial IDがあるので、同一Prompt Cacheで反復を潰すことはない。
SourceやPromptを修正した後は別Runを使う。Runの同時実行はDirectory単位のLockで拒否する。

費用はこの段階では補助Taskの実収集Calls/Token/時間。初回生成の費用は元Baseline Runへ保持している。
Phase 9以降の各方式の運用経路費用・修復候補の共用補正は未実装。

## 5. 実行手順

Repository Rootで実行する。Model/Runtimeは既存の固定ローカル資産を使い、外部APIやDownloadを使わない。

```powershell
uv run --locked python scripts/run_order_evaluation.py --config configs/order_phase8_v5.yaml --output-dir data/runs/order_sensitivity/your-phase8-run --record-id clapnq:c508d78:train:-2421097959159398117:answerable --record-id clapnq:c508d78:train:-996127241617807228:answerable
uv run --locked python scripts/render_order_example.py --run-dir data/runs/order_sensitivity/your-phase8-run --output data/runs/order_sensitivity/your-phase8-run/examples.md
uv run --locked pytest
uv run --locked ruff check .
```

既定BaselineはPhase 6の保存済み5問。Development Answerable 3問だけを使用する。
上の例はPhase 7で既に確認した2問を`--record-id`で指定する。これは実装確認用の選定で、研究の標本抽出ではない。
任意の`--baseline-answers`もDevelopment所属、質問一致、元Runの設定/Model/Prompt/QA Hashを確認する。
既存Phase 6の5問は過去の固定Manifestの回答Hashも照合する。
このCLIは少数の開発用動作確認で、未見20〜30問のPilot選定を実装したものではない。
既に確認した例を後の未見Pilotに数えない。Calibration/Evaluationは読み込まない。

## 6. 指示文の開発履歴

Phase 7の`configs/order_pilot.yaml`と`configs/order_prompts.yaml`は履歴として維持する。
v1では文章のある回答から空のClaim列を返す問題と、Judgeが原文の引用記号・空白を整形する問題があった。
v2で指示を追記したが、空のbare arrayや引用不一致が残ったため、途中で開発Runを終了し`aborted.json`へ記録した。
v3で完全なJSONの具体例を加え、引用だけ/事実文の2例は期待する形で抽出したが、元順序JudgeのJSONが不正だった。
v4でJSON形式と引用候補のDecoder制約を追加したが、引用配列で同じ引用を繰り返して出力上限に達した。
v5で引用数・理由長の上限と固定Claim順を加えた。現行は`configs/order_phase8_v5.yaml`と
`configs/order_prompts_phase8_v5.yaml`。v1〜v4の指示文・Raw出力・実装Source Snapshotを残している。
検索/初回回答/根拠本文/閾値/順序数/反復数/Model条件を維持し、出力制約の差をVersionに明示する。
判断反転を増やすための調整ではなく、抽出・根拠引用の妥当性を確認する開発上の修正である。
Developmentでの指示文修正なので、本実験の凍結を済ませたとは扱わない。

## 7. 実走結果とGate 8

2026年10月18日にGate 8を通過した。現行Runは
`data/runs/order_sensitivity/phase8-development-two-v5/`。
`examples.md`は全順序とRaw JSONを並べた説明用Artifact、`report.json`は集計、
`validation.json`は保存・公平性・再開の監査。小さい固定情報は`data/manifests/phase8_order_manifest.json`へ記録する。

### 実例1: 事実文を含むPradaの回答

質問は`what does prada mean in the devil wears prada`。
最初の回答を固定して次の2主張を一度だけ抽出した（以下は内容の日本語要約）。

- c1: 大半の市場で作品の題名が現地語に翻訳された。
- c2: イタリアでは題名がIl diavolo veste Pradaで、おおよそThe devil wears Pradaという意味である。

根拠10件を元の順にA〜Jと略記する。翻訳の記述があるBは`834292919_54767-55759`。
実際の入力にはA〜Jへの振り直しをせず、元のID/Title/Textを使用した。

| 条件 | 提示順序 | Bの位置 | F | 判断 |
|---|---|---:|---:|---|
| original | A B C D E F G H I J | 2 | 1.0 | accept |
| reversed | J I H G F E D C B A | 9 | 1.0 | accept |
| shuffle_1 | F J I A G E D C H B | 10 | 1.0 | accept |
| shuffle_2 | D F H E J C A B I G | 8 | 1.0 | accept |
| shuffle_3 | F H C D E B G I J A | 6 | 1.0 | accept |

元順序の5回（original+repeat_2〜5）も全てF=1.0/acceptだった。
両群の共通初回を一回と数え、実Judge Completionは9回。
両群各5有効Trial/10有効ペア、判断不一致はどちらも0ペアだった。
有効な質問は1件であり、順序効果の不存在を示す結果として扱わない。

**意味上の監査で残った問題:** c1はsupportedとされたが、引用箇所は「英語を使用するか、現地語へ翻訳する」
という選択肢であり、「大半が翻訳された」までを支持しているとは確認できない。
根拠本文を全10件点検しても、この割合を補う記述は見当たらなかった。
したがって少なくともc1には過大支持の問題がある。これは通常のJudge誤りの例で、順序による誤りの証拠ではない。
安定性・引用一致・JSON形式が、正しさを保証しないことが実装確認でも分かった。
この所見はClaimの開発監査であり、盲検化した回答全体の品質Yを確定したものではない。

### 実例2: 引用IDだけの回答

質問は`who proposed that atoms are the basic units of matter`。
最初の回答は`[845305320_4200-4964] [803775631_38239-38869]`のみだった。
Modelの実応答は`{"claims":[]}`で、F=null、`not_applicable/unscorable`、`keep_initial_fallback`となった。
Judgeは呼び出さず、予定Trialを採点不能として残す。これは満点や品質上の採用ではない。

### 呼出し・監査・検証範囲

- 抽出2回+Judge 9回=11 Completion。v5の構造・引用検証エラー0。
- 質問/回答/Claim/文書集合と本文・Title/IDが全条件で同一。異なる順序は5通り。
- 実Judge Prompt Hashは5種類、Decoder Schemaは全9回で同一。元順序は同じPromptで実際に5回評価。
- 最大の入力+出力予約は3,997 Tokenで、全Taskが8,192以内。本文の再切詰め0。
- 再開の追加Completionは0回。全11 Taskファイルは再開前後でByte単位に同一。
- 全182 Tests成功・Skip 0（31.98秒）、ruff成功。終了後のllama-serverは0件。
- Judgeの実測は平均96.52秒、最小86.05/最大116.55秒。開発中の他の検証を並行した値で、性能比較には使わない。
- 実際の回答書換え、独立品質Y、新規20〜30問Pilot、Calibration/本実験は未実施。
- 初期の長い別回答のClaim見落としはv1で確認したが、v5の対象2件には含めておらず、解消を主張しない。

開発途中のRunはv1三件が完走、v2/v4が中断、v3が元順序までの事前確認。
途中で中断したTaskの費用・応答は不完全として記録し、v5の11 Callsを開発全体の費用とは呼ばない。
Gate 8は計測処理の完成と少数例の動作確認。Judgeの精度確立や研究仮説の実証とは区別する。
**Phase 8終了時点ではPhase 1〜8完了、次はPhase 9だった。現状は[Phase 9記録](phase9_answer_rewrite.md)による。**
