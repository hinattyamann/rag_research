"""Detached completion watcher, finite workflow runner and allowlisted Git publisher."""

import argparse
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from common import alive, identity, load_config, now, read, require, run_owned, write

STEPS = ["review-main", "analyze-main", "publish-main", "prepare-cal", "collect-cal",
         "review-cal", "analyze-cal", "publish-cal", "figures"]
ARTIFACT_NAMES = {"main_summary.json", "cal_summary.json", "artifact_manifest.json", "annotation_cost.json", "results_brief.md",
    "primary_comparison.csv", "quality_and_operational_cost.csv", "collection_cost.csv", "threshold_sensitivity.csv"}
ARTIFACT_NAMES |= {f"{name}.{extension}" for name in ("01_order_vs_repeat", "02_quality_and_missingness",
    "03_collection_cost", "04_threshold_sensitivity") for extension in ("svg", "pdf", "png")}


def public_status(config, stage, *, error=None):
    main = read(Path(config["main_run"]) / "status.public.json")
    fields = ("state", "updated_at_utc", "attempts", "failed", "unknown", "completed_qa", "baseline_failed_qa",
              "rewrite_failed_qa", "processed_qa", "remaining_qa", "archived_external_attempts",
              "historical_unknown_responses", "external_reexecutions_started", "token_totals_complete")
    state = Path(config["state_dir"])
    ledger = read(state / "cli_ledger.json") if (state / "cli_ledger.json").exists() else {"invocations": []}
    progress = read(state / "progress.json") if (state / "progress.json").exists() else {}
    value = {"updated_at_utc": now(), "workflow": "fixed-v23-automation-v1", "stage": stage,
        "main": {k: main.get(k) for k in fields}, "progress": progress,
        "cli_invocations": len(ledger["invocations"]), "api_key_fallback": False,
        "git_publish_policy": config["git_publish_policy"],
        "error": error, "local_raw_data_is_not_transferred_by_git": True,
        "all_figures_completed": stage == "complete", "paper_written": False,
        "gate11_passed": False, "phase12_allowed": False}
    if Path(config["cal_run"]).exists():
        # No scores, candidate text or annotation labels are exposed before their complete seal.
        cal = {"baseline_success": 0, "baseline_failed": 0, "rewrite_success": 0, "rewrite_failed": 0,
               "completed": (Path(config["cal_run"]) / "collection_completed.json").exists()}
        for language in ("en", "ja"):
            folder = Path(config["cal_run"]) / language
            for p in (folder / "baseline").glob("*/record.json"):
                status = read(p).get("status")
                cal["baseline_success" if status == "ok" else "baseline_failed"] += status != "started"
            for p in (folder / "internal").glob("*/rewrite.json"):
                status = read(p).get("status")
                cal["rewrite_success" if status == "ok" else "rewrite_failed"] += status != "started"
        value["cal"] = cal
    return value


