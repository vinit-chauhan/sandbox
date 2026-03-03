import os
from functools import lru_cache

import chromadb
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
COLLECTION_NAME = "documents"

_splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=64)


@lru_cache(maxsize=1)
def _get_client():
    return chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)


@lru_cache(maxsize=1)
def _get_collection():
    return _get_client().get_or_create_collection(COLLECTION_NAME)


@lru_cache(maxsize=1)
def _get_embedder():
    return SentenceTransformer("all-MiniLM-L6-v2")


def add_document(doc_id: str, text: str) -> None:
    chunks = _splitter.split_text(text)
    if not chunks:
        return
    embeddings = _get_embedder().encode(chunks).tolist()
    ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"doc_id": doc_id}] * len(chunks)
    _get_collection().upsert(
        ids=ids, documents=chunks, embeddings=embeddings, metadatas=metadatas
    )


def query(doc_ids: list[str], query_text: str, top_k: int = 5) -> str:
    embedding = _get_embedder().encode([query_text]).tolist()
    results = _get_collection().query(
        query_embeddings=embedding,
        n_results=top_k,
        where={"doc_id": {"$in": doc_ids}},
    )
    documents = results.get("documents", [[]])[0]
    return "\n\n---\n\n".join(documents)


def delete_document(doc_id: str) -> None:
    _get_collection().delete(where={"doc_id": doc_id})
