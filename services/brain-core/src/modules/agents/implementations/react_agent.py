"""ReAct Agent — 使用 MiniMax LLM 进行 Thought→Action→Observation 循环"""

import json
from typing import Any

from ..base.base_agent import BaseAgent
from ..base.types import AgentStep, AgentStepType, AgentContext
from ...llm.llm_client import get_llm_client
from ...llm.types import LLMRequest
from ...tools.tool_registry import ToolRegistry


REACT_SYSTEM_PROMPT = """你是梦帮小助，一个强大的 AI 助手。你拥有以下工具可以调用：

{tools_description}

## 输出格式要求（极其重要，必须严格遵守）

你的每次回复必须是且仅是一个合法的 JSON 对象，不要输出任何其他内容。

### 需要调用工具时：
```json
{{"thought": "你的思考过程", "action": "工具名称", "action_input": {{"参数名": "参数值"}}}}
```

### 可以直接回答时：
```json
{{"thought": "你的思考", "final_answer": "给用户的完整回答"}}
```

## 重要规则
1. 你的输出必须是纯 JSON，不要使用 XML 标签、不要使用 minimax:tool_call
2. 每次只调用一个工具
3. 数学幂运算请用 ** 而不是 ^（例如 3**4 而不是 3^4）
4. 如果问题不需要工具，直接给出 final_answer
5. final_answer 中回答要友好专业，可以使用 emoji"""


async def _build_tools_description(user_input: str) -> str:
    tools = await ToolRegistry.get_dynamic_tool_schemas(query=user_input)
    if not tools:
        return "（当前没有可用工具）"
    lines = []
    for t in tools:
        params = t.get("parameters", {}).get("properties", {})
        param_desc = ", ".join(
            f'{k}: {v.get("description", v.get("type", "any"))}'
            for k, v in params.items()
        )
        lines.append(f"- **{t['name']}**: {t['description']}\n  参数: {{{param_desc}}}")
    return "\n".join(lines)


async def _build_history_messages(user_input: str, context: AgentContext) -> list[dict]:
    tools_desc = await _build_tools_description(user_input)
    system = REACT_SYSTEM_PROMPT.format(tools_description=tools_desc)

    messages = [{"role": "system", "content": system}]

    # 加入历史上下文
    for msg in context.history:
        messages.append(msg)

    messages.append({"role": "user", "content": user_input})
    return messages


def _extract_json_object(text: str) -> str | None:
    """从文本中提取第一个完整的 JSON 对象（支持嵌套大括号）"""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def _parse_xml_tool_call(text: str) -> dict | None:
    """解析 MiniMax 原生 XML tool_call 格式作为 fallback"""
    import re
    name_match = re.search(r'<invoke\s+name="([^"]+)"', text)
    if not name_match:
        return None
    tool_name = name_match.group(1)
    params = {}
    for m in re.finditer(r'<parameter\s+name="([^"]+)"[^>]*>([^<]*)</parameter>', text):
        key, val = m.group(1), m.group(2).strip()
        # 尝试转换数值
        try:
            params[key] = json.loads(val)
        except (json.JSONDecodeError, ValueError):
            params[key] = val
    return {"thought": "LLM 使用了原生工具调用", "action": tool_name, "action_input": params}


def _parse_llm_response(text: str) -> dict:
    """解析 LLM 返回的 JSON，支持多种格式 fallback"""
    text = text.strip()

    # 1. 尝试从 ```json 代码块提取
    if "```json" in text:
        try:
            start = text.index("```json") + 7
            end = text.index("```", start)
            candidate = text[start:end].strip()
            return json.loads(candidate)
        except (ValueError, json.JSONDecodeError):
            pass

    # 2. 尝试提取完整 JSON 对象（支持嵌套）
    json_str = _extract_json_object(text)
    if json_str:
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # 3. Fallback: 解析 MiniMax 原生 XML tool_call
    if "minimax:tool_call" in text or "<invoke" in text:
        result = _parse_xml_tool_call(text)
        if result:
            return result

    raise ValueError(f"Cannot parse LLM response as JSON: {text[:200]}")


