"""Outcome-blind quality packets sealed after each question, then a common final packet."""

import json

from rag_research.experiments.frozen_trace import require
from rag_research.experiments.protocol import ROOT
from rag_research.experiments.quality import blank_annotations, make_packet, verify_packet
from rag_research.experiments.quality_form import render_form
from rag_research.experiments.storage import checkpoint, read_json, write_json
from rag_research.retrieval.common import CORPUS_PATH, file_hash


def load_offline(config, selected_ids):
    qa = {r["record_id"]: r for r in map(json.loads, (ROOT / config["qa_path"]).read_text("utf-8").splitlines())
          if r["record_id"] in selected_ids}
    require(set(qa) == set(selected_ids), "Missing offline QA")
    needed = {i for row in qa.values() for i in row["gold_passage_ids"]}
    gold = {}
    with (ROOT / CORPUS_PATH).open(encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            if row["passage_id"] in needed:
                gold[row["passage_id"]] = {k: row[k] for k in ("passage_id", "title", "text")}
    require(set(gold) == needed, "Missing Gold evidence")
    return qa, gold


def publish(config, records, qa, gold, binding, output):
    rubric_path = ROOT / "configs/quality_ai_prompt_v1.txt"
    packet, mapping = make_packet(records, qa, gold, rubric_path.read_text("utf-8"),
                                  config["quality_rubric_version"], config["annotation_seed"], binding)
    if (output / "packet.json").exists():
        require(read_json(output / "packet.json") == packet, "Quality packet changed")
    output.mkdir(parents=True, exist_ok=True)
    if not (output / "packet.json").exists():
        write_json(output / "packet.json", packet)
    if (output / "mapping.private.json").exists():
        verify_packet(packet, read_json(output / "mapping.private.json"))
        require({k: v for k, v in read_json(output / "mapping.private.json").items() if k != "result_sha256"}
                == mapping, "Quality mapping changed")
    else:
        checkpoint(output / "mapping.private.json", mapping)
    if not (output / "annotations.blank.json").exists():
        write_json(output / "annotations.blank.json", blank_annotations(packet))
    html = render_form(packet)
    html_path = output / "採点画面.html"
    if html_path.exists():
        require(html_path.read_text("utf-8") == html, "Quality form changed")
    else:
        html_path.write_text(html, encoding="utf-8")
    export_manifest = {
        "packet_sha256": packet["packet_sha256"], "run_manifest_sha256": binding,
        "mapping_sha256": file_hash(output / "mapping.private.json"),
        "prompt_sha256": file_hash(rubric_path),
        "annotation_kind": "AI", "human_reviewed": False,
        "source_sha256": {p.relative_to(ROOT).as_posix(): file_hash(p) for p in
                          [ROOT / "src/rag_research/pilot/materials.py",
                           ROOT / "src/rag_research/experiments/quality.py",
                           ROOT / "src/rag_research/experiments/quality_form.py"]}}
    if (output / "export_manifest.json").exists():
        require({k: v for k, v in read_json(output / "export_manifest.json").items() if k != "result_sha256"}
                == export_manifest, "Quality export binding changed")
    else:
        checkpoint(output / "export_manifest.json", export_manifest)
