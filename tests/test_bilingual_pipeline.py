"""Bilingual isolation, offline denominators, durable resume and blind label sealing."""

import json
import math
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
import yaml

from rag_research.data import study_assets
from rag_research.experiments import bilingual_quality as quality
from rag_research.experiments import bilingual_runner as runner
from rag_research.experiments.decisions import decide, decide_with_refusal
from rag_research.experiments.frozen_trace import digest
from rag_research.experiments.protocol import validate_task_contract
from rag_research.experiments.quality import make_packet, reconstruct
from rag_research.experiments.storage import read_json, write_json
from rag_research.generation.config import GenerationConfig
from rag_research.generation.context import PromptSpec
from rag_research.generation.local import GenerationError
from rag_research.retrieval import bilingual
from rag_research.retrieval.bm25 import build_bm25, tokenize
from rag_research.retrieval.common import RetrievalHit, file_hash
from rag_research.retrieval.dense import build_dense
from rag_research.retrieval.parent_metrics import retrieval_metrics

REPO = Path(__file__).resolve().parents[1]


def test_parent_metrics_keep_missing_units_and_count_each_parent_once():
    result = retrieval_metrics(["a1", "a2", "x", "b1"],
                               {"a1": "a", "a2": "a", "x": "x", "b1": "b"},
                               ["a", "b"], missing_source_units=["missing", "missing"], top_ks=(2, 5))
    assert result["gold_parent_recall_at_2"] == .5
    assert result["gold_parent_recall_at_5"] == 1
    assert result["ndcg_at_5"] == pytest.approx((1 + 1 / math.log2(5)) / (1 + 1 / math.log2(3)))
    assert result["missing_cited_source_unit_count"] == 1
    assert result["ranking_depth_available"] == 4 and "ndcg_at_10" not in result
    empty = retrieval_metrics(["a1"], {"a1": "a"}, [], missing_source_units=["missing"])
    assert not empty["scorable"] and empty["success_at_5"] is None and empty["ndcg_at_5"] is None
    assert empty["missing_cited_source_unit_count"] == 1
    for ids in (["a1", "a1"], ["unknown"]):
        with pytest.raises(ValueError):
            retrieval_metrics(ids, {"a1": "a"}, ["a"])


