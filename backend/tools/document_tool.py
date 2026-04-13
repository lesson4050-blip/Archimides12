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
                # Извлекаем файл из песочницы через base64
                from backend.sandbox.singleton import sandbox_manager
                result = await sandbox_manager.executor.run_command(session_id, f"base64 {path}")
                if not result.get("success"):
                    return {"success": False, "error": f"Failed to read file {path}"}
                
                doc_bytes = base64.b64decode(result["output"].strip())
                temp_filename = f"temp_{os.path.basename(path)}"
                with open(temp_filename, "wb") as f:
                    f.write(doc_bytes)
                
                import fitz
                doc = fitz.open(temp_filename)
                text = "\n".join([page.get_text() for page in doc])
                
                doc_id = doc_id or path.split("/")[-1]
                
                chunk_size = 500
                chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
                for i, chunk in enumerate(chunks[:50]): # Ограничение 50 чанков
                    await vs.add_fact(chunk, {"doc_id": doc_id, "chunk": i, "path": path})
                
                try:
                    os.remove(temp_filename)
                except Exception:
                    pass
                    
                return {"success": True, "output": f"Indexed {len(chunks[:50])} chunks from {doc_id} (text length: {len(text)})"}
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
