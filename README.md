# rag-from-scratch

A minimal, from-scratch Retrieval-Augmented Generation (RAG) pipeline over a PDF book, built without any RAG framework — just PDF parsing, chunking, embeddings, cosine similarity, and an LLM call.

## Pipeline

The pipeline runs as a sequence of scripts, each reading the previous step's output and writing a JSON file for the next:

1. **`extract.py`** — Parses a PDF page range with PyMuPDF (`fitz`), classifies text blocks as headings vs. content based on font size, and merges list items into their own blocks. Output: `blocks_tagged.json`.
2. **`label.py`** — Walks the tagged blocks and labels each content block with the heading of the section it falls under. Output: `blocks_labeled.json`.
3. **`merge.py`** — Merges consecutive labeled blocks into chunks up to a target size (~800 chars), starting a new chunk whenever the section changes or the size limit would be exceeded. Output: `chunks_final.json`.
4. **`embed.py`** — Embeds each chunk (section heading + text) with Voyage AI (`voyage-4`). Output: `chunks_embedded.json`.
5. **`query.py`** — Given a question, embeds it and retrieves the top-k most similar chunks via cosine similarity (dot product over normalized embeddings).
6. **`generate.py`** — Runs an end-to-end query: retrieves relevant chunks and asks an LLM (via OpenRouter, `anthropic/claude-sonnet-4.6`) to answer strictly from the retrieved sources, citing which source each part of the answer came from.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install pymupdf voyageai numpy openai
```

Create a `.env` file (not committed) with:

```
api_key=<your Voyage AI API key>
open_router=<your OpenRouter API key>
```

## Usage

Run the pipeline in order to (re)build the indexed chunks from a PDF:

```bash
python extract.py   # PDF -> blocks_tagged.json
python label.py      # blocks_tagged.json -> blocks_labeled.json
python merge.py       # blocks_labeled.json -> chunks_final.json
python embed.py       # chunks_final.json -> chunks_embedded.json
```

Then ask a question:

```bash
python generate.py
```

Edit `user_question` in `generate.py` (or import `search`/`generate_answer` directly) to ask something else.

## Notes

- The PDF path and page range are currently hardcoded in `extract.py`.
- This is a learning/experimentation project — no error handling, tests, or CLI args are provided by design.
