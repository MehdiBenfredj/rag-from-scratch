# RAG Learning Notes — Ground Floor

## 1. The core idea
A plain LLM = closed-book exam (answers from memory, can be stale or wrong).
RAG = open-book exam (fetch relevant material first, then answer from it).

**Pipeline:** Indexing → Retrieval → Generation

| Stage | What happens | Common tools |
|---|---|---|
| Indexing | Split docs into chunks, turn chunks into embeddings, store in a vector DB | text splitters, embedding models, pgvector/Pinecone/Qdrant |
| Retrieval | Given a query, find the closest-matching chunks | cosine similarity search, hybrid (vector + keyword) search, reranking |
| Generation | LLM reads chunks + query, writes the answer | any chat LLM (Claude, GPT, open-source) |

## 2. Glossary (plain terms)
- **Chunk** — a small piece of a document (a paragraph or few sentences).
- **Embedding** — a chunk of text turned into a list of numbers that represents its meaning. Similar meanings → nearby numbers.
- **Vector store / vector database** — a database built to search "which stored numbers-list is closest to this one."
- **Hallucination** — the model confidently stating something false because it has no real source.
- **Reranking** — after an initial rough search, using a smarter (often slower) model to re-sort the top candidates by true relevance.
- **Hybrid search** — combining meaning-based (vector) search with classic keyword search (e.g. BM25), since each catches things the other misses.
- **Routing** — deciding *which* retrieval strategy or data source to use before you even search, based on the question.
- **Agentic RAG** — a RAG system that can loop: retrieve, judge if that was good enough, retrieve again or reformulate, repeat.

## 3. Tool landscape (as of mid-2026)
- **LangChain** — orchestration framework: chaining LLM calls, tools, memory. Big ecosystem, but API has churned a lot; code from 2024 tutorials often breaks.
- **LangGraph** — built for stateful, looping, multi-step flows (agents). This is where CRAG / Adaptive RAG-style logic now typically lives.
- **LlamaIndex** — retrieval-first framework; strongest at data ingestion (150+ connectors) and indexing strategies. Common pairing: LlamaIndex for data, LangGraph for control flow.
- **Haystack** — production-pipeline focused, popular in regulated/enterprise settings.
- **Vector databases** — pgvector (Postgres extension, fine under ~5-10M vectors, cheapest if you already run Postgres), Pinecone (managed, easy, costs scale with usage), Qdrant/Weaviate/Milvus (self-hosted, more control).
- **Embedding models** — OpenAI text-embedding-3-large (safe default), Cohere embed, open-source options like Qwen3-Embedding for multilingual/self-hosted needs.
- **Environment for learning** — Google Colab is fine for quick experiments with no local setup; local Python (venv) is better once you want persistence, real file handling, and to see costs/latency clearly.

## 4. Video relevance check — "RAG From Scratch" (Lance Martin, LangChain, April 2024)
**Still valid:** the 3-stage pipeline, query translation ideas (multi-query, RAG-fusion, decomposition, step-back, HyDE), routing, CRAG, Adaptive RAG — these are *reasoning patterns*, not syntax.

**Likely to need updating:**
- Exact LangChain/LCEL code (breaking API changes since, LangChain reached 1.0 in Oct 2025)
- Agent-like loops (CRAG, Adaptive RAG) — now more naturally built in LangGraph
- No mention of contextual retrieval (prepending a short "where this chunk fits" summary before embedding) — a solid 2024-onward upgrade
- No mention of hybrid search + reranking as now-standard baseline
- Mindset shift: build evaluation (does retrieval actually find the right chunk?) *before* optimizing retrieval tricks

## 5. Cost awareness (keep this front of mind as we go)
Every choice has a $ and latency tag:
- Embedding a document = one-time cost per chunk (small, but adds up at scale)
- Every query = 1 embedding call + 1+ LLM generation call, minimum
- Reranking, multi-query, HyDE, agentic loops = *extra* LLM calls per single user question — these improve quality but multiply cost and latency
- Managed vector DBs (Pinecone) = pay for hosting; self-hosted (pgvector) = pay in setup/maintenance time instead

## 6a. Progress log — Indexing (hands-on, raw Python)

**Corpus:** "Learning Go" (Bodner), Chapter 12 "Concurrency in Go" — pages 286-316 (PDF indices), ~30 pages.

**Stack decided:**
- Embeddings: **Voyage AI** (free tier, 200M tokens) — chosen over local `sentence-transformers` because the learning machine is an Intel Mac, and PyTorch dropped Intel Mac wheel support in 2024. Cloud embedding avoids adding heavy local dependencies.
- Generation: **Claude via OpenRouter**, using the OpenAI-compatible client — chosen because Claude Pro subscription doesn't include API access (separate billing), and OpenRouter credits were already available.
- PDF extraction: switched from `pypdf` to **PyMuPDF (`fitz`)** after discovering `pypdf` doesn't preserve paragraph structure (no double-newlines between paragraphs in this PDF's extracted text). `fitz` reads real layout data — paragraph blocks and font sizes — directly from the PDF.

