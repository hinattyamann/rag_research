"""Standalone scientific figures and aggregate tables from sealed Main/Cal analyses."""

import argparse
import csv
import json
import shutil
from pathlib import Path

from common import immutable, load_config, now, read, require, sha, write
from pipeline import public_tables, source_hashes, verify_seal


def csv_file(path, rows):
    require(rows, "Do not create an empty table with invented zeros")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def publish_analysis(config, cohort):
    """Only aggregate, fully sealed results are eligible for Git publication."""
    run = Path(config[cohort + "_run"])
    verify_seal(run)
    result = read(Path(config["state_dir"]) / cohort / "analysis.private.json")
    require(source_hashes(run) == result["source_files_sha256"], "Source run changed after sealed analysis")
    summary = {k: result[k] for k in ("cohort", "collection_costs", "condition_sha256", "progression_gate_passed",
        "gate11_passed", "phase12_allowed", "human_reviewed", "limitations")}
    summary["statistics"] = {k: v for k, v in result["statistics"].items() if k != "qa"}
    summary["semantics"] = result["semantics"]
    summary["quality_routes"] = public_tables(result)
    summary["threshold_sensitivity"] = result["threshold_sensitivity"]
    summary["source_analysis_sha256"] = sha(Path(config["state_dir"]) / cohort / "analysis.private.json")
    output = Path(config["public_dir"])
    output.mkdir(parents=True, exist_ok=True)
    immutable(output / (cohort + "_summary.json"), summary)
    return result, summary


