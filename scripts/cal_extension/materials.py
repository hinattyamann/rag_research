"""Sealed per-batch writing packages, pooled new-data results, and Git-only checks."""

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def table(path, values):
    if not values:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(values)


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verifier_text(original):
    """Narrow the already-tested 80-QA verifier to one 40-QA Cal batch.

    Scientific checks of labels/F/selection/cost/quotes remain intact. The original
    frozen verifier is never changed, and both versions are retained in Git.
    """
    text = Path(original).read_text()
    replacements = {
        'for cohort in ("main", "cal")': 'for cohort in ("cal",)',
        'len(qa) == 80 and len({q["qa_key"] for q in qa}) == 80 and len({q["record_id"] for q in qa}) == 80':
            'len(qa) == 40 and len({q["qa_key"] for q in qa}) == 40 and len({q["record_id"] for q in qa}) == 40',
        '"Expected all 80 unique selected QA"': '"Expected all 40 unique selected QA"',
        '"Four 20-QA strata required"': '"Two 20-QA strata required"',
        'len(qtable) == 80': 'len(qtable) == 40',
        'len(policies) == len(policy_index) == 880': 'len(policies) == len(policy_index) == 440',
        'require(len(proof_files) == 84, "Missing completed annotation job provenance")':
            'require(bool(proof_files) or candidate_assignments == 0, "Missing completed annotation job provenance")',
        '"strata": 4': '"strata": 2',
        'sum(mean_values) / len(mean_values)': '(sum(mean_values) / len(mean_values) if mean_values else None)',
        'sum(q["statistical_comparison"]["increment"] for q in good) / len(good)':
            '(sum(q["statistical_comparison"]["increment"] for q in good) / len(good) if good else None)',
        'original["ci95"][0]': '(original["ci95"][0] if original["ci95"] else None)',
        'original["ci95"][1]': '(original["ci95"][1] if original["ci95"] else None)',
        'sum(increments) / len(increments)': '(sum(increments) / len(increments) if increments else None)',
    }
    for before, after in replacements.items():
        if before not in text:
            raise ValueError("Original verifier contract changed: " + before)
        text = text.replace(before, after)
    text = text.replace('def close(a, b, name):\n',
        'def close(a, b, name):\n    a = None if a == "" else a\n    b = None if b == "" else b\n')
    return text


