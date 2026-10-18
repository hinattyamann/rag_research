# Phase 9: 一回書換えと独立品質確認

更新日: 2026年10月19日。研究計画7.3・実装計画8.3に対応する。

後続の方針更新: ユーザーが開発・本番ともAI採点を選択したため、[AI品質Protocol](ai_quality_protocol.md)で
Gate 9をAI代行による開発確認へ改訂し通過した。人手確認の達成とはせず、以下の未通過記載は旧要件の履歴として読む。

**実装と開発2例の実走は完了。あなたによる品質採点は未実施で、Gate 9はその確認待ち。**
未見のPhase 10 Pilot、本実験、品質改善の実証はまだ行っていない。

2026年10月19日追記: ユーザーの委任により[3候補のAI代行採点とJSON保存](phase9_ai_quality_review.md)を完了した。
以下の全pendingという記載は初回出力時点または人手Labelの状態であり、AI採点は別の来歴で保存している。
GUI操作・独立した人手採点・正式Gate 9を完了したとは扱わない。

## 1. 追加した処理

1. Phase 8の固定Trace・Claim・9条件の判断を保存済みファイルから読み、Hashと来歴を照合する。
2. 各質問につき、元質問・初回回答・**元順序の同じ実使用Context**から一回だけ回答を書き直す。
3. 初回と書換えの二候補を固定し、各条件の判断から最終回答を選ぶ。
4. 条件・F・判断・初回/書換え・JudgeのClaim/理由を隠した採点画面を出力する。
5. あなたが入力した品質Labelを検証して読み込み、四遷移・見逃し・悪化・経路費用へ対応付ける。

書換えには、並べ替え後のContext、評価Feedback、F、Reference、Gold、品質Labelを渡さない。
再検索・再Packing・再切詰め・成功するまでの再試行も行わない。
初回回答を検討して修正する指示を与えるため、単に検索から回答生成をやり直す処理とは異なる。
プロンプトはPhase 7から用意してあった`rewrite_answer`を使い、Phase 8の設定・評価結果は変更していない。
Qwen2.5-3B/Q4_K_M、llama.cpp b11433 CPU、Context 8192、出力予約512、温度0、Seed 42である。

全条件で初回採用または採点不能でも、比較用の書換え候補は1つ収集する。
これにより「書き直したら改善できたのに、判断がそれを選ばなかったか」を後で確認できる。
実験収集で生成した候補が必ず利用者向け出力になるわけではない。

| 保存済み判断 | 選ぶ回答 | 別記する状態 |
|---|---|---|
| accept / F >= 0.7 | 初回 | 通常の採用 |
| rewrite / F < 0.7 | 共通の書換え候補 | 書換えが失敗した場合は初回へ戻して`rewrite_failed` |
| unscorable / F=null | 初回 | `unscorable`。正しいと認定した採用ではない |

修復なし・常時書換えも同じ二候補から選ぶ。書換え失敗時は常時書換えも初回へ戻す。
モデルが初回と同じ文章を返しても有効な一回の書換え試行として保存し、別案を再生成しない。

## 2. 実走で確認したこと

入力はPhase 8と同じ、既に点検済みのDevelopment練習2件である。研究効果を測る未見標本ではない。
Run: `data/runs/answer_rewrite/phase9-development-two-v1/`。

| 質問 | 初回回答 | 書換え結果 | Phase 8の判断で実際に選ぶ回答 |
|---|---|---|---|
| who proposed that atoms are the basic units of matter | 引用IDが2つだけ | Daltonの1803年の原子説などを説明する文章へ変化 | 全9条件ともF=nullなので初回を保持 |
| what does prada mean in the devil wears prada | 題名の翻訳について説明 | 初回と完全に同じ文章 | 全9条件ともF=1/acceptなので初回を採用 |

原子の書換え出力は次のとおりである。

> Dalton proposed a modern atomic theory in 1803, stating that all matter is composed of small indivisible particles termed atoms. This was a significant advancement over the philosophical and theological reasoning of ancient Greek philosophers like Leucippus and Democritus. However, Dalton's theory was based on modern scientific evidence and experimentation, unlike the earlier atomistic ideas. [803775631_38239-38869]

文章になっただけでY=1とは決めない。「最初に誰が提案したか」という質問との対応、古代の考えとDaltonの区別、
すべての事実主張の支持を、人手で確認する必要がある。
Pradaでは初回の不十分な可能性がある説明や短縮引用ID`[54767-55759]`も残り、未知引用IDの監査Warningを保存した。
このWarningは自動的なY=0ではない。自動修正して都合のよい別候補へ置き換えない。

- 新たなCompletionは書換え2回だけ。Judge・Claim抽出・初回回答の再実行は0回。
- 書換えの入力は2,033 / 2,071 Token、出力は99 / 60 Token、処理時間は51.05 / 48.89秒。
- 元順序の文書ID・本文をそのまま渡し、入力超過・切詰めはない。
- 再開時の追加Completionは0回。成功・失敗の既存Journalを再試行しない。
- 同一質問・同一候補・同一Contextの採点は共用するため、2問×二候補でも採点対象は**3候補**。
- 品質Labelは全て`pending`。品質四遷移の既知件数は0、未知は2問である。

今回の例には、順序の違いによる修復判断の反転がない。
その後の分岐・四遷移・書換え失敗・費用は合成Testでも検証したが、合成Labelを実データの成果には数えていない。

