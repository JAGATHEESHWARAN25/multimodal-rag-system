import pytest
from app.core.graph.store import GraphStore, SQLiteGraphStore
from app.core.graph.manager import GraphManager
from app.core.llm_provider import LocalLLMProvider, OllamaProvider, MockLLMProvider, QwenProvider, LLMProviderFactory
from app.core.llm import LocalLLMConnector

def test_sqlite_graph_store_instantiation():
    store = SQLiteGraphStore()
    assert isinstance(store, GraphStore)
    node = store.get_node("non_existent_id")
    assert node is None

def test_graph_manager_facade():
    store = SQLiteGraphStore()
    GraphManager.set_store(store)
    assert GraphManager.get_store() == store
    assert GraphManager.get_node("non_existent_id") is None

def test_llm_provider_abstractions():
    mock_p = MockLLMProvider()
    assert isinstance(mock_p, LocalLLMProvider)
    assert mock_p.check_status() is True
    assert "[Offline Mock LLM Mode]" in mock_p.generate("Hello")

    qwen_p = QwenProvider()
    assert isinstance(qwen_p, LocalLLMProvider)
    # Since endpoint is offline, fallback is tested
    res = qwen_p.generate("Test prompt")
    assert res is not None

    LLMProviderFactory.set_provider(mock_p)
    assert LLMProviderFactory.get_provider() == mock_p

    conn_res = LocalLLMConnector.generate_response("Test prompt")
    assert "[Offline Mock LLM Mode]" in conn_res
