# RAG Customer Support Assistant (Fully Local)

A minimal, beginner-friendly Retrieval-Augmented Generation (RAG) chatbot  
that answers customer queries from a PDF knowledge base — **no cloud APIs, no costs**.

---

## Project Structure

```
rag-support/
├── app.py           ← CLI chatbot (entry point)
├── graph.py         ← LangGraph workflow (router → process → output / escalate)
├── ingest.py        ← PDF → chunks → embeddings → ChromaDB
├── prompts.py       ← Prompt templates
├── requirements.txt ← Python dependencies
└── README.md        ← This file
```

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.12+ | Runtime |
| Ollama | latest | Local LLM + embeddings |
| pip | latest | Package manager |

---

## Installation

### Step 1 — Install Ollama

Download and install from: https://ollama.com/download

Then pull the required models (run in terminal / PowerShell):

```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

Verify Ollama is running:
```bash
ollama list
```

---

### Step 2 — Clone / create the project folder

```bash
mkdir rag-support
cd rag-support
# place all project files here
```

---

### Step 3 — Create a virtual environment (recommended)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

---

### Step 4 — Install Python packages

```bash
pip install -r requirements.txt
```

---

### Step 5 — Add your PDF knowledge base

Place your customer support PDF (FAQs, manuals, policies, etc.) in the project folder:

```
rag-support/
└── knowledge_base.pdf   ← your file
```

---

### Step 6 — Ingest the PDF

```bash
python ingest.py knowledge_base.pdf
```

Expected output:
```
=== Ingesting: knowledge_base.pdf ===
Step 1: Loading PDF...
  Extracted 24300 characters.
Step 2: Chunking text...
  Created 52 chunks.
Step 3: Embedding and storing in ChromaDB...
Generating embeddings for 52 chunks using 'nomic-embed-text'...
Stored 52 chunks in ChromaDB at './chroma_db'.

Ingestion complete! You can now run app.py to start chatting.
```

---

### Step 7 — Start the chatbot

```bash
python app.py
```

---

## Usage

```
You: What is your return policy?
Assistant:
You can return any item within 30 days of purchase with a valid receipt...

──────────────────────────────────────────────────────

You: debug How do I reset my password?
[DEBUG] Retrieved 3 chunk(s):
  [1] To reset your password, visit the login page and click 'Forgot Password'...
──────────────────────────────────────────────────────
Assistant:
Visit the login page, click 'Forgot Password', and enter your email address...

You: quit
Goodbye!
```

**Prefix any question with `debug`** to see the retrieved context chunks.

---

## LangGraph Workflow

```
User Query
    │
    ▼
┌─────────────┐
│ router_node │  ── too short / no real words? ──► ┐
└─────────────┘                                      │
    │ (normal query)                                  │
    ▼                                                 │
┌──────────────┐                                     │
│ process_node │  ── not enough docs OR             │
│              │     LLM says "I don't know"? ──►   │
└──────────────┘                                     │
    │ (confident answer)                              │
    ▼                                                 ▼
┌─────────────┐                              ┌───────────────┐
│ output_node │                              │ escalate_node │ (HITL)
└─────────────┘                              └───────────────┘
    │                                                 │
    └─────────────────── END ────────────────────────┘
```

### Nodes

| Node | Responsibility |
|------|---------------|
| `router_node` | Validates query structure; escalates obviously bad queries |
| `process_node` | Embeds query → retrieves top-3 chunks → asks LLM → checks answer |
| `output_node` | Packages the confident answer as `final_response` |
| `escalate_node` | HITL placeholder — returns escalation message with reason |

### State Object (`SupportState`)

```python
{
  "query":              str,        # user's question
  "retrieved_docs":     list[str],  # top-K chunks from ChromaDB
  "answer":             str,        # LLM-generated answer
  "escalate":           bool,       # True → go to escalate_node
  "escalation_reason":  str,        # human-readable reason
  "final_response":     str,        # what the user sees
}
```

---

## Conditional Routing Logic

```
router_node:
  if len(query) < 3            → escalate (unclear query)
  if no alphabetic words       → escalate (not a real question)

process_node:
  if retrieved_docs < 1        → escalate (no relevant content)
  if LLM error                 → escalate (system failure)
  if "i don't know" in answer  → escalate (answer not in KB)