def status_documents(config, stage, *, error=None):
    value = public_status(config, stage, error=error)
    repo = Path(config["repo"])
    write(repo / config["public_status_json"], value)
    local = datetime.fromisoformat(value["updated_at_utc"]).astimezone(ZoneInfo("Asia/Tokyo"))
    lines = ["# 固定v23 自動実行の状況", "", f"更新: {local:%Y-%m-%d %H:%M:%S JST}", "",
        f"現在の工程: **{stage}**", "", f"Codex CLI起動予約数: {value['cli_invocations']}（ChatGPT認証、APIキーへの切替なし）", "",
        "収集待ち・GPU収集・通常のPython集計・Git反映ではCodexを呼ばない。CLIは匿名AI採点でのみ起動する。", "",
        "| Main項目 | 値 |", "|---|---:|"]
    lines.extend(f"| {k} | {v} |" for k, v in value["main"].items())
    if "cal" in value:
        lines += ["", "| Cal項目 | 値 |", "|---|---:|"]
        lines.extend(f"| {k} | {v} |" for k, v in value["cal"].items())
    if value["progress"]:
        lines += ["", "直近の作業: `" + str(value["progress"]) + "`"]
    if error:
        lines += ["", "停止理由: " + error]
    lines += ["", "## 工程と完了条件", "",
        "Main収集 → 日英全品質/Expected採点封印 → Main解析 → Cal進行条件確認/登録 → Cal収集 → 日英全採点封印 → Cal解析 → 図表/集計/結果説明資料。",
        "正常な完了状態を検知して進み、時刻だけでCalを開始しない。比較数不足・未知/他エラー・利用枠不足では保存して停止する。",
        "実行中のMain unknownは応答待ちのstarted記録を含む。終了済みの応答喪失と同一視しない。", "",
        "外的中断の許可済み再実行がある場合、元要求はarchived_external_attempts/historical_unknown_responsesに残す。"
        "現在のunknownとは別で、過去の応答/最終費用が復元された意味ではない。", "",
        "## ノートPCからの確認", "", "このBranchの最新を取得し、このファイルと `data/manifests/fixed_v23_automation_status_v1.json` を読む。",
        "集計・図表は `reports/fixed_v23_order_study_v1/`。工程の切替・完了・予期しない停止など、意味のある区切りでcommit/pushする。定時送信はしない。",
        "GitHubの更新時刻は最後に反映した区切りを示す。収集中は更新がなくても停止とは限らない。ローカルの状態記録は約1分ごとに更新する。",
        "Raw、環境、モデル、採点途中のラベルはGitで転送しない。研究室PC側の稼働を維持する。",
        "同じBranchで同じ箇所を両PCから同時編集しない。ノート側で収集を二重起動しない。", "",
        "## 残る著者作業", "", "図表完了後も、論文執筆・数値/主張/引用の照合・教員確認・投稿形式への整形・提出は未実施。",
        "旧Gate11/Phase12は未達のまま。限界と欠測を含めて結果を説明し、採択を保証するものではない。", ""]
    path = repo / config["public_status_markdown"]
    path.write_text("\n".join(lines), encoding="utf-8")
    write(Path(config["state_dir"]) / "status.json", value)
    return value


def publish_git(config):
    """Only named status/aggregate artifacts may be staged. Never merge/rebase/force."""
    repo = Path(config["repo"])

    def git(*args):
        return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, timeout=60, check=True).stdout.strip()

    require(git("branch", "--show-current") == config["branch"], "Unexpected branch; Git publication suspended")
    require(git("remote", "get-url", config["remote"]) == config["remote_url"], "Git remote changed")
    require(not git("diff", "--cached", "--name-only"), "Other staged changes exist; do not commit them")
    paths = [config["public_status_json"], config["public_status_markdown"]]
    output = Path(config["public_dir"])
    paths += [str((output / name).relative_to(repo)) for name in sorted(ARTIFACT_NAMES) if (output / name).is_file()]
    git("fetch", config["remote"])
    ahead, behind = map(int, git("rev-list", "--left-right", "--count", "HEAD...@{upstream}").split())
    require(behind == 0, "Remote advanced/diverged; preserve local work and suspend publication")
    git("add", "--", *paths)
    staged = git("diff", "--cached", "--name-only").splitlines()
    require(set(staged) <= set(paths), "Unexpected staged changes; do not commit them")
    if staged:
        git("diff", "--cached", "--check")
        git("commit", "-m", "固定v23自動実行の進捗と確定成果を更新", "--", *staged)
    git("push", config["remote"], config["branch"])
    require(git("rev-parse", "HEAD") == git("rev-parse", "@{upstream}"), "Remote tip differs after push")
    return {"at_utc": now(), "commit": git("rev-parse", "HEAD"), "pushed": True, "previous_ahead": ahead}


