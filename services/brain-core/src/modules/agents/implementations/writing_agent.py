"""写作助手 Agent — 专注文案、翻译、总结、改写（Phase 5）"""

from typing import Any

from ..base.base_agent import BaseAgent
from ..base.types import AgentStep, AgentStepType, AgentContext
from ...llm.llm_client import get_llm_client
from ...llm.types import LLMRequest


WRITING_SYSTEM_PROMPT = """你是梦帮小助的写作专家模式。你是一位资深的文字工作者。

## 你的能力
- 文案创作：营销文案、产品描述、社交媒体内容
- 文章写作：博客、报告、方案、邮件
- 翻译润色：中英互译、文本润色、语法修正
- 内容总结：长文摘要、会议纪要、要点提取
- 改写优化：风格转换、扩写缩写、SEO 优化

## 回答规范
1. 根据场景调整语气和风格
2. 结构清晰，善用标题、列表、分段
3. 翻译要信达雅，保留原文意境
4. 总结要抓住核心，去除冗余
5. 提供多个版本供选择（如适用）
6. 回答用中文（除非用户要求其他语言）"""


class WritingAgent(BaseAgent):
    """写作助手 Agent"""

    def __init__(self):
        super().__init__(
            name="writing_agent",
            description="写作助手：文案创作、翻译润色、内容总结、改写优化"
        )

    async def think(self, user_input: str, context: AgentContext) -> AgentStep:
        messages = [{"role": "system", "content": WRITING_SYSTEM_PROMPT}]
        for msg in context.history:
            messages.append(msg)
        messages.append({"role": "user", "content": user_input})

        client = get_llm_client()
        request = LLMRequest(
            messages=messages,
            model=context.model_name or "nvidia/llama-3.1-nemotron-ultra-253b-v1",
            temperature=0.8,
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
        return AgentStep(type=AgentStepType.OBSERVATION, content="WritingAgent 不使用工具")

    async def synthesize(self, user_input: str, context: AgentContext) -> AgentStep:
        return await self.think(user_input, context)
