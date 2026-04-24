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


async def query_related(
    entity: str,
    depth: int = 2,
    max_nodes: int = 20
) -> List[Dict[str, Any]]:
    """
    BFS traversal: find all entities related to 'entity' up to 'depth' hops.
    Returns context-rich description of the knowledge subgraph.
    """
    await _init_db()
    async with aiosqlite.connect(DB_PATH) as conn:
        visited = set()
        results = []
        queue = [(entity, 0)]

        while queue and len(results) < max_nodes:
            current, current_depth = queue.pop(0)
            if current in visited or current_depth > depth:
                continue
            visited.add(current)

            # Get outgoing relations
            cursor = await conn.execute(
                "SELECT relation_type, to_entity, context, weight "
                "FROM relations WHERE from_entity = ? "
                "ORDER BY weight DESC LIMIT 10",
                (current,)
            )
            rows = await cursor.fetchall()

            for rel_type, to_ent, ctx, weight in rows:
                results.append({
                    "from": current,
                    "relation": rel_type,
                    "to": to_ent,
                    "context": ctx,
                    "depth": current_depth + 1
                })
                if to_ent not in visited:
                    queue.append((to_ent, current_depth + 1))

            # Get incoming relations
            cursor = await conn.execute(
                "SELECT from_entity, relation_type, context "
                "FROM relations WHERE to_entity = ? LIMIT 5",
                (current,)
            )
            rows = await cursor.fetchall()
            for from_ent, rel_type, ctx in rows:
                if from_ent not in visited:
                    results.append({
                        "from": from_ent,
                        "relation": rel_type,
                        "to": current,
                        "context": ctx,
                        "depth": current_depth + 1
                    })

    return results


async def format_graph_context(entity: str, depth: int = 2) -> str:
    """
    Format knowledge graph query as readable context for LLM.
    """
    relations = await query_related(entity, depth=depth, max_nodes=15)
    if not relations:
        return ""

    lines = [f"Knowledge graph for '{entity}':"]
    for r in relations:
        lines.append(
            f"  [{r['from']}] —{r['relation']}→ [{r['to']}]"
            + (f" ({r['context'][:100]})" if r['context'] else "")
        )
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
