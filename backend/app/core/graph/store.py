import sqlite3
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.models.database import db_manager

class GraphStore(ABC):
    """Abstract interface for Knowledge Graph storage engines (SQLite, Neo4j, etc.)."""
    
    @abstractmethod
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def find_children(self, node_id: str, relationship_type: Optional[str] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def find_parent(self, node_id: str, relationship_type: Optional[str] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def find_neighbors(self, node_id: str, depth: int = 1, relationship_type: Optional[str] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def find_ancestors(self, node_id: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def find_descendants(self, node_id: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        pass


class SQLiteGraphStore(GraphStore):
    """Production SQLite implementation of the GraphStore interface."""

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        with db_manager._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_objects WHERE id = ?", (node_id,))
            row = cursor.fetchone()
            if row:
                d = dict(row)
                if d.get("metadata"):
                    try:
                        d["metadata"] = json.loads(d["metadata"])
                    except Exception:
                        pass
                return d
            return None

    def find_children(self, node_id: str, relationship_type: Optional[str] = None) -> List[Dict[str, Any]]:
        with db_manager._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = """
                SELECT k.*, r.relationship_type 
                FROM relationship_edges r
                JOIN knowledge_objects k ON r.target_id = k.id
                WHERE r.source_id = ?
            """
            params = [node_id]
            if relationship_type:
                query += " AND r.relationship_type = ?"
                params.append(relationship_type)
            cursor.execute(query, tuple(params))
            results = []
            for row in cursor.fetchall():
                d = dict(row)
                if d.get("metadata"):
                    try:
                        d["metadata"] = json.loads(d["metadata"])
                    except Exception:
                        pass
                results.append(d)
            return results

    def find_parent(self, node_id: str, relationship_type: Optional[str] = None) -> List[Dict[str, Any]]:
        with db_manager._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = """
                SELECT k.*, r.relationship_type 
                FROM relationship_edges r
                JOIN knowledge_objects k ON r.source_id = k.id
                WHERE r.target_id = ?
            """
            params = [node_id]
            if relationship_type:
                query += " AND r.relationship_type = ?"
                params.append(relationship_type)
            cursor.execute(query, tuple(params))
            results = []
            for row in cursor.fetchall():
                d = dict(row)
                if d.get("metadata"):
                    try:
                        d["metadata"] = json.loads(d["metadata"])
                    except Exception:
                        pass
                results.append(d)
            return results

    def find_neighbors(self, node_id: str, depth: int = 1, relationship_type: Optional[str] = None) -> List[Dict[str, Any]]:
        neighbors = []
        if depth >= 1:
            children = self.find_children(node_id, relationship_type)
            parents = self.find_parent(node_id, relationship_type)
            neighbors.extend(children)
            neighbors.extend(parents)
            
            if depth > 1:
                visited = {node_id}
                queue = [(n, 1) for n in neighbors]
                all_neighbors = {n["id"]: n for n in neighbors}
                
                while queue:
                    curr, current_depth = queue.pop(0)
                    visited.add(curr["id"])
                    
                    if current_depth < depth:
                        next_children = self.find_children(curr["id"], relationship_type)
                        next_parents = self.find_parent(curr["id"], relationship_type)
                        for n in next_children + next_parents:
                            if n["id"] not in visited and n["id"] not in all_neighbors:
                                all_neighbors[n["id"]] = n
                                queue.append((n, current_depth + 1))
                                
                return list(all_neighbors.values())
        return neighbors

    def find_ancestors(self, node_id: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        ancestors = []
        current_id = node_id
        depth = 0
        while depth < max_depth:
            parents = self.find_parent(current_id)
            if not parents:
                break
            ancestors.extend(parents)
            current_id = parents[0]["id"]
            depth += 1
        return ancestors

    def find_descendants(self, node_id: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        descendants = []
        visited = {node_id}
        queue = [(node_id, 0)]
        
        while queue:
            curr_id, current_depth = queue.pop(0)
            if current_depth < max_depth:
                children = self.find_children(curr_id)
                for child in children:
                    if child["id"] not in visited:
                        visited.add(child["id"])
                        descendants.append(child)
                        queue.append((child["id"], current_depth + 1))
        return descendants