@pytest.fixture
def registry(tmp_path):
    def bind(name, contents="{}"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
        return {"path": name, "sha256": file_hash(path)}

    datasets = {}
    for language, source in (("en", "CLAPNQ"), ("ja", "baobab-trees/wikipedia-human-retrieval-ja")):
        qa = {}
        for split in ("development", "calibration", "evaluation"):
            row = {"record_id": language + "-" + split, "research_split": split, "source_dataset": source,
                   "question": "猫の色は？", "is_answerable": True, "source_title": "CAFE\u0301",
                   "gold_passage_ids": ["p1"], "reference_answers": ["REFERENCE-SECRET"],
                   "selected_sentences_by_reference": [], "gold_parent_ids": ["parent"],
                   "unavailable_cited_reference_ids": ["missing"], "document_group_id": "native-group",
                   "gold_passage_mapping_status": "audited_cited_article_and_source_reference_markup_mapping_v2",
                   "reference_corpus_metadata_offline_only": True, "reference_evidence": [],
                   "reference_corpus_mapping": []}
            qa[split] = bind(language + "/" + split + ".jsonl", json.dumps(row) + "\n")
        documents = [{"passage_id": "p1", "title": "色", "text": "猫は赤い。"},
                     {"passage_id": "p2", "title": "別の資料", "text": "犬は青い。"}]
        datasets[language] = {"language": language, "source_dataset": source, "qa": qa,
                              "gold_parent_unit": "test-source-unit",
                              "corpus": bind(language + "/corpus.jsonl", "".join(json.dumps(d) + "\n" for d in documents)),
                              "parent_map": bind(language + "/parents.jsonl", json.dumps({
                                  "parent_passage_id": "parent", "child_passage_ids": ["p1", "p2"]}) + "\n"),
                              "indexes": {k: bind(language + "/" + k + "/manifest.json") for k in ("bm25", "embedding")}}
    assets = {"schema_version": 1, "purpose": "phase11-bilingual-assets-candidate", "status": "candidate_not_frozen",
              "phase12_allowed": False, "datasets": datasets, "fixed_files": [bind("fixed-code.py")],
              "embedding": {"provider": "cuda", "device_id": 0, "use_tf32": 0, "threads": 6},
              "retrieval": {"kind": "hybrid", "candidate_count": 50, "rrf_constant": 60, "top_k": 5}}
    path = tmp_path / "assets.json"
    write_json(path, assets)
    return assets, path


def test_assets_hash_but_never_parse_evaluation_and_reject_changes(registry, tmp_path, monkeypatch):
    assets, path = registry
    original_read = Path.read_text

    def guarded_read(self, *args, **kwargs):
        assert self.name != "evaluation.jsonl", "Evaluation QA content must stay unopened"
        return original_read(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read)
    assert study_assets.load_assets(path, root=tmp_path) == assets
    for language in ("en", "ja"):
        with pytest.raises(ValueError, match="Development/Calibration"):
            study_assets.load_rows(assets, language, "evaluation", root=tmp_path)
        rows, _ = study_assets.load_rows(assets, language, "development", root=tmp_path)
        assert rows[0]["reference_answers"] == ["REFERENCE-SECRET"]
        if language == "en":
            assert rows[0]["document_group_id"] == "clapnq-title:café"
            assert rows[0]["gold_parent_ids"] == ["p1"] and rows[0]["unavailable_cited_reference_ids"] == []
        else:
            assert rows[0]["document_group_id"] == "native-group"
            assert rows[0]["unavailable_cited_reference_ids"] == ["missing"]
    (tmp_path / "fixed-code.py").write_text("changed")
    with pytest.raises(ValueError, match="changed"):
        study_assets.load_assets(path, root=tmp_path)
    with pytest.raises(ValueError, match="escapes"):
        study_assets.local_path("../outside", tmp_path)


@pytest.mark.parametrize("language", ["en", "ja"])
def test_factory_loads_real_indexes_with_legacy_english_and_explicit_japanese_schema(
        registry, tmp_path, monkeypatch, language):
    assets, _ = registry
    assets["embedding"]["model_root"] = "synthetic-model"
    data = assets["datasets"][language]
    path = tmp_path / data["corpus"]["path"]
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    for row in rows:
        row.update(source_dataset=data["source_dataset"], source_revision="fixed-test-revision",
                   text_sha256=__import__("hashlib").sha256(row["text"].encode()).hexdigest())
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    data["corpus"]["sha256"] = file_hash(path)

    class Tokenizer:
        def tokenize(self, texts, *, return_ids=True):
            return tokenize(texts, return_ids=return_ids)

        def bm25_config(self):
            return {"tokenization": "synthetic-fixture-v1"}

    class Encoder:
        truncated_count = 0
        tokenizer = Tokenizer()

        def __init__(self, root, *, threads, provider, device_id):
            assert (threads, provider, device_id) == (6, "cuda", 0)

        def retrieval_config(self, batch_size):
            return {"kind": "embedding", "algorithm": "synthetic-test", "batch_size": batch_size}

        def encode_passages(self, texts):
            values = np.zeros((len(texts), 384), dtype=np.float32)
            values[:, 0] = 1.
            return values

        encode_queries = encode_passages

    encoder = Encoder(None, threads=6, provider="cuda", device_id=0)
    for kind, build in (("bm25", build_bm25), ("embedding", build_dense)):
        index = tmp_path / language / (kind + "-actual")
        kwargs = {"tokenizer": encoder.tokenizer} if kind == "bm25" else {"batch_size": 2, "encoder": encoder}
        build(path, index, source_dataset=data["source_dataset"], **kwargs)
        data["indexes"][kind] = {"path": (index / "manifest.json").relative_to(tmp_path).as_posix(),
                                   "sha256": file_hash(index / "manifest.json")}
    monkeypatch.setattr(bilingual, "MultilingualE5Encoder", Encoder)
    retriever = bilingual.load_retriever(assets, language, root=tmp_path)
    assert retriever.bm25.manifest["corpus"].get("source_dataset", "CLAPNQ") == data["source_dataset"]
    assert retriever.search("猫は赤い。", top_k=1)
    with pytest.raises(ValueError, match="QA/Gold"):
        retriever.search({"question": "猫", "gold": "SECRET"})


@pytest.fixture
def connection(registry, tmp_path, monkeypatch):
    assets, asset_path = registry
    config = yaml.safe_load((REPO / "configs/order_phase8_v5.yaml").read_text())
    config.update(purpose="phase11-bilingual-development-candidate", language="ja", assets="assets.json",
                  baseline_config="baseline.yaml", baseline_prompts="initial.yaml", prompts="prompts.yaml")
    config["output_constraints"] = "none"
    config["auxiliary_runtime"]["context_tokens"] = 65536
    config["tasks"]["verify_claims"]["max_output_tokens"] = 512
    prompts = {"schema_version": 1, "claim_units": "verbatim-sentences-ja-v1",
               "tasks": {task: {"system": task} for task in ("extract_claims", "verify_claims", "rewrite_answer")}}
    baseline = {"retrieval": assets["retrieval"]}
    generation = GenerationConfig(context_tokens=65536, passage_tokens=1024)
    rows, qa_path = study_assets.load_rows(assets, "ja", "development", root=tmp_path)
    config_path = tmp_path / "config.yaml"
    for path in (config_path, tmp_path / "baseline.yaml", tmp_path / "initial.yaml", tmp_path / "prompts.yaml",
                 tmp_path / "scripts/run_bilingual_development.py"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixed test input")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(quality, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "load_config", lambda p: (config, assets, rows, qa_path, baseline, generation,
                                                        PromptSpec("test", "initial"), prompts))
    monkeypatch.setattr(runner, "model_identity", lambda: {"test": "initial"})
    monkeypatch.setattr(runner, "auxiliary_identity", lambda c: {"test": "auxiliary"})
    monkeypatch.setattr(runner, "execution_identity", lambda c: {})
    monkeypatch.setattr(runner, "execution_kwargs", lambda c: {})
    monkeypatch.setattr(runner, "auxiliary_server_kwargs", lambda c: {})
    mapping = study_assets.parent_map(assets, "ja", root=tmp_path)
    monkeypatch.setattr(runner, "parent_map", lambda *a: mapping)
    monkeypatch.setattr(quality, "parent_map", lambda *a: mapping)
    monkeypatch.setattr(quality, "load_assets", lambda p: assets)
    rubric = tmp_path / "docs/order_quality_rubric.md"
    rubric.parent.mkdir()
    rubric.write_text("Apply all three criteria.")
    state = {"calls": [], "servers": 0, "failure": None, "overflow": False, "bare_refusal": False,
             "config": config, "prompts": prompts, "multi_sentences": False}

    class Client:
        def render(self, messages):
            self.messages = deepcopy(messages)
            return json.dumps(messages)

        def tokenize(self, text, *, special=False):
            if state["overflow"] and self.messages[0]["content"] == "verify_claims":
                return [1] * 65536
            return list(map(ord, text))

        def detokenize(self, tokens):
            return "".join(map(chr, tokens))

        def complete(self, tokens, config, **kwargs):
            state["calls"].append(deepcopy(self.messages))
            task = self.messages[0]["content"]
            if task == state["failure"]:
                raise GenerationError("Synthetic preserved failure")
            if task == "initial":
                content = ("提示された根拠には、この質問に答えるための十分な情報がありません。"
                           if state["bare_refusal"] else "猫は赤い。[p1]")
                if state["multi_sentences"]:
                    content = "猫は赤い。犬は青い。"
            elif task == "rewrite_answer":
                content = "資料では、猫は赤い。[p1]"
            elif task == "read_sources":
                payload = json.loads(self.messages[1]["content"].removeprefix("Input JSON:\n"))
                assert set(payload) == {"question", "documents"} and "REFERENCE-SECRET" not in json.dumps(payload)
                content = json.dumps({"readings": [{"passage_id": d["passage_id"], "actor": "Fixture",
                    "action": "Fixture", "quote": d["text"]} for d in payload["documents"]]})
            else:
                payload = json.loads(self.messages[1]["content"].removeprefix("Input JSON:\n"))
                content = json.dumps({"verdicts": [{"claim_id": c["claim_id"], "label": "supported",
                    "reason": "Synthetic support", "evidence": [{"passage_id": "p1", "quote": "猫は赤い。"}]}
                    for c in payload["claims"]]})
            return {"content": content, "tokens": [1, 2], "stop_type": "eos", "truncated": False}

    class Server:
        def __init__(self, *args, **kwargs):
            args[1].touch(exist_ok=False)
            state["servers"] += 1
            self.client = Client()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def report(self):
            return {"test_server": True}

    class Retriever:
        def search(self, question, *, top_k):
            assert type(question) is str and "REFERENCE" not in question
            return [RetrievalHit(passage_id="p1", rank=1, score=1., title="色", text="猫は赤い。", source_revision="test"),
                    RetrievalHit(passage_id="p2", rank=2, score=.5, title="別の資料", text="犬は青い。", source_revision="test")]

    monkeypatch.setattr(runner, "load_retriever", lambda *a: Retriever())
    monkeypatch.setattr(runner, "LocalServer", Server)
    return config_path, tmp_path / "data/runs/bilingual_development/connection", state


