import threading
import logging
import hashlib
import chromadb
import asyncio
from typing import List, Dict, Any, Optional
from google import genai
from backend.config import settings

logger = logging.getLogger(__name__)

_chroma_client = None
_client_lock = threading.Lock()

def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        with _client_lock:
            if _chroma_client is None:
                try:
                    _chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
                    logger.info(f"ChromaDB initialized at {settings.CHROMA_DB_PATH}")
                except Exception as e:
                    logger.error(f"CRITICAL: Failed to initialize ChromaDB: {e}")
                    return None
    return _chroma_client

class VectorStore:
    """
    Manages long-term memory: ChromaDB embeddings and retrieval.
    v2: Thread-safe, resilient, and monitored.
    """
    def __init__(self, user_id: str = "default_user"):
        self.user_id = user_id
        self._collection = None
        self.genai_client = genai.Client(api_key=settings.GOOGLE_API_KEY) if settings.GOOGLE_API_KEY else None
        self.embedding_model = "gemini-embedding-exp-03-07"

    async def _get_collection(self):
        """Lazy async initialization of the collection."""
        if self._collection is None:
            client = await asyncio.to_thread(get_chroma_client)
            if client:
                try:
                    self._collection = await asyncio.to_thread(
                        client.get_or_create_collection,
                        name=f"archimedes_{self.user_id}",
                        metadata={"hnsw:space": "cosine"}
                    )
                except Exception as e:
                    logger.error(f"Failed to get/create ChromaDB collection: {e}")
        return self._collection

    async def get_collection_stats(self) -> Dict[str, Any]:
        """Returns document count and health status (Async)."""
        try:
            col = await self._get_collection()
            if col:
                count = await asyncio.to_thread(col.count)
                return {
                    "count": count,
                    "status": "healthy",
                    "size_est_mb": round(count * 0.002, 2) # rough estimate: 2KB per doc
                }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
        return {"count": 0, "status": "unavailable", "size_est_mb": 0}

    async def _get_embedding(self, text: str) -> List[float]:
        if not self.genai_client:
            return []
        try:
            result = await asyncio.to_thread(
                self.genai_client.models.embed_content,
                model=self.embedding_model,
                contents=text,
                config={"task_type": "RETRIEVAL_QUERY"}
            )
            return result.embeddings[0].values
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            return []

    async def add_fact(self, text: str, metadata: Optional[Dict[str, Any]] = None):
        if not self.genai_client:
            return
        
        col = await self._get_collection()
        if not col:
            logger.warning("VectorStore: Skipping add_fact (ChromaDB unavailable)")
            return

        embedding = await self._get_embedding(text)
        if embedding:
            try:
                await asyncio.to_thread(
                    col.add,
                    documents=[text],
                    embeddings=[embedding],
                    metadatas=[metadata or {}],
                    ids=[f"fact_{hashlib.sha256(text.encode()).hexdigest()[:16]}"]
                )
                logger.info("Fact added to vector store.")
            except Exception as e:
                logger.error(f"Failed to add fact to ChromaDB: {e}")

    async def retrieve_similar(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        if not self.genai_client:
            return []
            
        col = await self._get_collection()
        if not col:
            logger.warning("VectorStore: Skipping retrieve (ChromaDB unavailable)")
            return []

        query_embedding = await self._get_embedding(query)
        if not query_embedding:
            return []
            
        try:
            results = await asyncio.to_thread(
                col.query,
                query_embeddings=[query_embedding],
                n_results=limit
            )
            
            retrieved = []
            if results and results["documents"]:
                for i in range(len(results["documents"][0])):
                    retrieved.append({
                        "document": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {}
                    })
            return retrieved
        except Exception as e:
            logger.error(f"Failed to query ChromaDB: {e}")
            return []

