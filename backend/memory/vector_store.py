import threading
import logging
import hashlib
import chromadb
import asyncio
import time
import os
from typing import List, Dict, Any, Optional
from google import genai
from backend.config import settings

COLLECTION_MAX_DOCS = settings.CHROMA_MAX_DOCS_PER_USER
COLLECTION_TTL_DAYS = settings.CHROMA_TTL_DAYS

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
        self._init_lock = None
        self.genai_client = genai.Client(api_key=settings.GOOGLE_API_KEY) if settings.GOOGLE_API_KEY else None
        self.embedding_model = "models/gemini-embedding-2"

    async def _get_collection(self):
        """Lazy async initialization of the collection."""
        if self._collection is None:
            if self._init_lock is None:
                self._init_lock = asyncio.Lock()
            async with self._init_lock:
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
                utilization = round(count / COLLECTION_MAX_DOCS * 100, 1) if COLLECTION_MAX_DOCS else 0
                return {
                    "count": count,
                    "limit": COLLECTION_MAX_DOCS,
                    "utilization_pct": utilization,
                    "ttl_days": COLLECTION_TTL_DAYS,
                    "status": "healthy" if utilization < 80 else "near_limit",
                    "size_est_mb": round(count * 0.002, 2)
                }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
        return {"count": 0, "limit": COLLECTION_MAX_DOCS, "utilization_pct": 0,
                "status": "unavailable", "size_est_mb": 0}

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

    async def _enforce_size_limit(self, col) -> None:
        """
        If collection exceeds COLLECTION_MAX_DOCS, delete the oldest 10%.
        Called before every add_fact to prevent unbounded growth.
        """
        try:
            count = await asyncio.to_thread(col.count)
            if count < COLLECTION_MAX_DOCS:
                return  # Fast path — no action needed
            
            evict_count = max(1, count // 10)
            logger.warning(
                f"VectorStore: Collection {self.user_id} has {count} docs "
                f"(limit: {COLLECTION_MAX_DOCS}). Evicting {evict_count} oldest."
            )
            
            all_docs = await asyncio.to_thread(
                col.get,
                include=["metadatas"]
            )
            
            if not all_docs or not all_docs.get("ids"):
                return
            
            id_timestamp_pairs = [
                (doc_id, meta.get("created_at", 0))
                for doc_id, meta in zip(all_docs["ids"], all_docs["metadatas"])
            ]
            id_timestamp_pairs.sort(key=lambda x: x[1])
            
            ids_to_delete = [pair[0] for pair in id_timestamp_pairs[:evict_count]]
            
            await asyncio.to_thread(col.delete, ids=ids_to_delete)
            logger.info(f"VectorStore: Evicted {len(ids_to_delete)} oldest docs from {self.user_id}")
            
        except Exception as e:
            logger.error(f"VectorStore: Size limit enforcement failed: {e}")

    async def archive_old_facts(self) -> int:
        """
        Delete documents older than COLLECTION_TTL_DAYS.
        Returns number of archived (deleted) documents.
        """
        col = await self._get_collection()
        if not col:
            return 0
        
        cutoff_ts = int(time.time()) - (COLLECTION_TTL_DAYS * 86400)
        
        try:
            old_docs = await asyncio.to_thread(
                col.get,
                where={"created_at": {"$lt": cutoff_ts}},
                include=[]  # Only need IDs
            )
            
            if not old_docs or not old_docs.get("ids"):
                return 0
            
            ids_to_archive = old_docs["ids"]
            if ids_to_archive:
                await asyncio.to_thread(col.delete, ids=ids_to_archive)
                logger.info(
                    f"VectorStore: Archived {len(ids_to_archive)} docs "
                    f"older than {COLLECTION_TTL_DAYS} days for user {self.user_id}"
                )
            return len(ids_to_archive)
            
        except Exception as e:
            logger.error(f"VectorStore: TTL archiving failed: {e}")
            return 0

    async def add_fact(self, text: str, metadata: Optional[Dict[str, Any]] = None):
        if not self.genai_client:
            return
        
        col = await self._get_collection()
        if not col:
            logger.warning("VectorStore: Skipping add_fact (ChromaDB unavailable)")
            return
            
        enriched_metadata = metadata or {}
        enriched_metadata["created_at"] = int(time.time())
        enriched_metadata["user_id"] = self.user_id
        
        await self._enforce_size_limit(col)

        embedding = await self._get_embedding(text)
        if embedding:
            try:
                await asyncio.to_thread(
                    col.add,
                    documents=[text],
                    embeddings=[embedding],
                    metadatas=[enriched_metadata],
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

async def get_all_collections_stats() -> Dict[str, Any]:
    """
    Returns stats for ALL user collections.
    Used by monitoring background task.
    """
    client = await asyncio.to_thread(get_chroma_client)
    if not client:
        return {"error": "ChromaDB unavailable", "collections": []}
    
    try:
        all_collections = await asyncio.to_thread(client.list_collections)
        stats = []
        total_docs = 0
        
        for col_info in all_collections:
            col = await asyncio.to_thread(client.get_collection, col_info.name)
            count = await asyncio.to_thread(col.count)
            total_docs += count
            
            user_id = col_info.name.replace("archimedes_", "", 1)
            
            stats.append({
                "collection": col_info.name,
                "user_id": user_id,
                "count": count,
                "utilization_pct": round(count / COLLECTION_MAX_DOCS * 100, 1) if COLLECTION_MAX_DOCS else 0,
                "status": "healthy" if count < COLLECTION_MAX_DOCS * 0.8 else "near_limit"
            })
        
        return {
            "collections": stats,
            "total_collections": len(stats),
            "total_docs": total_docs,
        }
    except Exception as e:
        logger.error(f"Failed to get all collections stats: {e}")
        return {"error": str(e), "collections": []}