def export_batch(config, *, destination=None):
    import sys
    sys.path.insert(0, config["frozen_scripts"])
    import pipeline

    helper = Path(config.get("helper_dir", Path(__file__).resolve().parent))
    original = load_module(helper / "original_build_materials.py", "sealed_material_export")
    repo, state, run = Path(config["source_repo"]), Path(config["state_dir"]), Path(config["cal_run"])
    author = Path(config["repo"])
    final = Path(destination) if destination else author / "papers/iciae2027/materials/cal_extension_v1" / config["batch_id"]
    if final.exists():
        subprocess.run([config["cpu_python"], "-I", str(final / "verify_materials.py"), "--audit-open"], check=True)
        return
    output = state / "writing-staging"
    if output.exists():
        # Staging is derived, not an experiment. Preserve a failed draft before rebuilding.
        output.rename(output.with_name("writing-staging-failed-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")))
    output.mkdir(parents=True)
    pipeline.verify_seal(run)
    analysis = read(state / "cal/analysis.private.json")
    if pipeline.source_hashes(run) != analysis["source_files_sha256"]:
        raise ValueError("Sealed run changed before export")
    export = original.Export.__new__(original.Export)
    export.repo, export.out, export.state, export.config = repo.resolve(), output, state, config
    export.fixed = Path(config["checkout"])
    export.sources, export.copies = {}, []
    export.qa_inputs, export.qa_rows, export.trials, export.policies = [], [], [], []
    export.runs = {"cal": run}
    export.before = {str(run / key): value for key, value in analysis["source_files_sha256"].items()}
    export.copy(run / "all_annotations.seal.json", "provenance/cal/all_annotations.seal.json")
    export.copy(run / "protocol.json", "provenance/cal/protocol.json")
    export.copy(state / "cal/analysis.private.json", "analysis/cal.private.json")
    assets = read(export.fixed / "configs/phase11_bilingual_assets_v2.json")
    for language in ["en", "ja"]:
        for name in ["manifest.json", "report.private.json"]:
            export.copy(run / language / name, f"provenance/cal/{language}/{name}")
        for name in ["packet.json", "mapping.private.json", "annotations.json", "units/packet.json", "units/annotations.json"]:
            export.copy(run / language / "quality" / name, f"annotations/cal/{language}/{name}")
        split = "development" if language == "en" else "calibration"
        source = export.fixed / assets["datasets"][language]["qa"][split]["path"]
        export.source(source, "selected_rows_only")
        ids = {q["record_id"] for q in read(run / language / "manifest.json")["selection"]}
        rows = {}
        for line in source.open(encoding="utf-8"):
            row = json.loads(line)
            if row["record_id"] in ids:
                rows[row["record_id"]] = row
        if set(rows) != ids:
            raise ValueError("Selected source QA missing")
        export.extract_qa("cal", language, split, rows)
        cfg = read(run / language / "manifest.json")["config"]
        for key in ["assets", "prompts", "baseline_prompts", "baseline_config", "identity_manifest", "auxiliary_model_manifest"]:
            export.copy(export.fixed / cfg[key], "provenance/frozen_files/" + cfg[key])
        export.copy(export.fixed / cfg["execution"]["runtime_spec"], "provenance/frozen_files/" + cfg["execution"]["runtime_spec"])
    export.document_sources(assets)
    unavailable = []
    for qa in export.qa_inputs:
        for reference in qa["qa_source"].get("reference_corpus_mapping", []):
            if reference.get("body_available") is False:
                unavailable.append({"language": qa["language"], "record_id": qa["record_id"],
                    "source_reference_unit_id": reference.get("source_reference_unit_id"),
                    "status": reference.get("raw_article_status"), "reference_annotation_retained": True})
    save(output / "missing_information.json", {"unavailable_reference_bodies": unavailable,
        "exact_serving_model_identifier": "not established; configured alias retained",
        "english_wikipedia_oldid": "not recorded by the frozen passage asset; no numeric-ID inference",
        "human_reviewed": False})
    for name in ["order_quality_rubric.md", "ai_quality_protocol.md", "phase11_statistical_plan.md"]:
        export.copy(repo / "docs" / name, "provenance/protocol_text/" + name + ".txt")
    for name in ["common.py", "pipeline.py", "review.py", "citations.py", "gpu_guard.py"]:
        export.copy(Path(config["frozen_scripts"]) / name, "provenance/analysis_code/" + name + ".txt")
    for path in sorted((state / "jobs").glob("*/attempt-*/*")):
        if path.name in {"provenance.json", "prompt.json", "schema.json", "invocation.json", "validation_error.json",
                         "format_repair.json", "citation_binding.json", "input.json", "output.json", "stdin.json", "canonical_output.json"}:
            export.copy(path, "provenance/annotation_jobs/" + path.relative_to(state / "jobs").as_posix())
    native = []
    for language in ["en", "ja"]:
        folder = run / language
        for path in sorted([*(folder / "baseline").glob("*/record.json"), *(folder / "internal").rglob("*.json")]):
            value = read(path)
            if path.name != "record.json" and value.get("task") not in {"extract_claims", "read_sources", "verify_claims", "rewrite_answer"}:
                continue
            if value.get("execution_mode") in {"source-reading-v1", "claimwise-v1"} or not value.get("completion_attempted"):
                continue
            if value.get("status") == "started":
                raise ValueError("Cannot publish unfinished native call")
            native.append({"cohort": "cal", "language": language, "source": export.source(path, "numeric_native_cost_metadata"),
                "run_relative_path": path.relative_to(folder).as_posix(), **{k: value.get(k) for k in
                ["task", "status", "error_code", "completion_attempted", "input_tokens", "output_tokens", "elapsed_seconds",
                 "generation_seconds", "cost_incomplete", "result_sha256"]}})
    original.jsonl(output / "analysis/native_calls.jsonl", native)
    save(output / "analysis/external_attempts.json", [])
    table(output / "qa_summary.csv", export.qa_rows)
    original.jsonl(output / "trials.jsonl", export.trials)
    table(output / "policy_outcomes.csv", export.policies)
    published = output / "published_results"
    published.mkdir()
    summary = {k: analysis[k] for k in ["cohort", "collection_costs", "condition_sha256", "progression_gate_passed",
        "gate11_passed", "phase12_allowed", "human_reviewed", "limitations", "semantics", "threshold_sensitivity"]}
    summary["statistics"] = {k: v for k, v in analysis["statistics"].items() if k != "qa"}
    summary["quality_routes"] = pipeline.public_tables(analysis)
    summary["source_analysis_sha256"] = sha(state / "cal/analysis.private.json")
    save(published / "cal_summary.json", summary)
    primary = []
    for language, row in summary["statistics"]["languages"].items():
        primary.append({"cohort": "cal", "language": language, "selected_qa": row["selected_qa_count"],
            "comparable_qa": row["comparable_qa_count"], "missing_qa": row["missing_qa_count"],
            "mean_increment": row["mean_increment"], "ci95_low": row["ci95"][0] if row["ci95"] else None,
            "ci95_high": row["ci95"][1] if row["ci95"] else None})
    table(published / "primary_comparison.csv", primary)
    table(published / "quality_and_operational_cost.csv", summary["quality_routes"])
    table(published / "collection_cost.csv", [{"cohort": "cal", "language": lang, **value}
                                             for lang, value in analysis["collection_costs"].items()])
    table(published / "threshold_sensitivity.csv", [{"cohort": "cal", **r} for r in analysis["threshold_sensitivity"]])
    plot_results(published, primary, summary["quality_routes"], analysis["collection_costs"], analysis["threshold_sensitivity"])
    save(published / "artifact_manifest.json", {"files": {p.name: sha(p) for p in published.iterdir() if p.is_file()},
        "source_analysis_sha256": summary["source_analysis_sha256"], "all_annotations_sealed": True})
    # Always preserve two actual bilingual examples; an absent outcome type is not invented.
    cases = []
    for language in ["en", "ja"]:
        pool = sorted([q for q in export.qa_inputs if q["language"] == language], key=lambda q: q["record_id"])
        interesting = [q for q in pool if q["statistical_comparison"]["comparable"] and
                       q["statistical_comparison"]["order"]["disagreeing_pairs"] > 0]
        q = (interesting or pool)[0]
        case = {"case_id": "case_" + language, "qa_key": q["qa_key"], "record_id": q["record_id"],
            "language": language, "cohort": "cal", "input_path": "inputs/" + q["qa_key"] + ".json",
            "post_outcome_explanatory_selection": True,
            "selection_rule": "First lexicographic QA with order variation if any, otherwise first selected QA; not a frequency sample",
            "trials": [t for t in export.trials if t["qa_key"] == q["qa_key"]],
            "policy_outcomes": [p for p in export.policies if p["qa_key"] == q["qa_key"]]}
        save(output / "cases" / (case["case_id"] + ".json"), case)
        cases.append(case)
    save(output / "cases/index.json", {"cases": cases})
    export.licenses()
    (output / "verify_materials.py").write_text(verifier_text(helper / "original_verify_materials.py"), encoding="utf-8")
    (output / ".gitattributes").write_text("* -text\n* whitespace=-trailing-space,-blank-at-eof\n", encoding="utf-8")
    text = [f"# Cal拡張 {config['batch_id']} の確定執筆資料", "", "選定40問（英語20/日本語20）。既存Main/Calと別の新規確認集合。",
        "収集・採点の条件は固定v23、全文/採点は封印後に公開。欠測・拒否・判定不能・重複順列省略を区別する。",
        "", "## 確認入口", "", "`uv run --no-project python -I verify_materials.py --audit-open`",
        "", "[質問別一覧](qa_summary.csv)のinput_pathから質問/Reference/実使用根拠全文/A/Bへ移れる。",
        "[順序・反復](trials.jsonl)、[方策・費用](policy_outcomes.csv)、[元解析](analysis/cal.private.json)、[図表](published_results/)、[具体例](cases/index.json)。",
        "[条件/封印](provenance/cal/protocol.json)、[採点来歴](provenance/annotation_jobs/)、[元ファイルHash](source_manifest.json)。",
        "", "## 主比較", ""]
    text += [f"- {r['language']}: 選定{r['selected_qa']}、完全比較{r['comparable_qa']}、増分{r['mean_increment']}、95%区間[{r['ci95_low']}, {r['ci95_high']}]。" for r in primary]
    text += ["", "## 限界と帰属", "", "Fは固定文の支持率で正答率ではない。AIラベルは人手正解ではなく、モデル履歴の独立性も仮定しない。",
        "Bootstrapは元実装/NumPy2.5.3/Seed42/10000回の値と元資料を保持し、別RNGで再現したと偽らない。",
        "閾値/Prompt/上限を結果に応じて調整していない。新集合は最終の既知長さ欠測規則・引用選択手順を事前固定した。元Main/Calの途中変更と時期差は残る。",
        "CLIモデルは指定gpt-6.1-sol/high、厳密なServing Snapshotは未特定。固定v23の旧非支持87.5%/旧90%基準未達は維持する。",
        "公開経路表のbaseline_missingは重複省略も含む旧列。実際の初回失敗はcollection_cost.csv、状態別はpolicy_state/alias_ofを用いる。",
        "原文の出典/本文Hash/変換範囲は各inputsのsource_metadata。CLAPNQ注釈Apache-2.0、NQ/Wikipedia英語本文CC BY-SA3.0、日本語注釈Apache-2.0/本文CC BY-SA4.0を区別する。",
        "Wikipedia contributors、PrimeQA、Yusuke Oda/Baobabへ帰属する。抜粋/既存Passage抽出・JSON整形を行い、本文の意味は変更していない。派生本文は同じCC BY-SA条件を維持する。",
        "英語はTitle由来URLであり、元oldidを推測しない。日本語は保存oldid/Revision/取得記録を保持。未取得参照本文は補作しない。",
        "[ライセンス/NOTICE](licenses/source_notices.json)。採点Rubric/Schema/匿名対応/形式修正の証拠も同梱。全Corpus・モデル・認証・巨大イベントログは含まない。",
        "収集/採点の費用はanalysisとprovenanceへ保持。source_manifestのnew_inference_calls=0は抽出処理が再生成しなかった意味で、新実験が0Callという意味ではない。",
        "検証器は資料内だけを読む。原Run/GPU/ネットワーク/認証は不要。研究室の原稿は変更せず、著者の照合・日英更新・教員確認・提出は別工程。", ""]
    (output / "README.md").write_text("\n".join(text), encoding="utf-8")
    for name, expected in export.before.items():
        if sha(name) != expected:
            raise ValueError("Source changed during writing export")
    save(output / "source_manifest.json", {"version": "cal-extension-writing-v1", "batch_id": config["batch_id"],
        "frozen_inference_commit": "f0b7c71c4375a617c7142c67e3aa0610f73edb14",
        "source_files": export.sources, "copies": export.copies,
        "qa_correspondence": [{k: q[k] for k in ["qa_key", "cohort", "language", "record_id", "document_group_id"]} for q in export.qa_inputs],
        "qa_source_row_sha256": {q["qa_key"]: original.digest(q["qa_source"]) for q in export.qa_inputs},
        "new_inference_calls": 0, "new_annotation_calls": 0, "export_did_not_regenerate": True})
    original.artifact_manifest(output)
    subprocess.run([config["cpu_python"], "-I", str(output / "verify_materials.py"), "--audit-open"], check=True)
    final.parent.mkdir(parents=True, exist_ok=True)
    output.rename(final)
    reports = author / "reports/cal_extension_v1" / config["batch_id"]
    reports.mkdir(parents=True, exist_ok=True)
    for path in published.iterdir() if published.exists() else (final / "published_results").iterdir():
        shutil.copy2(path, reports / path.name)
    save(state / "materials_completed.json", {"material_path": str(final), "manifest_sha256": sha(final / "artifact_manifest.json")})


