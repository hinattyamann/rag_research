"""Render Phase 8's actual saved outputs for inspection, not blind quality annotation."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_research.experiments.storage import read_json  # noqa: E402


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def render(run):
    report = read_json(run / "report.json")
    manifest = read_json(run / "manifest.json")
    entries = {r["record_id"]: r for r in manifest["traces"]}
    lines = ["# Phase 8 実行結果の確認", "",
             "保存済みの実出力。開発用の動作確認であり、本実験・独立品質評価ではない。",
             "根拠本文の抜粋は表示用。評価機には保存済み本文の全体を渡している。", "",
             f"Run: `{report['run_id']}`", "",
             f"実Completion数: {report['actual_completion_attempts']}。"
             f"判定状態: `{json.dumps(report['judge_status_counts'])}`", ""]
    for record in report["records"]:
        entry = entries[record["record_id"]]
        folder = run / entry["directory"]
        trace = read_json(folder / "trace.json")
        labels = {d["passage_id"]: chr(65 + i) for i, d in enumerate(trace["documents"])}
        lines += [f"## {trace['question']}", "", f"ID: `{record['record_id']}`", "",
                  "### 固定した最初の回答", "", trace["answer"], "",
                  "### 元の根拠順序と表示用抜粋", "",
                  "| 表示記号 | Passage ID | Title | 本文の先頭（表示用抜粋） |",
                  "|---|---|---|---|"]
        for document in trace["documents"]:
            excerpt = document["text"][:180]
            if len(document["text"]) > 180:
                excerpt += "…"
            lines.append(f"| {labels[document['passage_id']]} | `{document['passage_id']}` | "
                         f"{cell(document['title'])} | {cell(excerpt)} |")
        lines += ["", "表示記号A〜はこの説明用の略記。実際の評価入力では元のPassage IDを保持する。", "",
                  "### 一度だけ抽出して固定した主張", "",
                  f"抽出状態: `{record['extraction_status']}`。", ""]
        if record["claims"]:
            lines += [f"- `{c['claim_id']}`: {c['text']}" for c in record["claims"]]
        else:
            extraction = read_json(folder / "claims.json")
            lines += ["抽出された主張なし／抽出失敗。Fはnullで、採用の正解認定ではない。", "",
                      "```text", str(extraction.get("raw_output")), "```"]
        lines += ["", f"閾値: {record['threshold']}。F=支持された主張数/固定主張数。", "",
                  "### 各試行の実出力", "",
                  "| 条件 | 根拠の提示順序 | 状態 | F | 判断 |",
                  "|---|---|---|---|---|"]
        trials = {r["trial_id"]: r for r in record["trials"]}
        trial_ids = record["plan"]["order_group"] + record["plan"]["repeat_group"][1:]
        for trial_id in trial_ids:
            row = trials[trial_id]
            order = " → ".join(labels[i] for i in row["document_ids"])
            score = "null" if row["score"] is None else f"{row['score']:.4f}"
            lines.append(f"| {trial_id} | {order} | {row['status']} | {score} | {row['decision']} |")
        lines += ["", "`rewrite`は書換え要求の記録。Phase 8では実際の回答書換えを行わない。", ""]
        for trial_id in trial_ids:
            row = trials[trial_id]
            if "task_file" not in row:
                continue
            task = read_json(run / row["task_file"])
            lines += [f"#### {trial_id}", "",
                      f"入力Token: {task['input_tokens']}、出力Token: {task['output_tokens']}。", ""]
            if row["error"]:
                lines += [f"検証エラー: {row['error']}", ""]
            lines += ["```json", task.get("raw_output") or "null", "```", ""]
        lines += ["**解釈上の注意:** 構造検証・引用一致は、主張分解の完全性、意味上の支持、"
                  "質問への正答を保証しない。", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rendered = render(args.run_dir)
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(rendered + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
