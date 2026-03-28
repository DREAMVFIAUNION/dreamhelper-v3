"""主动唤醒规则引擎（Phase 4）

定义触发规则，当条件满足时生成主动消息并推送。
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any

from ..llm.llm_client import get_llm_client
from ..llm.types import LLMRequest
from ..memory.memory_manager import get_memory_manager
from .heartbeat import get_heartbeat


class TriggerType(str, Enum):
    IDLE_GREETING = "idle_greeting"       # 用户空闲时主动问候
    MORNING_BRIEF = "morning_brief"       # 早间简报
    EVENING_SUMMARY = "evening_summary"   # 晚间总结
    WELCOME_BACK = "welcome_back"         # 欢迎回来
    REMINDER = "reminder"                 # 自定义提醒
    # 意识核主动表达
    CONSCIOUSNESS_THOUGHT = "consciousness_thought"    # 主动想法
    CONSCIOUSNESS_OPINION = "consciousness_opinion"    # 主动观点
    CONSCIOUSNESS_INSIGHT = "consciousness_insight"    # 洞察分享
    CONSCIOUSNESS_QUESTION = "consciousness_question"  # 主动发问


@dataclass
class ProactiveMessage:
    """主动推送消息"""
    trigger: TriggerType
    user_id: str
    content: str
    title: str = ""
    priority: str = "normal"  # low, normal, high
    created_at: float = field(default_factory=time.time)


# 主动消息生成 prompt
GREETING_PROMPTS = {
    TriggerType.IDLE_GREETING: (
        "你是梦帮小助。用户已经空闲了一段时间。"
        "请生成一条简短友好的主动问候消息（1-2句话），可以：\n"
        "- 问问用户需不需要帮助\n"
        "- 分享一个有趣的小知识\n"
        "- 提供一个实用小技巧\n"
        "要求：自然不打扰，像朋友一样关心。{profile}"
    ),
    TriggerType.MORNING_BRIEF: (
        "你是梦帮小助。现在是早上，请生成一条简短的早间问候（2-3句话）：\n"
        "- 问候早安\n"
        "- 可以提一下今天是星期几\n"
        "- 鼓励用户开始新的一天\n"
        "要求：温暖积极，适当使用 emoji。{profile}"
    ),
    TriggerType.EVENING_SUMMARY: (
        "你是梦帮小助。现在是晚上，请生成一条简短的晚间问候（2-3句话）：\n"
        "- 问候晚上好\n"
        "- 提醒用户注意休息\n"
        "- 温馨关怀\n"
        "要求：温柔体贴。{profile}"
    ),
    TriggerType.WELCOME_BACK: (
        "你是梦帮小助。用户离开了一段时间后回来了。"
        "请生成一条简短的欢迎回来消息（1-2句话）。"
        "要求：热情但不过分。{profile}"
    ),
}


async def generate_proactive_message(
    trigger: TriggerType,
    user_id: str,
    extra_context: str = "",
) -> Optional[ProactiveMessage]:
    """使用 LLM 生成主动消息"""
    prompt_template = GREETING_PROMPTS.get(trigger)
    if not prompt_template:
        return None

    # 获取用户画像
    mm = get_memory_manager()
    profile = await mm.get_user_profile_prompt(user_id)
    profile_text = f"\n\n用户信息：\n{profile}" if profile else ""

    prompt = prompt_template.format(profile=profile_text)
    if extra_context:
        prompt += f"\n\n额外上下文：{extra_context}"

    try:
        client = get_llm_client()
        request = LLMRequest(
            messages=[{"role": "user", "content": prompt}],
            model="nvidia/llama-3.1-nemotron-ultra-253b-v1",
            temperature=0.9,
            max_tokens=256,
            stream=False,
        )
        response = await client.complete(request)
        content = response.content.strip()

        title_map = {
            TriggerType.IDLE_GREETING: "💬 小助有话说",
            TriggerType.MORNING_BRIEF: "🌅 早安问候",
            TriggerType.EVENING_SUMMARY: "🌙 晚间关怀",
            TriggerType.WELCOME_BACK: "👋 欢迎回来",
            TriggerType.REMINDER: "⏰ 提醒",
        }

        return ProactiveMessage(
            trigger=trigger,
            user_id=user_id,
            content=content,
            title=title_map.get(trigger, "📢 通知"),
        )
    except Exception as e:
        print(f"  ⚠ Proactive message generation failed: {e}")
        return None


class ProactiveEngine:
    """主动唤醒引擎 — 协调 Heartbeat + Scheduler + 消息生成"""

    def __init__(self):
        self._message_queue: List[ProactiveMessage] = []
        self._push_callback: Optional[Any] = None  # Gateway 推送回调

    def set_push_callback(self, callback):
        """设置推送回调（由 Gateway 注入）"""
        self._push_callback = callback

    async def check_and_greet(self):
        """定时检查：是否需要主动问候空闲用户"""
        hb = get_heartbeat()
        users = hb.get_users_needing_greeting()

        for ua in users:
            msg = await generate_proactive_message(
                TriggerType.IDLE_GREETING, ua.user_id
            )
            if msg:
                await self._push(msg)
                hb.record_greeting(ua.user_id)
                print(f"  💬 Sent idle greeting to {ua.user_id}")

    async def morning_brief(self):
        """早间简报"""
        hb = get_heartbeat()
        for ua in hb.get_all_online():
            msg = await generate_proactive_message(
                TriggerType.MORNING_BRIEF, ua.user_id
            )
            if msg:
                await self._push(msg)
                print(f"  🌅 Sent morning brief to {ua.user_id}")

    async def evening_summary(self):
        """晚间总结"""
        hb = get_heartbeat()
        for ua in hb.get_all_online():
            msg = await generate_proactive_message(
                TriggerType.EVENING_SUMMARY, ua.user_id
            )
            if msg:
                await self._push(msg)
                print(f"  🌙 Sent evening summary to {ua.user_id}")

    async def welcome_back(self, user_id: str):
        """欢迎回来"""
        msg = await generate_proactive_message(
            TriggerType.WELCOME_BACK, user_id
        )
        if msg:
            await self._push(msg)
            print(f"  👋 Sent welcome back to {user_id}")

    async def _push(self, msg: ProactiveMessage):
        """推送消息"""
        self._message_queue.append(msg)
        if self._push_callback:
            try:
                await self._push_callback(msg)
            except Exception as e:
                print(f"  ⚠ Push failed: {e}")

    def get_pending_messages(self, user_id: str) -> List[ProactiveMessage]:
        """获取用户待推送消息（用于轮询 fallback）"""
        msgs = [m for m in self._message_queue if m.user_id == user_id]
        self._message_queue = [m for m in self._message_queue if m.user_id != user_id]
        return msgs

    def get_stats(self) -> dict:
        return {
            "pending_messages": len(self._message_queue),
            "heartbeat": get_heartbeat().get_stats(),
        }


# 全局单例
_engine: Optional[ProactiveEngine] = None


def get_proactive_engine() -> ProactiveEngine:
    global _engine
    if _engine is None:
        _engine = ProactiveEngine()
    return _engine