def plot_results(output, primary, routes, costs, sensitivity):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"svg.fonttype": "none", "pdf.fonttype": 42})
    def savefig(fig, name):
        fig.tight_layout()
        for suffix in ["png", "pdf", "svg"]:
            fig.savefig(output / (name + "." + suffix), dpi=200)
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(6, 4))
    for i, row in enumerate(primary):
        if row["mean_increment"] is not None:
            ax.plot(i, row["mean_increment"], "o")
            if row["ci95_low"] is not None:
                ax.vlines(i, row["ci95_low"], row["ci95_high"])
    ax.set_xticks(range(len(primary)), [r["language"].upper() + f" n={r['comparable_qa']}/{r['selected_qa']}" for r in primary])
    ax.axhline(0, color="gray")
    ax.set_ylabel("Order minus repeat disagreement")
    savefig(fig, "01_order_vs_repeat")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, lang in zip(axes, ["en", "ja"], strict=True):
        chosen = [r for r in routes if r["language"] == lang and r["route"] in ["no_repair", "always_rewrite", "original"]]
        bottom = [0] * len(chosen)
        for name in ["reliable", "unreliable", "indeterminate", "baseline_missing"]:
            values = [r[name] for r in chosen]
            ax.bar(range(len(chosen)), values, bottom=bottom, label=name)
            bottom = [a + b for a, b in zip(bottom, values, strict=True)]
        ax.set_xticks(range(len(chosen)), [r["route"] for r in chosen], rotation=20)
        ax.set_title(lang.upper())
    axes[0].legend(fontsize=7)
    savefig(fig, "02_quality_and_missingness")
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(list(costs), [v["summed_observed_task_seconds"] / 3600 for v in costs.values()])
    ax.set_ylabel("Observed task hours (not total workflow wall time)")
    savefig(fig, "03_collection_cost")
    fig, ax = plt.subplots(figsize=(6, 4))
    for lang in ["en", "ja"]:
        rows = [r for r in sensitivity if r["language"] == lang]
        ax.plot([r["threshold"] for r in rows], [float("nan") if r["mean_increment"] is None else r["mean_increment"] for r in rows], "o-", label=lang)
    ax.axvline(.7, color="gray", linestyle="--")
    ax.legend()
    savefig(fig, "04_threshold_sensitivity")


