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
    assert keys == ["development", "primary", "quality", "selection", "cases", "cost"]
    assert len(tables) == len(keys)
    actual = {key: table_rows(table)[1:] for key, table in zip(keys, tables, strict=True)}
    audit = json.loads((PAPER / "notes/pooled_results_v1.json").read_text(encoding="utf-8"))
    assert [row[1:3] for row in actual["development"]] == [["EN", "12"], ["JA", "15"], ["EN", "15"]]
    for row, expected in zip(actual["primary"], audit["primary"], strict=True):
        assert row[0] == expected["language"].upper()
        assert row[1] == f"{expected['comparable_qa']}/{expected['selected_qa']}"
        assert float(row[2]) == round(expected["mean_increment"] * 100, 2)
        assert [float(v) for v in re.findall(r"-?\d+\.\d+", row[3])] == [
            round(value * 100, 2) for value in expected["ci95"]
        ]
    routes = {(r["language"].upper(), r["route"]): r for r in audit["quality"]}
    assert len(actual["quality"]) == 2
    for row in actual["quality"]:
        for column, route in enumerate(("no_repair", "original", "always_rewrite"), 1):
            expected = routes[(row[0], route)]
            assert [int(v) for v in row[column].split("/")] == [
                expected[k] for k in ("reliable", "unreliable", "indeterminate", "missing")
            ]
    for row, expected in zip(actual["selection"], audit["selection"], strict=True):
        assert row[0] == expected["language"].upper()
        assert [int(v) for v in row[1:]] == [
            expected["known_pairs"],
            expected["transitions"]["0->1"],
            expected["oe_missed_improvements"],
            expected["transitions"]["1->0"],
            expected["oe_harmful_rewrites"],
        ]
    assert len(actual["cost"]) == 4
    for row in actual["cost"]:
        expected = routes[(row[0], "original" if row[1] == "OE" else "always_rewrite")]
        assert int(row[2]) == expected["calls"]
        assert int(row[3].replace(",", "")) == expected["input_tokens"] + expected["output_tokens"]
    assert len(actual["cases"]) == 6
    for row in actual["cases"]:
        case = json.loads(
            (PAPER / f"materials/fixed_v23_v1/cases/case_{int(row[0]):02d}.json").read_text(
                encoding="utf-8"
            )
        )
        trial = next(t for t in case["trials"] if t["trial_id"] == row[1])
        policy = next(p for p in case["policy_outcomes"] if p["route"] == row[1])
        assert float(row[2]) == round(trial["score"], 2)
        assert (
            row[3]
            == ("A" if policy["selected_stage"] == "initial" else "B") + f" / {policy['quality_y']}"
        )


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
    # Development-purpose prose is translated; all numeric result cells match.
    assert tables[0][1:] == tables[1][1:]
    assert [r[1:3] for r in tables[0][0]] == [r[1:3] for r in tables[1][0]]
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
