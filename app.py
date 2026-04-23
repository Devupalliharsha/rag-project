"""
app.py — CLI Customer Support Chatbot (RAG-powered, fully local).
"""

from graph import run_query

BANNER = """
╔══════════════════════════════════════════════════════╗
║      RAG Customer Support Assistant  (Local AI)      ║
║  Type your question | 'debug <q>' | 'quit' to exit   ║
╚══════════════════════════════════════════════════════╝
"""


def print_separator():
    print("─" * 56)


def main():
    print(BANNER)

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        debug_mode = user_input.lower().startswith("debug ")
        query = user_input[6:].strip() if debug_mode else user_input

        if not query:
            print("Assistant: Please enter a question.\n")
            continue

        print("\nThinking...\n")

        try:
            result = run_query(query)
        except Exception as e:
            print(f"[ERROR] Something went wrong: {e}\n")
            continue

        if debug_mode:
            print_separator()
            docs = result.get("retrieved_docs", [])
            if docs:
                print(f"[DEBUG] Retrieved {len(docs)} chunk(s):\n")
                for i, doc in enumerate(docs, 1):
                    snippet = doc[:200].replace("\n", " ")
                    print(f"  [{i}] {snippet}...")
            else:
                print("[DEBUG] No chunks retrieved.")
            print_separator()

        escalated = result.get("needs_escalation", False)
        response = result.get("final_response", "No response generated.")

        if escalated:
            print(f"Assistant (⚠ Escalated):\n{response}\n")
        else:
            print(f"Assistant:\n{response}\n")

        print_separator()
        print()


if __name__ == "__main__":
    main()