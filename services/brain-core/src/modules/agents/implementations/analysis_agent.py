"""分析助手 Agent — 专注数据分析、逻辑推理、问题拆解（Phase 5）"""

from typing import Any

from ..base.base_agent import BaseAgent
from ..base.types import AgentStep, AgentStepType, AgentContext
from ...llm.llm_client import get_llm_client
from ...llm.types import LLMRequest
from ...tools.tool_registry import ToolRegistry


ANALYSIS_SYSTEM_PROMPT = """你是梦帮小助的分析专家模式。你擅长逻辑推理和深度分析。

## 你的能力
- 问题分析：拆解复杂问题，找到核心矛盾
- 数据分析：解读数据趋势、统计结论
- 对比评测：多方案优劣对比、决策建议
- 逻辑推理：因果分析、假设验证
- 知识整理：知识图谱、概念梳理

## 你可以使用的工具
{tools}

## 回答规范
1. 先明确问题本质，再展开分析
2. 用结构化方式呈现（表格、列表、分层）
3. 数据要有来源说明
4. 给出明确结论和建议
5. 区分事实和推测

## 工具调用格式
需要工具时输出 JSON：
{{"thought": "思考", "action": "工具名", "action_input": {{"参数": "值"}}}}
直接回答时：
{{"thought": "思考", "final_answer": "回答"}}"""


class AnalysisAgent(BaseAgent):
    """分析助手 Agent — 支持工具调用"""

    def __init__(self):
        super().__init__(
            name="analysis_agent",
            description="分析助手：数据分析、逻辑推理、对比评测、问题拆解"
        )

    async def think(self, user_input: str, context: AgentContext) -> AgentStep:
        dynamic_schemas = await ToolRegistry.get_dynamic_tool_schemas(query=user_input)
        tools_desc = "\n".join(
            f"- {t['name']}: {t['description']}"
            for t in dynamic_schemas
        ) or "（无可用工具）"
        system = ANALYSIS_SYSTEM_PROMPT.format(tools=tools_desc)

        messages = [{"role": "system", "content": system}]
        for msg in context.history:
            messages.append(msg)
        messages.append({"role": "user", "content": user_input})

        client = get_llm_client()
        request = LLMRequest(
            messages=messages,
            model=context.model_name or "nvidia/llama-3.1-nemotron-ultra-253b-v1",
            temperature=0.4,
            max_tokens=8192,
            stream=False,
        )
        response = await client.complete(request)
        raw = response.content.strip()

        # 尝试解析 JSON（工具调用或最终回答）
        try:
            from .react_agent import _parse_llm_response
            parsed = _parse_llm_response(raw)
            thought = parsed.get("thought", "")

            if "final_answer" in parsed:
                return AgentStep(
                    type=AgentStepType.FINAL_ANSWER,
                    content=thought,
                    is_final=True,
                    final_answer=parsed["final_answer"],
                )
            if "action" in parsed:
                return AgentStep(
                    type=AgentStepType.TOOL_CALL,
                    content=thought,
                    tool_name=parsed["action"],
                    tool_input=parsed.get("action_input", {}),
                )
        except (ValueError, KeyError):
            pass

        return AgentStep(
            type=AgentStepType.FINAL_ANSWER,
            content=raw,
            is_final=True,
            final_answer=raw,
        )

    async def act(self, tool_name: str, tool_input: dict[str, Any], context: AgentContext) -> AgentStep:
        try:
            result = await ToolRegistry.execute(tool_name, **tool_input)
            return AgentStep(
                type=AgentStepType.OBSERVATION,
                content=result,
                tool_name=tool_name,
                tool_output=result,
            )
        except Exception as e:
            return AgentStep(type=AgentStepType.ERROR, content=f"工具执行失败: {e}")

    async def synthesize(self, user_input: str, context: AgentContext) -> AgentStep:
        return await self.think(user_input, context)