@pytest.mark.parametrize("failure", [None, "verify_claims", "initial"])
def test_common_connection_keeps_failures_resumes_without_server_or_calls(connection, capsys, failure):
    config, output, state = connection
    state["failure"] = failure
    result = runner.run(config, output)
    calls, servers = len(state["calls"]), state["servers"]
    assert calls == (1 if failure == "initial" else 8)
    assert result["baseline_failures"] == int(failure == "initial")
    assert runner.run(config, output) == result
    assert (len(state["calls"]), state["servers"]) == (calls, servers)
    assert "REFERENCE-SECRET" not in json.dumps(state["calls"])
    assert "gold_parent" not in json.dumps(state["calls"])
    console = capsys.readouterr().out
    assert "猫は赤い" not in console and '"score"' not in console and '"decision"' not in console
    manifest, report = quality.read_run(output)
    assert report["selected_qa_count"] == 1 and manifest["phase12_allowed"] is False
    if failure == "verify_claims":
        assert report["records"][0]["evaluation"]["repeat_group"]["valid_trials"] == 0
    if failure == "initial":
        assert report["failures"][0]["status"] == "error" and not report["records"]


def test_started_judge_becomes_unknown_without_resampling(connection):
    config, output, state = connection
    runner.run(config, output)
    report = read_json(output / "report.private.json")
    trial = report["records"][0]["evaluation"]["trials"][0]
    path = output / "internal" / trial["task_file"]
    task = read_json(path)
    task.pop("result_sha256")
    task["status"] = "started"
    write_json(path, task)
    calls = len(state["calls"])
    runner.run(config, output)
    assert len(state["calls"]) == calls
    saved = read_json(path)
    assert saved["error_code"] == "interrupted_unknown_outcome" and saved["cost_incomplete"]
    quality.read_run(output)


