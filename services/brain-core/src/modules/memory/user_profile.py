"""用户画像自动提取 — 从对话中提取用户信息/偏好（Phase 3）"""

import json
from typing import Optional

from ..llm.llm_client import get_llm_client
from ..llm.types import LLMRequest
from .memory_manager import get_memory_manager

EXTRACT_PROMPT_TEMPLATE = """你是一个信息提取助手。请从以下对话中提取用户的个人信息和偏好。

对话内容：
{conversation}

请提取以下类别的信息（如果对话中提到了的话）：
- name: 用户姓名
- nickname: 用户昵称
- occupation: 职业
- location: 所在地
- interests: 兴趣爱好
- tech_stack: 技术栈/编程语言
- preference_language: 语言偏好
- preference_style: 回答风格偏好（简洁/详细/幽默等）
- company: 公司/组织
- age: 年龄
- education: 学历
- other_facts: 其他重要信息

只提取对话中明确提到的信息，不要猜测。
返回 JSON 格式，只包含有值的字段，例如：
{{"name": "张三", "occupation": "工程师"}}
如果没有提取到任何信息，返回空 JSON：
{{}}"""


async def extract_user_facts(
    user_id: str,
    conversation: list[dict],
    session_id: str = "",
    model: str = "nvidia/llama-3.1-nemotron-ultra-253b-v1",
) -> dict[str, str]:
    """从对话中提取用户事实并存入长期记忆

    Args:
        user_id: 用户 ID
        conversation: 对话消息列表 [{"role": "user", "content": "..."}, ...]
        session_id: 来源会话 ID
        model: 使用的模型

    Returns:
        提取到的事实字典
    """
    if not conversation:
        return {}

    # 构建对话文本
    conv_text = "\n".join(
        f"{'用户' if m['role'] == 'user' else '助手'}: {m['content'][:200]}"
        for m in conversation[-10:]  # 最近 10 条
    )

    prompt = EXTRACT_PROMPT_TEMPLATE.format(conversation=conv_text)

    client = get_llm_client()
    request = LLMRequest(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        temperature=0.3,  # 低温度，更精确
        max_tokens=1024,
        stream=False,
    )

    try:
        response = await client.complete(request)
        raw = response.content.strip()

        # 提取 JSON
        if "```json" in raw:
            start = raw.index("```json") + 7
            end = raw.index("```", start)
            raw = raw[start:end].strip()
        elif "```" in raw:
            start = raw.index("```") + 3
            end = raw.index("```", start)
            raw = raw[start:end].strip()

        brace_start = raw.find("{")
        brace_end = raw.rfind("}")
        if brace_start != -1 and brace_end != -1:
            raw = raw[brace_start:brace_end + 1]

        facts = json.loads(raw)
        if not isinstance(facts, dict):
            return {}

        # 存入长期记忆
        mm = get_memory_manager()
        extracted = {}
        for key, value in facts.items():
            if value and isinstance(value, str) and value.strip():
                await mm.set_user_fact(
                    user_id=user_id,
                    key=key,
                    value=value.strip(),
                    source=session_id,
                )
                extracted[key] = value.strip()

        if extracted:
            print(f"  📝 Extracted {len(extracted)} user facts for {user_id}: {list(extracted.keys())}")

        return extracted

    except Exception as e:
        print(f"  ⚠ User fact extraction failed: {e}")
        return {}


async def should_extract(conversation: list[dict], min_messages: int = 4) -> bool:
    """判断是否应该触发用户画像提取

    条件：
    1. 对话至少 min_messages 条消息
    2. 用户消息中包含可能的个人信息关键词
    """
    if len(conversation) < min_messages:
        return False

    user_messages = " ".join(
        m["content"] for m in conversation if m["role"] == "user"
    ).lower()

    triggers = [
        "我是", "我叫", "我的名字", "我在", "我住", "我做", "我喜欢",
        "我的工作", "我的职业", "我学", "我用", "我写", "我的公司",
        "岁", "年级", "专业", "大学", "学校",
    ]

    return any(t in user_messages for t in triggers)