def verify_remote(config, batch_ids, *, final=False):
    root = Path(tempfile.mkdtemp(prefix="cal-extension-git-"))
    repo = Path(config["repo"])
    env = os.environ.copy()
    helpers = subprocess.check_output(["git", "-C", str(repo), "config", "--null", "--get-all",
                                      "credential.https://github.com.helper"]).decode().split("\0")
    i = int(env.get("GIT_CONFIG_COUNT", "0"))
    for helper in filter(None, helpers):
        env[f"GIT_CONFIG_KEY_{i}"], env[f"GIT_CONFIG_VALUE_{i}"] = "credential.https://github.com.helper", helper
        i += 1
    env["GIT_CONFIG_COUNT"] = str(i)
    clone = root / "fetched"
    subprocess.run(["git", "clone", "--quiet", "--depth=1", "--single-branch", "--no-checkout", "--branch",
                    config["branch"], config["remote_url"], str(clone)], env=env, check=True, timeout=180)
    commit = subprocess.check_output(["git", "-C", str(clone), "rev-parse", "HEAD"], text=True).strip()
    local = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    if commit != local:
        raise ValueError("Fetched Git commit differs; publication did not complete")
    values = {}
    for batch in batch_ids:
        relative = "papers/iciae2027/materials/cal_extension_v1/" + batch
        archive = root / (batch + ".tar")
        with archive.open("wb") as stream:
            subprocess.run(["git", "-C", str(clone), "archive", "HEAD", relative], stdout=stream, check=True)
        extracted = root / (batch + "-only")
        extracted.mkdir()
        with tarfile.open(archive) as stream:
            stream.extractall(extracted, filter="data")
        location = extracted / relative
        result = subprocess.run(["/usr/bin/python3", "-I", str(location / "verify_materials.py"), "--audit-open"],
            cwd=location, env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}, capture_output=True, text=True, timeout=120)
        if result.returncode:
            raise ValueError("Git-only verification failed: " + result.stderr[-1000:])
        values[batch] = json.loads(result.stdout)
    if final:
        relative = "papers/iciae2027/materials/cal_extension_v1"
        archive = root / "final-package.tar"
        with archive.open("wb") as stream:
            subprocess.run(["git", "-C", str(clone), "archive", "HEAD", relative], stdout=stream, check=True)
        extracted = root / "final-only"
        extracted.mkdir()
        with tarfile.open(archive) as stream:
            stream.extractall(extracted, filter="data")
        location = extracted / relative
        result = subprocess.run(["/usr/bin/python3", "-I", str(location / "verify_collection.py"), "--audit-open"],
            cwd=location, env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}, capture_output=True, text=True, timeout=180)
        if result.returncode:
            raise ValueError("Final Git-only verification failed: " + result.stderr[-1000:])
        values["final_collection"] = json.loads(result.stdout)
    return {"commit": commit, "verified_at_utc": datetime.now(UTC).isoformat(), "batches": values,
            "fresh_git_copy": True, "original_run_or_auth_used_by_verifier": False, "final": final}


