"""Bilingual isolation, offline denominators, durable resume and blind label sealing."""

import json
import math
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from rag_research.data import study_assets
from rag_research.experiments import bilingual_quality as quality
from rag_research.experiments import bilingual_runner as runner
from rag_research.experiments.frozen_trace import digest
from rag_research.experiments.quality import make_packet
from rag_research.experiments.storage import read_json, write_json
from rag_research.generation.config import GenerationConfig
from rag_research.generation.context import PromptSpec
from rag_research.generation.local import GenerationError
from rag_research.retrieval.common import RetrievalHit, file_hash
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
    state = {"calls": [], "servers": 0, "failure": None, "overflow": False}

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
                content = "猫は赤い。[p1]"
            elif task == "rewrite_answer":
                content = "資料では、猫は赤い。[p1]"
            else:
                payload = json.loads(self.messages[1]["content"].removeprefix("Input JSON:\n"))
                content = json.dumps({"verdicts": [{"claim_id": c["claim_id"], "label": "supported",
                    "reason": "Synthetic support", "evidence": [{"passage_id": "p1", "quote": "猫は赤い。"}]}
                    for c in payload["claims"]]})
            return {"content": content, "tokens": [1, 2], "stop_type": "eos", "truncated": False}

    class Server:
        def __init__(self, *args, **kwargs):
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
