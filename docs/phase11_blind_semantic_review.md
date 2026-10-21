# Phase 11 日英の匿名固定文意味監査

2026年10月21日。主Developmentの意味採用条件を、内部判定を開く前のAI注釈へ結ぶ実装。
主20問の実走/採点は未実施であり、この追加だけで意味採用やGate 11を通さない。

## 公開PacketとLabelの封印

既存の匿名品質Packetから、質問・匿名候補回答・実使用Context・同じ決定的文単位だけを投影する。
初回/書換えの両候補を含み、段階/QA ID/内部F/判断/判定理由は公開しない。
同じ候補は既存品質Packetと同じ匿名IDで一度だけ注釈し、内部Mappingを開くのは封印後とする。
Reference/Gold/人手要約/欠測の外部資料を文支持の根拠へ渡さない。
品質採点の必須要点のためのReferenceと、Judgeが見たContextに対する支持は別の判断である。

文ごとにsupported/contradicted/not_supported/ambiguousを注釈し、理由・実使用本文内の原文Evidence・
採点者/経過秒/Timezone付き時刻・human_reviewed=false・厳密Model ID取得可否/履歴分離の実態を記録する。
支持/矛盾には原文Evidenceを要求する。出力形式/引用の検証は意味の正解を保証しない。
裸拒否/空文の候補もPacketへ保持し、文0件へ架空Labelを発行しない。

解析入口は日英両方の全品質Labelと全文Labelを先に検証/封印し、Packet/Mapping/LabelのHashを固定する。
一つでもpendingなら両言語とも内部Fを読み込まず、初回/書換え対応との比較を行わない。
私的Mappingは封印時のPacket整合性検証に用いる。封印後もHash差を検出して停止する。
その後、Raw/Source/候補・文内容を照合し、私的Mappingで初回回答のExpectedを割り当てる。
人手正解や独立した履歴の真値とはしない。現在のCodex AI採点では厳密Model IDは取得不能、履歴共有を明記する。

## 集計と主Developmentの採用

全予定の文×試行を保持し、無効試行も正確一致の予定分母から消さない。
曖昧注釈は精度だけから除き、実験の全固定文/F分母を変えない。
確定/支持/非支持/曖昧の実数と、固有の文数・文0 QA・完全比較QAを別に報告する。
分母0はnullで、100%へ補完しない。同じ文の多数試行を独立した正解例数としない。

Source/予算/Prompt等の日英共通条件を検査し、事前Policyの各言語精度/支持精度90%以上・
明確な非支持の誤支持0・完全比較QA10以上・全20 QA/Health失敗0を計算する。
旧接続Smokeの解析を主20問の採用へ昇格させず、最終Gate 11やEvaluationの通過にしない。

入口は`scripts/review_bilingual_units.py export`/`analyze`。
Exportは品質Bundleから公開Packetと空注釈を新Directoryへ保存し、内部結果を読み込まない。
Analyzeの入力JSONは日英2行で、各行に`run`、`quality_bundle`、`quality_annotations`、
`unit_bundle`、`unit_annotations`のRepo相対Pathを指定する。すべてDevelopment Run配下に限る。

新規9 Testで匿名/Gold除外・同一候補共有・全単位/引用/AI来歴・裸拒否、全予定分母/曖昧/失敗とF不変、
日英いずれかの品質/文Label未完了時の内部読込み0、封印中の改変拒否、事前20問/10比較Gateを確認した。
全545 Test/Ruff成功。実主対象の新規Model呼出し/注釈は0である。
