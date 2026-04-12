import logging
import chromadb
import asyncio
from typing import List, Dict, Any, Optional
from google import genai
from backend.config import settings

logger = logging.getLogger(__name__)

_chroma_client = None

def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path="./chroma_db")
    return _chroma_client

class VectorStore:
    """
    Manages long-term memory: ChromaDB embeddings and retrieval.
    """
    def __init__(self, user_id: str = "default_user"):
        self.client = get_chroma_client()
        self.collection = self.client.get_or_create_collection(
            name=f"archimedes_{user_id}",
            metadata={"hnsw:space": "cosine"}
        )
        if not settings.GOOGLE_API_KEY:
            logger.warning(
                "VectorStore: GOOGLE_API_KEY not set. "
                "Long-term memory (embeddings) is DISABLED. "
                "Set GOOGLE_API_KEY in .env to enable."
            )
        self.genai_client = genai.Client(api_key=settings.GOOGLE_API_KEY) if settings.GOOGLE_API_KEY else None
        self.embedding_model = "gemini-embedding-exp-03-07"

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
            logger.error("VectorStore: Cannot add fact because GOOGLE_API_KEY is missing.")
            return

        embedding = await self._get_embedding(text)
        if embedding:
            self.collection.add(
                documents=[text],
                embeddings=[embedding],
                metadatas=[metadata or {}],
                ids=[f"fact_{hash(text)}"]
            )
            logger.info("Fact added to vector store.")

    async def retrieve_similar(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        if not self.genai_client:
            logger.error("VectorStore: Cannot retrieve facts because GOOGLE_API_KEY is missing.")
            return []

        query_embedding = await self._get_embedding(query)
        if not query_embedding:
            return []
            
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit
        )
        
        # Format results
        retrieved = []
        if results and results["documents"]:
            for i in range(len(results["documents"][0])):
                retrieved.append({
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {}
                })
        return retrieved
