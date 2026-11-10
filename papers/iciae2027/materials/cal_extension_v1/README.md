# Cal拡張の論文用資料

完了Batch: batch_01, batch_02, batch_03。予定120問中、封印済み資料の選定数120。

各batch_XX/README.mdから全文・出典・採点・判断・費用・図表・検証入口へ進む。
pooled_new_extension.jsonは新規追加集合だけの統合。既存Main/Calを合算していない。Batch別の結果も保持。
未収集/未封印の予定QAを成功扱いにせず、completion.jsonの残件数を参照する。

ノートPCではGit状態とFetch後の履歴差分を確認し、未完成原稿を保全して取込む。同一DOCXの両PC同時編集を避ける。
取込元Branch: research/cal-extension-v1。研究室側ではDOCXを編集していない。
全体検証: `uv run --no-project python -I verify_collection.py --audit-open`。各Batchにも独立した検証入口を同梱。
方法・欠測・分母・AI採点/人手未確認・時期差・Serving版不明を保持して日英両原稿へ反映する。
論文への反映、教員確認、引用最終照合、投稿は著者の作業。
