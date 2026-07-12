from openai import OpenAI
import os
from query import search

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)


def generate_answer(query, retrieved_chunks):
    # Build the "book pages" the model gets to read -- numbered so we can
    # ask it to reference which one it used
    context = "\n\n".join(
        f"[Source {i + 1} — {c['section']}]\n{c['text']}"
        for i, c in enumerate(retrieved_chunks)
    )

    prompt = f"""Answer the question using ONLY the sources below. If the sources don't contain enough information to answer, say so clearly instead of guessing.

{context}

Question: {query}

When you use information from a source, mention which source number it came from."""

    response = client.chat.completions.create(
        model="anthropic/claude-sonnet-4.6",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
    )

    return response.choices[0].message.content


user_question = "How do Go generics work?"
results = search(user_question, top_k=5)
answer = generate_answer(user_question, results)


print(answer)
