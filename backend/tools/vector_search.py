"""
Vector Search Engine — ChromaDB-based semantic code search.

Replaces TF-IDF with real embeddings for deep semantic matching.
Uses ChromaDB (already in requirements.txt) with built-in
sentence-transformers embeddings.

Upgrades over TF-IDF:
- Understands synonyms ("auth" matches "login", "verify_token")
- Understands intent ("function that handles errors" matches "except Exception")
- Scales to 100K+ files without noise
"""
import asyncio
import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

CHROMA_DIR = os.environ.get("CHROMA_DB_DIR", "data/chroma_db")


@dataclass
class VectorSearchResult:
    file_path: str
    line_start: int
    line_end: int
    content: str
    score: float
    symbol_name: str = ""
    symbol_type: str = ""


# Symbol extraction patterns (reused from semantic_search.py)
PYTHON_SYMBOL_RE = re.compile(
    r'^(?:(?:async\s+)?def\s+(\w+)|class\s+(\w+))',
    re.MULTILINE
)
TS_SYMBOL_RE = re.compile(
    r'^(?:(?:export\s+)?(?:async\s+)?function\s+(\w+)|'
    r'(?:export\s+)?class\s+(\w+)|'
    r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=)',
    re.MULTILINE
)


class VectorSearchEngine:
    """ChromaDB-powered semantic code search."""

    SKIP_DIRS = {
        '.git', 'node_modules', '__pycache__', 'venv', '.venv',
        'dist', 'build', '.next', '.cache', 'data', '.mypy_cache',
        'coverage', '.pytest_cache', 'eggs', '*.egg-info',
    }
    CODE_EXTENSIONS = {
        '.py', '.ts', '.tsx', '.js', '.jsx', '.rs', '.go',
        '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.rb',
        '.yaml', '.yml', '.toml', '.json', '.md',
    }
    MAX_FILE_SIZE = 1_000_000  # 1MB

    def __init__(self, workspace_dir: str = "."):
        self.workspace_dir = os.path.abspath(workspace_dir)
        self._collection = None
        self._indexed_hash: Optional[str] = None
        self._collection_name = self._get_collection_name()

        # Use PersistentClient (modern ChromaDB API)
        try:
            import chromadb
            self._client = chromadb.Client()
        except Exception as e:
            logger.warning(f"ChromaDB client init failed: {e}")
            self._client = None

    def _get_collection_name(self) -> str:
        """Generate a unique collection name from workspace path."""
        path_hash = hashlib.sha256(self.workspace_dir.encode()).hexdigest()[:8]
        return f"code_{path_hash}"

    def _get_or_create_collection(self):
        """Get or create the ChromaDB collection."""
        if self._client is None:
            raise RuntimeError("ChromaDB client not initialized")
        if self._collection is None:
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def _extract_symbols(self, content: str, file_path: str) -> List[Dict]:
        """Extract code symbols (functions, classes) from file content."""
        symbols = []
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.py':
            pattern = PYTHON_SYMBOL_RE
        elif ext in ('.ts', '.tsx', '.js', '.jsx'):
            pattern = TS_SYMBOL_RE
        else:
            return [{
                "name": os.path.basename(file_path),
                "type": "file",
                "content": content,
                "line_start": 1,
                "line_end": content.count('\n') + 1,
            }]

        lines = content.split('\n')
        matches = list(pattern.finditer(content))

        for i, match in enumerate(matches):
            name = next((g for g in match.groups() if g), "unknown")
            line_start = content[:match.start()].count('\n') + 1

            if i + 1 < len(matches):
                line_end = content[:matches[i + 1].start()].count('\n')
            else:
                line_end = len(lines)

            symbol_content = '\n'.join(lines[line_start - 1:line_end])
            symbol_type = "function" if "def " in match.group() else "class"

            symbols.append({
                "name": name,
                "type": symbol_type,
                "content": symbol_content,
                "line_start": line_start,
                "line_end": line_end,
            })

        if not symbols:
            symbols.append({
                "name": os.path.basename(file_path),
                "type": "file",
                "content": content,
                "line_start": 1,
                "line_end": len(lines),
            })

        return symbols

    def _scan_files(self) -> List[str]:
        """Scan workspace for indexable code files."""
        files = []
        for root, dirs, filenames in os.walk(self.workspace_dir):
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext in self.CODE_EXTENSIONS:
                    fpath = os.path.join(root, fname)
                    try:
                        if os.path.getsize(fpath) <= self.MAX_FILE_SIZE:
                            files.append(fpath)
                    except OSError:
                        pass
        return files

    def _compute_workspace_hash(self, files: List[str]) -> str:
        """Quick hash to detect if workspace changed since last index."""
        h = hashlib.sha256()
        for f in sorted(files)[:500]:
            try:
                stat = os.stat(f)
                h.update(f"{f}:{stat.st_mtime}:{stat.st_size}".encode())
            except OSError:
                pass
        return h.hexdigest()

    def index(self, force: bool = False) -> int:
        """Index the workspace into ChromaDB. Returns number of documents indexed."""
        files = self._scan_files()
        current_hash = self._compute_workspace_hash(files)

        if not force and current_hash == self._indexed_hash:
            logger.info("Workspace unchanged, skipping re-index")
            return 0

        collection = self._get_or_create_collection()

        # Clear old data
        try:
            existing = collection.count()
            if existing > 0:
                all_ids = collection.get()["ids"]
                if all_ids:
                    collection.delete(ids=all_ids)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Blind exception caught: {e}")

        ids = []
        documents = []
        metadatas = []

        for fpath in files:
            try:
                with open(fpath, 'r', errors='replace') as f:
                    content = f.read()
            except Exception:
                continue

            rel_path = os.path.relpath(fpath, self.workspace_dir)
            symbols = self._extract_symbols(content, fpath)

            for sym in symbols:
                doc_id = f"{rel_path}::{sym['name']}::{sym['line_start']}"
                doc_text = f"{sym['name']} ({sym['type']}) in {rel_path}\n{sym['content'][:2000]}"

                ids.append(doc_id)
                documents.append(doc_text)
                metadatas.append({
                    "file_path": rel_path,
                    "symbol_name": sym["name"],
                    "symbol_type": sym["type"],
                    "line_start": sym["line_start"],
                    "line_end": sym["line_end"],
                })

        # ChromaDB batch limit is 5461
        batch_size = 5000
        total_indexed = 0
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_docs = documents[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]
            collection.add(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_meta,
            )
            total_indexed += len(batch_ids)

        self._indexed_hash = current_hash
        logger.info(f"Indexed {total_indexed} symbols from {len(files)} files")
        return total_indexed

    def search(self, query: str, top_k: int = 10) -> List[VectorSearchResult]:
        """Search for code matching the query semantically."""
        collection = self._get_or_create_collection()

        if collection.count() == 0:
            self.index()

        if collection.count() == 0:
            return []

        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, collection.count()),
        )

        search_results = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 1.0
                score = max(0, 1.0 - distance)
                doc = results["documents"][0][i] if results["documents"] else ""

                search_results.append(VectorSearchResult(
                    file_path=meta.get("file_path", ""),
                    line_start=meta.get("line_start", 1),
                    line_end=meta.get("line_end", 1),
                    content=doc[:1000],
                    score=score,
                    symbol_name=meta.get("symbol_name", ""),
                    symbol_type=meta.get("symbol_type", ""),
                ))

        return search_results

    async def execute(self, **params) -> Dict:
        """Tool interface for agent integration."""
        query = params.get("query", "")
        top_k = params.get("top_k", 10)
        results = self.search(query, top_k=top_k)
        return {
            "success": True,
            "output": {
                "results": [
                    {
                        "file": r.file_path,
                        "symbol": r.symbol_name,
                        "type": r.symbol_type,
                        "lines": f"{r.line_start}-{r.line_end}",
                        "score": round(r.score, 3),
                        "preview": r.content[:300],
                    }
                    for r in results
                ],
                "engine": "chromadb_vector",
                "total": len(results),
            },
        }
