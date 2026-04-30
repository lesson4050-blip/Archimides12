"""
Semantic Codebase Search — TF-IDF based code search.

Unlike grep (text matching), this finds code by MEANING.
Zero external dependencies — works offline with Ollama.

Query: "function that handles user authentication"
Finds: def login_user(), def verify_token(), class AuthMiddleware
Even if the word "authentication" never appears in the code.
"""
import logging
import math
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    file_path: str
    line_start: int
    line_end: int
    content: str
    score: float
    symbol_name: str = ""
    symbol_type: str = ""


@dataclass
class CodeSymbol:
    name: str
    symbol_type: str
    file_path: str
    line_start: int
    line_end: int
    content: str
    docstring: str = ""
    tokens: List[str] = field(default_factory=list)


class SemanticSearchEngine:
    """TF-IDF based semantic search over a codebase."""

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
    STOP_WORDS = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
        'has', 'have', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'can', 'shall', 'must',
        'self', 'cls', 'this', 'return', 'import', 'from', 'def',
        'class', 'if', 'else', 'elif', 'for', 'while', 'try',
        'except', 'finally', 'with', 'as', 'in', 'not', 'and', 'or',
        'true', 'false', 'none', 'null', 'undefined', 'async', 'await',
    }

    def __init__(self, root_path: str, extensions: Optional[List[str]] = None):
        self.root_path = Path(root_path)
        self.extensions = extensions or ['.py', '.ts', '.tsx', '.js', '.jsx']
        self._symbols: List[CodeSymbol] = []
        self._idf: Dict[str, float] = {}
        self._indexed = False

    def _tokenize(self, text: str) -> List[str]:
        text = re.sub(r'[^a-zA-Z0-9_]', ' ', text)
        words = []
        for word in text.split():
            parts = word.split('_')
            for part in parts:
                camel_split = re.sub(r'([a-z])([A-Z])', r'\1 \2', part).split()
                words.extend(camel_split)
        return [w.lower() for w in words if len(w) > 1 and w.lower() not in self.STOP_WORDS]

    def _extract_symbols_python(self, file_path: Path, content: str) -> List[CodeSymbol]:
        symbols = []
        lines = content.split('\n')
        for match in self.PYTHON_SYMBOL_RE.finditer(content):
            name = match.group(1) or match.group(2)
            sym_type = 'function' if match.group(1) else 'class'
            line_start = content[:match.start()].count('\n')
            indent = len(match.group(0)) - len(match.group(0).lstrip())
            line_end = line_start + 1
            for i in range(line_start + 1, len(lines)):
                stripped = lines[i].strip()
                if stripped and not stripped.startswith('#'):
                    current_indent = len(lines[i]) - len(lines[i].lstrip())
                    if current_indent <= indent and stripped:
                        break
                line_end = i + 1
            block = '\n'.join(lines[line_start:min(line_end, line_start + 50)])
            docstring = ""
            ds_match = re.search(r'"""(.*?)"""', block, re.DOTALL)
            if ds_match:
                docstring = ds_match.group(1).strip()[:200]
            tokens = self._tokenize(f"{name} {docstring} {block}")
            symbols.append(CodeSymbol(
                name=name, symbol_type=sym_type,
                file_path=str(file_path), line_start=line_start + 1,
                line_end=line_end, content=block[:500],
                docstring=docstring, tokens=tokens
            ))
        return symbols

    def _extract_symbols_typescript(self, file_path: Path, content: str) -> List[CodeSymbol]:
        symbols = []
        lines = content.split('\n')
        for match in self.TS_SYMBOL_RE.finditer(content):
            name = match.group(1) or match.group(2) or match.group(3)
            sym_type = 'class' if match.group(2) else ('variable' if match.group(3) else 'function')
            line_start = content[:match.start()].count('\n')
            line_end = min(line_start + 30, len(lines))
            block = '\n'.join(lines[line_start:line_end])
            tokens = self._tokenize(f"{name} {block}")
            symbols.append(CodeSymbol(
                name=name, symbol_type=sym_type,
                file_path=str(file_path), line_start=line_start + 1,
                line_end=line_end, content=block[:500],
                tokens=tokens
            ))
        return symbols

    def index(self) -> int:
        """Index the codebase. Returns number of symbols found."""
        self._symbols.clear()
        doc_freq: Dict[str, int] = defaultdict(int)

        for ext in self.extensions:
            for file_path in self.root_path.rglob(f'*{ext}'):
                rel = file_path.relative_to(self.root_path)
                skip_dirs = {'node_modules', '__pycache__', '.git', 'venv', '.venv', 'dist', 'build'}
                if any(part in skip_dirs for part in rel.parts):
                    continue
                try:
                    content = file_path.read_text(errors='ignore')
                except Exception:
                    continue
                if ext == '.py':
                    symbols = self._extract_symbols_python(file_path, content)
                elif ext in ('.ts', '.tsx', '.js', '.jsx'):
                    symbols = self._extract_symbols_typescript(file_path, content)
                else:
                    continue
                for sym in symbols:
                    seen = set()
                    for token in sym.tokens:
                        if token not in seen:
                            doc_freq[token] += 1
                            seen.add(token)
                self._symbols.extend(symbols)

        n_docs = max(len(self._symbols), 1)
        self._idf = {
            token: math.log(n_docs / freq) if freq > 0 else 0
            for token, freq in doc_freq.items()
        }
        self._indexed = True
        logger.info(f"Semantic search: indexed {len(self._symbols)} symbols")
        return len(self._symbols)

    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """Search the codebase by semantic query."""
        if not self._indexed:
            self.index()

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        query_tfidf = Counter(query_tokens)
        for token in query_tfidf:
            query_tfidf[token] *= self._idf.get(token, 0)

        results = []
        for sym in self._symbols:
            doc_tfidf = Counter(sym.tokens)
            for token in doc_tfidf:
                doc_tfidf[token] *= self._idf.get(token, 0)

            # Cosine similarity
            dot = sum(query_tfidf[t] * doc_tfidf[t] for t in query_tfidf if t in doc_tfidf)
            q_norm = math.sqrt(sum(v**2 for v in query_tfidf.values()))
            d_norm = math.sqrt(sum(v**2 for v in doc_tfidf.values()))
            score = dot / (q_norm * d_norm) if q_norm * d_norm > 0 else 0.0

            if score > 0:
                results.append(SearchResult(
                    file_path=sym.file_path,
                    line_start=sym.line_start,
                    line_end=sym.line_end,
                    content=sym.content,
                    score=score,
                    symbol_name=sym.name,
                    symbol_type=sym.symbol_type,
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def get_definition(self) -> dict:
        """Tool definition for agent registration."""
        return {
            "type": "function",
            "function": {
                "name": "semantic_search",
                "description": (
                    "Search the codebase by MEANING, not text matching. "
                    "Finds functions/classes semantically related to the query. "
                    "Use when grep returns too many or too few results."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "What to find"},
                        "top_k": {"type": "integer", "default": 10},
                    },
                    "required": ["query"]
                }
            }
        }

    async def execute(self, query: str, top_k: int = 10, **kwargs) -> dict:
        results = self.search(query, top_k)
        if not results:
            return {"success": True, "output": "No results found", "results": []}
        lines = []
        for r in results:
            lines.append(
                f"[{r.symbol_type}] {r.symbol_name} — {r.file_path}:{r.line_start} (score={r.score:.3f})"
            )
            lines.append(f"  {r.content[:150].strip()}")
            lines.append("")
        return {
            "success": True,
            "output": "\n".join(lines),
            "results": [{"file": r.file_path, "line": r.line_start, "name": r.symbol_name} for r in results]
        }
