"""Validate actual paired Word artifacts against source text and published data."""

import hashlib
import json
import os
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
DOCX_DIR = Path(os.environ.get("ICIAE_DOCX_DIR", str(HERE)))
BUILD_MANIFEST = Path(
    os.environ.get("ICIAE_BUILD_MANIFEST", str(PAPER / "notes/draft_build_manifest.json"))
)
EXTENSION = PAPER / "materials/cal_extension_v1"


def text(node):
    return "".join(t.text or "" for t in node.findall(".//w:t", NS))


def display_text(value):
    value = re.sub(r"\[\[(\d+)\]\]", r"(\1)", value)
    return re.sub(r"([ABFmsDORΣ])_(it|i)", r"\1\2", value)


def table_rows(table):
    return [[text(cell) for cell in row.findall("w:tc", NS)] for row in table.findall("w:tr", NS)]


@pytest.mark.parametrize("lang", ["en", "ja"])
def test_word_text_references_and_tables_match_evidence(lang):
    """Check actual emitted OOXML independently of the rendering code."""
    with ZipFile(DOCX_DIR / f"iciae2027_manuscript_{lang}.docx") as package:
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
    assert not re.search(r"\b(?:Main|Cal|Ext)\b", " ".join(paragraphs))
    tables = document.findall("w:body/w:tbl", NS)
    keys = [b["key"] for b in CONTENT["blocks"] if b["type"] == "table"]
    assert keys == [
        "configuration",
        "development",
        "primary",
        "quality",
        "selection",
        "order_quality",
        "cases",
        "cost",
        "semantics",
        "thresholds",
    ]
    assert len(tables) == len(keys)
    actual = {key: table_rows(table)[1:] for key, table in zip(keys, tables, strict=True)}
    audit = json.loads((PAPER / "notes/pooled_results_v1.json").read_text(encoding="utf-8"))
    assert [re.findall(r"\d+(?:\.\d+)?", row[1]) for row in actual["development"]] == [
        ["12"],
        ["15"],
        ["15", "42"],
        ["57", "58", "98.3"],
        ["14", "16", "87.5"],
    ]
    for column, expected in enumerate(audit["primary"], 1):
        cells = [row[column] for row in actual["primary"]]
        assert [int(c) for c in cells[:5]] == [
            expected["selected_qa"],
            expected["comparable_qa"],
            expected["exclusion_reasons"].get("invalid_or_unscorable_trials", 0),
            expected["initial_failures"],
            expected["rewrite_failures"],
        ]
        assert cells[5] == f"{expected['decision_change_qa']}/{expected['comparable_qa']}"
        assert [float(c) for c in cells[6:9]] == [
            round(expected[k] * 100, 2)
            for k in ("mean_order_rate", "mean_repeat_rate", "mean_increment")
        ]
        assert [float(v) for v in re.findall(r"-?\d+\.\d+", cells[9])] == [
            round(value * 100, 2) for value in expected["ci95"]
        ]
    assert sum(map(int, actual["primary"][0][1:])) == audit["selected_qa"]
    assert sum(map(int, actual["primary"][1][1:])) == audit["comparable_qa"]
    difference = display_text(
        next(b[lang] for b in CONTENT["blocks"] if b["id"] == "table-primary")
    )
    for v in [audit["ja_minus_en"]["mean"], *audit["ja_minus_en"]["ci95"]]:
        assert f"{v * 100:.2f}".replace("-", "−") in difference
    routes = {(r["language"].upper(), r["route"]): r for r in audit["quality"]}
    assert len(actual["quality"]) == 6
    for row in actual["quality"]:
        expected = routes[
            (row[0], {"NR": "no_repair", "OE": "original", "AR": "always_rewrite"}[row[1]])
        ]
        assert [int(v) for v in row[2:]] == [
            expected[k] for k in ("reliable", "unreliable", "indeterminate", "missing")
        ]
        assert sum(int(v) for v in row[2:]) == 100
    for column, expected in enumerate(audit["selection"], 1):
        cells = [r[column] for r in actual["selection"]]
        assert [int(c) for c in cells[:5]] == [expected["known_pairs"]] + [
            expected["transitions"][k] for k in ("0->0", "0->1", "1->0", "1->1")
        ]
        assert sum(int(c) for c in cells[1:5]) == int(cells[0])
        assert cells[5] == f"{expected['oe_missed_improvements']}/{expected['transitions']['0->1']}"
        assert cells[6] == f"{expected['oe_harmful_rewrites']}/{expected['transitions']['1->0']}"
    for column, language in enumerate(("en", "ja"), 1):
        varying = [
            q
            for q in audit["questions"]
            if q["language"] == language
            and q["comparable"]
            and q["decision_varies_in_valid_orders"]
        ]
        assert [int(r[column]) for r in actual["order_quality"]] == [len(varying)] + [
            sum(q["classification"] == k for q in varying)
            for k in (
                "decision_change_quality_changes",
                "decision_change_same_binary_quality",
                "decision_change_quality_unknown",
            )
        ] + [
            sum(
                q["known_route_cost_range"]["recorded_input_plus_output_tokens"]["max"]
                > q["known_route_cost_range"]["recorded_input_plus_output_tokens"]["min"]
                for q in varying
            )
        ]
    assert [int(r[3]) for r in actual["order_quality"]] == [
        sum(map(int, r[1:3])) for r in actual["order_quality"]
    ]
    assert sum(int(r[3]) for r in actual["order_quality"][1:4]) == int(
        actual["order_quality"][0][3]
    )
    assert len(actual["cost"]) == 4
    for row in actual["cost"]:
        expected = routes[(row[0], "original" if row[1] == "OE" else "always_rewrite")]
        assert int(row[2]) == expected["calls"]
        assert int(row[3].replace(",", "")) == expected["input_tokens"] + expected["output_tokens"]
        ar = routes[(row[0], "always_rewrite")]
        assert float(row[4]) == round(
            (expected["input_tokens"] + expected["output_tokens"])
            / (ar["input_tokens"] + ar["output_tokens"]),
            2,
        )
    assert len(actual["cases"]) == 6
    for row in actual["cases"]:
        case = json.loads(
            (PAPER / f"materials/fixed_v23_v1/cases/case_{int(row[0]):02d}.json").read_text(
                encoding="utf-8"
            )
        )
        trial = next(t for t in case["trials"] if t["trial_id"] == row[1])
        policy = next(p for p in case["policy_outcomes"] if p["route"] == row[1])
        numerator, denominator = map(int, row[2].split("/"))
        assert denominator == len(trial["fixed_claims"])
        assert numerator == sum(v["label"] == "supported" for v in trial["verdicts"])
        assert numerator / denominator == pytest.approx(trial["score"])
        assert (
            row[3]
            == ("A" if policy["selected_stage"] == "initial" else "B") + f" / {policy['quality_y']}"
        )
    for row, expected in zip(actual["semantics"], audit["semantics"], strict=True):
        assert row[0] == expected["language"].upper()
        assert list(map(int, row[1:3])) == [
            expected["false_support_observations"],
            expected["negative_sentence_trial_observations"],
        ]
        assert row[3] == f"{100 * int(row[1]) / int(row[2]):.1f}%"
    assert len(actual["thresholds"]) == 5
    for row in actual["thresholds"]:
        for column, language in enumerate(("en", "ja"), 1):
            expected = next(
                r
                for r in audit["thresholds"]
                if r["language"] == language and r["threshold"] == float(row[0])
            )
            assert float(row[column]) == round(expected["mean_increment"] * 100, 2)


