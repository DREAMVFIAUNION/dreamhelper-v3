"""动态 Agent — 根据 DB 中的 Agent 配置驱动 LLM 对话

从 agents 表读取 system_prompt / model / temperature 等参数，
无需硬编码即可创建新 Agent。
"""

from typing import Any

from ..base.base_agent import BaseAgent
from ..base.types import AgentStep, AgentStepType, AgentContext
from ...llm.llm_client import get_llm_client
from ...llm.types import LLMRequest
from ...tools.tool_registry import ToolRegistry


class DynamicAgent(BaseAgent):
    """由数据库定义的动态 Agent"""

    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str = "",
        system_prompt: str = "",
        model_provider: str = "minimax",
        model_name: str = "nvidia/llama-3.1-nemotron-ultra-253b-v1",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[str] | None = None,
        capabilities: list[str] | None = None,
    ):
        super().__init__(name=name, description=description)
        self.agent_id = agent_id
        self.system_prompt = system_prompt or f"你是{name}。{description}"
        self.model_provider = model_provider
        self.default_model = model_name
        self.default_temperature = temperature
        self.default_max_tokens = max_tokens
        self.tool_names = tools or []
        self.capabilities = capabilities or []
        self._has_tools = bool(self.tool_names)

    async def think(self, user_input: str, context: AgentContext) -> AgentStep:
        messages = [{"role": "system", "content": self.system_prompt}]
        for msg in context.history:
            messages.append(msg)
        messages.append({"role": "user", "content": user_input})

        model = context.model_name or self.default_model
        temperature = context.temperature if context.temperature is not None else self.default_temperature

        client = get_llm_client()

        # If this agent has tools, use ReAct-style tool calling
        if self._has_tools:
            return await self._think_with_tools(messages, model, temperature, user_input, context)

        # 双脑模式: 无工具 Agent 可委托 BrainEngine 获得更强推理
        try:
            from ...dual_brain import get_brain_engine
            brain = get_brain_engine()
            if brain.config.enabled and not self._has_tools:
                result = await brain.think(
                    query=user_input,
                    context={"session_id": context.session_id},
                    system_prompt=self.system_prompt,
                    history=context.history,
                )
                return AgentStep(
                    type=AgentStepType.FINAL_ANSWER,
                    content=result.content,
                    is_final=True,
                    final_answer=result.content,
                    metadata={
                        "agent_id": self.agent_id,
                        "brain_mode": "dual",
                        "task_type": result.task_type,
                        "fusion_strategy": result.fusion_strategy,
                        "confidence": result.confidence,
                    },
                )
        except Exception:
            pass  # 双脑失败时静默降级为单脑

        # Simple LLM completion (单脑 fallback)
        request = LLMRequest(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=self.default_max_tokens,
            stream=False,
        )
        response = await client.complete(request)
        return AgentStep(
            type=AgentStepType.FINAL_ANSWER,
            content=response.content,
            is_final=True,
            final_answer=response.content,
            metadata={"agent_id": self.agent_id, "model": model},
        )

    async def _think_with_tools(
        self, messages: list[dict], model: str, temperature: float,
        user_input: str, context: AgentContext,
    ) -> AgentStep:
        """带工具调用的思考（简化版 ReAct）"""
        tool_descriptions = []
        for tn in self.tool_names:
            tool = ToolRegistry.get(tn)
            if tool:
                tool_descriptions.append(f"- {tn}: {tool.description}")

        if tool_descriptions:
            tool_section = "\n\n## 可用工具\n" + "\n".join(tool_descriptions)
            tool_section += '\n\n如需调用工具，返回 JSON: {"tool": "tool_name", "input": {...}}\n否则直接回答。'
            messages[0]["content"] += tool_section

        client = get_llm_client()
        request = LLMRequest(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=self.default_max_tokens,
            stream=False,
        )
        response = await client.complete(request)
        content = response.content.strip()

        # Try to parse tool call
        import json
        try:
            if '{"tool"' in content:
                start = content.index('{"tool"')
                decoder = json.JSONDecoder()
                parsed, _ = decoder.raw_decode(content, start)
                if "tool" in parsed:
                    return AgentStep(
                        type=AgentStepType.TOOL_CALL,
                        content=content[:start].strip() if start > 0 else f"调用工具 {parsed['tool']}",
                        tool_name=parsed["tool"],
                        tool_input=parsed.get("input", {}),
                        metadata={"agent_id": self.agent_id},
                    )
        except (json.JSONDecodeError, ValueError):
            pass

        return AgentStep(
            type=AgentStepType.FINAL_ANSWER,
            content=content,
            is_final=True,
            final_answer=content,
            metadata={"agent_id": self.agent_id, "model": model},
        )

    async def act(self, tool_name: str, tool_input: dict[str, Any], context: AgentContext) -> AgentStep:
        """执行工具"""
        tool = ToolRegistry.get(tool_name)
        if not tool:
            return AgentStep(
                type=AgentStepType.OBSERVATION,
                content=f"工具 {tool_name} 不存在",
            )
        try:
            result = await tool.execute(**tool_input)
            return AgentStep(
                type=AgentStepType.OBSERVATION,
                content=str(result),
                tool_name=tool_name,
                tool_output=str(result),
            )
        except Exception as e:
            return AgentStep(
                type=AgentStepType.ERROR,
                content=f"工具执行失败: {e}",
                tool_name=tool_name,
            )

    async def synthesize(self, user_input: str, context: AgentContext) -> AgentStep:
        """超过最大步数时综合回答"""
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(context.history)
        messages.append({
            "role": "user",
            "content": f"请根据之前的对话历史，综合回答用户的原始问题：{user_input}",
        })
        client = get_llm_client()
        request = LLMRequest(
            messages=messages,
            model=context.model_name or self.default_model,
            temperature=self.default_temperature,
            max_tokens=self.default_max_tokens,
            stream=False,
        )
        response = await client.complete(request)
        return AgentStep(
            type=AgentStepType.FINAL_ANSWER,
            content=response.content,
            is_final=True,
            final_answer=response.content,
            metadata={"agent_id": self.agent_id},
        )
