import fitz
import json
import re

HEADING_SIZE_THRESHOLD = 14
LIST_MARKER = re.compile(r"^(•|\d+\.)\s")


def extract_blocks_with_headings(doc, start, end):
    """Returns a list of {"text": ..., "is_heading": bool} for each block,
    across the page range, with the last block (footer) of each page dropped."""
    all_blocks = []
    for i in range(start, end):
        page = doc[i]
        info = page.get_text("dict")

        page_blocks = []
        for block in info["blocks"]:
            if "lines" not in block:
                continue
            spans = [s for line in block["lines"] for s in line["spans"]]
            if not spans:
                continue
            text = "".join(s["text"] for s in spans).strip()
            if not text:
                continue
            max_size = max(s["size"] for s in spans)
            page_blocks.append(
                {"text": text, "is_heading": max_size > HEADING_SIZE_THRESHOLD}
            )

        if page_blocks:
            page_blocks = page_blocks[:-1]  # drop footer, same as before

        all_blocks.extend(page_blocks)
    return all_blocks


def merge_lists(blocks):
    """Same list-merging logic as before, now operating on {"text","is_heading"} dicts."""
    merged = []
    buffer = []
    for b in blocks:
        if b["is_heading"]:
            if buffer:
                merged.append(
                    {"text": "\n".join(x["text"] for x in buffer), "is_heading": False}
                )
                buffer = []
            merged.append(b)
        elif LIST_MARKER.match(b["text"]):
            buffer.append(b)
        else:
            if buffer:
                merged.append(
                    {"text": "\n".join(x["text"] for x in buffer), "is_heading": False}
                )
                buffer = []
            merged.append(b)
    if buffer:
        merged.append(
            {"text": "\n".join(x["text"] for x in buffer), "is_heading": False}
        )
    return merged


doc = fitz.open(
    "/Users/mehdi/code/prog_docs/go/learning_go_an_idiomatic_approach_to_real_world_go_jon_bodner_we_lib_org.pdf"
)
blocks = extract_blocks_with_headings(doc, 310, 339)
blocks = merge_lists(blocks)

with open("blocks_tagged.json", "w") as f:
    json.dump(blocks, f, indent=2)
print(
    f"{len(blocks)} blocks saved, {sum(b['is_heading'] for b in blocks)} of them headings"
)