def test_input_overflow_preserves_journal_and_stops_without_completion(connection):
    config, output, state = connection
    state["overflow"] = True
    with pytest.raises(ValueError, match="Input overflow stops"):
        runner.run(config, output)
    assert len(state["calls"]) == 1
    journals = list((output / "internal").glob("*/*.json"))
    overflows = [read_json(p) for p in journals if read_json(p).get("error_code") == "input_overflow"]
    assert len(overflows) == 1 and not overflows[0]["completion_attempted"]
    assert not (output / "report.private.json").exists()


def test_blind_packet_seals_all_labels_before_routes_and_rejects_tampering(connection):
    config, output, state = connection
    runner.run(config, output)
    bundle = output / "quality"
    result = quality.export(output, bundle)
    assert result["candidate_count"] == 2
    packet = read_json(bundle / "packet.json")
    public = json.dumps(packet)
    for field in ('"score"', '"decision"', '"stage"', '"record_id"', '"claims"'):
        assert field not in public
    assert packet["cases"][0]["reference_provenance"]["missing_cited_source_units"] == ["missing"]
    blank = bundle / "annotations.blank.json"
    with pytest.raises(ValueError, match="Seal all external labels"):
        quality.import_annotations(output, bundle, blank)
    assert not (bundle / "routes.scored.json").exists()
    annotations = read_json(blank)
    for annotation in annotations["annotations"]:
        annotation.update(label="reliable", criteria={k: "pass" for k in annotation["criteria"]},
                          essential_points="猫の色", reason="Synthetic labels for test only", annotator="test",
                          elapsed_seconds=1., confirmed_at_utc="2026-10-21T08:00:00+00:00",
                          evidence=[{"passage_id": "p1", "quote": "猫は赤い。"}])
    path = bundle / "annotations.test.json"
    write_json(path, annotations)
    assert quality.import_annotations(output, bundle, path)["sealed_candidates"] == 2
    assert len(state["calls"]) == 8
    packet["cases"][0]["answer"] += " TAMPERED"
    write_json(bundle / "packet.json", packet)
    with pytest.raises(ValueError, match="hash"):
        quality.import_annotations(output, bundle, path)


