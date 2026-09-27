import pytest
from app.core.rag.agents import (
    AgentContext, QueryPlanner, RetrievalAgent, GraphAgent,
    EvidenceAgent, AnswerAgent, CitationAgent, ModularMultiAgentPipeline
)

def test_agent_context_timeout():
    ctx = AgentContext(timeout_seconds=0.01)
    import time
    time.sleep(0.02)
    with pytest.raises(TimeoutError):
        ctx.check_timeout()

def test_query_planner():
    ctx = AgentContext()
    planner = QueryPlanner()
    plan = planner.run("summarize NTRO document report", ctx)
    assert "query" in plan
    assert "sub_queries" in plan
    assert plan["trace_id"] == ctx.trace_id

def test_modular_multi_agent_pipeline():
    pipeline = ModularMultiAgentPipeline()
    res = pipeline.execute_rag("What is in the document?", user_role="SYSTEM_ADMIN", limit=2)
    
    assert "trace_id" in res
    assert "citations" in res
    assert "answer_stream" in res

    tokens = list(res["answer_stream"])
    assert len(tokens) > 0