def main_ready(config):
    run = Path(config["main_run"])
    status, control = read(run / "status.public.json"), read(run / "control.json")
    require(status["state"] in {"collecting", "awaiting_scoring"}, "Main stopped before scoring readiness")
    if status["state"] == "collecting":
        require(alive(control.get("supervisor", {})),
                "Main collector exited while status still says collecting; preserve unknown outcomes and inspect supervisor.log")
        return False
    if status["state"] != "awaiting_scoring" or alive(control.get("supervisor", {})) or alive(control.get("child", {})):
        return False
    require(status["collection_completed"] is True and status["processed_qa"] == 40 and status["remaining_qa"] == 0
            and status["unknown"] == 0 and status["unhandled_failure_records"] == 0,
            "Main is not a complete known-outcome collection")
    for language in ("en", "ja"):
        for leaf in ("quality/packet.json", "quality/annotations.blank.json", "quality/units/packet.json",
                     "quality/units/annotations.blank.json"):
            require((run / language / leaf).is_file(), "Main annotation packet is incomplete")
    require((run / "failure_inventory.json").is_file(), "Main failure inventory is missing")
    return True


def serve(config_path):
    config = load_config(config_path)
    require(config["git_publish_policy"] == "events_only", "Publish only meaningful workflow events")
    from rag_research.experiments.storage import run_lock

    state = Path(config["state_dir"])
    stage = "waiting_main"
    last_status = 0.

    def heartbeat(event=False, error=None):
        nonlocal last_status
        load_config(config_path)
        require(datetime.now().timestamp() < datetime.fromisoformat(config["deadline_utc"]).timestamp(),
                "Finite workflow deadline reached")
        if (state / "stop.request").exists():
            if stage == "collect-cal":
                write(Path(config["cal_run"]) / "stop.request", {"requested_at_utc": now()})
            else:
                raise ValueError("Workflow stop requested")
        current = time.monotonic()
        if event or current - last_status >= 60:
            status_documents(config, stage, error=error)
            last_status = current
        if event:
            try:
                write(state / "git_publication.json", publish_git(config))
            except Exception as failure:
                write(state / "git_publication.json", {"at_utc": now(), "pushed": False,
                    "error": type(failure).__name__ + ": " + str(failure)[:300]})

    with run_lock(state / "service-lock"):
        write(state / "owner.json", identity(__import__("os").getpid()))
        try:
            heartbeat(event=True)
            while not main_ready(config):
                heartbeat()
                time.sleep(config["poll_seconds"])
            for stage in STEPS:
                heartbeat(event=True)
                if stage in {"publish-main", "publish-cal", "figures"}:
                    argv = [config["uv"], "run", "--offline", "--frozen", "--project", config["repo"], "python",
                            str(Path(__file__).with_name("figures.py")), "--config", str(config_path)]
                    if stage.startswith("publish-"):
                        argv += ["--publish-cohort", stage.split("-")[1]]
                    timeout = 1800
                else:
                    argv = [config["uv"], "run", "--offline", "--frozen", "--project",
                        str(Path(config["checkout"]) / "environments/embedding_gpu"), "python",
                        str(Path(__file__).with_name("pipeline.py")), "--config", str(config_path), "--action", stage]
                    timeout = 259200 if stage == "collect-cal" else 86400 if stage.startswith("review-") else 3600
                run_owned(argv, cwd=config["checkout"], receipt=state / "steps" / (stage + ".json"),
                          timeout=timeout, heartbeat=heartbeat)
                heartbeat(event=True)
            stage = "complete"
            heartbeat(event=True)
        except BaseException as failure:
            stage = "stopped" if (state / "stop.request").exists() else "failed"
            error = type(failure).__name__ + ": " + str(failure)[:400]
            (state / "error.log").write_text(traceback.format_exc(), encoding="utf-8")
            status_documents(config, stage, error=error)
            try:
                write(state / "git_publication.json", publish_git(config))
            except Exception as publication_failure:
                write(state / "git_publication.json", {"at_utc": now(), "pushed": False,
                    "error": str(publication_failure)[:300]})
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    # This service runs in the uv-managed repository environment, not the inference checkout.
    sys.path.insert(0, str(Path(read(args.config)["checkout"]) / "src"))
    serve(args.config)
