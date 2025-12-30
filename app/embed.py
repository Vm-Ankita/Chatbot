import sys
import os
import pysqlite3
sys.modules["sqlite3"] = pysqlite3

from app.ingest import collect_documents
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings


def main():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CHROMA_PATH = os.path.join(BASE_DIR, ".chroma")

    docs = collect_documents()
    if not docs:
        print("❌ No documents collected. Embedding aborted.")
        return

    print(f"📄 Preparing to embed {len(docs)} documents")

    model = SentenceTransformer("all-MiniLM-L6-v2")

    client = chromadb.Client(
        Settings(
            persist_directory=CHROMA_PATH,
            is_persistent=True,          # 🔥 THIS WAS MISSING
            anonymized_telemetry=False
        )
    )

    collection = client.get_or_create_collection("erp_docs")

    for i, text in enumerate(docs):
        collection.add(
            ids=[f"doc_{i}"],
            documents=[text],
            embeddings=[model.encode(text).tolist()]
        )

    print(f"✅ Embedded {collection.count()} documents successfully")


if __name__ == "__main__":
    main()
