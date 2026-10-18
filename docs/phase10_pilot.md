# Phase 10: 未見Development予備実験

2026年10月19日開始。研究計画7.4・実装計画8.4。Study Version: order-ai-pilot-v1。
**20問を結果を見る前に固定し、初回生成20問が完了。内部評価と書換えを実行中。品質採点とPilot Reportは未完成。**

## 1. 今回確定したこと

- 品質採点はユーザーの委任によりCodex AIが担当する。[AI品質Protocol](ai_quality_protocol.md)を適用する。
- 過去に生成・点検済みの5問と同一Titleを除外し、Development Answerableから異なる20 Titleを選んだ。
- Seed42とIDのSHA256昇順で最初の各Titleを採用し、モデル実行前に`phase10_selection_manifest.json`へ固定した。
- 検索・初回生成はPhase 6条件、内部JudgeはPhase 8 v5条件、書換えは同じ元Contextから1回だけである。
- 失敗QAを補充せず、成功までの自動再試行をしない。中断時の不明な試行も失敗として残す。
- 同じ文書本文・質問・初回回答・固定Claimを使い、順序群5条件と同一順序5回を共通初回込み9回で比較する。
- Health Gateも内部実行前に固定した。最初の5問で完全採点可能QAが3問未満、または実Judgeの
  形式/Runtime失敗率が25%超なら残りへの内部試行を停止する。入力超過は1問でも停止する。
  これは測定系の健全性の確認であり、Fや反転率・品質改善の大小を停止条件にはしない。

Source/Split/Baseline/Phase 8/9の旧設定・旧ソース・旧Manifestを上書きしていない。
内部推論には、旧Protocolの推論部分だけを再利用する。旧Config内の人手採点方針は適用せず、
外部品質の方針は`configs/phase10.yaml`と新Protocolで定める。

## 2. 実行方法

```powershell
uv run --locked python scripts/run_pilot.py select
uv run --locked python scripts/run_pilot.py baseline
uv run --locked python scripts/run_pilot.py internal
```

出力Rootは`data/runs/pilot/phase10-twenty-v1/`。
Baselineは`baseline/`、内部実行は`internal/`、匿名採点資料は`quality/ready-001/`等へ分離する。
外部採点へ渡すのは匿名Packet/HTMLのみとし、privateと付く内部結果・対応表を採点前に開かない。
進捗の`progress.json`とConsoleは質問数等を表示し、内部Fや判断・回答本文を表示しない。

採点は次のCLIで候補を一つずつ開き、理由・原文引用を含むDecision JSONを書いて保存する。
各候補の確認時間は実際に資料を開いてから保存するまでの経過時間であり、人手時間ではない。

```powershell
uv run --locked python scripts/assess_pilot.py open --packet 1
uv run --locked python scripts/assess_pilot.py save --packet 1 --decision "decision.json"
```

確認者表示名はリサーチャー01、実採点者はCodex AI、human_reviewed=falseとする。
完了済み候補への再採点で元Labelを上書きせず、訂正が必要なら別の改訂履歴を作る。
判定不能を0/1へ強制しない。元文書の引用IDと原文の完全一致を既存Validatorで確認する。

全対象の採点後に初めて対応表と内部結果を開き、次のCLIでPilot Reportを作る。
事前のHealth Gateが停止した場合は、実施済み範囲を採点し、未実施IDもReportに残す。

```powershell
uv run --locked python scripts/run_pilot.py report
```

## 3. 評価範囲と制約

採点側はReference/Goldを知るが、内部のF/条件/判断/段階を伏せる。支持の確認には実使用Contextを使う。
今回のPilotは同じ作業セッションで新しい内部結果を伏せて採点するため、完全な履歴分離とは主張しない。
Codexの正確なモデル識別子はこのセッションから取得できずnullとして保存する。
本番の専用セッション・モデル固定と妥当性検証はPhase 11で確定する必要がある。
今回の再確認を、人間との一致率や独立した複数評価者の一致として報告しない。

主比較は両群の必要Trialがすべて有効で、ペアを作れる共通QA。
順序群と反復群の不一致率を質問内でまとめて差を取る。各ペアを独立QAとして水増ししない。
部分失敗・Claimなし・品質不明・書換え失敗・初回失敗・Health停止後の未実施を別に報告する。
費用は実験の収集と各条件の経路、外部AI採点の時間を分ける。経路のStep和を実測Latencyとは呼ばない。
本Pilotの記述集計は、本実験や正式な信頼区間の代わりにはしない。

## 4. 実装確認

`pilot/`以下に選定、初回生成Journal、内部推論、匿名資料、AI採点記録、集計を追加した。
合成例で抽出1+Judge9+書換え1の11呼出しと、再開時の追加0回・Raw Byte同一を確認した。
初回失敗の非補充、AI採点と人手の区別、全候補採点前の集計拒否、Health Gateも検証した。
`uv run pytest --quiet`: 全222件成功（27.21秒、Skipなし）。`uv run ruff check .`: 成功。
実験が進んでもこの初期記録を完了済みの研究結果へ読み替えず、完了時に実測と現在地を更新する。
