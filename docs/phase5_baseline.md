# Phase 5: ノートPC上の開発用Baseline RAG

2026-10-06。ユーザーの承認に基づき、Phase 4の固定Embedding検索にローカルLLMを接続した。
Development少数問でEnd-to-Endを検証し、**Phase 5完了・Gate 5通過**。
これは開発用Baselineの動作確認であり、提案手法の有効性や最終回答品質を示す比較実験ではない。

## 1. 処理と成果物

```text
元の質問文字列
  → LangGraph: retrieve（固定MiniLM Embedding検索、上位5件）
  → LangGraph: generate（Context整形、Qwenで回答を1回生成）
  → 回答・根拠・実行条件をJSONL/Manifestへ保存
```

- `src/rag_research/baseline.py`: 検索・生成の2ノードを持つWorkflow。
- `src/rag_research/generation/`: 固定Model/Runtimeの準備、設定、Token予算、生成、Development確認。
- `configs/phase5.yaml`: ノートPC用の初期条件。最終Calibrationの確定条件ではない。
- `configs/prompts.yaml`: 英語の根拠付き回答Prompt、Version `phase5-grounded-en-v1`。
- `scripts/prepare_generation.py`: 固定公式配布をプロジェクト内へ取得・検証する。
- `scripts/run_baseline.py`: 任意の質問または固定Development少数問の実行。
- `data/manifests/phase5_generation_manifest.json`: Model/Runtimeの固定情報。Git管理する。
- `data/runs/phase5/`: 回答・Prompt・Context・実測ログ。Git対象外。

Generatorの公開APIは`generate(question: str, context: list[RetrievalHit]) -> str`。
Pipelineは監査用の`generate_record`を使い、回答だけでなく実際の入出力を保存する。

## 2. 固定Modelと実行条件

| 項目 | 採用条件 |
|---|---|
| Model | `Qwen/Qwen2.5-3B-Instruct-GGUF` |
| Revision | `7dabda4d13d513e3e842b20f0d435c732f172cbe` |
| File | `qwen2.5-3b-instruct-q4_k_m.gguf` |
| Size | 2,104,932,768 Bytes（約2.10GB、約1.96GiB） |
| Model SHA-256 | `626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d` |
| License表示 | `qwen-research`。固定RevisionのREADME・LICENSEも保持する |
| Runtime | llama.cpp `b11433`、Windows x64 CPU公式Binary |
| Version表示 | `0.6.0-dev (build 11433, commit 50569eb87)`、Clang 20.1.8 |
| Runtime ZIP SHA-256 | `301943380e45deae3991d42dddd03fae65c6a4963a5d882328a60208b43aa9e0` |
| Threads / Parallel / GPU Layers | 6 / 1 / 0（CPU実行） |
| Batch / Micro Batch | 128 / 128 Token |
| 重み再配置 | 無効、`--no-repack`。初回のRAM不足傾向を受けて採用 |
| Context / 最大出力 | 合計4,096 Token / 出力512 Tokenを予約 |
| Passage本文上限 | 各512 Token、上位5件を順位順に詰める |
| Sampling | Temperature 0、Seed 42、Samplerはtemperatureのみ、Repeat Penalty 1 |
| Prompt Cache / RAM Slot Cache | 無効 / 0 MiB |
| Timeout | 起動120秒、各HTTP要求300秒 |