## 3. あなたの品質採点

現在使う採点票は`quality-v2`。`quality-v1`は開発途中の出力で、今回の採点には使わない。

1. [採点画面](../data/runs/answer_rewrite/phase9-development-two-v1/quality-v2/採点画面.html)をブラウザで開く。
2. 確認者名を入れ、候補ごとに「採点開始」を押す。休憩は停止する。
3. 質問と回答を読み、実使用根拠・Reference・Gold根拠を展開して確認する。
4. 必須要点、重大な誤りの有無、実使用Contextでの支持を判定し、要点・理由・根拠箇所を記録する。
5. 「採点JSONを保存」を押し、`quality-annotations.json`を保存する。途中保存・再読込もできる。
6. 次のImportを実行すると、Labelと各条件の出力を結び付けた集計ができる。

```powershell
uv run --locked python scripts/answer_quality.py import `
  --run-dir data/runs/answer_rewrite/phase9-development-two-v1 `
  --bundle-dir data/runs/answer_rewrite/phase9-development-two-v1/quality-v2 `
  --annotations "保存したquality-annotations.jsonのパス"
```

画面内の根拠記録は`passage_id | 原文の完全一致する引用`を1行ずつ入力する。
Y=1には全3観点の合格と支持根拠が必要。Y=0は明確な失敗が1観点あればよく、他の観点が未確認でも確定できる。
判定不能は、確認後も曖昧さ等で決められず、明確な失敗がない場合である。単なる未採点と区別する。
要点・理由・確認者・正の確認秒数・日時を記録し、不正なID/Hash/引用/Labelの組合せはImportで拒否する。

ネットワークへの送信はなく、JSONを保存しないまま画面を閉じた入力は保持されない。
採点者へ渡すのはHTML/packet/空の採点JSONのみ。`mapping.private.json`や`routes.pending.json`は対応を明かすため採点中に見ない。
基準本文からも、既に答えを示した練習例の節を除いて画面へ載せる。
過去の会話で例を見ているため、完全な盲検とは主張できず、単独採点の制約も残る。

Importは日付付きの新しい`imports/{UTC時刻}/`へ保存し、前回の採点を上書きしない。
未完了のJSONも取り込めるが、`pending`をY=0/判定不能へ変換しない。
開発確認として空の採点JSONをImportし、全3候補が`pending`のまま保持されることを確認した。

## 4. 出力と費用の読み方

`report.json`には固定入力、初回・書換え、Phase 8の評価、各処理の実測値を保存する。
採点票の`routes.pending.json`、Import後の`analysis.json`には次を出力する。

- `routes`: 各QA×修復なし/常時修復/各Trialの選択候補、品質、Fallback、見逃し/悪化、費用。
- `quality_transitions`: 初回Y→書換えYの0→0、0→1、1→0、1→1と未知。単位はQA。
- `auxiliary_collection_cost`: 既に収集したPhase 8の抽出・全JudgeとPhase 9の全書換えの費用。
- `offline_annotation_seconds`: 人手確認時間。候補を共用しても重複して加算しない。

通常の条件別経路は初回生成+Claim抽出+その条件のJudge+必要時のみ書換え。
保存済み候補を使い回しても、書換えを要求する経路には書換え1回の費用を計上する。
修復なしは初回1回、常時書換えは初回+書換え2回。今回のPradaの条件別経路は3回、
原子の採点不能経路は初回+抽出の2回であり、比較用書換えの費用はその経路へ載せない。
費用の秒数は保存済みStepの和で、検索・Server起動・人手確認を含む実運用Latencyの実測ではない。
中断して実行結果が不明なら、回数を確定値にせず不完全と記録する。
信頼区間・全体の反転率・論文用グラフはPhase 13の工程である。

## 5. 再実行・検証・現在地

```powershell
uv run --locked python scripts/run_answer_rewrite.py `
  --output-dir data/runs/answer_rewrite/phase9-development-two-v1

# 新規出力先に出す。既存採点票は上書きしない。
uv run --locked python scripts/answer_quality.py export `
  --run-dir data/runs/answer_rewrite/phase9-development-two-v1 `
  --output-dir data/runs/answer_rewrite/phase9-development-two-v1/quality-new

uv run --locked pytest
uv run --locked ruff check .
```

Phase 9は完了済みPhase 8のRaw/Manifestを読み取り、再評価しない。
Phase 8の再開CLIはSource一覧もHashへ含むため、新Module追加後の旧Run再開はHash差で停止する。
旧Manifestを更新して再開を通さず、保存済みRawのHashを検証してPhase 9から参照する。
Phase 8のBaseline・Prompt・Config・Raw出力と既存Manifestは保持した。

実装は`recovery/answer_rewrite.py`、`experiments/repair_runner.py`、`quality.py`、`quality_form.py`。
全216 Tests成功、Ruff成功。新規34 Testsで入力分離、固定候補、再開、失敗、採点改変検知、
四遷移と経路費用、採点画面の安全な本文埋込とJavaScript構文を確認した。
ブラウザ画面を人が操作した評価や、実回答の人手Label確定はまだ行っていない。

次は**この3候補をあなたが確認し、Import後に判断・品質・費用を照合してGate 9を通すこと**。
その後、Phase 10で未見Development 20〜30問を事前選定し、Pilotを行う。
