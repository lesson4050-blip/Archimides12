import networkx as nx
import json
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class GraphMemory:
    """
    Bi-Temporal Knowledge Graph Memory for Archimedes.
    Moves beyond flat vector embeddings by establishing causal reasoning paths
    between entities, tasks, and historical outcomes.
    """
    def __init__(self, db_path: str = "./data/graph_memory.json"):
        self.db_path = db_path
        self.graph = nx.MultiDiGraph()
        self._load()

    def _load(self):
        """Loads graph from disk if it exists."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.graph = nx.node_link_graph(data)
                logger.info(f"Loaded GraphMemory from {self.db_path}")
            except Exception as e:
                logger.error(f"Failed to load GraphMemory: {e}")
                self.graph = nx.MultiDiGraph()
        else:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _save(self):
        """Persists graph to disk."""
        try:
            data = nx.node_link_data(self.graph)
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save GraphMemory: {e}")

    def add_entity(self, entity: str, entity_type: str = "concept", metadata: Optional[Dict] = None):
        """Adds a node to the graph."""
        if not self.graph.has_node(entity):
            self.graph.add_node(entity, type=entity_type, **(metadata or {}))
            self._save()

    def add_fact(self, source_entity: str, relation: str, target_entity: str, metadata: Optional[Dict] = None):
        """Adds an edge (causal or semantic relation) between two entities."""
        # Ensure nodes exist
        self.add_entity(source_entity)
        self.add_entity(target_entity)
        
        # Add edge
        self.graph.add_edge(source_entity, target_entity, key=relation, **(metadata or {}))
        self._save()

    def retrieve_causal_path(self, start_entity: str, max_depth: int = 3) -> List[List[Dict[str, Any]]]:
        """
        Traverses the graph to find multi-hop causal reasoning paths.
        Returns a list of causal chains (paths), where each path is a sequence of edges.
        """
        if not self.graph.has_node(start_entity):
            return []

        all_paths = []
        
        # DFS to track exact causal sequences up to max_depth
        def dfs(current_node, current_path, current_depth):
            if current_depth > max_depth:
                return
            
            if current_path:
                all_paths.append(list(current_path))
                
            for neighbor in self.graph.successors(current_node):
                # Prevent cycles in the current reasoning chain
                if any(edge['source'] == neighbor for edge in current_path):
                    continue
                    
                edge_data_dict = self.graph.get_edge_data(current_node, neighbor)
                for key, attr in edge_data_dict.items():
                    edge_obj = {
                        "source": current_node,
                        "relation": key,
                        "target": neighbor,
                        "metadata": attr
                    }
                    current_path.append(edge_obj)
                    dfs(neighbor, current_path, current_depth + 1)
                    current_path.pop()

        dfs(start_entity, [], 1)
        all_paths.sort(key=len)
        return all_paths

    def find_causal_link(self, start_entity: str, end_entity: str, max_depth: int = 4) -> List[List[Dict[str, Any]]]:
        """Finds directed causal paths between two specific entities to establish facts."""
        if not self.graph.has_node(start_entity) or not self.graph.has_node(end_entity):
            return []
            
        paths = []
        try:
            simple_paths = nx.all_simple_paths(self.graph, start_entity, end_entity, cutoff=max_depth)
            for path in simple_paths:
                path_edges = []
                for i in range(len(path) - 1):
                    u, v = path[i], path[i+1]
                    edge_data_dict = self.graph.get_edge_data(u, v)
                    # For simplicity, take the first relation if multiple exist
                    rel = list(edge_data_dict.keys())[0]
                    attr = edge_data_dict[rel]
                    path_edges.append({
                        "source": u,
                        "relation": rel,
                        "target": v,
                        "metadata": attr
                    })
                paths.append(path_edges)
        except nx.NetworkXNoPath:
            pass
            
        return paths

    def summarize_subgraph(self, start_entity: str, max_depth: int = 2) -> str:
        """
        Generates a textual summary of the causal chains originating from the entity.
        Useful for LLM context injection to provide factual grounded reasoning.
        """
        paths = self.retrieve_causal_path(start_entity, max_depth=max_depth)
        if not paths:
            return f"No causal paths found for {start_entity}."
            
        summary_lines = set()
        for path in paths:
            chain = []
            for edge in path:
                chain.append(f"{edge['source']} -[{edge['relation']}]-> {edge['target']}")
            summary_lines.add(" => ".join(chain))
            
        return "\n".join(sorted(list(summary_lines)))