公式配布: [固定Qwen Model](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/tree/7dabda4d13d513e3e842b20f0d435c732f172cbe)、
[固定Runtime](https://github.com/ggml-org/llama.cpp/releases/tag/b11433)、
[Runtime API](https://github.com/ggml-org/llama.cpp/blob/b11433/tools/server/README.md)。

Modelは`data/models/`、Runtimeは`data/runtimes/`へ置く。取得時の公式Hashと照合し、完成済み条件が
異なる場合は上書きしない。実行時もGGUFとRuntime全FileのHashを検証する。
Python依存はuvで管理し、LangGraph/PyYAMLを追加した。学習やFine-tuningは行わない。

サーバーは毎回空きPortを選び、`127.0.0.1`だけで待ち受ける。既存サーバーを流用せず、
自分が起動したProcessを正常終了・例外時とも終了させる。生成はOfflineで、外部LLM APIや
LangSmith Tracingを使わない。PC全体の設定変更・可視Windowの起動は行わない。
自動取得はWindows x64のみ対応。Ubuntu/GPUへの移行時は別Runtime条件を固定・検証する。

## 3. Context・Token予算・正解情報の分離

Workflowへ渡すのは元質問文字列のみ。GeneratorのContextは全Corpusから実際に取得した
`RetrievalHit`だけとする。QA辞書を直接受け取らず、Gold、Reference、Selected Sentences、
Answerability、派生条件、独立品質LabelはInference State/Promptへ含めない。

LLMにはPassage ID、Title、使用本文を渡す。検索Scoreは記録用であり、Confidenceや正解確率として
使わない。質問/文書をJSONで表現し、Chat区切りTokenとして解釈され得る`<`をエスケープする。
Promptは元質問への直接的な英語回答、根拠IDの角括弧引用、証拠不足時の回答抑制を指示する。
文書を証拠として扱い、文書中の指示に従わないよう指示する。

Token数はEmbeddingのTokenizerではなく、実GGUFのTokenizerで数える。実Chat Templateへ適用した
Prompt全体を特殊Token・Metadata込みで確認する。入力最大3,584＋出力予約512＝合計4,096 Token。
数えたToken IDsをそのまま生成へ渡し、RuntimeのContext Shiftを無効にする。

本文は各512 TokenまでのPrefixを使う。全体予算を超える場合は順位順に本文を縮め、Metadataも
収まらない文書は省く。各候補の実Prompt長を確認し、Unicode途中の切断は有効なPrefixまで戻す。
元の質問は切り詰めず、指示と質問だけで上限を超える場合は停止する。
取得全文、実使用本文、切詰め/省略理由を別々に保存し、Goldを見てContextを選び直さない。
文書0件でもAnswerabilityを使った分岐はせず、同じPromptで1回生成する。

## 4. 実行コマンドと記録

Repository Rootで実行する。

```powershell
uv run --locked python scripts/prepare_generation.py
uv run --locked python scripts/run_baseline.py "who does the voice of plankton from spongebob"
uv run --locked python scripts/run_baseline.py --smoke --limit 5
```

準備コマンドは初回だけModel/Runtimeを取得し、以降は検証して再利用する。
質問CLIは毎回日時とUUIDで新Directoryを作る。`--output-dir`を指定しても既存Directoryは上書きしない。
検索CLIより時間がかかるため、少数問を1問ずつ処理し、不要なアプリを閉じてRAMを確保する。

- `answers.jsonl`: 質問、取得全文/ID/Title/Score/Rank、使用Context、切詰め、Messages、
  実Prompt/Hash/Token IDs、回答、出力Token数、引用ID、生成Count、Latency、Runtime Response。
- `run_manifest.json`: 設定/Prompt/コードHash、Model/Runtime、Corpus/Index、依存Version、質問、
  実生成要求数、完了状態、起動/全体時間、Python/ServerのMemory測定。
- `server.log`: 起動/生成Log。終了後も残る。
- `offline_checks.json`: Development生成後だけ、Reference/Gold取得有無を別保存する。
  品質Yと独立Failure Labelは未採点の`null`。

`status=ok`は生成が正常終了した実行状態であり、回答正解・根拠支持・Y=1を意味しない。
使用Contextにない引用は`unrecognized_citations`へ記録する。存在する引用でも根拠支持は別途確認する。
Timeout、空回答、予期しないContext切詰め、出力上限到達等はErrorにし、情報不足回答へ置き換えたり
暗黙に再生成したりしない。失敗時にもManifestを残す。

## 5. Development検証と実測

Developmentだけを開き、Seed 42/Record IDのSHA-256順でAnswerable 3問・Unanswerable 2問を選ぶ。
選択にModel成績は使わず、同じHash順に実行する。`--limit`は1〜10。
Calibration/Evaluationの成績測定・調整は行わない。UnanswerableのCorpus-level監査は未実施なので、
元Labelだけで情報不足回答が正解だとは判断しない。

初回は重み再配置ありで実行し、RAM余裕が小さかったため無効化して同一質問と固定5問を再検証した。
採用設定は`repack: false`。旧条件は別Runとして保持する。

| 声優質問の実測 | 重み再配置あり | 重み再配置なし（採用） |
|---|---:|---:|
| Pipeline時間（読込除く） | 36.23秒 | 36.38秒 |
| Process全体（読込含む） | 45.41秒 | 42.76秒 |
| Python + ServerのSampled Peak RSS | 3.686GiB | 2.446GiB |
| PC全体の最小空きRAM | 0.030GiB | 1.881GiB |

100ms間隔で両ProcessのRSSを採取し、同時点の和の最大値を記録する。空きRAMは他アプリにも左右される。
個別Peakの単純合計やVRAM量とは区別する。1問の比較から統計的な速度・品質改善は主張しない。
Temperature 0でもBackend変更で回答が変わった。別CPU/Runtime間のByte一致は保証しない。

採用条件で固定5問すべてが実LLMで検索→生成→保存まで完了し、各1回、合計5回生成した。
各Pipeline時間は28.96/20.83/18.77/25.85/20.33秒。入力は873〜1,185 Token、出力は14〜68 Token。
実行Logは`data/runs/phase5/development-five-no-repack-v2/`。
最終集計のHashとMemoryは`data/manifests/phase5_smoke_report.json`を参照する。
5問の全体時間（読込含む）は120.66秒、Pipeline平均22.95秒、合計Peak RSS 2.453GiB、
PC全体の最小空きRAMは1.679GiBだった。最終`uv run --locked pytest`は116件成功・Skipなし（23.68秒）、
`uv run --locked ruff check .`は問題なし。固定Base/Split/検索ManifestのHashが変わらないことも確認した。

観察された課題:

- 初回声優回答には正しい名前に加え、根拠にない「KarenはPlanktonの母」という追加文があった。
- 固定5問では2件の情報不足回答が出たが、Corpus監査前のため拒否正解率とは扱わない。
- Answerable 3問中2問でGoldを取得した。残る質問ではGold未取得のまま回答した。
- 採用条件でも質問に十分答えない回答と、Passage IDの末尾だけの引用を観察した。

これは開発観察であり、正式な独立Failure Label、ECE、Hallucination率として集計しない。
正常動作と回答品質を区別する必要を確認できた。**Gate 5通過**はEnd-to-End動作についての判定である。

## 6. 次の工程

Phase 6でBM25/EmbeddingをRRFで統合し、Calibrationで共通Retrieverを調整・固定する。
自己評価、Confidence、Failure判定、Recovery、独立品質評価、最終比較、Ubuntu再現は未実施。
小型Generatorは開発用。最終Model変更時は理由・Revision・量子化・Runtime・Prompt・Context予算を
記録し、比較3方式へ共通適用する。異なるGenerator条件の結果を混ぜて効果を主張しない。
