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
            ["English (n=80)", "Japanese (n=68)", "Japanese − English"]
            if lang == "en"
            else ["英語（n=80）", "日本語（n=68）", "日本語 − 英語"],
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
                "Evaluate sentence support F\nF ≥ 0.7: retain A; otherwise rewrite",
                "Select A or the same rewrite B\nB uses original evidence and A",
                "Compare selected-answer quality\nand computation cost",
            ]
            if lang == "en"
            else [
                "質問 ＋ 実使用根拠 ＋ 初回回答 A",
                "根拠本文と回答の文を固定",
                "元順序・逆順・シャッフル3種\n元順序を5回反復",
                "文の支持スコア F を評価\nF ≥ 0.7：Aを採用、未満：書換え",
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
    if key == "configuration":
        rows = [
            (
                "Evaluation questions",
                "評価対象の質問",
                "EN 100; JA 100; total 200",
                "EN 100、JA 100、計200問",
            ),
            (
                "Retrieval",
                "検索",
                "50 candidates; RRF constant 60; top-k 5",
                "候補50、RRF定数60、top-k 5",
            ),
            (
                "Initial generation",
                "初回生成",
                "Context 4096; temperature 0; output limit 512",
                "文脈4096、温度0、出力上限512",
            ),
            (
                "Evaluation and rewriting",
                "評価・書換え",
                "Context 12288; temperature 0.2; batch 128; prompt version 12",
                "文脈12288、温度0.2、バッチ128、プロンプト第12版",
            ),
            (
                "Task and reasoning limits",
                "タスク・推論上限",
                "6144 total; 4096 for reasoning",
                "タスク全体6144、うち推論4096",
            ),
            (
                "Trial plan per question",
                "質問ごとの試行",
                "5 orders; 5 repetitions; first trial shared; at most 9 trials",
                "順序5条件、反復5回、最初の試行を共用、最大9試行",
            ),
            (
                "Seeds",
                "シード",
                "Generation/shuffles 42; execution order 43",
                "生成・シャッフル42、実行順43",
            ),
            (
                "Decision thresholds",
                "判断閾値",
                "Operating 0.7; audit 0.5, 0.6, 0.7, 0.8, 0.9",
                "運用0.7、監査0.5・0.6・0.7・0.8・0.9",
            ),
            (
                "Bootstrap",
                "ブートストラップ",
                "10000 document-group resamples; seed 42; 95% interval",
                "文書グループを10000回復元抽出、シード42、95%区間",
            ),
        ]
        values = [[r[0 if lang == "en" else 1], r[2 if lang == "en" else 3]] for r in rows]
        return (["Setting", "Value"] if lang == "en" else ["設定", "値"]), values, [1600, 3219]
    if key == "development":
        values = (
            [
                ["Synthetic EN", "12 cases", "Relations, scope, uncertainty"],
                ["Synthetic JA", "15 cases", "Relations, scope, uncertainty"],
                ["Saved EN QA", "15 questions / 42 sentences", "Previously observed errors"],
                ["Support recall", "57/58 (98.3%)", "Original + reversed evidence"],
                ["Non-support specificity", "14/16 (87.5%)", "Original + reversed evidence"],
            ]
            if lang == "en"
            else [
                ["人工例 EN", "12例", "関係・範囲・不確実性"],
                ["人工例 JA", "15例", "関係・範囲・不確実性"],
                ["保存QA EN", "15問 / 42文", "既知の誤り"],
                ["支持の再現率", "57/58 (98.3%)", "元順序＋逆順"],
                ["非支持の特異度", "14/16 (87.5%)", "元順序＋逆順"],
            ]
        )
        headers = (
            ["Diagnostic", "Size / result", "Purpose / condition"]
            if lang == "en"
            else ["診断", "規模 / 結果", "用途 / 条件"]
        )
        return headers, values, [1550, 1450, 1819]
    if key == "primary":
        labels = [
            ("Selected questions", "選定問数"),
            ("Comparable questions", "比較可能問数"),
            ("Excluded refusals", "除外：拒否"),
            ("Missing initial answers", "初回回答の欠測"),
            ("Failed rewrites", "書換え失敗"),
            ("Order-varying / comparable", "判断変動 / 比較可能"),
            ("Order disagreement O (%)", "順序間不一致 O (%)"),
            ("Repetition disagreement R (%)", "反復間不一致 R (%)"),
            ("Mean D (pp)", "平均D (pp)"),
            ("95% interval for D (pp)", "Dの95%区間 (pp)"),
        ]
        columns = []
        for r in result["primary"]:
            columns.append(
                [
                    str(r["selected_qa"]),
                    str(r["comparable_qa"]),
                    str(r["exclusion_reasons"].get("invalid_or_unscorable_trials", 0)),
                    str(r["initial_failures"]),
                    str(r["rewrite_failures"]),
                    f"{r['decision_change_qa']}/{r['comparable_qa']}",
                    f"{r['mean_order_rate'] * 100:.2f}",
                    f"{r['mean_repeat_rate'] * 100:.2f}",
                    f"{r['mean_increment'] * 100:.2f}",
                    f"[{r['ci95'][0] * 100:.2f}, {r['ci95'][1] * 100:.2f}]",
                ]
            )
        values = [
            [label[lang == "ja"], columns[0][i], columns[1][i]] for i, label in enumerate(labels)
        ]
        return (
            (["Measure", "EN", "JA"] if lang == "en" else ["指標", "EN", "JA"]),
            values,
            [2350, 1234, 1235],
        )
    if key == "quality":
        values = []
        for language in ("en", "ja"):
            for route in ("no_repair", "original", "always_rewrite"):
                policy = next(
                    r
                    for r in result["quality"]
                    if r["language"] == language and r["route"] == route
                )
                values.append(
                    [
                        language.upper(),
                        {"no_repair": "NR", "original": "OE", "always_rewrite": "AR"}[route],
                    ]
                    + [
                        str(policy[k])
                        for k in ("reliable", "unreliable", "indeterminate", "missing")
                    ]
                )
        headers = (
            ["Lang.", "Policy", "Y=1", "Y=0", "Unclear", "Missing"]
            if lang == "en"
            else ["言語", "方策", "Y=1", "Y=0", "判定不能", "欠測"]
        )
        return headers, values, [650, 650, 650, 650, 1050, 1169]
    if key == "selection":
        labels = [
            ("Known A/B pairs", "判定可能なA/B"),
            ("Y(A)=0 → Y(B)=0", "Y(A)=0 → Y(B)=0"),
            ("Y(A)=0 → Y(B)=1", "Y(A)=0 → Y(B)=1"),
            ("Y(A)=1 → Y(B)=0", "Y(A)=1 → Y(B)=0"),
            ("Y(A)=1 → Y(B)=1", "Y(A)=1 → Y(B)=1"),
            ("OE missed / 0→1", "OE見逃し / 0→1"),
            ("OE harmful / 1→0", "OE有害選択 / 1→0"),
        ]
        columns = []
        for r in result["selection"]:
            columns.append(
                [str(r["known_pairs"])]
                + [str(r["transitions"][k]) for k in ("0->0", "0->1", "1->0", "1->1")]
                + [
                    f"{r['oe_missed_improvements']}/{r['transitions']['0->1']}",
                    f"{r['oe_harmful_rewrites']}/{r['transitions']['1->0']}",
                ]
            )
        values = [
            [label[lang == "ja"], columns[0][i], columns[1][i]] for i, label in enumerate(labels)
        ]
        return (
            (
                ["Transition / selection", "EN", "JA"]
                if lang == "en"
                else ["遷移 / 選択", "EN", "JA"]
            ),
            values,
            [2819, 1000, 1000],
        )
    if key == "order_quality":
        labels = [
            ("Order-varying decisions", "順序で判断が変動"),
            ("Both Y=0 and Y=1 selected", "Y=0とY=1の両方を選択"),
            ("A and B have the same Y", "AとBが同じY"),
            ("Includes indeterminate Y", "判定不能Yを含む"),
            ("Route tokens vary", "経路トークン数が変動"),
        ]
        columns = []
        for r in result["primary"]:
            c = r["classification_counts"]
            varying = [
                q
                for q in result["questions"]
                if q["language"] == r["language"]
                and q["comparable"]
                and q["decision_varies_in_valid_orders"]
            ]
            token_varying = sum(
                q["known_route_cost_range"]["recorded_input_plus_output_tokens"]["max"]
                > q["known_route_cost_range"]["recorded_input_plus_output_tokens"]["min"]
                for q in varying
            )
            columns.append(
                [
                    r["decision_change_qa"],
                    c["decision_change_quality_changes"],
                    c["decision_change_same_binary_quality"],
                    c["decision_change_quality_unknown"],
                    token_varying,
                ]
            )
        values = [
            [
                label[lang == "ja"],
                str(columns[0][i]),
                str(columns[1][i]),
                str(columns[0][i] + columns[1][i]),
            ]
            for i, label in enumerate(labels)
        ]
        return (
            (["Outcome", "EN", "JA", "Total"] if lang == "en" else ["結果", "EN", "JA", "計"]),
            values,
            [2619, 650, 650, 900],
        )
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
                sentences = len(trial["fixed_claims"])
                supported = sum(v["label"] == "supported" for v in trial["verdicts"])
                assert abs(supported / sentences - trial["score"]) < 1e-12
                values.append(
                    [
                        str(number),
                        order,
                        f"{supported}/{sentences}",
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
        ar_tokens = {
            r["language"]: r["input_tokens"] + r["output_tokens"]
            for r in result["quality"]
            if r["route"] == "always_rewrite"
        }
        values = [
            [
                r["language"].upper(),
                "OE" if r["route"] == "original" else "AR",
                str(r["calls"]),
                f"{r['input_tokens'] + r['output_tokens']:,}",
                f"{(r['input_tokens'] + r['output_tokens']) / ar_tokens[r['language']]:.2f}",
            ]
            for r in result["quality"]
            if r["route"] != "no_repair"
        ]
        headers = (
            ["Lang.", "Policy", "Calls", "Tokens", "Tokens / AR"]
            if lang == "en"
            else ["言語", "方策", "呼出し", "トークン", "AR比"]
        )
        return headers, values, [650, 650, 650, 1719, 1150]
    if key == "semantics":
        values = [
            [
                r["language"].upper(),
                str(r["false_support_observations"]),
                str(r["negative_sentence_trial_observations"]),
                f"{100 * r['false_support_observations'] / r['negative_sentence_trial_observations']:.1f}%",
            ]
            for r in result["semantics"]
        ]
        headers = (
            ["Lang.", "False support", "External negatives", "Rate"]
            if lang == "en"
            else ["言語", "誤支持", "外部の非支持", "割合"]
        )
        return headers, values, [650, 1450, 1669, 1050]
    if key == "thresholds":
        values = [
            [f"{t:.1f}"]
            + [
                f"{next(r['mean_increment'] for r in result['thresholds'] if r['language'] == language and r['threshold'] == t) * 100:.2f}"
                for language in ("en", "ja")
            ]
            for t in (0.5, 0.6, 0.7, 0.8, 0.9)
        ]
        headers = (
            ["Threshold", "EN D (pp)", "JA D (pp)"]
            if lang == "en"
            else ["閾値", "EN D (pp)", "JA D (pp)"]
        )
        return headers, values, [1219, 1800, 1800]
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
        if kind == "table_note":
            for name in ("ind", "jc", "spacing"):
                for node in props.findall(f"w:{name}", NS):
                    props.remove(node)
            props.append(element("jc", val="left"))
            props.append(element("spacing", before="40", after="100"))
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
                for column, (text, width) in enumerate(zip(row, widths, strict=True)):
                    tc = E.SubElement(tr, tag("tc"))
                    tc_props = E.SubElement(tc, tag("tcPr"))
                    tc_props.append(element("tcW", w=str(width), type="dxa"))
                    tc_props.append(element("vAlign", val="center"))
                    if index == 0:
                        tc_props.append(element("shd", fill="E7E6E6", val="clear"))
                    p = E.SubElement(tc, tag("p"))
                    pp = E.SubElement(p, tag("pPr"))
                    narrative_column = column == 0 and block["key"] in {
                        "configuration",
                        "primary",
                        "selection",
                        "order_quality",
                    }
                    narrative_column |= block["key"] == "configuration" and column == 1
                    pp.append(element("jc", val="left" if index and narrative_column else "center"))
                    pp.append(element("spacing", before="20", after="20"))
                    if (
                        index == 0
                        or (index == len(values) and block.get("notes"))
                        or (
                            (len(values) <= 7 or block["key"] in {"configuration", "primary"})
                            and index < len(values)
                        )
                    ):
                        pp.append(element("keepNext"))
                    if lang == "ja":
                        pp.append(element("snapToGrid", val="false"))
                    add_text(p, text, 20, index == 0)
            if block.get("notes"):
                paragraph(block["notes"][lang], "table_note")
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

    def numeric(cells):
        return [re.findall(r"\d+(?:\.\d+)?", " ".join(row)) for row in cells]

    for key, rows in results[0]["tables"].items():
        assert numeric(rows) == numeric(results[1]["tables"][key]), key
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
