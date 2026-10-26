"""Continue the four preregistered five-QA sessions without changing their inputs."""

from rag_research.experiments.frozen_trace import require


def collect_language(runner, config, output, record_session):
    """A finite schedule, stopping on health errors or an unexpected progress state."""
    for stage in ("baseline", "internal"):
        previous = 0
        for session in range(1, 5):
            result = runner(config, output, stage=stage)
            record_session(stage, session, result)
            if result.get("stage", "").endswith("_stopped"):
                return {"collection_completed": False, "reason": result["reason"]}
            if stage == "baseline":
                count = result.get("baseline_count", result.get("processed_qa"))
                complete = result.get("stage") == "baseline" and count == 20
                if complete:
                    require(result.get("baseline_ok") == 20, "All selected baselines must be healthy")
            else:
                count = result.get("trace_count", result.get("processed_qa"))
                complete = count == 20 and result.get("quality_status") == "pending_external_blinded_annotation"
                if complete:
                    require(result.get("baseline_failures") == 0
                            and set(result.get("judge_status_counts", {})) <= {"ok", "not_applicable"}
                            and all(status == "ok" for status in result.get("rewrite_statuses", [])),
                            "All selected internal paths must be healthy")
            require(type(count) is int and previous < count <= 20 and count - previous <= 5,
                    "Each planned session must advance by at most five selected QA")
            if complete:
                break
            require(result.get("stage") == stage + "_batch_complete", "Unexpected collection state")
            previous = count
        else:
            raise ValueError("Four planned sessions did not finish all twenty selected QA")
    return {"collection_completed": True, "selected_qa": 20,
            "quality_and_expected_sealed": False, "scientific_adoption_claimed": False}
