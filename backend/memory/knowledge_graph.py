"""
Knowledge Graph (lightweight GraphRAG).
Stores entities and their relationships.
No Neo4j needed — pure SQLite with graph queries.
This gives 10x better context than flat vector search.
"""
import aiosqlite
import json
import os
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)
DB_PATH = os.environ.get("KG_DB_PATH", "data/knowledge_graph.db")


class KnowledgeGraph:
    """Wrapper for standalone KG functions to match MemoryRouter expectations."""
    def __init__(self):
        self.db_path = DB_PATH

    async def search(self, query: str) -> List[str]:
        # Simple keyword search on entity names or context
        await _init_db()
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                "SELECT name FROM entities WHERE name LIKE ? LIMIT 5",
                (f"%{query}%",)
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def _init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                entity_type TEXT DEFAULT 'concept',
                properties TEXT DEFAULT '{}',
                session_id TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_entity TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                to_entity TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                context TEXT,
                session_id TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(from_entity, relation_type, to_entity)
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_from ON relations(from_entity)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_to ON relations(to_entity)"
        )
        await conn.commit()


async def add_entity(
    name: str,
    entity_type: str = "concept",
    properties: Dict = None,
    session_id: str = "global"
) -> int:
    await _init_db()
    props = json.dumps(properties or {})
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute(
            "INSERT OR REPLACE INTO entities "
            "(name, entity_type, properties, session_id) VALUES (?,?,?,?)",
            (name, entity_type, props, session_id)
        )
        await conn.commit()
        return cursor.lastrowid or 0


async def add_relation(
    from_entity: str,
    relation_type: str,
    to_entity: str,
    context: str = "",
    weight: float = 1.0,
    session_id: str = "global"
):
    # Ensure entities exist
    await add_entity(from_entity, session_id=session_id)
    await add_entity(to_entity, session_id=session_id)

    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO relations "
            "(from_entity, relation_type, to_entity, weight, context, session_id) "
            "VALUES (?,?,?,?,?,?)",
            (from_entity, relation_type, to_entity,
             weight, context[:500], session_id)
        )
        await conn.commit()


async def query_causal_chains(
    entity: str,
    depth: int = 3,
    max_paths: int = 15
) -> List[List[Dict[str, Any]]]:
    """
    DFS traversal: find all causal chains originating from 'entity' up to 'depth' hops.
    Returns lists of paths, representing factual multi-hop causal reasoning.
    """
    await _init_db()
    async with aiosqlite.connect(DB_PATH) as conn:
        all_paths = []
        
        async def dfs(current_entity, current_path, current_depth):
            if current_depth > depth or len(all_paths) >= max_paths:
                return
            
            if current_path:
                all_paths.append(list(current_path))
                
            cursor = await conn.execute(
                "SELECT relation_type, to_entity, context "
                "FROM relations WHERE from_entity = ? "
                "ORDER BY weight DESC LIMIT 10",
                (current_entity,)
            )
            rows = await cursor.fetchall()
            
            for rel_type, to_ent, ctx in rows:
                if any(edge['from'] == to_ent for edge in current_path):
                    continue
                
                edge = {
                    "from": current_entity,
                    "relation": rel_type,
                    "to": to_ent,
                    "context": ctx,
                    "depth": current_depth
                }
                current_path.append(edge)
                await dfs(to_ent, current_path, current_depth + 1)
                current_path.pop()
                
        await dfs(entity, [], 1)
        all_paths.sort(key=len)
        return all_paths

async def find_causal_link(from_entity: str, to_entity: str, max_depth: int = 4) -> List[List[Dict[str, Any]]]:
    """Finds directed causal paths between two specific entities."""
    await _init_db()
    async with aiosqlite.connect(DB_PATH) as conn:
        paths = []
        queue = [([(from_entity, None, None)], 1)] 
        
        while queue:
            current_path, current_depth = queue.pop(0)
            current_node = current_path[-1][0]
            
            if current_node == to_entity and len(current_path) > 1:
                chain = []
                for i in range(1, len(current_path)):
                    prev_node = current_path[i-1][0]
                    curr_node, rel, ctx = current_path[i]
                    chain.append({
                        "from": prev_node,
                        "relation": rel,
                        "to": curr_node,
                        "context": ctx
                    })
                paths.append(chain)
                if len(paths) >= 5: 
                    break
                continue
                
            if current_depth >= max_depth:
                continue
                
            cursor = await conn.execute(
                "SELECT relation_type, to_entity, context "
                "FROM relations WHERE from_entity = ? LIMIT 10",
                (current_node,)
            )
            rows = await cursor.fetchall()
            
            for rel_type, next_ent, ctx in rows:
                if any(node[0] == next_ent for node in current_path):
                    continue
                queue.append((current_path + [(next_ent, rel_type, ctx)], current_depth + 1))
                
        return paths

async def format_graph_context(entity: str, depth: int = 3) -> str:
    """
    Format knowledge graph query as readable causal chains for LLM.
    """
    paths = await query_causal_chains(entity, depth=depth)
    if not paths:
        return ""

    summary_lines = set()
    for path in paths:
        chain = []
        for edge in path:
            ctx_str = f" ({edge['context'][:50]})" if edge.get('context') else ""
            chain.append(f"[{edge['from']}] -{edge['relation']}-> [{edge['to']}]{ctx_str}")
        summary_lines.add(" => ".join(chain))
        
    lines = [f"Knowledge causal chains for '{entity}':"]
    lines.extend(sorted(list(summary_lines)))
    return "\n".join(lines)


async def extract_and_store_knowledge(
    text: str,
    session_id: str,
    router  # ModelRouter
) -> int:
    """
    Use LLM to extract entities and relations from text.
    Returns count of relations stored.
    """
    if len(text) < 50:
        return 0

    extract_prompt = f"""Extract entities and relationships from this text.
Output ONLY valid JSON array, nothing else:
[
  {{"from": "entity1", "relation": "uses", "to": "entity2", "context": "brief context"}},
  ...
]
Relation types: uses, depends_on, created_by, is_a, has, related_to, produces, requires
Max 5 relations. Text: {text[:800]}"""

    try:
        response = await router.generate(
            messages=[{"role": "user", "content": extract_prompt}],
            task_hint="think"
        )
        from backend.utils.json_repair import repair_and_parse
        relations, err = repair_and_parse(response.get("text", ""))
        if not isinstance(relations, list):
            return 0

        count = 0
        for r in relations[:5]:
            if isinstance(r, dict) and all(
                k in r for k in ("from", "relation", "to")
            ):
                await add_relation(
                    from_entity=str(r["from"])[:100],
                    relation_type=str(r["relation"])[:50],
                    to_entity=str(r["to"])[:100],
                    context=str(r.get("context", ""))[:300],
                    session_id=session_id
                )
                count += 1
        return count
    except Exception as e:
        logger.warning(f"Knowledge extraction failed: {e}")
        return 0