def test_optional_offline_provenance_preserves_legacy_packets_and_deduplicates():
    trace = {"record_id": "q", "question": "Q?", "answer": "A.", "documents": []}
    rows = [{"trace": trace, "rewrite": {"status": "ok", "answer": "A."}}]
    reference = {"q": {"reference_answers": ["A."], "selected_sentences_by_reference": [], "gold_passage_ids": []}}
    legacy = make_packet(rows, reference, {}, "rubric", "v1", 42, "binding")
    assert make_packet(rows, reference, {}, "rubric", "v1", 42, "binding", reference_metadata=None) == legacy
    packet, mapping = make_packet(rows, reference, {}, "rubric", "v1", 42, "binding",
                                  reference_metadata={"q": {"missing": ["source"]}})
    assert len(packet["cases"]) == 1 and len(next(iter(mapping["assignments"].values()))) == 2
    assert packet["packet_sha256"] != legacy[0]["packet_sha256"]
    assert digest(packet["cases"][0]["reference_provenance"]) == digest({"missing": ["source"]})


@pytest.mark.parametrize("policy", ["keep_initial", "rewrite_once"])
def test_bare_refusal_policy_preserves_null_score_no_judge_and_single_rewrite(connection, policy):
    config, output, state = connection
    state["bare_refusal"] = True
    state["config"]["decision"]["bare_refusal_policy"] = policy
    result = runner.run(config, output)
    assert len(state["calls"]) == 2
    assert [m[0]["content"] for m in state["calls"]] == ["initial", "rewrite_answer"]
    _, report = quality.read_run(output)
    row = report["records"][0]
    for trial in row["evaluation"]["trials"]:
        assert trial["score"] is None and trial["decision"] == "unscorable"
        assert trial["action"] == ("rewrite_requested" if policy == "rewrite_once" else "keep_initial_fallback")
    assert not row["tasks"]["judges"]
    identifier = row["trace"]["record_id"]
    routes = reconstruct([row], {(identifier, "initial"): "unreliable", (identifier, "rewritten"): "reliable"})
    selected = [r for r in routes["routes"] if r["route"] not in {"no_repair", "always_rewrite"}]
    assert all(r["selected_stage"] == ("rewritten" if policy == "rewrite_once" else "initial") for r in selected)
    assert all(r["fallback"] == ("bare_refusal_rewrite_once" if policy == "rewrite_once" else "unscorable") for r in selected)
    assert all(r["operational_cost"]["completion_attempts"] == (2 if policy == "rewrite_once" else 1) for r in selected)
    assert runner.run(config, output) == result and len(state["calls"]) == 2


@pytest.mark.parametrize("change", [
    {"status": "error"}, {"extraction_kind": "model"}, {"unit_audit": {"exclusion": "empty_or_citations"}},
    {"unit_audit": {"exclusion": None}}, {"parsed": {"claims": [{"claim_id": "c1", "text": "Fact."}]}},
])
def test_non_refusal_or_failed_extraction_never_triggers_refusal_rewrite(change):
    task = {"status": "not_applicable", "extraction_kind": "verbatim_sentence_units",
            "unit_audit": {"exclusion": "standalone_refusal"}, "parsed": {"claims": []}}
    assert decide_with_refusal(None, .7, {**task, **change}, policy="rewrite_once") == decide(None, .7)
    assert decide_with_refusal(.7, .7, task, policy="rewrite_once") == decide(.7, .7)
    with pytest.raises(ValueError, match="Unknown bare-refusal"):
        decide_with_refusal(None, .7, task, policy="unknown")