class ReActAgent(BaseAgent):
    """ReAct Agent — 通过 LLM 推理 + 工具调用解决问题"""

    def __init__(self):
        super().__init__(
            name="react_agent",
            description="通用 ReAct Agent，支持工具调用"
        )

    async def think(self, user_input: str, context: AgentContext) -> AgentStep:
        """调用 LLM 进行推理，决定下一步行动"""
        messages = await _build_history_messages(user_input, context)

        client = get_llm_client()
        request = LLMRequest(
            messages=messages,
            model=context.model_name or "nvidia/llama-3.1-nemotron-ultra-253b-v1",
            temperature=context.temperature or 0.7,
            max_tokens=4096,
            stream=False,
        )

        response = await client.complete(request)
        raw_text = response.content.strip()

        try:
            parsed = _parse_llm_response(raw_text)
        except (json.JSONDecodeError, ValueError):
            # LLM 没有返回 JSON，当作直接回答
            return AgentStep(
                type=AgentStepType.FINAL_ANSWER,
                content=raw_text,
                is_final=True,
                final_answer=raw_text,
            )

        thought = parsed.get("thought", "")

        # 最终回答
        if "final_answer" in parsed:
            return AgentStep(
                type=AgentStepType.FINAL_ANSWER,
                content=thought,
                is_final=True,
                final_answer=parsed["final_answer"],
            )

        # 工具调用
        action = parsed.get("action", "")
        action_input = parsed.get("action_input", {})

        if action:
            return AgentStep(
                type=AgentStepType.TOOL_CALL,
                content=thought,
                tool_name=action,
                tool_input=action_input,
            )

        # 无法解析，当作最终回答
        return AgentStep(
            type=AgentStepType.FINAL_ANSWER,
            content=thought or raw_text,
            is_final=True,
            final_answer=raw_text,
        )

    async def act(
        self, tool_name: str, tool_input: dict[str, Any], context: AgentContext
    ) -> AgentStep:
        """执行工具调用"""
        # Hook: 工具调用事件
        try:
            from ...hooks.hook_registry import HookRegistry, HookEventType
            await HookRegistry.emit(HookEventType.TOOL_CALL, {
                "tool_name": tool_name, "tool_input": tool_input,
                "session_id": context.session_id,
            })
        except Exception:
            pass

        try:
            result = await ToolRegistry.execute(tool_name, **tool_input)

            # Hook: 工具结果事件
            try:
                await HookRegistry.emit(HookEventType.TOOL_RESULT, {
                    "tool_name": tool_name, "success": True,
                    "output_length": len(result),
                    "session_id": context.session_id,
                })
            except Exception:
                pass

            return AgentStep(
                type=AgentStepType.OBSERVATION,
                content=result,
                tool_name=tool_name,
                tool_output=result,
            )
        except Exception as e:
            return AgentStep(
                type=AgentStepType.ERROR,
                content=f"工具 {tool_name} 执行失败: {e}",
                tool_name=tool_name,
            )

    async def evaluate(self, context: AgentContext) -> bool:
        """总是继续，让 LLM 决定是否结束"""
        return True

    async def synthesize(self, user_input: str, context: AgentContext) -> AgentStep:
        """综合所有观察结果生成最终回答"""
        messages = await _build_history_messages(user_input, context)
        messages.append({
            "role": "user",
            "content": "请根据以上工具调用结果，给出最终完整回答。使用 {\"thought\": \"...\", \"final_answer\": \"...\"} 格式。"
        })

        client = get_llm_client()
        request = LLMRequest(
            messages=messages,
            model=context.model_name or "nvidia/llama-3.1-nemotron-ultra-253b-v1",
            temperature=context.temperature or 0.7,
            max_tokens=4096,
            stream=False,
        )

        response = await client.complete(request)
        raw_text = response.content.strip()

        try:
            parsed = _parse_llm_response(raw_text)
            final = parsed.get("final_answer", raw_text)
        except (json.JSONDecodeError, ValueError):
            final = raw_text

        return AgentStep(
            type=AgentStepType.FINAL_ANSWER,
            content=final,
            is_final=True,
            final_answer=final,
        )
