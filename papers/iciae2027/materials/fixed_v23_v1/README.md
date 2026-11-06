# 固定v23 Main/Calの検証済み執筆資料 v1

対象は既存Main/Cal×日英各20問、計80選定のみ。新規推論0・再採点0。元Run/GPU/モデル/Index/認証/ネット接続なしで、ここにある資料から本文・図表・実例を追跡できる。

## ノートPCで最初に実行

Repository Rootから `uv run --no-project python -I papers/iciae2027/materials/fixed_v23_v1/verify_materials.py --audit-open` を実行する。Python標準ライブラリのみ使用する。資料フォルダ単体を任意の場所へ移した場合も `uv run --no-project python -I verify_materials.py --audit-open` で動く。成功時のJSONに80 QA、全4区分、全予定Trial、採点対応、方策行、全Hashと集計の検証件数が出る。認証・モデル取得・推論は行わない。

## 索引と章への対応

| 資料 | 使う章/用途 |
|---|---|
| [実験条件](experiment_conditions.md) | 方法・実験条件。実設定本文はprovenance/frozen_files/ |
| [結果の読み方](results_explanation.md) | 結果・考察。既存表との対応と列名の注意 |
| [限界/事後変更](limitations_and_deviations.md) | 条件・考察・限界 |
| [採点来歴](annotation_provenance.md) | AI採点・遮蔽・実モデルIDの取得範囲 |
| [出典/利用条件](references_and_attributions.md) | 文献・Dataset・モデル・原文の帰属 |
| [80問の要約](qa_summary.csv) | 全選定/比較可能/対象外、A/B品質、O/R/D |
| [予定Trial](trials.jsonl) | 実提示順序、F/判定/Action、固定文Label/根拠/費用 |
| [全方策](policy_outcomes.csv) | 80×11枠。未実施・重複省略を明示、nullを0へ補完しない |
| [質問別全文](inputs/) | 質問/Reference・実使用根拠・A/B・固定文・日本語参照来歴 |
| [確定採点](annotations/) | 匿名Packet・対応表・品質/Expected。共用候補を保存 |
| [具体例](cases/) | 結果閲覧後に規則で選んだ2～4例。JSONでF/Y/費用を追跡 |
| [詳細解析](analysis/) | 元詳細解析の同一バイト複製と数値費用台帳 |
| [公開成果](published_results/) | 元図表/CSV/集計/Manifestと同一バイト |
| [来歴](provenance/) | 元Manifest/Seal/Report、設定・Prompt・採点Job来歴 |
| [元ファイル対応](source_manifest.json) | 元Repository/Commit・各入力の位置/Hash、変換、80問対応 |
| [資料Hash一覧](artifact_manifest.json) | 自己参照以外の全成果・Byte数・SHA-256 |

qa_keyは集合/言語/元IDのHashから作る資料内のキー。qa_summary.csvのinput_pathで質問別JSONへ進み、record_idとtrial_idでtrials.jsonl、routeでpolicy_outcomes.csvを結合する。匿名IDはannotations内のmapping.private.jsonでQA/initial・rewrittenへ結合する。同じ文章の採点共用を独立候補へ水増ししない。

## 抽出と再現

研究室での抽出コマンドは `uv run python build_materials.py --source-repo /path/to/lab/repo --output /path/to/new/materials`。この抽出だけは元Runが必要で、完成版への上書きを拒否する。通常のノート検証ではverify_materials.pyだけを使う。build_materials.py/test_verify_materials.pyも同梱し、処理と反証検証を追跡できる。

元の4つのreport.private.jsonは必要な確定資料としてByte不変で複製し、巨大なServer/Eventログ・全Run/Corpus・モデルを複製していない。provenance/protocol_textとanalysis_codeの*.txtは原文の証拠コピーで、元文書内のリンク/絶対パスは歴史的記録。検証器はそのパスを開かない。資料内の案内リンクはこのフォルダ内で完結する。

## 完了範囲と残件

本資料は抽出時の元Hash・封印・解析Sourceを検証したもの。Git再取得後の実検証結果と取込元Commitは、執筆Branchのnotes/materials_handoff.mdも参照する。原稿の著者情報確認、関連研究本文の精読、人手による採点妥当性確認、教員確認と提出は別工程。初回生成失敗1件と書換え失敗2件、既知の外的中断の応答/最終費用不明、未特定の採点Serving Model IDを補完していない。

## 元から未取得・未特定の情報

- Main日本語のwhrja:02e85c8:answered:857は引用元jawiki-page:5273510のCorpus本文を元取得段階で確保できていない。保存されたReference引用/URL・欠測状態はinputsに保持し、本文を捏造していない。実使用根拠の全文とは別の参照側の不足である。
- 英語の元Wikipedia oldidはCLAPNQ加工資産に記録されていない。Title由来URLと固定Dataset Revision/Passage ID/本文Hashへ追跡する。
- 採点Serving Modelの厳密な実識別子は未取得で、configured modelと来歴を保存する。
- 人手確認・著者情報・関連研究本文の精読は本資料の完了範囲に含めない。

## 保存した粒度

A成功79件、B成功77件、匿名品質候補156件、外部固定文注釈460件。初回欠測1問はTrial計画未作成。残る79問の通常9条件から重複順列5条件を省き、実計画Trialは706件。これらをNative呼出し数や独立QA数へ読み替えない。方策表は80×11=880枠で、実記録864・初回欠測による未実施11・重複省略5を区別する。

実使用文書のうち1件は、初回のContext PackingでCorpus Passageの先頭645文字が使われたもの。used_documentsに実際の645文字を無変更で保持し、corpus_documentsに元Passage全文、corpus_character_spanと両方のHashを保存した。順序試行では実使用本文を固定しており、Corpus全文へ置換していない。