def test_bare_refusal_rewrite_failure_keeps_initial_with_explicit_failure(connection):
    config, output, state = connection
    state.update(bare_refusal=True, failure="rewrite_answer")
    state["config"]["decision"]["bare_refusal_policy"] = "rewrite_once"
    runner.run(config, output)
    _, report = quality.read_run(output)
    row = report["records"][0]
    identifier = row["trace"]["record_id"]
    routes = reconstruct([row], {(identifier, "initial"): "unreliable"})
    selected = [r for r in routes["routes"] if r["route"] not in {"no_repair", "always_rewrite"}]
    assert all(r["rewrite_requested"] and r["selected_stage"] == "initial" and r["fallback"] == "rewrite_failed" for r in selected)
    assert len(state["calls"]) == 2
    runner.run(config, output)
    assert len(state["calls"]) == 2


def test_refusal_policy_requires_opt_in_candidate_and_rejects_legacy_protocol():
    config = yaml.safe_load((REPO / "configs/phase11_bilingual_connection_en_v2.yaml").read_text())
    prompts = yaml.safe_load((REPO / config["prompts"]).read_text())
    config["decision"]["bare_refusal_policy"] = "rewrite_once"
    validate_task_contract(config, prompts)
    config["purpose"] = "phase8-development-protocol"
    with pytest.raises(ValueError, match="separate bilingual candidate"):
        validate_task_contract(config, prompts)


@pytest.mark.parametrize("mode", ["claimwise-v1", "source-reading-v1"])
def test_claimwise_bilingual_runner_quality_raw_validation_and_operational_calls(connection, mode):
    config, output, state = connection
    state["config"]["verification_mode"] = mode
    state["prompts"]["judge_layout"] = "draft_sources_target"
    state["multi_sentences"] = True
    reading = mode == "source-reading-v1"
    if reading:
        state["prompts"]["source_reading_auxiliary"] = "untrusted_reading_v1"
        state["prompts"]["tasks"]["read_sources"] = {"system": "read_sources"}
        state["config"]["tasks"]["read_sources"] = {"max_output_tokens": 512}
    (config.parent / "prompts.yaml").write_text(yaml.safe_dump(state["prompts"]))
    result = runner.run(config, output)
    assert len(state["calls"]) == 14 + 6 * reading
    for messages in state["calls"]:
        if messages[0]["content"] == "verify_claims":
            assert list(json.loads(messages[1]["content"].removeprefix("Input JSON:\n"))) == ["answer", "documents", "question", "claims"] + (["source_reading"] if reading else [])
    _, report = quality.read_run(output)
    row = report["records"][0]
    assert len(row["evaluation"]["claims"]) == 2
    assert all(t["completion_attempts_recorded"] == 2 + reading for t in row["tasks"]["judges"].values())
    identifier = row["trace"]["record_id"]
    routes = reconstruct([row], {(identifier, "initial"): "reliable", (identifier, "rewritten"): "reliable"})
    assert routes["auxiliary_collection_cost"]["completion_attempts"] == 13 + 6 * reading
    assert all(r["operational_cost"]["completion_attempts"] == 3 + reading for r in routes["routes"]
               if r["route"] not in {"no_repair", "always_rewrite"})
    servers = state["servers"]
    assert runner.run(config, output) == result
    assert len(state["calls"]) == 14 + 6 * reading and state["servers"] == servers
    # Children are absent from the public anonymous packet.
    _, _, packet, _ = quality.build_packet(output)
    assert "subtasks" not in json.dumps(packet) and "score" not in json.dumps(packet)


def test_pending_quality_is_rejected_before_access_to_private_scores(connection, monkeypatch):
    config, output, state = connection
    runner.run(config, output)
    bundle = output / "quality"
    quality.export(output, bundle)

    def forbidden(*args):
        raise AssertionError("Private verification must wait until labels are sealed")

    monkeypatch.setattr(quality, "build_packet", forbidden)
    with pytest.raises(ValueError, match="Seal all external labels"):
        quality.validated_annotations(output, bundle, bundle / "annotations.blank.json")
