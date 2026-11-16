"""Check every figure/table in the exported English PDF, including captions/notes.

Run after native Word export. This inspects PDF geometry, not Word keep settings.
The numeric tolerances below are measurement tolerances, not conference rules.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pdfplumber
import pymupdf

HERE = Path(__file__).resolve().parent
POINTS_PER_MM = 72 / 25.4
BODY_TOP = 25 * POINTS_PER_MM


def same_column(rect_a, rect_b, page_width):
    return ((rect_a[0] + rect_a[2]) / 2 < page_width / 2) == (
        (rect_b[0] + rect_b[2]) / 2 < page_width / 2
    )


def audit(pdf_path: Path, content_path: Path) -> dict:
    content = json.loads(content_path.read_text(encoding="utf8"))
    results = []
    with pymupdf.open(pdf_path) as pdf, pdfplumber.open(pdf_path) as physical:
        assert len(pdf) == 8, "English full paper must remain within the 4–8 page limit"
        first_page = pdf[0]
        author = first_page.search_for(content["corresponding_author"]["en"])
        abstract_heading = first_page.search_for("Abstract")
        keywords = first_page.search_for(
            next(b["en"] for b in content["blocks"] if b["id"] == "keywords")
        )
        assert author and abstract_heading and keywords
        metadata_gap = abstract_heading[0].y0 - max(r.y1 for r in author)
        # A readability guard against losing the template's blank lines, not an official point value.
        assert metadata_gap >= 12, "Corresponding author and Abstract are too close"
        assert all(r.x1 < first_page.rect.width / 2 for r in keywords)
        abstract_region = pymupdf.Rect(
            35, max(r.y1 for r in abstract_heading) + 0.5,
            first_page.rect.width / 2, min(r.y0 for r in keywords) - 0.5,
        )
        expected_abstract = next(b["en"] for b in content["blocks"] if b["id"] == "abstract")
        assert re.sub(r"\s+", "", first_page.get_text(clip=abstract_region)) == re.sub(
            r"\s+", "", expected_abstract
        ), "Abstract must be complete before Keywords in the left column"
        for block in content["blocks"]:
            if block["type"] not in ("figure", "table"):
                continue
            matches = [
                (i, page.search_for(block["en"]))
                for i, page in enumerate(pdf)
                if page.search_for(block["en"])
            ]
            assert len(matches) == 1, f"Missing or ambiguous caption: {block['id']}"
            index, caption_rectangles = matches[0]
            page = pdf[index]
            caption = pymupdf.Rect(caption_rectangles[0])
            for rect in caption_rectangles[1:]:
                caption |= rect
            group = pymupdf.Rect(caption)
            if block["type"] == "figure":
                candidates = [
                    image["bbox"]
                    for image in page.get_image_info()
                    if same_column(image["bbox"], caption, page.rect.width)
                    and image["bbox"][3] <= caption.y0 + 1
                ]
                assert candidates, f"Image absent above caption: {block['id']}"
                object_box = min(candidates, key=lambda r: caption.y0 - r[3])
                group |= pymupdf.Rect(object_box)
            else:
                candidates = [
                    table.bbox
                    for table in physical.pages[index].find_tables()
                    if same_column(table.bbox, caption, page.rect.width)
                    and table.bbox[1] >= caption.y1 - 1
                ]
                assert candidates, f"Table absent below caption: {block['id']}"
                object_box = min(candidates, key=lambda r: r[1] - caption.y1)
                group |= pymupdf.Rect(object_box)
                notes = [
                    text_block
                    for text_block in page.get_text("blocks")
                    if text_block[4].lstrip().startswith("Note.")
                    and same_column(text_block, caption, page.rect.width)
                    and text_block[1] >= object_box[3] - 1
                ]
                assert notes, f"Note absent after table: {block['id']}"
                note = min(notes, key=lambda r: r[1] - object_box[3])
                group |= pymupdf.Rect(note[:4])

            column_left = (
                16 * POINTS_PER_MM
                if (object_box[0] + object_box[2]) / 2 < page.rect.width / 2
                else 109 * POINTS_PER_MM
            )
            assert abs(object_box[0] - column_left) < 0.6, block["id"]
            assert object_box[2] <= column_left + 85 * POINTS_PER_MM + 0.6, block["id"]
            words = [
                word
                for word in page.get_text("words")
                if same_column(word, group, page.rect.width)
                and BODY_TOP - 2 <= word[1] <= page.rect.height - BODY_TOP + 1
            ]
            above = [word for word in words if word[3] < group.y0 - 0.5]
            below = [word for word in words if word[1] > group.y1 + 0.5]
            if not above and group.y0 <= BODY_TOP + 10:
                placement = "top"
            elif not below and group.y0 > page.rect.height / 2:
                placement = "bottom"
            else:
                raise AssertionError(
                    f"{block['id']} is inside a column: page {index + 1}, "
                    f"{len(above)} words above / {len(below)} words below"
                )
            results.append(
                {
                    "id": block["id"],
                    "caption": block["en"],
                    "page": index + 1,
                    "column": "left" if column_left < 100 else "right",
                    "placement": placement,
                    "group_bbox_points": [round(v, 3) for v in group],
                    "object_bbox_points": [round(v, 3) for v in object_box],
                    "body_words_above": len(above),
                    "body_words_below": len(below),
                    "remaining_body_height_below_points": round(
                        page.rect.height - BODY_TOP - group.y1, 3
                    ),
                }
            )
        assert len(results) == 12
        links = {link["uri"] for p in pdf for link in p.get_links() if "uri" in link}
        assert all(ref["url"] in links for ref in content["references"])
    return {
        "english_pdf_pages": 8,
        "figures_and_tables": results,
        "top_count": sum(r["placement"] == "top" for r in results),
        "bottom_count": sum(r["placement"] == "bottom" for r in results),
        "all_12_at_column_top_or_bottom": True,
        "all_reference_hyperlinks_present": True,
        "author_to_abstract_gap_points": round(metadata_gap, 3),
        "abstract_and_keywords_on_first_page_left_column": True,
        "interpretation": "Top groups have no preceding text or heading in the column; "
        "bottom groups occupy its lower part and have no subsequent text. "
        "Captions and table notes belong to their figure/table group. "
        "Numeric tolerances are inspection tolerances, not official layout allowances.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=HERE / "iciae2027_manuscript_en.pdf")
    parser.add_argument("--content", type=Path, default=HERE / "draft_content.json")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = audit(args.pdf, args.content)
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
