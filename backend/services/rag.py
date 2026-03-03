import os

import chromadb
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
COLLECTION_NAME = "documents"

_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
_collection = _client.get_or_create_collection(COLLECTION_NAME)
_embedder = SentenceTransformer("all-MiniLM-L6-v2")
_splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=64)


def add_document(doc_id: str, text: str) -> None:
    chunks = _splitter.split_text(text)
    if not chunks:
        return
    embeddings = _embedder.encode(chunks).tolist()
    ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"doc_id": doc_id}] * len(chunks)
    _collection.upsert(ids=ids, documents=chunks, embeddings=embeddings, metadatas=metadatas)


def query(doc_ids: list[str], query_text: str, top_k: int = 5) -> str:
    embedding = _embedder.encode([query_text]).tolist()
    results = _collection.query(
        query_embeddings=embedding,
        n_results=top_k,
        where={"doc_id": {"$in": doc_ids}},
    )
    documents = results.get("documents", [[]])[0]
    return "\n\n---\n\n".join(documents)


def delete_document(doc_id: str) -> None:
    _collection.delete(where={"doc_id": doc_id})