```

---

## HITL Design

When escalation is triggered the system:
1. Sets `escalate = True` with a `escalation_reason` string
2. Calls `escalate_node` which formats and returns an escalation message
3. In production, this node would:
   - POST to a ticketing API (Zendesk, Freshdesk, etc.)
   - Send a Slack/Teams notification to the on-call agent
   - Append the query to a review queue in a database

**Manual override simulation**: run `python app.py` and type `debug <query>`.  
You can inspect retrieved chunks and see why the system escalated.

---

## RAG Details

| Parameter | Value | Why |
|-----------|-------|-----|
| Chunk size | 500 chars | Fits embedding context, carries full sentences |
| Chunk overlap | 50 chars | Prevents context loss at chunk boundaries |
| Embedding model | `nomic-embed-text` | Fast, high-quality, runs locally via Ollama |
| LLM | `llama3.1:8b` | Accurate 8B model, runs on 8 GB RAM |
| Top-K retrieval | 3 | Provides enough context without noise |
| Vector DB | ChromaDB (persistent) | Zero-config, local, no server needed |

---

## HLD — High-Level Design

```
┌──────────┐   PDF    ┌───────────┐  chunks  ┌───────────┐ embeddings ┌──────────┐
│  PDF KB  │ ───────► │ ingest.py │ ───────► │  Ollama   │ ─────────► │ ChromaDB │
└──────────┘          └───────────┘          │ (embed)   │            └──────────┘
                                             └───────────┘                  │
                                                                            │ stored
                                                                            ▼
┌──────────┐  query  ┌───────────┐          ┌───────────┐  top-K     ┌──────────┐
│  User    │ ──────► │  app.py   │ ───────► │ graph.py  │ ─────────► │ ChromaDB │
└──────────┘         └───────────┘          │(LangGraph)│  retrieve  └──────────┘
     ▲                                      └───────────┘
     │  answer                                    │
     └────────────────────────────────────────────┘
                                            Ollama LLM
                                          (llama3.1:8b)
```

---

## LLD — Low-Level Design

### Modules

```
ingest.py
  load_pdf(path)             → str
  chunk_text(text)           → list[str]
  embed_and_store(chunks)    → None

graph.py
  router_node(state)         → SupportState
  process_node(state)        → SupportState
  output_node(state)         → SupportState
  escalate_node(state)       → SupportState
  should_escalate(state)     → "escalate" | "continue"
  build_graph()              → CompiledGraph
  run_query(query)           → dict

prompts.py
  RAG_PROMPT                 str (template)
  ESCALATION_MESSAGE         str (template)

app.py
  main()                     → None  (REPL loop)
```

---

## Error Handling

| Scenario | Handled In | Behaviour |
|----------|-----------|-----------|
| PDF not found | `ingest.py` | `FileNotFoundError` with clear message |
| PDF is empty / scanned | `ingest.py` | `ValueError` with clear message |
| ChromaDB not ingested yet | `process_node` | Escalates with reason |
| No docs retrieved | `process_node` | Escalates with reason |
| LLM call fails | `process_node` | Escalates with reason |
| LLM says "I don't know" | `process_node` | Escalates with reason |
| Query too short | `router_node` | Escalates with reason |

---

## Testing Approach

1. **Happy path** — ask a question clearly answered in the PDF → confident answer
2. **Out-of-scope** — ask something not in the PDF → escalation
3. **Short query** — type `hi` → escalation (too short)
4. **Debug mode** — prefix with `debug` → inspect retrieved chunks
5. **No PDF ingested** — run `app.py` without running `ingest.py` first → graceful escalation

---

## Future Improvements

- **Similarity score threshold** — use ChromaDB distance scores for smarter confidence
- **Re-ranking** — use a cross-encoder to re-rank retrieved chunks
- **Chat history** — pass previous turns to the LLM for multi-turn conversations
- **Web UI** — replace CLI with a Streamlit or FastAPI frontend
- **Real HITL** — integrate Zendesk / Linear API in `escalate_node`
- **Metadata filtering** — tag chunks by product/category and filter at retrieval time
- **Eval harness** — automated test suite with golden Q&A pairs

---

## Trade-offs

| Decision | Why | Trade-off |
|----------|-----|-----------|
| Fixed-size chunking | Simple, predictable | May split sentences awkwardly |
| Top-3 retrieval | Low noise, fast | May miss edge-case relevant chunks |
| Heuristic confidence | Zero extra latency | Less accurate than embedding distance |
| ChromaDB local | No server needed | Single-machine only |
| llama3.1:8b | Runs on 8 GB RAM | Slower / less capable than 70B models |