def test_pair_and_frozen_evidence_integrity():
    assert len(CONTENT["blocks"]) == len({b["id"] for b in CONTENT["blocks"]})
    tables = []
    manifest = json.loads(BUILD_MANIFEST.read_text(encoding="utf-8"))
    digest = hashlib.sha256(
        json.dumps(CONTENT, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert digest == manifest["content_digest"]
    assert manifest["evidence_trees"] == CONTENT["evidence_trees"]
    assert manifest["extension_evidence_commit"] == CONTENT["extension_evidence_commit"]
    for name, value in manifest["evidence_packages"].items():
        assert (
            hashlib.sha256(
                (PAPER / "materials" / name / "artifact_manifest.json").read_bytes()
            ).hexdigest()
            == value
        )
    for name, value in manifest["derived_evidence"].items():
        source = json.loads((PAPER / name).read_text(encoding="utf-8"))
        assert (
            hashlib.sha256(
                json.dumps(
                    source, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode()
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
            file = DOCX_DIR / f"iciae2027_manuscript_{lang}.docx"
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

    # Labels and captions are translated; every row retains the same numbers.
    def numbers(table):
        return [re.findall(r"\d+(?:\.\d+)?", " ".join(row)) for row in table]

    assert [numbers(t) for t in tables[0]] == [numbers(t) for t in tables[1]]
    result_dir = ROOT / "reports/fixed_v23_order_study_v1"
    frozen = json.loads((result_dir / "artifact_manifest.json").read_text(encoding="utf-8"))
    for file, digest in frozen["files"].items():
        assert hashlib.sha256((result_dir / file).read_bytes()).hexdigest() == digest
    extension_manifest = json.loads(
        (EXTENSION / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    for file, entry in extension_manifest["files"].items():
        contents = (EXTENSION / file).read_bytes()
        assert len(contents) == entry["bytes"]
        assert hashlib.sha256(contents).hexdigest() == entry["sha256"], file


def test_case_excerpt_wording_is_present_in_both_actual_documents():
    excerpts = json.loads((PAPER / "notes/case_excerpts_v1.json").read_text(encoding="utf-8"))
    for lang in ("en", "ja"):
        with ZipFile(DOCX_DIR / f"iciae2027_manuscript_{lang}.docx") as package:
            document = ET.fromstring(package.read("word/document.xml"))
        paragraphs = [text(p) for p in document.findall("w:body/w:p", NS)]
        quoted_blocks = [
            b
            for b in CONTENT["blocks"]
            if b["id"] in {"case-ja-excerpts", "case-ja-A", "case-ja-B"}
        ]
        expected = " ".join(display_text(b[lang]) for b in quoted_blocks)
        assert all(display_text(b[lang]) in paragraphs for b in quoted_blocks)
        for quote in excerpts["quotes"]:
            value = quote["original_ja" if lang == "ja" else "translation_en"]
            quoted = f"「{value}」" if lang == "ja" else f'"{value}"'
            assert quoted in expected


def test_extended_output_excerpts_are_literal_saved_answer_slices():
    blocks = {b["id"]: b for b in CONTENT["blocks"]}
    for number, lang, mappings in (
        (1, "en", {"case-en-A": "A", "case-en-B": "B"}),
        (2, "ja", {"case-ja-A": "A", "case-ja-B": "B"}),
    ):
        case = json.loads(
            (PAPER / f"materials/fixed_v23_v1/cases/case_{number:02d}.json").read_text(
                encoding="utf-8"
            )
        )
        source = json.loads(
            (PAPER / "materials/fixed_v23_v1" / case["input_path"]).read_text(encoding="utf-8")
        )
        for block_id, stage in mappings.items():
            pattern = r"“([^”]+)”" if lang == "en" else r"「([^」]+)」"
            quotes = re.findall(pattern, blocks[block_id][lang])
            assert quotes
            assert all(quote in source[stage]["answer"] for quote in quotes)