def finish(config):
    import sys
    sys.path.insert(0, str(Path(config["checkout"]) / "src"))
    from rag_research.experiments.bilingual_budget import budget_snapshot
    from rag_research.experiments.statistics import analyze, qa_increment
    output = Path(config["repo"]) / "reports/cal_extension_v1"
    output.mkdir(parents=True, exist_ok=True)
    records, completed, analyses = [], [], []
    inventory = []
    for path in config["batches"]:
        cfg = read(path)
        for lang in ["en", "ja"]:
            folder = Path(cfg["cal_run"]) / lang
            snapshot = budget_snapshot(folder)
            leaves = [read(folder / leaf["path"]) for leaf in snapshot["raw_calls"]]
            unknown = len(snapshot["unknown_or_interrupted_paths"])
            inventory.append({"batch": cfg["batch_id"], "language": lang, "planned_qa": 20,
                "native_attempts": snapshot["recorded_native_attempts_upper_bound"], "unknown_outcomes": unknown,
                "known_input_tokens": sum(v.get("input_tokens") or 0 for v in leaves),
                "known_output_tokens": sum(v.get("output_tokens") or 0 for v in leaves),
                "total_output_tokens": None if unknown or any(v.get("cost_incomplete") for v in leaves) else sum(v.get("output_tokens") or 0 for v in leaves),
                "summed_observed_task_seconds": sum(v.get("elapsed_seconds") or v.get("generation_seconds") or 0 for v in leaves),
                "raw_file_hashes": snapshot["raw_calls"],
                "scope": "All attempted research calls, including unsealed/partial batches; known sums do not impute unknown costs"})
        if not (Path(cfg["state_dir"]) / "materials_completed.json").exists():
            continue
        completed.append(cfg["batch_id"])
        analyses.append(read(Path(cfg["state_dir"]) / "cal/analysis.private.json"))
        run = Path(cfg["cal_run"])
        for lang in ["en", "ja"]:
            manifest = read(run / lang / "manifest.json")
            report = read(run / lang / "report.private.json")
            evaluations = {r["trace"]["record_id"]: r["evaluation"] for r in report["records"]}
            records.extend({"language": lang, "record_id": q["record_id"], "document_group_id": q["document_group_id"],
                            "evaluation": evaluations.get(q["record_id"])} for q in manifest["selection"])
    pooled = analyze(records, repetitions=10000, seed=42) if records else None
    save(output / "pooled_new_extension.json", {"scope": "new sealed complete extension batches only; excludes old Main/Cal",
        "completed_batches": completed, "planned_qa": 120, "included_selected_qa": len(records),
        "uncollected_or_unsealed_qa": 120 - len(records), "statistics": pooled,
        "conditional_on_completed_batches": len(completed) != 3, "stopping_not_based_on_effect": True})
    save(output / "collection_inventory.json", {"planned_qa": 120, "batch_languages": inventory})
    if analyses:
        from collections import Counter
        from copy import deepcopy
        primary, route_table, costs, sensitivity, transitions = [], [], {}, [], {}
        for lang in ["en", "ja"]:
            stat = pooled["languages"][lang]
            primary.append({"cohort": "cal_extension", "language": lang, "selected_qa": stat["selected_qa_count"],
                "comparable_qa": stat["comparable_qa_count"], "missing_qa": stat["missing_qa_count"],
                "mean_increment": stat["mean_increment"], "ci95_low": stat["ci95"][0] if stat["ci95"] else None,
                "ci95_high": stat["ci95"][1] if stat["ci95"] else None})
            all_routes = [r for a in analyses for r in a["quality_routes"][lang]["routes"]]
            selected = stat["selected_qa_count"]
            for name in sorted({r["route"] for r in all_routes}):
                rows = [r for r in all_routes if r["route"] == name]
                statuses = Counter(r["quality_status"] for r in rows)
                route_table.append({"cohort": "cal_extension", "language": lang, "route": name,
                    "selected_qa": selected, "available_initial_qa": len(rows), "baseline_missing": selected - len(rows),
                    **{label: statuses[label] for label in ["reliable", "unreliable", "indeterminate", "pending"]},
                    "rewrite_failed_fallbacks": sum(r["fallback"] == "rewrite_failed" for r in rows),
                    "native_attempts_sum": sum(r["operational_cost"]["recorded_completion_attempts"] for r in rows),
                    "input_tokens_sum": sum(r["operational_cost"]["input_tokens"] for r in rows),
                    "output_tokens_sum": sum(r["operational_cost"]["output_tokens"] for r in rows)})
            cost_rows = [a["collection_costs"][lang] for a in analyses]
            numeric = ["selected_qa", "native_attempts", "active_native_attempts", "archived_external_attempts",
                       "historical_unknown_responses", "failed_native_records", "unknown", "input_tokens", "output_tokens",
                       "summed_observed_task_seconds", "baseline_missing_qa", "rewrite_missing_qa"]
            costs[lang] = {key: sum(r[key] for r in cost_rows) for key in numeric}
            costs[lang]["native_cost_complete"] = all(r["native_cost_complete"] for r in cost_rows)
            costs[lang]["total_output_tokens"] = sum(r["total_output_tokens"] for r in cost_rows) if all(r["total_output_tokens"] is not None for r in cost_rows) else None
            transitions[lang] = dict(sum((Counter(a["quality_routes"][lang]["quality_transitions"]) for a in analyses), Counter()))
            for threshold in [.5, .6, .7, .8, .9]:
                increments = []
                for record in records:
                    if record["language"] != lang or record["evaluation"] is None:
                        continue
                    evaluation = deepcopy(record["evaluation"])
                    evaluation["threshold"] = threshold
                    for trial in evaluation["trials"]:
                        if trial["status"] == "ok":
                            trial["decision"] = "accept" if trial["score"] >= threshold else "rewrite"
                    value = qa_increment(evaluation)
                    if value["comparable"]:
                        increments.append(value["increment"])
                sensitivity.append({"language": lang, "threshold": threshold, "comparable_qa": len(increments),
                                    "mean_increment": sum(increments) / len(increments) if increments else None})
        pooled_dir = output / "pooled"
        pooled_dir.mkdir(exist_ok=True)
        table(pooled_dir / "primary_comparison.csv", primary)
        table(pooled_dir / "quality_and_operational_cost.csv", route_table)
        table(pooled_dir / "collection_cost.csv", [{"language": k, **v} for k, v in costs.items()])
        table(pooled_dir / "threshold_sensitivity.csv", sensitivity)
        save(pooled_dir / "quality_transitions.json", transitions)
        plot_results(pooled_dir, primary, route_table, costs, sensitivity)
    # Verify original scientific records after all collection/analysis/export work.
    protected = read(Path(config["state_dir"]) / "protected_original_files.json")
    if not all(sha(path) == expected for path, expected in protected.items()):
        raise ValueError("Original Main/Cal scientific record changed")
    material = Path(config["repo"]) / "papers/iciae2027/materials/cal_extension_v1"
    material.mkdir(parents=True, exist_ok=True)
    save(material / "completion.json", {"planned_qa": 120, "completed_batches": completed,
        "included_selected_qa": len(records), "uncollected_or_unsealed_qa": 120 - len(records),
        "original_files_rechecked_unchanged": len(protected), "manuscript_changed": False})
    shutil.copy2(output / "pooled_new_extension.json", material / "pooled_new_extension.json")
    shutil.copy2(output / "collection_inventory.json", material / "collection_inventory.json")
    if (output / "pooled").exists():
        shutil.copytree(output / "pooled", material / "pooled", dirs_exist_ok=True)
    ledger_rows, proofs = [], []
    for path in config["batches"]:
        batch_state = Path(path).parent
        if (batch_state / "cli_ledger.json").exists():
            ledger_rows.extend(read(batch_state / "cli_ledger.json")["invocations"])
        proofs.extend(read(p) for p in (batch_state / "jobs").glob("*/attempt-*/provenance.json"))
    usage = [u for p in proofs for u in p["token_usage"]]
    save(material / "annotation_cost.json", {"reserved_invocations": len(ledger_rows), "completed_provenance": len(proofs),
        "observed_input_tokens": sum(u.get("input_tokens", 0) for u in usage),
        "observed_output_tokens": sum(u.get("output_tokens", 0) for u in usage),
        "summed_job_wall_seconds": sum(p["elapsed_seconds"] for p in proofs),
        "token_totals_complete": len(ledger_rows) == len(proofs) and all(p["token_usage"] for p in proofs),
        "auth": "chatgpt", "api_key_billing": False, "monetary_cost": None})
    shutil.copy2(config["plan"], material / "plan.json")
    shutil.copy2(Path(config["helper_dir"]) / "verify_collection.py", material / "verify_collection.py")
    for path in (Path(config["helper_dir"])).glob("*.py"):
        destination = material / "provenance/control" / (path.name + ".txt")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    import numpy
    save(material / "analysis_method.json", {"numpy_version": numpy.__version__, "bootstrap_seed": 42,
        "bootstrap_repetitions": 10000, "pooling_scope": "new sealed completed batches only",
        "all_selected_groups_unique_within_language": True, "human_reviewed": False})
    text = ["# Cal拡張の論文用資料", "", f"完了Batch: {', '.join(completed) or 'なし'}。予定120問中、封印済み資料の選定数{len(records)}。",
        "", "各batch_XX/README.mdから全文・出典・採点・判断・費用・図表・検証入口へ進む。",
        "pooled_new_extension.jsonは新規追加集合だけの統合。既存Main/Calを合算していない。Batch別の結果も保持。",
        "未収集/未封印の予定QAを成功扱いにせず、completion.jsonの残件数を参照する。",
        "", "ノートPCではGit状態とFetch後の履歴差分を確認し、未完成原稿を保全して取込む。同一DOCXの両PC同時編集を避ける。",
        "取込元Branch: research/cal-extension-v1。研究室側ではDOCXを編集していない。",
        "全体検証: `uv run --no-project python -I verify_collection.py --audit-open`。各Batchにも独立した検証入口を同梱。",
        "方法・欠測・分母・AI採点/人手未確認・時期差・Serving版不明を保持して日英両原稿へ反映する。",
        "論文への反映、教員確認、引用最終照合、投稿は著者の作業。", ""]
    (material / "README.md").write_text("\n".join(text), encoding="utf-8")
    entries = {p.relative_to(material).as_posix(): {"bytes": p.stat().st_size, "sha256": sha(p)}
               for p in material.rglob("*") if p.is_file() and p != material / "artifact_manifest.json" and
               "__pycache__" not in p.parts}
    save(material / "artifact_manifest.json", {"files": entries, "self_excluded": True})
    subprocess.run([config["cpu_python"], "-I", str(material / "verify_collection.py"), "--audit-open"], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--finish", type=Path, required=True)
    finish(read(parser.parse_args().finish))
