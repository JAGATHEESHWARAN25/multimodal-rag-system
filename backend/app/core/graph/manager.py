from typing import List, Dict, Any, Optional
from app.core.graph.store import GraphStore, SQLiteGraphStore

class GraphManager:
    """Facade for Knowledge Graph operations, delegating to a configured GraphStore backend."""
    
    _store: GraphStore = SQLiteGraphStore()

    @classmethod
    def set_store(cls, store: GraphStore):
        cls._store = store

    @classmethod
    def get_store(cls) -> GraphStore:
        return cls._store

    @staticmethod
    def get_node(node_id: str) -> Optional[Dict[str, Any]]:
        return GraphManager._store.get_node(node_id)

    @staticmethod
    def find_children(node_id: str, relationship_type: Optional[str] = None) -> List[Dict[str, Any]]:
        return GraphManager._store.find_children(node_id, relationship_type)

    @staticmethod
    def find_parent(node_id: str, relationship_type: Optional[str] = None) -> List[Dict[str, Any]]:
        return GraphManager._store.find_parent(node_id, relationship_type)

    @staticmethod
    def find_neighbors(node_id: str, depth: int = 1, relationship_type: Optional[str] = None) -> List[Dict[str, Any]]:
        return GraphManager._store.find_neighbors(node_id, depth, relationship_type)

    @staticmethod
    def find_ancestors(node_id: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        return GraphManager._store.find_ancestors(node_id, max_depth)

    @staticmethod
    def find_descendants(node_id: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        return GraphManager._store.find_descendants(node_id, max_depth)