def create_figures(config):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    source = [publish_analysis(config, cohort) for cohort in ("main", "cal")]
    results = [item[0] for item in source]
    require(results[0]["condition_sha256"] == results[1]["condition_sha256"], "Main/Cal scientific conditions differ")
    output = Path(config["public_dir"])
    manifest_path = output / "artifact_manifest.json"
    if manifest_path.exists():
        require(all(sha(output / name) == value for name, value in read(manifest_path)["files"].items()),
                "Published figure artifact changed")
        return
    staging = Path(config["state_dir"]) / "figure-staging"
    require(not staging.exists(), "Preserve incomplete figure output; explicit recovery is needed")
    staging.mkdir()
    plt.rcParams.update({"font.size": 10, "figure.dpi": 130, "savefig.dpi": 300,
                         "svg.fonttype": "none", "pdf.fonttype": 42})

    def save(fig, name):
        fig.tight_layout()
        for extension in ("svg", "pdf", "png"):
            fig.savefig(staging / (name + "." + extension), bbox_inches="tight")
        plt.close(fig)

    primary = []
    for result in results:
        for language in ("en", "ja"):
            row = result["statistics"]["languages"][language]
            primary.append({"cohort": result["cohort"], "language": language,
                "selected_qa": row["selected_qa_count"], "comparable_qa": row["comparable_qa_count"],
                "missing_qa": row["missing_qa_count"], "mean_increment": row["mean_increment"],
                "ci95_low": row["ci95"][0] if row["ci95"] else None,
                "ci95_high": row["ci95"][1] if row["ci95"] else None})
    csv_file(staging / "primary_comparison.csv", primary)
    fig, ax = plt.subplots(figsize=(7, 4))
    for index, row in enumerate(primary):
        value = row["mean_increment"]
        if value is not None:
            low, high = row["ci95_low"], row["ci95_high"]
            # A percentile interval need not contain the sample mean; draw its endpoints directly.
            ax.plot(index, value, "o", color="#2563a6")
            if low is not None:
                ax.vlines(index, low, high, color="#2563a6")
                ax.hlines([low, high], index - .07, index + .07, color="#2563a6")
        ax.text(index, .97, f"n={row['comparable_qa']}/{row['selected_qa']}",
                transform=ax.get_xaxis_transform(), ha="center", va="top")
    ax.set_xticks(range(4), [f"{r['cohort'].upper()} {r['language'].upper()}" for r in primary])
    ax.axhline(0, color="0.4", linewidth=.8)
    ax.set_ylabel("Mean QA increment (order disagreement − repeat disagreement)")
    ax.set_title("Order sensitivity; document-group bootstrap 95% CI")
    ax.margins(x=.2)
    save(fig, "01_order_vs_repeat")

    route_rows = [r for result in results for r in public_tables(result)]
    csv_file(staging / "quality_and_operational_cost.csv", route_rows)
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), sharey=True)
    statuses = [("reliable", "#267c62"), ("unreliable", "#c85c4d"),
                ("indeterminate", "#e6b757"), ("pending", "#9e86b6"), ("baseline_missing", "#b8bec7")]
    for ax, (result, language) in zip(axes.flat, [(r, lang) for r in results for lang in ("en", "ja")], strict=True):
        rows = [r for r in route_rows if r["cohort"] == result["cohort"] and r["language"] == language and
                r["route"] in {"no_repair", "always_rewrite", "original"}]
        bottom = np.zeros(len(rows))
        for status, color in statuses:
            values = [r[status] for r in rows]
            ax.bar(range(len(rows)), values, bottom=bottom, label=status, color=color)
            bottom += values
        ax.set_xticks(range(len(rows)), [r["route"].replace("_", " ") for r in rows], rotation=15)
        ax.set_ylim(0, 20)
        ax.set_title(f"{result['cohort'].upper()} {language.upper()} (selected n=20)")
        ax.set_ylabel("QA count; failed rewrites use the initial answer")
    axes[0, 0].legend(fontsize=7)
    save(fig, "02_quality_and_missingness")

    costs = [{"cohort": r["cohort"], "language": lang, **values}
             for r in results for lang, values in r["collection_costs"].items()]
    csv_file(staging / "collection_cost.csv", costs)
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, key, title, divisor in zip(axes, ["native_attempts", "output_tokens", "summed_observed_task_seconds"],
            ["All attempts (includes cancelled requests)", "Known output tokens (thousands)", "Known observed step hours"],
            [1, 1000, 3600], strict=True):
        ax.bar(range(4), [r[key] / divisor for r in costs], color=["#2563a6", "#36a0aa"] * 2)
        ax.set_xticks(range(4), [f"{r['cohort']}\n{r['language']}" for r in costs])
        ax.set_title(title)
    save(fig, "03_collection_cost")

    sensitivity = [{"cohort": r["cohort"], **row} for r in results for row in r["threshold_sensitivity"]]
    csv_file(staging / "threshold_sensitivity.csv", sensitivity)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, result in zip(axes, results, strict=True):
        for language, color in (("en", "#2563a6"), ("ja", "#d47724")):
            rows = [r for r in result["threshold_sensitivity"] if r["language"] == language]
            ax.plot([r["threshold"] for r in rows], [np.nan if r["mean_increment"] is None else r["mean_increment"]
                    for r in rows], "o-", label=language.upper(), color=color)
        ax.axvline(.7, color="0.5", linestyle="--", linewidth=.8)
        ax.axhline(0, color="0.5", linewidth=.8)
        ax.set_title(result["cohort"].upper() + ": preregistered sensitivity analysis")
        ax.set_xlabel("Threshold (primary = 0.7; no selection/tuning)")
        ax.set_ylabel("Mean QA disagreement increment")
        ax.legend()
    save(fig, "04_threshold_sensitivity")
    ledger_path = Path(config["state_dir"]) / "cli_ledger.json"
    ledger = read(ledger_path) if ledger_path.exists() else {"invocations": []}
    proofs = [read(p) for p in (Path(config["state_dir"]) / "jobs").glob("*/attempt-*/provenance.json")]
    usage = [u for proof in proofs for u in proof["token_usage"]]
    write(staging / "annotation_cost.json", {"reserved_cli_invocations": len(ledger["invocations"]),
        "recorded_completed_invocations": len(proofs), "summed_cli_job_wall_seconds": sum(p["elapsed_seconds"] for p in proofs),
        "observed_input_tokens": sum(u.get("input_tokens", 0) for u in usage),
        "observed_cached_input_tokens_subset": sum(u.get("cached_input_tokens", 0) for u in usage),
        "observed_output_tokens": sum(u.get("output_tokens", 0) for u in usage),
        "token_totals_complete": len(proofs) == len(ledger["invocations"]) and all(p["token_usage"] for p in proofs),
        "auth": "chatgpt", "api_key_billing": False, "monetary_cost": None,
        "scope": "offline AI annotation including bounded format repairs; separate from GPU collection and operational routes",
        "timing_note": "CLI job wall includes model/tool/startup overhead; not pure reading time or human time"})
    notes = ["# 結果説明資料（論文原稿ではない）", "", "MainとCalは別集合として報告し、統合して件数を水増ししない。", ""]
    for row in primary:
        notes.append(f"- {row['cohort']} / {row['language']}: 選定{row['selected_qa']}、完全比較{row['comparable_qa']}、"
            f"比較欠測{row['missing_qa']}。平均増分={row['mean_increment']}、95%区間=[{row['ci95_low']}, {row['ci95_high']}]。")
    for result in results:
        for language, cost in result["collection_costs"].items():
            if cost.get("archived_external_attempts", 0):
                notes.append(f"- {result['cohort']} / {language}: 外的監視中断の要求{cost['archived_external_attempts']}件を同一入力で1回再実行。"
                    "中断前の要求は試行数に含めるが、応答と最終費用は不明。Token/時間図は既知分の下限で、総費用完全とは扱わない。"
                    "この外的中断自体を候補欠測にはしていない。")
        for language in ("en", "ja"):
            rows = [r for r in route_rows if r["cohort"] == result["cohort"] and r["language"] == language]
            base = next(r for r in rows if r["route"] == "no_repair")
            rewrite = next(r for r in rows if r["route"] == "always_rewrite")
            transitions = result["quality_routes"][language].get("quality_transitions")
            notes.append(f"- {result['cohort']} / {language}: 修復なしのAI品質Y=1は{base['reliable']}/20、"
                f"常時書換え（失敗時初回保持）は{rewrite['reliable']}/20。初回欠測{base['baseline_missing']}、"
                f"常時書換えの失敗Fallback {rewrite['rewrite_failed_fallbacks']}。")
            if transitions:
                notes.append(f"  初回→書換えの品質遷移: {transitions}。unknownを改善/悪化/品質不良へ補完しない。")
    notes += ["", "## 読み方と執筆前の確認", "",
        "- 増分はQAごとの順序群不一致率と同順序反復群不一致率の差であり、正答率ではない。",
        "- 区間が0を含む場合、効果なしを証明したとは書かない。少数Groupと欠測による精度の限界を示す。",
        "- 品質図は失敗書換え時に初回保持した運用結果。初回対書換えの品質遷移の欠測とは区別する。",
        "- Native試行数は失敗/取消も含む。中断応答の費用が不明な場合、Token/時間は既知分で総額ではない。方策の運用費用は別CSVで、外的中断の追加費用と区別し、CLI採点費用は別台帳を参照する。",
        "- 言語間にはDataset/領域/参照構造の差があり、言語単独の因果効果を主張しない。",
        "- Mainの停止規則は2回事後変更した。長さに依存する欠測、AI採点/人手未確認、既知v23の非支持87.5%と旧90%基準未達を明記する。",
        "- Calは調整に使っていない。旧Gate11/Phase12の達成や、一般的なRAG全体への保証として解釈しない。",
        "- 投稿前に著者が図表と本文の数値、主張、引用、投稿形式を照合し、教員の確認を受ける。", ""]
    (staging / "results_brief.md").write_text("\n".join(notes), encoding="utf-8")
    for path in staging.iterdir():
        require(not (output / path.name).exists(), "Preserve published artifacts")
        shutil.copy2(path, output / path.name)
    files = {p.name: sha(p) for p in output.iterdir() if p.is_file()}
    immutable(manifest_path, {"created_at_utc": now(), "files": files, "matplotlib_version": matplotlib.__version__,
        "numpy_version": np.__version__, "source_analyses": {r["cohort"]: sha(Path(config["state_dir"]) /
        r["cohort"] / "analysis.private.json") for r in results}, "all_annotations_sealed": True,
        "human_reviewed": False, "gate11_passed": False, "phase12_allowed": False})
    write(Path(config["state_dir"]) / "figures_completed.json", {"artifact_manifest_sha256": sha(manifest_path)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--publish-cohort", choices=("main", "cal"))
    args = parser.parse_args()
    config = load_config(args.config)
    if args.publish_cohort:
        publish_analysis(config, args.publish_cohort)
    else:
        create_figures(config)
    print(json.dumps({"figures_or_summary_saved": True}))
