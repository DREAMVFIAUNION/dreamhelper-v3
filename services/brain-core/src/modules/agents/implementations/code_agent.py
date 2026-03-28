"""编程助手 Agent — 专注代码生成、调试、解释（Phase 5）"""

import json
from typing import Any

from ..base.base_agent import BaseAgent
from ..base.types import AgentStep, AgentStepType, AgentContext
from ...llm.llm_client import get_llm_client
from ...llm.types import LLMRequest


CODE_SYSTEM_PROMPT = """你是梦帮小助的编程专家模式。你是一个经验丰富的全栈工程师。

## 你的能力
- 代码生成：根据需求生成高质量代码
- 代码解释：逐行解释代码逻辑
- Bug 调试：分析错误信息，定位问题
- 代码优化：性能优化、重构建议
- 技术方案：架构设计、技术选型

## 回答规范
1. 代码必须用 ```language 代码块包裹，标注语言
2. 先简要说明思路，再给出代码
3. 关键逻辑加注释
4. 如有多种方案，说明优劣
5. 提及潜在的边界情况和错误处理
6. 回答用中文，代码注释可中英混合"""


class CodeAgent(BaseAgent):
    """编程助手 Agent"""

    def __init__(self):
        super().__init__(
            name="code_agent",
            description="编程助手：代码生成、调试、解释、优化、技术方案"
        )

    async def think(self, user_input: str, context: AgentContext) -> AgentStep:
        messages = [{"role": "system", "content": CODE_SYSTEM_PROMPT}]
        for msg in context.history:
            messages.append(msg)
        messages.append({"role": "user", "content": user_input})

        client = get_llm_client()
        request = LLMRequest(
            messages=messages,
            model=context.model_name or "nvidia/llama-3.1-nemotron-ultra-253b-v1",
            temperature=0.5,
            max_tokens=8192,
            stream=False,
        )
        response = await client.complete(request)
        return AgentStep(
            type=AgentStepType.FINAL_ANSWER,
            content=response.content,
            is_final=True,
            final_answer=response.content,
        )

    async def act(self, tool_name: str, tool_input: dict[str, Any], context: AgentContext) -> AgentStep:
        return AgentStep(type=AgentStepType.OBSERVATION, content="CodeAgent 不使用工具")

    async def synthesize(self, user_input: str, context: AgentContext) -> AgentStep:
        return await self.think(user_input, context)
