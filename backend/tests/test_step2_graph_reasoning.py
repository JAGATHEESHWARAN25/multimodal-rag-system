import pytest
from app.core.graph.reasoning import GraphReasoningEngine

def test_graph_reasoning_bounded_neighbors():
    res = GraphReasoningEngine.find_neighbors("non_existent_node", depth=2)
    assert res == []

def test_graph_reasoning_find_path():
    path = GraphReasoningEngine.find_path("node_a", "node_b", max_depth=3)
    assert isinstance(path, list)

def test_graph_reasoning_find_related_entities():
    entities = GraphReasoningEngine.find_related_entities("node_a")
    assert isinstance(entities, list)

def test_graph_reasoning_find_parent_documents():
    docs = GraphReasoningEngine.find_documents_containing_entity("entity_a")
    assert isinstance(docs, list)
