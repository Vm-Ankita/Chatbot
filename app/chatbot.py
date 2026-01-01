import sys
import os
import re
import pysqlite3
sys.modules["sqlite3"] = pysqlite3

import chromadb
from sentence_transformers import SentenceTransformer
import ollama
from difflib import get_close_matches

# -----------------------------
# Paths & DB
# -----------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_PATH = os.path.join(BASE_DIR, ".chroma")

# Load embedding model once
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# Persistent Chroma client
client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection("erp_docs")


# -----------------------------
# ERP Vocabulary (for spelling)
# -----------------------------
ERP_KEYWORDS = [
    "outcome", "course", "course outcome", "program outcome",
    "attendance", "regularization", "leave",
    "approval", "event", "exam", "result",
    "delete", "add", "edit", "update", "view"
]


def correct_spelling(word: str) -> str:
    matches = get_close_matches(word, ERP_KEYWORDS, n=1, cutoff=0.8)
    return matches[0] if matches else word


def normalize_question(question: str) -> str:
    """
    Normalize question ONLY for retrieval:
    - lowercase
    - remove punctuation
    - correct ERP spelling mistakes
    """
    q = question.lower()
    q = re.sub(r"[^\w\s]", " ", q)

    words = q.split()
    corrected_words = [correct_spelling(w) for w in words]

    return " ".join(corrected_words)


# -----------------------------
# Chat function
# -----------------------------
def ask(question: str) -> str:
    # 1️⃣ Safety check
    if collection.count() == 0:
        return "Documentation is not indexed yet."

    # 2️⃣ Normalize ONLY for retrieval
    normalized_q = normalize_question(question)

    q_emb = embed_model.encode(normalized_q).tolist()

    # 3️⃣ Retrieve top chunks (OCR-safe)
    results = collection.query(
        query_embeddings=[q_emb],
        n_results=2
    )

    docs = results.get("documents", [[]])[0]
    if not docs:
        return "This information is not available in the system."

    # Keep LAST part so OCR text is included
    context = "\n\n".join(docs)[-1200:]

    # 4️⃣ Strict professional prompt
    prompt = f"""### INFORMATION PROVIDED:
{context}

### USER QUESTION:
{question}

### ROLE:
Professional Support Engine. Provide deterministic, factual responses based ONLY on the data above.

### ORDER OF OPERATIONS (STRICT):
1. IF the USER QUESTION is a standalone greeting (Hi, Hello, Hey):
   Respond ONLY with "Hello. How can I assist you?"
2. IF the USER QUESTION asks to explain, how to, what is, can I, or mentions any technical term:
   Extract the answer from INFORMATION PROVIDED and stop.
3. IF the answer is not present:
   Respond "This information is not available in the system."

### EXECUTION CONSTRAINTS:
- START with "Yes." or "No." for "Can I" or "Is it possible" questions.
- NO HEDGING.
- NO META-TALK.
- TONE: Sterile, professional, factual.

### RESPONSE:"""

    # 5️⃣ Generate response
    response = ollama.generate(
        model="phi3:mini",
        prompt=prompt,
        options={
            "num_predict": 200,
            "temperature": 0.0,
            "top_p": 0.1,
            "stop": ["###", "\n\n", "User", "INFORMATION"]
        }
    )

    return response["response"].strip()














