import logging
import base64
import os
from typing import Dict, Any
from backend.memory.vector_store import VectorStore

logger = logging.getLogger(__name__)

class DocumentTool:
    """Индексирование и RAG-поиск по документам через ChromaDB."""
    base_dir = "backend/memory"

    def __init__(self):
        self._stores: Dict[str, VectorStore] = {}

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "document",
                "description": "Index PDF/TXT files and query them using semantic search.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["index", "query", "list"]},
                        "path": {"type": "string", "description": "File path in sandbox"},
                        "question": {"type": "string"},
                        "doc_id": {"type": "string"}
                    },
                    "required": ["action"]
                }
            }
        }

    async def execute(self, action: str, path: str = None,
                      question: str = None, doc_id: str = None,
                      session_id: str = None, **kwargs) -> Dict[str, Any]:
        
        uid = session_id or "default"
        if uid not in self._stores:
            self._stores[uid] = VectorStore(user_id=uid)
        vs = self._stores[uid]
        
        if action == "index":
            if not path:
                return {"success": False, "error": "path required for index action"}
            try:
                # Try direct filesystem read first (more reliable than base64 piping)
                text = ""
                try:
                    from backend.sandbox.singleton import sandbox_manager
                    fs = sandbox_manager._filesystems.get(session_id)
                    if fs:
                        read_result = await fs.read_file(session_id, path)
                        if read_result.get("success"):
                            text = read_result.get("content", "")
                except Exception:
                    pass
                
                # Fallback: PDF extraction via PyMuPDF
                if not text and path.lower().endswith(".pdf"):
                    try:
                        import fitz
                        # Read via sandbox
                        from backend.sandbox.singleton import sandbox_manager
                        result = await sandbox_manager.executor.run_command(
                            session_id, f"base64 {path}"
                        )
                        if result.get("success"):
                            doc_bytes = base64.b64decode(result["output"].strip())
                            temp_filename = f"temp_{os.path.basename(path)}"
                            with open(temp_filename, "wb") as f:
                                f.write(doc_bytes)
                            doc = fitz.open(temp_filename)
                            text = "\n".join([page.get_text() for page in doc])
                            doc.close()
                            try:
                                os.remove(temp_filename)
                            except Exception:
                                pass
                    except ImportError:
                        return {"success": False, "error": "PyMuPDF not installed for PDF parsing"}
                
                if not text:
                    return {"success": False, "error": f"Could not extract text from {path}"}
                
                doc_id = doc_id or os.path.basename(path)
                
                # Sentence-aware chunking with overlap for better RAG
                chunks = self._chunk_text(text, chunk_size=800, overlap=200)
                indexed = 0
                for i, chunk in enumerate(chunks[:100]):  # Cap at 100 chunks
                    if chunk.strip():
                        await vs.add_fact(
                            chunk, 
                            {"doc_id": doc_id, "chunk": i, "path": path}
                        )
                        indexed += 1
                    
                return {
                    "success": True, 
                    "output": (
                        f"Indexed {indexed} chunks from {doc_id} "
                        f"(text length: {len(text)}, "
                        f"chunk_size: 800, overlap: 200)"
                    )
                }
            except Exception as e:
                logger.error(f"Document Tool Error: {e}")
                return {"success": False, "error": str(e)}
        
        elif action == "query":
            if not question:
                return {"success": False, "error": "question required for query action"}
            results = await vs.retrieve_similar(question, limit=5)
            if not results:
                return {"success": True, "output": "No results. Index a document first."}
            context = "\n\n".join([r["document"] for r in results])
            return {"success": True, "output": context[:3000]}
        
        elif action == "list":
            return {"success": True, "output": "Use 'query' to search indexed documents."}
            
        return {"success": False, "error": f"Unknown action: {action}"}

    @staticmethod
    def _chunk_text(
        text: str, chunk_size: int = 800, overlap: int = 200
    ) -> list:
        """
        Split text into chunks with overlap, trying to break on sentence boundaries.
        """
        import re
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            if end >= len(text):
                chunks.append(text[start:])
                break
            
            # Try to find a sentence boundary near the end
            # Look backwards from `end` for a period/newline
            boundary = text.rfind('. ', start + chunk_size // 2, end)
            if boundary == -1:
                boundary = text.rfind('\n', start + chunk_size // 2, end)
            if boundary == -1:
                boundary = text.rfind(' ', start + chunk_size // 2, end)
            if boundary != -1:
                end = boundary + 1
            
            chunks.append(text[start:end])
            start = end - overlap  # overlap for context continuity
        
        return chunks
