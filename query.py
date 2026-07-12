import voyageai
import numpy as np
import json


def search(query, top_k=3):
    with open("chunks_embedded.json") as f:
        chunks = json.load(f)

    vo = voyageai.Client()

    chunks_embeddings = np.array([c["embedding"] for c in chunks])

    print(f"searching for question: {query}")
    result = vo.embed([query], model="voyage-4", input_type="query")
    print(f"result of embedding query {result}")
    query_embedding = np.array(result.embeddings[0])

    scores = chunks_embeddings @ query_embedding

    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for i in top_indices:
        results.append(
            {
                "score": float(scores[i]),
                "section": chunks[i]["section"],
                "text": chunks[i]["text"],
            }
        )
    return results
