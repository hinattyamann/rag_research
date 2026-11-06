"""Validate actual paired Word artifacts against source text and published data."""

import csv
import hashlib
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import pytest

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent
ROOT = PAPER.parent.parent
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT = json.loads((HERE / "draft_content.json").read_text(encoding="utf-8"))


def text(node):
    return "".join(t.text or "" for t in node.findall(".//w:t", NS))


def display_text(value):
    value = re.sub(r"\[\[(\d+)\]\]", r"(\1)", value)
    return re.sub(r"([ABFmsDORΣ])_(it|i)", r"\1\2", value)


def table_rows(table):
    return [[text(cell) for cell in row.findall("w:tc", NS)] for row in table.findall("w:tr", NS)]


@pytest.mark.parametrize("lang", ["en", "ja"])
def test_word_text_references_and_tables_match_evidence(lang):
    """Read the emitted ZIP independently of the builder and inspect all content."""
    with ZipFile(HERE / f"iciae2027_manuscript_{lang}.docx") as package:
        document = ET.fromstring(package.read("word/document.xml"))
        relations = ET.fromstring(package.read("word/_rels/document.xml.rels"))
    paragraphs = [text(p) for p in document.findall("w:body/w:p", NS)]
    assert CONTENT["title"][lang] in paragraphs
    for block in CONTENT["blocks"]:
        assert display_text(block[lang]) in paragraphs, block["id"]
    assert len(document.findall(".//w:drawing", NS)) == 2
    ids = [r.attrib["Id"] for r in relations]
    assert len(ids) == len(set(ids))
    links = [
        r.attrib["Target"] for r in relations if r.attrib.get("Type", "").endswith("/hyperlink")
    ]
    assert links == [r["url"] for r in CONTENT["references"]]
    citation_runs = [
        text(r)
        for r in document.findall("w:body/w:p/w:r", NS)
        if r.find("w:rPr/w:vertAlign[@w:val='superscript']", NS) is not None
    ]
    assert citation_runs == [f"({i})" for i in range(1, len(CONTENT["references"]) + 1)]
    assert not any("Preparation of Papers" in p or "Click here" in p for p in paragraphs)
    tables = document.findall("w:body/w:tbl", NS)
    assert len(tables) == 5
    primary = table_rows(tables[0])[1:]
    with (ROOT / "reports/fixed_v23_order_study_v1/primary_comparison.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        records = list(csv.DictReader(stream))
    for actual, expected in zip(primary, records, strict=True):
        assert actual[1] == expected["comparable_qa"]
        assert float(actual[2]) == round(100 * float(expected["mean_increment"]), 2)
        interval = [float(x) for x in re.findall(r"\d+\.\d+", actual[3])]
        assert interval == [
            round(100 * float(expected[key]), 2) for key in ("ci95_low", "ci95_high")
        ]
    with (ROOT / "reports/fixed_v23_order_study_v1/quality_and_operational_cost.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        routes = {
            (r["cohort"].capitalize() + " " + r["language"].upper(), r["route"]): r
            for r in csv.DictReader(stream)
        }
    route_names = {"NR": "no_repair", "OE": "original", "AR": "always_rewrite"}
    for actual in table_rows(tables[1])[1:]:
        expected = routes[(actual[0], route_names[actual[1]])]
        assert actual[2:] == [expected[key] for key in ("reliable", "unreliable", "indeterminate")]
    for actual in table_rows(tables[4])[1:]:
        expected = routes[(actual[0], route_names[actual[1]])]
        assert actual[2] == expected["native_attempts_sum"]
        assert int(actual[3]) == int(expected["input_tokens_sum"]) + int(
            expected["output_tokens_sum"]
        )
    material_root = PAPER / "materials/fixed_v23_v1"
    with (material_root / "policy_outcomes.csv").open(encoding="utf-8", newline="") as stream:
        policies = list(csv.DictReader(stream))
    for actual in table_rows(tables[2])[1:]:
        original = [
            r
            for r in policies
            if r["cohort"].capitalize() + " " + r["language"].upper() == actual[0]
            and r["route"] == "original"
            and r["policy_state"] == "observed"
        ]
        always = [
            r
            for r in policies
            if r["cohort"].capitalize() + " " + r["language"].upper() == actual[0]
            and r["route"] == "always_rewrite"
            and r["policy_state"] == "observed"
        ]
        assert [int(v) for v in actual[1:]] == [
            sum(r["quality_transition"] != "unknown" for r in original),
            sum(r["missed_improvement"] == "True" for r in original),
            sum(r["harmful_rewrite"] == "True" for r in original),
            sum(r["harmful_rewrite"] == "True" for r in always),
        ]
    case_rows = table_rows(tables[3])[1:]
    for actual in case_rows:
        case_id = "case_01" if actual[0] == "EN" else "case_02"
        case = json.loads((material_root / "cases" / f"{case_id}.json").read_text(encoding="utf-8"))
        trial = next(t for t in case["trials"] if t["trial_id"] == actual[1])
        policy = next(p for p in case["policy_outcomes"] if p["route"] == actual[1])
        assert float(actual[2]) == round(trial["score"], 2)
        assert (
            actual[3]
            == ("A" if policy["selected_stage"] == "initial" else "B") + f" / {policy['quality_y']}"
        )


def test_pair_and_frozen_evidence_integrity():
    assert len(CONTENT["blocks"]) == len({b["id"] for b in CONTENT["blocks"]})
    tables = []
    manifest = json.loads((PAPER / "notes/draft_build_manifest.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256(
        json.dumps(CONTENT, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert digest == manifest["content_digest"]
    assert manifest["evidence_trees"] == CONTENT["evidence_trees"]
    for name, value in manifest["evidence_packages"].items():
        assert (
            hashlib.sha256(
                (PAPER / "materials" / name / "artifact_manifest.json").read_bytes()
            ).hexdigest()
            == value
        )
    template = PAPER / "templates/official/ICIAE2027_template.docx"
    assert hashlib.sha256(template.read_bytes()).hexdigest() == manifest["template_sha256"]
    editable = {
        "word/document.xml",
        "word/_rels/document.xml.rels",
        "word/styles.xml",
        "word/settings.xml",
        "docProps/core.xml",
    }
    with ZipFile(template) as original:
        original_sections = ET.fromstring(original.read("word/document.xml")).findall(
            ".//w:sectPr", NS
        )
        for lang, document_manifest in zip(("en", "ja"), manifest["documents"], strict=True):
            file = HERE / f"iciae2027_manuscript_{lang}.docx"
            assert hashlib.sha256(file.read_bytes()).hexdigest() == document_manifest["sha256"]
            with ZipFile(file) as draft:
                root = ET.fromstring(draft.read("word/document.xml"))
                tables.append([table_rows(t)[1:] for t in root.findall("w:body/w:tbl", NS)])
                sections = root.findall(".//w:sectPr", NS)
                assert [ET.tostring(s) for s in sections] == [
                    ET.tostring(s) for s in original_sections
                ]
                for name in original.namelist():
                    if name not in editable:
                        assert draft.read(name) == original.read(name), name
    assert tables[0] == tables[1]
    result_dir = ROOT / "reports/fixed_v23_order_study_v1"
    frozen = json.loads((result_dir / "artifact_manifest.json").read_text(encoding="utf-8"))
    for file, digest in frozen["files"].items():
        assert hashlib.sha256((result_dir / file).read_bytes()).hexdigest() == digest
