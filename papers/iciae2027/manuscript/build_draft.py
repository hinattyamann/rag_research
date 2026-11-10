"""Build paired Word manuscripts from the retained ICIAE template and public results.

Run explicitly after synchronizing draft_content.json with any manual Word edits.
This script renders separately verified analysis; it performs no model inference or grading.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree as E

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent
ROOT = PAPER.parent.parent
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"w": W}
TEMPLATE_HASH = "d8e16e91295692e10abab92847abf3e11fa7a66949ff71b31388466949877391"


def tag(local: str) -> str:
    return f"{{{W}}}{local}"


def element(local: str, **attrs: str) -> E._Element:
    return E.Element(tag(local), {tag(k): str(v) for k, v in attrs.items()})


def xml_bytes(root: E._Element) -> bytes:
    return E.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pooled_results() -> dict:
    return json.loads((PAPER / "notes/pooled_results_v1.json").read_text(encoding="utf-8"))


def make_figures() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.patches import FancyArrowPatch, Rectangle

    for font in (Path("C:/Windows/Fonts/yumin.ttf"), Path("C:/Windows/Fonts/YuMincho.ttc")):
        if font.exists():
            font_manager.fontManager.addfont(str(font))
    plt.rcParams.update({"font.size": 9, "axes.unicode_minus": False, "svg.fonttype": "path"})
    folder = PAPER / "figures"
    data = pooled_results()
    estimates = [
        {"mean": row["mean_increment"], "ci95": row["ci95"]} for row in data["primary"]
    ] + [data["ja_minus_en"]]
    for lang in ("en", "ja"):
        plt.rcParams["font.family"] = "Yu Mincho" if lang == "ja" else "Times New Roman"
        fig, ax = plt.subplots(figsize=(3.35, 2.1), layout="constrained")
        for index, row in enumerate(estimates):
            mean = row["mean"] * 100
            low, high = (value * 100 for value in row["ci95"])
            ax.errorbar(
                mean,
                2 - index,
                xerr=[[mean - low], [high - mean]],
                fmt="o",
                color="#1f4e79" if index < 2 else "#555555",
                capsize=3,
                markersize=4,
            )
        ax.set_yticks(
            [2, 1, 0],
            ["English", "Japanese", "Japanese − English"]
            if lang == "en"
            else ["英語", "日本語", "日本語 − 英語"],
        )
        ax.set_xlabel(
            "Excess disagreement / difference (pp)"
            if lang == "en"
            else "判断不一致の増分・日英差（pp）"
        )
        ax.set_xlim(-8, 16)
        ax.set_ylim(-0.6, 2.6)
        ax.axvline(0, color="0.5", linewidth=0.8)
        ax.spines[["top", "right"]].set_visible(False)
        for extension in ("png", "svg"):
            fig.savefig(folder / f"order_increment_{lang}.{extension}", dpi=360)
        plt.close(fig)
        labels = (
            [
                "Question + used evidence + initial answer A",
                "Fix evidence text and answer sentences",
                "Original / reversed / 3 shuffles\nOriginal order repeated 5 times",
                "Evaluate sentence support\nRetain A or request a rewrite",
                "Select A or the same rewrite B\nB uses original evidence and A",
                "Compare selected-answer quality\nand computation cost",
            ]
            if lang == "en"
            else [
                "質問 ＋ 実使用根拠 ＋ 初回回答 A",
                "根拠本文と回答の文を固定",
                "元順序・逆順・シャッフル3種\n元順序を5回反復",
                "文の支持を評価\nAを採用 または 書換えを要求",
                "A または 共通の書換え B を選択\nBの入力は元順序の根拠とA",
                "選択回答の品質と計算費用を比較",
            ]
        )
        fig, ax = plt.subplots(figsize=(3.35, 2.85), layout="constrained")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 6)
        ax.axis("off")
        for index, label in enumerate(labels):
            y = 5.08 - index
            ax.add_patch(
                Rectangle(
                    (0.025, y), 0.95, 0.78, facecolor="#f2f4f5", edgecolor="0.35", linewidth=0.7
                )
            )
            ax.text(0.5, y + 0.39, label, ha="center", va="center", fontsize=8.5)
            if index < 5:
                ax.add_patch(
                    FancyArrowPatch(
                        (0.5, y - 0.01),
                        (0.5, y - 0.20),
                        arrowstyle="-|>",
                        mutation_scale=9,
                        color="0.3",
                    )
                )
        for extension in ("png", "svg"):
            fig.savefig(folder / f"experimental_design_{lang}.{extension}", dpi=360)
        plt.close(fig)


def data_table(key: str, lang: str) -> tuple[list[str], list[list[str]], list[int]]:
    result = pooled_results()
    if key == "development":
        values = (
            [
                ["Synthetic", "EN", "12", "Relations, scope, uncertainty"],
                ["Synthetic", "JA", "15", "Relations, scope, uncertainty"],
                ["Saved QA", "EN", "15", "Previously observed errors (42 sentences)"],
            ]
            if lang == "en"
            else [
                ["人工例", "EN", "12", "関係・範囲・不確実性"],
                ["人工例", "JA", "15", "関係・範囲・不確実性"],
                ["保存QA", "EN", "15", "既知の誤り（42文）"],
            ]
        )
        headers = (
            ["Data", "Lang.", "n", "Purpose"] if lang == "en" else ["種類", "言語", "数", "用途"]
        )
        return headers, values, [1000, 750, 400, 2669]
    if key == "primary":
        values = [
            [
                row["language"].upper(),
                f"{row['comparable_qa']}/{row['selected_qa']}",
                f"{row['mean_increment'] * 100:.2f}",
                f"[{row['ci95'][0] * 100:.2f}, {row['ci95'][1] * 100:.2f}]",
            ]
            for row in result["primary"]
        ]
        headers = (
            ["Language", "n", "D (pp)", "95% CI (pp)"]
            if lang == "en"
            else ["言語", "n", "D (pp)", "95%区間 (pp)"]
        )
        return headers, values, [1000, 750, 850, 2219]
    if key == "quality":
        values = []
        for language in ("en", "ja"):
            row = [language.upper()]
            for route in ("no_repair", "original", "always_rewrite"):
                policy = next(
                    r
                    for r in result["quality"]
                    if r["language"] == language and r["route"] == route
                )
                row.append(
                    "/".join(
                        str(policy[k])
                        for k in ("reliable", "unreliable", "indeterminate", "missing")
                    )
                )
            values.append(row)
        headers = ["Language", "NR", "OE", "AR"] if lang == "en" else ["言語", "NR", "OE", "AR"]
        return headers, values, [1000, 1273, 1273, 1273]
    if key == "selection":
        values = [
            [
                r["language"].upper(),
                str(r["known_pairs"]),
                str(r["transitions"]["0->1"]),
                str(r["oe_missed_improvements"]),
                str(r["transitions"]["1->0"]),
                str(r["oe_harmful_rewrites"]),
            ]
            for r in result["selection"]
        ]
        headers = (
            ["Lang.", "Pairs", "0→1", "OE miss", "1→0", "OE harm"]
            if lang == "en"
            else ["言語", "組数", "0→1", "OE見逃し", "1→0", "OE有害"]
        )
        return headers, values, [650, 600, 600, 1100, 600, 1269]
    if key == "cases":
        values = []
        for number, orders in (
            (1, ("original", "shuffle_3")),
            (2, ("original", "shuffle_2")),
            (3, ("original", "reversed")),
        ):
            file = PAPER / "materials/fixed_v23_v1/cases" / f"case_{number:02d}.json"
            case = json.loads(file.read_text(encoding="utf-8"))
            for order in orders:
                trial = next(t for t in case["trials"] if t["trial_id"] == order)
                policy = next(p for p in case["policy_outcomes"] if p["route"] == order)
                choice = "A" if policy["selected_stage"] == "initial" else "B"
                values.append(
                    [
                        str(number),
                        order,
                        f"{trial['score']:.2f}",
                        f"{choice} / {policy['quality_y']}",
                    ]
                )
        headers = (
            ["Case", "Order", "F", "Selected / Y"]
            if lang == "en"
            else ["例", "順序", "F", "選択 / Y"]
        )
        return headers, values, [650, 1350, 850, 1969]
    if key == "cost":
        values = [
            [
                r["language"].upper(),
                "OE" if r["route"] == "original" else "AR",
                str(r["calls"]),
                f"{r['input_tokens'] + r['output_tokens']:,}",
            ]
            for r in result["quality"]
            if r["route"] != "no_repair"
        ]
        headers = (
            ["Language", "Policy", "Calls", "Tokens"]
            if lang == "en"
            else ["言語", "方策", "呼出し", "トークン"]
        )
        return headers, values, [1000, 850, 850, 2119]
    raise ValueError(f"Unknown table: {key}")


def build(content: dict, lang: str, output_dir: Path | None = None) -> dict:
    template = PAPER / "templates/official/ICIAE2027_template.docx"
    assert sha(template.read_bytes()) == TEMPLATE_HASH, "Official template hash changed"
    with ZipFile(template) as z:
        parts = {info.filename: z.read(info) for info in z.infolist()}
    original = {name: sha(data) for name, data in parts.items()}
    document = E.fromstring(parts["word/document.xml"])
    body = document.find(tag("body"))
    original_sections = [E.tostring(s) for s in document.findall(".//w:sectPr", NS)]
    paras = list(body.findall("w:p", NS))

    def find_p(prefix: str) -> E._Element:
        return next(p for p in paras if "".join(p.itertext()).startswith(prefix))

    patterns = {
        "title": find_p("Preparation of Papers"),
        "author": find_p("First Author"),
        "affiliation": find_p("aFirst affiliation"),
        "p": find_p("This template gives"),
        "h1": find_p("Introduction"),
        "h2": find_p("Structure"),
        "abstract_heading": find_p("Abstract"),
        "keywords": find_p("Keywords:"),
    }
    first_carrier = next(deepcopy(p) for p in paras if p.find("w:pPr/w:sectPr", NS) is not None)
    for child in list(first_carrier):
        if child.tag != tag("pPr"):
            first_carrier.remove(child)
    last_section = deepcopy(body.find("w:sectPr", NS))
    for child in list(body):
        body.remove(child)

    def add_run(
        p: E._Element,
        text: str,
        size: int = 20,
        bold: bool = False,
        superscript: bool = False,
        subscript: bool = False,
    ) -> E._Element:
        run = E.SubElement(p, tag("r"))
        props = E.SubElement(run, tag("rPr"))
        props.append(
            element(
                "rFonts", ascii="Times New Roman", hAnsi="Times New Roman", eastAsia="Yu Mincho"
            )
        )
        props.append(element("sz", val=str(size)))
        props.append(element("color", val="000000"))
        if bold:
            props.append(element("b"))
        if superscript or subscript:
            props.append(element("vertAlign", val="superscript" if superscript else "subscript"))
        node = E.SubElement(run, tag("t"))
        node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        node.text = text
        return run

    def add_text(p: E._Element, text: str, size: int = 20, bold: bool = False) -> None:
        for token in re.split(r"(\[\[\d+\]\]|[ABFmsDORΣ]_(?:it|i))", text):
            if re.fullmatch(r"\[\[\d+\]\]", token):
                add_run(p, f"({token[2:-2]})", size, superscript=True)
            elif re.fullmatch(r"[ABFmsDORΣ]_(?:it|i)", token):
                base, sub = token.split("_")
                add_run(p, base, size, bold)
                add_run(p, sub, size, bold, subscript=True)
            elif token:
                add_run(p, token, size, bold)

    def paragraph(text: str, kind: str = "p", parent: E._Element | None = None) -> E._Element:
        p = E.SubElement(body if parent is None else parent, tag("p"))
        pattern = patterns.get(kind, patterns["p"])
        props = deepcopy(pattern.find("w:pPr", NS))
        if props is None:
            props = element("pPr")
        for node in list(props):
            if node.tag in (tag("sectPr"), tag("numPr"), tag("pBdr"), tag("rPr")):
                props.remove(node)
        p.append(props)
        heading = kind in ("h1", "h2", "abstract_heading")
        size = (
            32
            if kind == "title"
            else 21
            if kind in ("author", "affiliation")
            else 24
            if kind in ("h1", "abstract_heading")
            else 20
        )
        if kind == "title":
            props.insert(0, element("pStyle", val="Title"))
        if heading:
            props.append(element("keepNext"))
            props.append(element("outlineLvl", val="1" if kind == "h2" else "0"))
        if kind in (
            "title",
            "author",
            "affiliation",
            "h1",
            "abstract_heading",
            "caption",
            "equation",
        ):
            for node in props.findall("w:jc", NS):
                props.remove(node)
            props.append(element("jc", val="center"))
            for node in props.findall("w:ind", NS):
                props.remove(node)
        if kind in ("caption", "equation"):
            for node in props.findall("w:spacing", NS):
                props.remove(node)
            props.append(element("spacing", before="60", after="100"))
        if kind == "caption":
            props.append(element("keepLines"))
        if kind in ("p", "keywords"):
            for node in props.findall("w:widowControl", NS):
                props.remove(node)
            props.append(element("widowControl", val="true"))
        if kind == "excerpt":
            for node in props.findall("w:ind", NS):
                props.remove(node)
            props.append(element("ind", left="120", right="60"))
            props.append(element("keepLines"))
            for node in props.findall("w:spacing", NS):
                props.remove(node)
            props.append(element("spacing", before="60", after="60"))
        if lang == "ja":
            props.append(element("snapToGrid", val="false"))
            spacing = props.find("w:spacing", NS)
            if spacing is None:
                spacing = E.SubElement(props, tag("spacing"))
            spacing.set(tag("line"), "300")
            spacing.set(tag("lineRule"), "atLeast")
        add_text(p, text, size, heading or kind == "title")
        return p

    paragraph(content["title"][lang], "title")
    paragraph(content["authors"][lang], "author")
    paragraph(content["affiliation"][lang], "affiliation")
    body.append(first_carrier)
    relations = E.fromstring(parts["word/_rels/document.xml.rels"])
    rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    next_rel = 100

    def relation(kind: str, target: str, external: bool = False) -> str:
        nonlocal next_rel
        next_rel += 1
        rid = f"rId{next_rel}"
        attrs = {"Id": rid, "Type": R + "/" + kind, "Target": target}
        if external:
            attrs["TargetMode"] = "External"
        E.SubElement(relations, f"{{{rel_ns}}}Relationship", attrs)
        return rid

    table_snapshot = {}
    for block in content["blocks"]:
        kind = block["type"]
        if kind == "table":
            cap = paragraph(block[lang], "caption")
            cap.find("w:pPr", NS).append(element("keepNext"))
            headers, values, widths = data_table(block["key"], lang)
            table_snapshot[block["key"]] = values
            tbl = E.SubElement(body, tag("tbl"))
            props = E.SubElement(tbl, tag("tblPr"))
            props.append(element("tblW", w=str(sum(widths)), type="dxa"))
            props.append(element("tblLayout", type="fixed"))
            borders = E.SubElement(props, tag("tblBorders"))
            for name in ("top", "left", "bottom", "right", "insideH", "insideV"):
                borders.append(element(name, val="single", sz="4", color="D9D9D9"))
            margins = E.SubElement(props, tag("tblCellMar"))
            for name in ("top", "bottom", "left", "right"):
                margins.append(element(name, w="55", type="dxa"))
            grid = E.SubElement(tbl, tag("tblGrid"))
            for width in widths:
                grid.append(element("gridCol", w=str(width)))
            for index, row in enumerate([headers] + values):
                tr = E.SubElement(tbl, tag("tr"))
                tr_props = E.SubElement(tr, tag("trPr"))
                tr_props.append(element("cantSplit"))
                if index == 0:
                    tr_props.append(element("tblHeader"))
                for text, width in zip(row, widths, strict=True):
                    tc = E.SubElement(tr, tag("tc"))
                    tc_props = E.SubElement(tc, tag("tcPr"))
                    tc_props.append(element("tcW", w=str(width), type="dxa"))
                    tc_props.append(element("vAlign", val="center"))
                    if index == 0:
                        tc_props.append(element("shd", fill="E7E6E6", val="clear"))
                    p = E.SubElement(tc, tag("p"))
                    pp = E.SubElement(p, tag("pPr"))
                    pp.append(element("jc", val="center"))
                    pp.append(element("spacing", before="20", after="20"))
                    if index < len(values):
                        pp.append(element("keepNext"))
                    if lang == "ja":
                        pp.append(element("snapToGrid", val="false"))
                    add_text(p, text, 20, index == 0)
        elif kind == "figure":
            from docx import Document
            from docx.shared import Mm

            # Only use python-docx to construct a new inline drawing; retained package parts are patched directly.
            temp = Document()
            fig_name = (
                "experimental_design" if block["key"] == "design" else "order_increment"
            ) + f"_{lang}.png"
            picture = PAPER / "figures" / fig_name
            temp.add_paragraph().add_run().add_picture(str(picture), width=Mm(85))
            drawing = deepcopy(temp.paragraphs[0]._p)
            for shape in drawing.findall(
                ".//{http://schemas.openxmlformats.org/drawingml/2006/main}blip"
            ):
                shape.set(f"{{{R}}}embed", relation("image", f"media/{fig_name}"))
            for shape in drawing.findall(
                ".//{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}docPr"
            ):
                shape.set("id", str(next_rel))
                shape.set("descr", block[lang])
            props = E.Element(tag("pPr"))
            props.append(element("jc", val="center"))
            props.append(element("keepNext"))
            drawing.insert(0, props)
            body.append(drawing)
            parts[f"word/media/{fig_name}"] = picture.read_bytes()
            paragraph(block[lang], "caption")
        else:
            p = paragraph(block[lang], kind)
            if block.get("keep_together"):
                p.find("w:pPr", NS).append(element("keepLines"))
            if block.get("keep_with_next"):
                p.find("w:pPr", NS).append(element("keepNext"))
    for ref in content["references"]:
        if ref["id"] == content.get("reference_column_break_before", {}).get(lang):
            p = E.SubElement(body, tag("p"))
            pp = E.SubElement(p, tag("pPr"))
            pp.append(element("spacing", before="0", after="0", line="1", lineRule="exact"))
            run = E.SubElement(p, tag("r"))
            E.SubElement(run, tag("br"), {tag("type"): "column"})
        p = paragraph(f"({ref['id']}) {ref['text']} ")
        props = p.find("w:pPr", NS)
        for node in props.findall("w:ind", NS):
            props.remove(node)
        props.append(element("ind", left="300", hanging="300"))
        for node in props.findall("w:jc", NS):
            props.remove(node)
        props.append(element("jc", val="left"))
        props.append(element("keepLines"))
        link = E.SubElement(
            p, tag("hyperlink"), {f"{{{R}}}id": relation("hyperlink", ref["url"], True)}
        )
        add_run(link, ref.get("display_url", ref["url"]))
    body.append(last_section)
    assert original_sections == [E.tostring(s) for s in document.findall(".//w:sectPr", NS)], (
        "Section contract changed"
    )
    parts["word/document.xml"] = xml_bytes(document)
    parts["word/_rels/document.xml.rels"] = xml_bytes(relations)
    styles = E.fromstring(parts["word/styles.xml"])
    if styles.find("w:style[@w:styleId='Title']", NS) is None:
        style = element("style", type="paragraph", styleId="Title")
        style.append(element("name", val="Title"))
        styles.append(style)
        parts["word/styles.xml"] = xml_bytes(styles)
    settings = E.fromstring(parts["word/settings.xml"])
    for node in settings.findall("w:updateFields", NS):
        settings.remove(node)
    settings.append(element("updateFields", val="true"))
    parts["word/settings.xml"] = xml_bytes(settings)
    core = E.fromstring(parts["docProps/core.xml"])
    for node in core:
        if E.QName(node).localname in ("creator", "lastModifiedBy"):
            node.text = ""
        elif E.QName(node).localname == "title":
            node.text = content["title"][lang]
        elif E.QName(node).localname in ("created", "modified"):
            core.remove(node)
    parts["docProps/core.xml"] = xml_bytes(core)
    editable = {
        "word/document.xml",
        "word/_rels/document.xml.rels",
        "word/styles.xml",
        "word/settings.xml",
        "docProps/core.xml",
    }
    preserved = [
        name
        for name, digest in original.items()
        if name not in editable and sha(parts[name]) == digest
    ]
    assert len(preserved) == len(set(original) - editable), "Preserve-only package part changed"
    output = (output_dir or HERE).resolve() / f"iciae2027_manuscript_{lang}.docx"
    with ZipFile(output, "w", ZIP_DEFLATED) as z:
        for name, data in parts.items():
            z.writestr(name, data)
    return {
        "language": lang,
        "output": str(output.relative_to(ROOT)),
        "sha256": sha(output.read_bytes()),
        "tables": table_snapshot,
        "preserved_parts": preserved,
        "package_inventory": {
            name: {"bytes": len(data), "sha256": sha(data)} for name, data in parts.items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--build",
        action="store_true",
        help="Explicitly rebuild both Word files from the paired source",
    )
    parser.add_argument(
        "--refresh-figures", action="store_true", help="Explicitly redraw the two retained figures"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Stage both DOCX and their build manifest in a separate directory for review",
    )
    args = parser.parse_args()
    if not args.build:
        parser.error("Use --build only after synchronizing source with Word edits")
    content = json.loads((HERE / "draft_content.json").read_text(encoding="utf-8"))
    ids = [b["id"] for b in content["blocks"]]
    assert len(ids) == len(set(ids))
    for block in content["blocks"]:
        assert block["en"] and block["ja"]
        assert re.findall(r"\[\[\d+\]\]", block["en"]) == re.findall(r"\[\[\d+\]\]", block["ja"]), (
            block["id"]
        )
    assert len(next(b["en"] for b in content["blocks"] if b["id"] == "abstract").split()) < 300
    required_figures = [
        PAPER / "figures" / f"{name}_{lang}.png"
        for name in ("experimental_design", "order_increment")
        for lang in ("en", "ja")
    ]
    if args.refresh_figures or not all(path.exists() for path in required_figures):
        make_figures()
    if args.output_dir:
        args.output_dir = args.output_dir.resolve()
        args.output_dir.mkdir(parents=True, exist_ok=True)
    results = [build(content, lang, args.output_dir) for lang in ("en", "ja")]
    assert {k: v for k, v in results[0]["tables"].items() if k != "development"} == {
        k: v for k, v in results[1]["tables"].items() if k != "development"
    }
    assert [r[1:3] for r in results[0]["tables"]["development"]] == [
        r[1:3] for r in results[1]["tables"]["development"]
    ]
    report = {
        "version": content["version"],
        "evidence_commit": content["evidence_commit"],
        "extension_evidence_commit": content["extension_evidence_commit"],
        "evidence_trees": content.get("evidence_trees", {}),
        "content_digest": sha(
            json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ),
        "evidence_packages": {
            name: sha((PAPER / "materials" / name / "artifact_manifest.json").read_bytes())
            for name in content.get("evidence_trees", {})
        },
        "derived_evidence": {
            name: sha(
                json.dumps(
                    json.loads((PAPER / name).read_text(encoding="utf-8")),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            )
            for name in content.get("derived_evidence", [])
        },
        "template_sha256": TEMPLATE_HASH,
        "block_count": len(ids),
        "documents": results,
    }
    report_path = (
        (args.output_dir / "draft_build_manifest.json")
        if args.output_dir
        else (PAPER / "notes/draft_build_manifest.json")
    )
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "blocks": len(ids),
                "abstract_words": len(
                    next(b["en"] for b in content["blocks"] if b["id"] == "abstract").split()
                ),
                "outputs": [{k: r[k] for k in ("language", "output", "sha256")} for r in results],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
