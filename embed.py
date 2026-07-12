import voyageai
import json
import os

from voyageai.object import embeddings

with open("chunks_final.json") as f:
    chunks = json.load(f)


vo = voyageai.Client()

embedding_input = [f"{c['section']}\n\n{c['text']}" for c in chunks]


print(f"Embedding {len(embedding_input)} chunks")
result = vo.embed(embedding_input, model="voyage-4", input_type="document")

for chunk, embedding in zip(chunks, result.embeddings):
    chunk["embedding"] = embedding

print(f"Done. Each embedding has {len(chunks[0]['embedding'])} dimensions.")
print(f"Total tokens used: {result.total_tokens}")

with open("chunks_embedded.json", "w") as f:
    json.dump(chunks, f)

print("Saved to chunks_embedded.json")
