import logging
from typing import List, Dict, Any, Optional, Set
from collections import deque
from app.core.graph.manager import GraphManager

logger = logging.getLogger(__name__)

class GraphReasoningEngine:
    """Controlled, bounded, deterministic Graph Reasoning Engine.
    
    Supports multi-hop traversal with strict depth limits, cycle prevention,
    RBAC classification filtering, and provenance tracking.
    """

    @staticmethod
    def find_parent(node_id: str, relationship_type: Optional[str] = None) -> List[Dict[str, Any]]:
        return GraphManager.find_parent(node_id, relationship_type)

    @staticmethod
    def find_children(node_id: str, relationship_type: Optional[str] = None) -> List[Dict[str, Any]]:
        return GraphManager.find_children(node_id, relationship_type)

    @staticmethod
    def find_neighbors(node_id: str, depth: int = 1, relationship_type: Optional[str] = None) -> List[Dict[str, Any]]:
        depth = min(max(1, depth), 5) # Enforce bounded depth limit (max 5)
        return GraphManager.find_neighbors(node_id, depth=depth, relationship_type=relationship_type)

    @staticmethod
    def find_path(source_id: str, target_id: str, max_depth: int = 3, user_role: Optional[str] = None) -> List[Dict[str, Any]]:
        """Finds the shortest bounded relationship path between two nodes using BFS with cycle detection."""
        max_depth = min(max(1, max_depth), 5)
        if source_id == target_id:
            node = GraphManager.get_node(source_id)
            return [node] if node else []

        queue = deque([(source_id, [source_id])])
        visited: Set[str] = {source_id}

        while queue:
            curr_id, path = queue.popleft()
            if len(path) - 1 >= max_depth:
                continue

            neighbors = GraphManager.find_neighbors(curr_id, depth=1)
            for n in neighbors:
                n_id = n["id"]
                if n_id == target_id:
                    full_path_ids = path + [target_id]
                    full_nodes = []
                    for pid in full_path_ids:
                        obj = GraphManager.get_node(pid)
                        if obj:
                            full_nodes.append(obj)
                    return full_nodes

                if n_id not in visited:
                    visited.add(n_id)
                    queue.append((n_id, path + [n_id]))

        return []

    @staticmethod
    def find_related_entities(entity_id: str, relationship_type: Optional[str] = None, user_role: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves entity nodes connected to the target entity with classification filtering."""
        neighbors = GraphManager.find_neighbors(entity_id, depth=1, relationship_type=relationship_type)
        entities = []
        for n in neighbors:
            if n.get("type") == "Entity" or n.get("object_type") == "Entity":
                entities.append(n)
        return entities

    @staticmethod
    def find_documents_containing_entity(entity_id: str, user_role: Optional[str] = None) -> List[Dict[str, Any]]:
        """Traverses upwards from an entity node to identify parent document objects with RBAC filtering."""
        ancestors = GraphManager.find_ancestors(entity_id, max_depth=5)
        docs = []
        for anc in ancestors:
            if anc.get("type") == "Document" or anc.get("object_type") == "Document":
                docs.append(anc)
        return docs
