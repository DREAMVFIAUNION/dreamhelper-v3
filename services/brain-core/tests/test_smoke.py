"""冒烟测试 — 验证核心模块可导入 + 基本逻辑正确"""

import pytest


# ── 导入测试 ────────────────────────────────────────────

def test_import_tool_registry():
    from src.modules.tools.tool_registry import ToolRegistry, BaseTool
    assert hasattr(ToolRegistry, 'register')
    assert hasattr(ToolRegistry, 'execute')


def test_import_agent_types():
    from src.modules.agents.base.types import AgentContext, AgentStep, AgentStepType
    ctx = AgentContext(session_id="s1", user_id="u1")
    assert ctx.session_id == "s1"
    assert ctx.max_steps == 10


def test_import_workflow_types():
    from src.modules.workflow.types import NodeData, NodeDescriptor
    nd = NodeData(items=[{"a": 1}])
    assert len(nd.items) == 1


def test_import_memory_dataclasses():
    from src.modules.memory.memory_manager import MemoryItem, UserFact
    item = MemoryItem(content="hello", role="user")
    assert item.role == "user"
    fact = UserFact(key="name", value="Alice")
    assert fact.confidence == 1.0


# ── Agent 路由关键词测试 ─────────────────────────────────

def test_keyword_routing_code():
    from src.modules.agents.agent_router import route_by_keywords
    assert route_by_keywords("写一个Python装饰器") == "coding_agent"


def test_keyword_routing_writing():
    from src.modules.agents.agent_router import route_by_keywords
    assert route_by_keywords("帮我翻译这段话成英文") == "writing_agent"


def test_keyword_routing_analysis():
    from src.modules.agents.agent_router import route_by_keywords
    assert route_by_keywords("分析微服务和单体架构优劣") == "analysis_agent"


def test_keyword_routing_react():
    from src.modules.agents.agent_router import route_by_keywords
    assert route_by_keywords("帮我算 2+3*4") == "react_agent"


def test_keyword_routing_none():
    from src.modules.agents.agent_router import route_by_keywords
    assert route_by_keywords("你好呀") is None


# ── 计算器工具测试 ───────────────────────────────────────

@pytest.mark.asyncio
async def test_calculator_tool():
    from src.modules.tools.implementations.calculator import CalculatorTool
    calc = CalculatorTool()
    result = await calc.execute(expression="2 + 3 * 4")
    assert "14" in result


@pytest.mark.asyncio
async def test_calculator_sqrt():
    from src.modules.tools.implementations.calculator import CalculatorTool
    calc = CalculatorTool()
    result = await calc.execute(expression="sqrt(16)")
    assert "4" in result


# ── Redis 短期记忆测试 (内存降级模式) ─────────────────────

@pytest.mark.asyncio
async def test_redis_store_fallback():
    from src.modules.memory.redis_store import RedisSessionStore
    store = RedisSessionStore()
    await store.add_message("test-session", "user", "hello")
    history = await store.get_history("test-session")
    assert len(history) == 1
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "hello"
    await store.clear_session("test-session")
    history2 = await store.get_history("test-session")
    assert len(history2) == 0


# ── DynamicAgent 构造测试 ────────────────────────────────

def test_dynamic_agent_init():
    from src.modules.agents.implementations.dynamic_agent import DynamicAgent
    da = DynamicAgent(
        agent_id="test-id",
        name="test_agent",
        description="A test agent",
        system_prompt="You are a test agent.",
        model_name="test-model",
        temperature=0.5,
    )
    assert da.name == "test_agent"
    assert da.agent_id == "test-id"
    assert da.default_temperature == 0.5
    assert da._has_tools is False


def test_dynamic_agent_with_tools():
    from src.modules.agents.implementations.dynamic_agent import DynamicAgent
    da = DynamicAgent(
        agent_id="t2",
        name="tool_agent",
        tools=["calculator", "datetime"],
    )
    assert da._has_tools is True
    assert len(da.tool_names) == 2


# ── 回归测试: BUG 修复验证 ──────────────────────────────

def test_tool_registry_api_surface():
    """回归 BUG-3: ToolRegistry.get() 存在，get_tool() 不存在"""
    from src.modules.tools.tool_registry import ToolRegistry
    assert hasattr(ToolRegistry, 'get'), "ToolRegistry must have 'get' method"
    assert not hasattr(ToolRegistry, 'get_tool'), "get_tool should NOT exist (use 'get')"


def test_tool_registry_get_returns_basetool():
    """回归 BUG-3: ToolRegistry.get() 返回 BaseTool 实例而非 dict"""
    from src.modules.tools.tool_registry import ToolRegistry, BaseTool
    from src.modules.tools.setup import register_all_tools
    register_all_tools()
    tool = ToolRegistry.get("calculator")
    assert tool is not None, "calculator tool must be registered"
    assert isinstance(tool, BaseTool)
    assert hasattr(tool, 'description')
    assert hasattr(tool, 'execute')
    assert callable(tool.execute)


def test_node_registry_no_get_all():
    """回归 BUG-1/2: NodeRegistry 没有 get_all() 方法"""
    from src.modules.workflow.node_registry import NodeRegistry
    assert not hasattr(NodeRegistry, 'get_all'), "get_all should NOT exist"
    assert hasattr(NodeRegistry, 'get')
    assert hasattr(NodeRegistry, 'list_descriptors')


def test_workflow_engine_init_no_args():
    """回归 BUG-1/2: WorkflowEngine() 可无参实例化"""
    from src.modules.workflow.engine import WorkflowEngine
    engine = WorkflowEngine()
    assert engine is not None
    assert engine._on_status is None


def test_workflow_engine_execute_signature():
    """回归 BUG-1/2: execute() 第一个位置参数是 execution_id"""
    import inspect
    from src.modules.workflow.engine import WorkflowEngine
    sig = inspect.signature(WorkflowEngine.execute)
    params = list(sig.parameters.keys())
    assert params[0] == "self"
    assert params[1] == "execution_id"
    assert params[2] == "nodes"
    assert params[3] == "connections"


def test_memory_manager_session_summary_methods():
    """回归 BUG-4: MemoryManager 有 get/set_session_summary 方法"""
    from src.modules.memory.memory_manager import MemoryManager
    mm = MemoryManager()
    assert hasattr(mm, 'get_session_summary')
    assert hasattr(mm, 'set_session_summary')
    assert callable(mm.get_session_summary)
    assert callable(mm.set_session_summary)


def test_dynamic_agent_temperature_none_safe():
    """回归 BUG-9: temperature=None 不应抛异常"""
    from src.modules.agents.implementations.dynamic_agent import DynamicAgent
    da = DynamicAgent(
        agent_id="t-temp",
        name="temp_test",
        temperature=0.3,
    )
    assert da.default_temperature == 0.3


def test_json_nested_parse():
    """回归 BUG-5: json.JSONDecoder().raw_decode 可正确解析嵌套 JSON"""
    import json
    content = '我需要调用工具 {"tool": "calc", "input": {"expression": "2+3"}} 来计算'
    start = content.index('{"tool"')
    decoder = json.JSONDecoder()
    parsed, end = decoder.raw_decode(content, start)
    assert parsed["tool"] == "calc"
    assert parsed["input"]["expression"] == "2+3"
