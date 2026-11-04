"""Build paired Word manuscripts from the retained ICIAE template and public results.

Run explicitly after synchronizing draft_content.json with any manual Word edits.
This script performs no model inference or research reanalysis.
"""

from __future__ import annotations

import argparse
import csv
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


def rows(filename: str) -> list[dict[str, str]]:
    with (ROOT / "reports/fixed_v23_order_study_v1" / filename).open(
        encoding="utf-8", newline=""
    ) as stream:
        return list(csv.DictReader(stream))


def make_figures() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.patches import FancyArrowPatch, Rectangle

    candidates = [Path("C:/Windows/Fonts/yumin.ttf"), Path("C:/Windows/Fonts/YuMincho.ttc")]
    for font in candidates:
        if font.exists():
            font_manager.fontManager.addfont(str(font))
    plt.rcParams.update({"font.size": 9, "axes.unicode_minus": False, "svg.fonttype": "path"})
    folder = PAPER / "figures"
    data = rows("primary_comparison.csv")
    for lang in ("en", "ja"):
        plt.rcParams["font.family"] = "Yu Mincho" if lang == "ja" else "Times New Roman"
        fig, ax = plt.subplots(figsize=(3.35, 2.5), layout="constrained")
        for index, row in enumerate(data):
            mean, low, high = (
                float(row[k]) * 100 for k in ("mean_increment", "ci95_low", "ci95_high")
            )
            ax.errorbar(
                mean,
                3 - index,
                xerr=[[mean - low], [high - mean]],
                fmt="o",
                color="#1f4e79",
                capsize=3,
                markersize=4,
            )
        ax.set_yticks(range(4), ["Cal JA", "Cal EN", "Main JA", "Main EN"])
        ax.set_xlabel("Excess disagreement D (pp)" if lang == "en" else "判断不一致の増分 D（pp）")
        ax.set_xlim(-1, 25)
        ax.set_ylim(-0.5, 3.5)
        ax.axvline(0, color="0.5", linewidth=0.8)
        ax.spines[["top", "right"]].set_visible(False)
        for ext in ("png", "svg"):
            fig.savefig(folder / f"order_increment_{lang}.{ext}", dpi=360)
        plt.close(fig)

        labels = (
            [
                "Question + used evidence + initial answer A",
                "Freeze evidence text and answer sentences",
                "Original / reversed / 3 shuffles\nOriginal order repeated 5 times",
                "Support score F and accept / rewrite decision",
                "Select A or common rewrite B\nB uses original evidence and A",
                "Join sealed external AI labels\nCompare quality and route cost",
            ]
            if lang == "en"
            else [
                "質問 ＋ 実使用根拠 ＋ 初回回答 A",
                "根拠本文と回答の文を固定",
                "元順序・逆順・シャッフル3種\n元順序を5回反復",
                "支持スコア F と採用・書換え判断",
                "A または共通の書換え B を選択\nB の入力は元順序の根拠と A",
                "封印済みの外部AIラベルを結合\n品質と経路費用を比較",
            ]
        )
        fig, ax = plt.subplots(figsize=(3.35, 3.3), layout="constrained")
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
            ax.text(0.5, y + 0.39, label, ha="center", va="center", fontsize=8.6)
            if index < len(labels) - 1:
                ax.add_patch(
                    FancyArrowPatch(
                        (0.5, y - 0.01),
                        (0.5, y - 0.20),
                        arrowstyle="-|>",
                        mutation_scale=9,
                        color="0.3",
                    )
                )
        for ext in ("png", "svg"):
            fig.savefig(folder / f"experimental_design_{lang}.{ext}", dpi=360)
        plt.close(fig)


def data_table(key: str, lang: str) -> tuple[list[str], list[list[str]], list[int]]:
    primary = rows("primary_comparison.csv")
    quality = rows("quality_and_operational_cost.csv")
    if key == "primary":
        headers = (
            ["Cohort", "n", "D (pp)", "95% CI (pp)"]
            if lang == "en"
            else ["区分", "n", "D (pp)", "95%区間 (pp)"]
        )
        values = [
            [
                f"{r['cohort'].capitalize()} {r['language'].upper()}",
                r["comparable_qa"],
                f"{float(r['mean_increment']) * 100:.2f}",
                f"[{float(r['ci95_low']) * 100:.2f}, {float(r['ci95_high']) * 100:.2f}]",
            ]
            for r in primary
        ]
        return headers, values, [1250, 380, 850, 2339]
    values = []
    for cohort, language in [("main", "en"), ("main", "ja"), ("cal", "en"), ("cal", "ja")]:
        for route, short in [("no_repair", "NR"), ("original", "OE"), ("always_rewrite", "AR")]:
            r = next(
                r
                for r in quality
                if (r["cohort"], r["language"], r["route"]) == (cohort, language, route)
            )
            label = f"{cohort.capitalize()} {language.upper()}"
            if key == "quality":
                values.append([label, short, r["reliable"], r["unreliable"], r["indeterminate"]])
            elif route != "no_repair":
                values.append(
                    [
                        label,
                        short,
                        r["native_attempts_sum"],
                        str(int(r["input_tokens_sum"]) + int(r["output_tokens_sum"])),
                    ]
                )
    if key == "quality":
        return (
            (
                ["Cohort", "Route", "Y=1", "Y=0", "Y=?"]
                if lang == "en"
                else ["区分", "方策", "Y=1", "Y=0", "Y=?"]
            ),
            values,
            [1350, 850, 873, 873, 873],
        )
    return (
        (
            ["Cohort", "Route", "Calls", "Tokens"]
            if lang == "en"
            else ["区分", "方策", "呼出し", "トークン"]
        ),
        values,
        [1350, 700, 850, 1919],
    )


def build(content: dict, lang: str) -> dict:
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
            paragraph(block[lang], kind)
    for ref in content["references"]:
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
        add_run(link, ref["url"])
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
    output = HERE / f"iciae2027_manuscript_{lang}.docx"
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
    make_figures()
    results = [build(content, lang) for lang in ("en", "ja")]
    assert results[0]["tables"] == results[1]["tables"]
    report = {
        "version": content["version"],
        "template_sha256": TEMPLATE_HASH,
        "block_count": len(ids),
        "documents": results,
    }
    (PAPER / "notes/draft_build_manifest.json").write_text(
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
