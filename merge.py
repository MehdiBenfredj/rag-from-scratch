import json

TARGET_SIZE = 800


def merge_to_target_size(blocks, target_size):
    chunks = []
    current_text = ""
    current_section = None

    for block in blocks:
        text = block["text"]
        section = block["section"]

        section_changed = current_text and section != current_section
        too_big = current_text and len(current_text) + len(text) > target_size

        if section_changed or too_big:
            chunks.append({"text": current_text.strip(), "section": current_section})
            current_text = text
            current_section = section
        else:
            current_text = current_text + "\n\n" + text if current_text else text
            current_section = section

    if current_text:
        chunks.append({"text": current_text.strip(), "section": current_section})

    return chunks


with open("blocks_labeled.json") as f:
    blocks = json.load(f)

chunks = merge_to_target_size(blocks, TARGET_SIZE)

print(f"{len(blocks)} blocks -> {len(chunks)} final chunks")
print(
    f"Average chunk size: {sum(len(c['text']) for c in chunks) // len(chunks)} characters"
)
print(
    f"Smallest: {min(len(c['text']) for c in chunks)}, Largest: {max(len(c['text']) for c in chunks)}"
)

with open("chunks_final.json", "w") as f:
    json.dump(chunks, f, indent=2)
print("Saved to chunks_final.json")
