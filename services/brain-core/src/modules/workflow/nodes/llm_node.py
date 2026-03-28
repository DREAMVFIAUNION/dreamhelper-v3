"""LLM 节点 — 调用大语言模型（复用现有 llm_client）"""

from typing import Any

from ..base_node import BaseNode
from ..types import NodeData, NodeDescriptor


class LlmNode(BaseNode):
    def descriptor(self) -> NodeDescriptor:
        return NodeDescriptor(
            type="llm",
            name="大模型对话",
            description="调用 MiniMax / Qwen / DeepSeek 等大模型",
            category="ai",
            icon="Brain",
            color="#8B5CF6",
            inputs=["input"],
            outputs=["output"],
            config_schema={
                "provider": {
                    "type": "select", "label": "模型厂商", "default": "minimax",
                    "options": ["minimax", "qwen", "deepseek", "openai"],
                },
                "model": {"type": "string", "label": "模型名称", "default": "nvidia/llama-3.1-nemotron-ultra-253b-v1"},
                "prompt": {"type": "textarea", "label": "提示词", "default": "", "placeholder": "你是一个专业助手..."},
                "message_template": {
                    "type": "textarea", "label": "消息模板",
                    "default": "{{input}}", "placeholder": "使用 {{input}} 引用上游数据",
                },
                "temperature": {"type": "number", "label": "温度", "default": 0.7, "min": 0, "max": 2},
                "max_tokens": {"type": "number", "label": "最大 Token", "default": 4096},
            },
        )

    async def execute(self, input_data: NodeData, config: dict[str, Any]) -> NodeData:
        from ...llm.llm_client import get_llm_client

        provider = config.get("provider", "minimax")
        model = config.get("model", "nvidia/llama-3.1-nemotron-ultra-253b-v1")
        system_prompt = config.get("prompt", "")
        msg_template = config.get("message_template", "{{input}}")
        temperature = config.get("temperature", 0.7)
        max_tokens = config.get("max_tokens", 4096)

        # 将上游数据注入模板
        input_text = ""
        if input_data.items:
            import json
            input_text = json.dumps(input_data.items, ensure_ascii=False, default=str)
        user_message = msg_template.replace("{{input}}", input_text)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        client = get_llm_client()
        response = await client.chat(
            messages=messages,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return NodeData(
            items=[{
                "content": response.content,
                "model": response.model,
                "tokens": response.usage.get("total_tokens", 0) if response.usage else 0,
            }],
            metadata={
                "tokens": response.usage.get("total_tokens", 0) if response.usage else 0,
                "provider": provider,
                "model": model,
            },
        )
