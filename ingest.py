"""
ingest.py — Load a PDF, chunk it, embed with Ollama, store in ChromaDB.

Usage:
    python ingest.py <path_to_pdf>

Example:
    python ingest.py knowledge_base.pdf
"""

import sys
import os
import chromadb
from pypdf import PdfReader
from langchain_ollama import OllamaEmbeddings

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CHUNK_SIZE = 500        # characters per chunk
CHUNK_OVERLAP = 50      # overlap so context isn't lost at boundaries
EMBEDDING_MODEL = "nomic-embed-text"   # fast, accurate Ollama embedding model
CHROMA_PATH = "./chroma_db"            # local ChromaDB storage folder
COLLECTION_NAME = "support_kb"         # collection name inside ChromaDB

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_pdf(path: str) -> str:
    """Extract all text from a PDF file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"PDF not found: {path}")

    reader = PdfReader(path)
    if len(reader.pages) == 0:
        raise ValueError("PDF has no pages.")

    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

    if not text.strip():
        raise ValueError("PDF appears to be empty or scanned (no extractable text).")

    return text


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping fixed-size chunks.

    Why 500 chars?
      - Small enough to stay within embedding context limits.
      - Large enough to carry meaningful sentences.
      - Overlap avoids cutting mid-thought.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        start += chunk_size - overlap  # slide forward with overlap

    # Remove empty chunks
    chunks = [c for c in chunks if len(c) > 20]
    return chunks


def embed_and_store(chunks: list[str]) -> None:
    """Create embeddings for each chunk and store them in ChromaDB."""
    # 1. Set up ChromaDB (persistent local storage)
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Delete existing collection so re-ingestion is clean
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # Collection didn't exist yet — fine

    collection = client.create_collection(COLLECTION_NAME)

    # 2. Create embeddings via Ollama
    print(f"Generating embeddings for {len(chunks)} chunks using '{EMBEDDING_MODEL}'...")
    embedder = OllamaEmbeddings(model=EMBEDDING_MODEL)

    embeddings = embedder.embed_documents(chunks)

    # 3. Store in ChromaDB
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    collection.add(
        documents=chunks,
        embeddings=embeddings,
        ids=ids,
    )
    print(f"Stored {len(chunks)} chunks in ChromaDB at '{CHROMA_PATH}'.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def ingest(pdf_path: str) -> None:
    print(f"\n=== Ingesting: {pdf_path} ===")

    print("Step 1: Loading PDF...")
    text = load_pdf(pdf_path)
    print(f"  Extracted {len(text)} characters.")

    print("Step 2: Chunking text...")
    chunks = chunk_text(text)
    print(f"  Created {len(chunks)} chunks.")

    print("Step 3: Embedding and storing in ChromaDB...")
    embed_and_store(chunks)

    print("\nIngestion complete! You can now run app.py to start chatting.\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <path_to_pdf>")
        sys.exit(1)
    ingest(sys.argv[1])