**Pipeline built so far (in order):**
1. `extract.py` — pull raw text per page with `pypdf`, sanity-checked page count/chars. (Later superseded for structure by `fitz`.)
2. Manually identified and excluded front/back matter (index page, ad page) — decided **not** to strip inconsistent page-number footers by hand (accepted as minor noise) *until* switching to `fitz`, where footers turned out to be reliably the last block on every page — so they get dropped for free.
3. Discovered naive fixed-size (500-char) chunking cuts code blocks and sentences in half — confirmed by inspection, motivating a structure-aware approach.
4. Built a **recursive character splitter** (paragraph → line → sentence → word fallback), mirroring what LangChain's `RecursiveCharacterTextSplitter` does internally.
5. Found `pypdf`'s text lacked real paragraph breaks — switched to `fitz`'s `get_text("blocks")`, which groups text using the PDF's actual layout/spacing data.
6. Fixed list fragmentation: bulleted (`•`) and numbered (`\d+.`) list items were each becoming separate blocks — merged consecutive list-marker blocks into one.
7. Used font size (`get_text("dict")`, ~18.9pt for headings vs ~10.5pt body text in this book) to detect section headings automatically.
8. Labeled every content block with its current section (the most recent heading seen), then dropped headings themselves as standalone chunks (their text lives on as metadata instead).
9. Final merge: group blocks up to an ~800-character target, **closing a chunk early whenever the section changes** — guaranteeing no chunk mixes content from two sections.

**Output:** `chunks_final.json` — a list of `{"text": ..., "section": ...}` records. This structured shape (not just raw text) is what gets embedded next; `section` rides along as unembedded metadata for later use in generation (citing where an answer came from).

**Key lesson threaded through all of this:** clean structure-aware chunking took far more iteration than the "one-line" naive version — and that iteration is exactly where retrieval quality is won or lost, not in picking a fancier embedding model.

## 6b. Progress log — Retrieval & Generation (hands-on, raw Python)

**Embedding the corpus:**
- Before embedding, glued `section` + `text` together as the embedding input (a lightweight version of "contextual retrieval" — giving the model surrounding context, not an isolated fragment). Kept the original `text` field clean and separate for later display/generation use — only the embedding *input* was glued, not the stored data.
- Embedded all 96 chunks in a single batched `vo.embed()` call (`model="voyage-4"`, `input_type="document"`) rather than one call per chunk — far fewer round-trips.
- Result: 96 chunks → 1024-dimension vectors each, 13,132 total tokens used (~0.007% of Voyage's 200M free tier — confirms cost was never a real constraint at this scale).

**Retrieval (`query.py` / `search()`):**
- Query gets embedded separately with `input_type="query"` — the other side of the query/document distinction Voyage expects.
- Similarity computed as a **dot product** between the query vector and all chunk vectors at once (via numpy), not a slow per-chunk loop. Dot product is valid here (instead of full cosine similarity) specifically because Voyage returns vectors already normalized to length 1 — a real simplification, not a shortcut taken for convenience.
- Top-k chunks returned by score, highest first.
- Observed: mostly accurate top matches, occasionally "slightly off" — expected and acceptable at this small a corpus size (96 chunks); flagged as something a proper evaluation set would let us measure precisely later, rather than eyeballing.

**Generation (`generate.py` / `generate_answer()`):**
- Retrieved chunks formatted as numbered, labeled sources (`[Source N — section]`) inside the prompt.
- Explicit instruction: answer **only** from the provided sources, and say so clearly if the sources are insufficient — this is the instruction that actually separates "RAG" from "an expensive wrapper around the model's pretrained guesses."
- Generation via Claude (`anthropic/claude-sonnet-4.6`) through the OpenRouter OpenAI-compatible client.

**Validation — two real tests run:**
1. **In-scope query** ("How do I safely share data between goroutines?") → produced a detailed, correctly-grounded answer citing the book's actual guidance (channels vs. mutex decision criteria, `sync.RWMutex`, the "share memory by communicating" proverb) with source numbers attached throughout.
2. **Out-of-scope query** ("How do Go generics work?") → Claude correctly refused to answer from its own pretrained knowledge (which it clearly has) and explicitly stated the sources didn't cover it. This confirmed the "answer only from sources" instruction holds under real pressure, not just in easy cases.

**End-to-end pipeline, final form:**
```
PDF → PyMuPDF layout-aware extraction → heading/list-aware chunking
    → Voyage embeddings → dot-product retrieval → Claude generation (source-grounded)
```

**Status: complete, working v1** — built by hand, every stage understood and justified, not copy-pasted from a tutorial.

## 6c. Where to go next (real options, no wrong answer)
1. **Scale up** — run the full 494-page book instead of one chapter; expect new problems (more embeddings, more section collisions, slower search) worth meeting firsthand.
2. **Add evaluation** — build a small set of question/expected-answer pairs and *measure* retrieval quality instead of eyeballing it. Likely the single highest-leverage next skill.
3. **Try a query-translation technique** (multi-query or HyDE, from the original video) — see if it measurably improves the "slightly off" retrieval cases noticed during testing.
4. **Rebuild in LangChain or LlamaIndex** — now that the underlying mechanics are understood firsthand, see which hand-written functions collapse into single framework calls, and decide if that trade-off (convenience vs. transparency) is worth it.

## 6. Suggested learning path (draft — to be tuned to your setup)
1. Build indexing + retrieval **from raw Python**, no framework — chunk text, call an embedding API, do cosine similarity by hand. Goal: understand what frameworks later automate.
2. Add generation — wire retrieved chunks into a prompt, call an LLM, compare grounded vs ungrounded answers.
3. Introduce one framework (LangChain or LlamaIndex) and rebuild the same pipeline — feel the abstraction, know what it's hiding.
4. Query translation techniques (multi-query, HyDE, etc.) — add one at a time, measure if it actually helps.
5. Routing + hybrid search + reranking.
6. Agentic patterns (CRAG, Adaptive RAG) via LangGraph.
7. Evaluation — build a small test set of Q&A pairs, measure retrieval accuracy and groundedness before/after each change.
