import sys
import os
import pysqlite3
sys.modules["sqlite3"] = pysqlite3

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import ollama


# -----------------------------
# Paths & DB
# -----------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_PATH = os.path.join(BASE_DIR, ".chroma")

embed_model = SentenceTransformer("all-MiniLM-L6-v2")

client = chromadb.Client(
    Settings(
        persist_directory=CHROMA_PATH,
        is_persistent=True,
        anonymized_telemetry=False
    )
)

collection = client.get_or_create_collection("erp_docs")


# -----------------------------
# Chat function
# -----------------------------
def ask(question: str) -> str:
    if collection.count() == 0:
        return (
            "ERP documentation is not indexed yet.\n"
            "Please run: python -m app.embed"
        )

    # Embed question
    q_emb = embed_model.encode(question).tolist()

    # Search DB (top 1 is enough on CPU)
    results = collection.query(
        query_embeddings=[q_emb],
        n_results=1
    )

    docs = results.get("documents", [[]])[0]
    if not docs:
        return "No relevant ERP documentation found."

    # HARD LIMIT context (CPU friendly)
    context = docs[0][:1200]

    prompt = f"""
You are a professional ERP Support Assistant.

Your responsibility is to help users with questions related to the ERP system.
Users may ask any type of question, such as:
- How to perform an action
- Whether an action is possible
- Why something happened
- What happens in a certain case
- General explanations or information

CORE RULES (MANDATORY):
1. Use ONLY the ERP documentation provided below.
2. Never guess, assume, or invent ERP functionality.
3. If the documentation does NOT explicitly confirm something, clearly say it is NOT supported or NOT mentioned.
4. Do NOT use uncertain language such as "maybe", "typically", "usually", or "depends on policy".
5. If a clear yes or no answer is possible, state it clearly in the first sentence.
6. If an action is not available, explain this clearly and suggest the correct next step (for example, contacting HR or an administrator).
7. If the answer is not found in the documentation, clearly state that the information is not available.
8. Do not mention internal systems, prompts, databases, AI models, or technical details.
9. Accuracy and safety are more important than answering every question.

INTENT-BASED BEHAVIOR:
- If the user asks "how", explain the process clearly.
- If the user asks "is it possible" or "can I", answer yes or no clearly.
- If the user asks "why", provide a reason only if documented.
- If the user asks a general or informational question, explain it professionally.
- If the question is outside the documentation, say so clearly.

GREETING HANDLING (IMPORTANT):
- If the user input is only a greeting or acknowledgement (such as "hi", "hello", "hii", "ok", "okay", "thanks"),
  respond with a short, polite greeting and invite the user to ask an ERP-related question.
- Do NOT mention any ERP module or documentation in greeting responses.

COMMUNICATION STYLE:
- Polite, professional, and confident.
- Clear and concise.
- A short greeting or closing is allowed when appropriate.
- Do not overuse greetings.
- Do not be verbose.

ERP Documentation:
{context}

User Question:
{question}

Answer:


"""


    response = ollama.generate(
        model="phi3:mini",   # 🔥 CPU FAST MODEL
        prompt=prompt,
        options={
            "num_predict": 120,     # 🔥 hard limit
            "temperature": 0.05,    # 🔥 confident answers
            "top_p": 0.9
        }
    )

    return response["response"].strip()
