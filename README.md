# 🧠 RAG Customer Support Assistant (Fully Local)

![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python)
![Local](https://img.shields.io/badge/100%25-Local-green)
![LLM](https://img.shields.io/badge/LLM-Ollama-orange)
![Embeddings](https://img.shields.io/badge/Embeddings-nomic--embed--text-purple)
![Cost](https://img.shields.io/badge/Cost-Free-brightgreen)

> A minimal, beginner-friendly **Retrieval-Augmented Generation (RAG)** chatbot  
> that answers customer queries from a PDF knowledge base —  
> 🚫 No cloud APIs • 💸 Zero cost • 🔒 Fully local

---

## ✨ Key Features

- 📄 Works directly with your **PDF knowledge base**
- ⚡ Fully **offline setup (Ollama-powered)**
- 🧠 Clean **RAG pipeline** (retrieval + generation)
- 🔍 Built-in **debug mode** to inspect retrieved chunks
- 🧩 Modular architecture using **LangGraph**
- 🚨 Smart **escalation system (HITL-ready)**

---

## 📁 Project Structure

```bash
rag-support/
├── app.py           # CLI chatbot (entry point)
├── graph.py         # LangGraph workflow (router → process → output / escalate)
├── ingest.py        # PDF → chunks → embeddings → ChromaDB
├── prompts.py       # Prompt templates
├── requirements.txt # Python dependencies
└── README.md        # This file
```

---

## ⚙️ Prerequisites

| Tool    | Version | Purpose                |
|---------|--------|------------------------|
| Python  | 3.12+  | Runtime                |
| Ollama  | latest | Local LLM + embeddings |
| pip     | latest | Package manager        |

---

## 🚀 Installation

### 1️⃣ Install Ollama

Download from: https://ollama.com/download

Pull required models:

```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

Verify Ollama:

```bash
ollama list
```

---

### 2️⃣ Setup Project

```bash
mkdir rag-support
cd rag-support
# place all project files here
```

---

### 3️⃣ Create Virtual Environment (Recommended)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

---

### 4️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 5️⃣ Add PDF Knowledge Base

```bash
rag-support/
└── knowledge_base.pdf
```

---

### 6️⃣ Ingest the PDF

```bash
python ingest.py knowledge_base.pdf
```

**Expected Output:**

```text
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

### 7️⃣ Start Chatbot

```bash
python app.py
```

---

## 💬 Usage

```text
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

👉 Prefix any query with `debug` to view retrieved chunks.

---

## 🔄 LangGraph Workflow

```text
                User Query
                    │
                    ▼
            ┌─────────────┐
            │ router_node │
            └──────┬──────┘
                   │
       ┌───────────┴───────────┐
       │                       │
       ▼                       ▼
(normal query)        (invalid / too short)
       │                       │
       ▼                       ▼
┌──────────────┐        ┌───────────────┐
│ process_node │        │ escalate_node │ (HITL)
└──────┬───────┘        └───────────────┘
       │
       │
       ▼
┌─────────────┐
│ output_node │
└──────┬──────┘
       │
       ▼
      END
```
---

## 🧩 Nodes

| Node            | Responsibility |
|-----------------|----------------|
| `router_node`   | Validates query structure; escalates bad queries |
| `process_node`  | Embeds query → retrieves top-3 chunks → queries LLM |
| `output_node`   | Returns confident answer |
| `escalate_node` | HITL placeholder with escalation reason |

---

## 📦 State Object (`SupportState`)

```python
{
  "query": str,
  "retrieved_docs": list[str],
  "answer": str,
  "escalate": bool,
  "escalation_reason": str,
  "final_response": str,
}
```

---

## 🧠 Conditional Routing Logic

```text
router_node:
  if len(query) < 3           → escalate (unclear query)
  if no alphabetic words      → escalate (not a real question)

process_node:
  if retrieved_docs < 1       → escalate (no relevant content)
  if LLM error               → escalate (system failure)
  if "i don't know" in answer → escalate (answer not in KB)
```

---

## 🚨 HITL Design

When escalation is triggered:

1. Set `escalate = True`
2. Add `escalation_reason`
3. Call `escalate_node`

In production, this would:
- POST to ticketing APIs (Zendesk, Freshdesk)
- Send Slack/Teams alerts
- Store queries for human review

**Manual simulation:**

```bash
python app.py
# then type:
debug <query>
```

---

## 📊 RAG Details

| Parameter        | Value                | Why |
|-----------------|---------------------|-----|
| Chunk size      | 500 chars           | Fits context, keeps sentences intact |
| Chunk overlap   | 50 chars            | Prevents boundary loss |
| Embedding model | `nomic-embed-text`  | Fast, local, high-quality |
| LLM             | `llama3.1:8b`       | Runs on ~8GB RAM |
| Top-K           | 3                   | Balanced context vs noise |
| Vector DB       | ChromaDB            | Local, persistent, zero-config |

---

## 🏗️ HLD — High-Level Design

```text
PDF → ingest.py → Ollama (embeddings) → ChromaDB
                    ↓
User → app.py → graph.py → retrieve → LLM → answer
```

---

## 🔧 LLD — Low-Level Design

### Modules

```text
ingest.py
  load_pdf(path) → str
  chunk_text(text) → list[str]
  embed_and_store(chunks) → None

graph.py
  router_node(state) → SupportState
  process_node(state) → SupportState
  output_node(state) → SupportState
  escalate_node(state) → SupportState
  should_escalate(state) → "escalate" | "continue"
  build_graph() → CompiledGraph
  run_query(query) → dict

prompts.py
  RAG_PROMPT → str
  ESCALATION_MESSAGE → str

app.py
  main() → None
```

---

## ⚠️ Error Handling

| Scenario                     | Handled In     | Behaviour |
|-----------------------------|---------------|-----------|
| PDF not found               | ingest.py     | FileNotFoundError |
| Empty/scanned PDF           | ingest.py     | ValueError |
| DB not ingested             | process_node  | Escalation |
| No docs retrieved           | process_node  | Escalation |
| LLM failure                 | process_node  | Escalation |
| "I don't know" response     | process_node  | Escalation |
| Query too short             | router_node   | Escalation |

---

## 🧪 Testing Approach

1. Happy path → correct answer
2. Out-of-scope → escalation
3. Short query (`hi`) → escalation
4. Debug mode → inspect chunks
5. No ingestion → graceful failure

---

## 🚀 Future Improvements

- Similarity score thresholds
- Re-ranking with cross-encoder
- Chat history (multi-turn)
- Web UI (Streamlit / FastAPI)
- Real HITL integrations
- Metadata filtering
- Evaluation harness

---

## ⚖️ Trade-offs

| Decision            | Why                  | Trade-off |
|---------------------|----------------------|-----------|
| Fixed chunking      | Simple               | May split sentences |
| Top-3 retrieval     | Fast, clean          | May miss edge cases |
| Heuristic confidence| No latency           | Less accurate |
| Local ChromaDB      | No setup             | Single-machine only |
| llama3.1:8b         | Runs locally         | Slower than large models |

---
