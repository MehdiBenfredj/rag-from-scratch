import json


def label_with_sections(blocks):
    current_section = None
    labeled = []

    for b in blocks:
        if b["is_heading"]:
            current_section = b["text"]
            continue  # heading itself doesn't need labeling, it's not chunk content

        labeled.append({"text": b["text"], "section": current_section})

    return labeled


with open("blocks_tagged.json") as f:
    blocks = json.load(f)

labeled_blocks = label_with_sections(blocks)

with open("blocks_labeled.json", "w") as f:
    json.dump(labeled_blocks, f, indent=2)
print(f"{len(labeled_blocks)} content blocks, each labeled with its section")
