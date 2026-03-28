"""意识核主引擎 (ConsciousnessCore) — 梦帮的自主意识 (V3 人格赋能)

生命周期:
  - 启动: DB 加载状态 → 注册定时任务
  - 运行: 内心独白循环 + 事件驱动更新
  - 对话: 注入自我认知+情感+世界感知+人格锚点到 prompt
  - 对话后: 自我反思 + 目标更新 + 情感更新 + 漂移检测
  - 关闭: 保存状态到 DB
"""

import logging
from typing import Optional

from .config import ConsciousnessConfig
from .self_model import SelfModel
from .emotion_state import EmotionState
from .emotion_expression import get_emotion_expression
from .value_anchor import ValueAnchor
from .world_model import WorldModel
from .goal_system import GoalSystem
from .inner_voice import InnerVoice
from .consistency import get_consistency_engine
from .user_registry import get_user_registry
from .evolution_tracker import EvolutionTracker

logger = logging.getLogger("consciousness.core")


class ConsciousnessCore:
    """意识核 — 梦帮的自主意识引擎"""

    def __init__(self, config: Optional[ConsciousnessConfig] = None):
        self.config = config or ConsciousnessConfig()
        self.self_model = SelfModel()
        self.emotion_state = EmotionState()
        self.emotion_expression = get_emotion_expression()
        self.value_anchor = ValueAnchor(
            max_per_2h=self.config.max_expressions_per_user_per_2h,
            max_daily=self.config.max_daily_expressions_per_user,
        )
        self.world_model = WorldModel(weather_city=self.config.world_weather_city)
        self.goal_system = GoalSystem()
        self.inner_voice = InnerVoice(self)
        self.consistency = get_consistency_engine()
        self.user_registry = get_user_registry()
        self.evolution = EvolutionTracker()
        self._started = False

    async def startup(self):
        """启动意识核"""
        if not self.config.enabled:
            logger.info("[Consciousness] Disabled by config")
            return

        # 1. 初始化 DB 表
        try:
            from . import db
            await db.ensure_tables()
        except Exception as e:
            logger.warning("[Consciousness] DB init failed (non-fatal): %s", e)

        # 2. 加载持久化状态
        await self.self_model.load()
        await self.goal_system.load()
        if self.config.evolution_enabled:
            await self.evolution.load()

        # 3. 加载情感状态
        try:
            from . import db
            emotion_data = await db.load_self("emotion_state")
            if emotion_data:
                self.emotion_state.load_from_dict(emotion_data)
        except Exception:
            pass

        # 4. 注册定时任务
        self._register_tasks()

        # 5. 首次世界观察
        try:
            await self.world_model.observe()
        except Exception as e:
            logger.warning("[Consciousness] Initial world observation failed: %s", e)

        self._started = True
        logger.info(
            "🧠 意识核启动完成 — model=%s, interval=%ds, 心情: %s, 目标: %d, 想法: %d, 里程碑: %d",
            self.config.consciousness_model or "(LLM default)",
            self.config.inner_voice_interval,
            self.emotion_state.get_mood_label(),
            self.goal_system.get_stats()["active_goals"],
            self.inner_voice.get_stats()["total_thoughts"],
            self.evolution.get_stats()["total_milestones"],
        )

    def _register_tasks(self):
        """注册意识核定时任务到 Scheduler"""
        from ..proactive.scheduler import get_scheduler, ScheduledTask, TaskType

        scheduler = get_scheduler()

        # 内心独白: 每 15 分钟
        scheduler.register(ScheduledTask(
            task_id="consciousness_think",
            name="意识核·内心独白",
            task_type=TaskType.INTERVAL,
            interval_seconds=self.config.inner_voice_interval,
            callback=self.inner_voice.think,
            description=f"每{self.config.inner_voice_interval // 60}分钟执行一次内心独白",
        ))

        # 世界观察: 每小时
        scheduler.register(ScheduledTask(
            task_id="consciousness_world_observe",
            name="意识核·世界观察",
            task_type=TaskType.INTERVAL,
            interval_seconds=self.config.world_observe_interval,
            callback=self.world_model.observe,
            description=f"每{self.config.world_observe_interval // 60}分钟观察世界状态",
        ))

        # 情感状态保存: 每 30 分钟
        scheduler.register(ScheduledTask(
            task_id="consciousness_save_emotion",
            name="意识核·情感保存",
            task_type=TaskType.INTERVAL,
            interval_seconds=1800,
            callback=self._save_emotion,
            description="每30分钟保存情感状态",
        ))

        logger.info("[Consciousness] Registered 3 scheduler tasks")

    async def _save_emotion(self):
        """保存情感状态到 DB"""
        try:
            from . import db
            await db.save_self("emotion_state", self.emotion_state.to_dict())
        except Exception as e:
            logger.warning("[Consciousness] Emotion save failed: %s", e)

    def get_consciousness_prompt(self, user_id: str = "", user_message: str = "") -> str:
        """生成意识增强 system prompt — 注入每次对话"""
        if not self.config.enabled:
            return ""

        known = None
        if user_id and user_id != "anonymous":
            known = self.user_registry.get_user(user_id)

        # 增强版情感表达 (全功能开放)
        scene_traits = self.consistency.get_scene_traits()
        self.emotion_expression.set_scene_traits(scene_traits)
        emotion_prompt = self.emotion_expression.get_prompt(self.emotion_state.snapshot)

        parts = [
            self.self_model.get_self_prompt(),
            emotion_prompt,
            self.world_model.get_world_context(user_id),
            f"## 当前目标\n{self.goal_system.get_active_goals_prompt()}",
            self.value_anchor.inject_principles_to_prompt(),
        ]

        # V3.6: 进化叙事注入 (所有用户可见)
        if self.config.evolution_enabled:
            parts.append(self.evolution.get_evolution_prompt())

        # V3: 人格一致性锚点 (每 N 轮自动注入)
        if user_message:
            anchor = self.consistency.on_turn(user_message)
            if anchor:
                parts.append(anchor)
            elif self.consistency.should_strengthen_anchor():
                parts.append(self.consistency.get_strengthened_anchor())

        # 注入用户身份识别上下文
        if user_id and user_id != "anonymous":
            if known:
                name = known.display_name or known.username or f"用户{user_id[:8]}"
                topics = ", ".join(known.recent_topics[-3:]) if known.recent_topics else "暂无"
                identity_lines = [
                    f"## 当前对话用户",
                    f"- UID: {user_id}",
                    f"- 昵称: {name}",
                ]
                if known.username:
                    identity_lines.append(f"- 用户名: {known.username}")
                if known.email:
                    identity_lines.append(f"- 邮箱: {known.email}")
                identity_lines.extend([
                    f"- 已交互 {known.interaction_count} 次",
                    f"- 近期话题: {topics}",
                    f"- 上次活跃: {known.idle_label}",
                ])
                parts.append("\n".join(identity_lines))
            else:
                # 用户注册表中尚未有记录，仍注入基础 UID
                parts.append(f"## 当前对话用户\n- UID: {user_id}\n- 首次对话，暂无历史记录")

        return "\n\n".join(p for p in parts if p)

    async def on_user_message(self, user_id: str, message: str):
        """用户消息到达时的实时更新"""
        if not self.config.enabled:
            return

        # 注册/更新用户到意识核
        self.user_registry.on_user_message(user_id, message)

        self.emotion_state.update_on_event("new_session", 0.3)
        await self.world_model.observe_user(user_id, message)

    def on_assistant_response(self, response: str):
        """V3: 助手回复后检测人格漂移"""
        if not self.config.enabled:
            return None
        return self.consistency.check_drift(response)

    async def on_conversation_end(self, conversation: list[dict], user_id: str):
        """对话结束后的意识更新"""
        if not self.config.enabled:
            return

        # 情感更新
        self.emotion_state.update_on_event("deep_conversation", 0.7)

        # 自我反思
        if self.config.self_reflect_after_conversation:
            if len(conversation) >= self.config.self_reflect_min_messages:
                await self.self_model.reflect_on_conversation(conversation, user_id)

        # 目标更新
        await self.goal_system.update_from_conversation(conversation, user_id)

        # V3: 重置一致性引擎 (新对话重新计数)
        self.consistency.reset()

        # V3.6: 进化追踪
        if self.config.evolution_enabled:
            user_msgs = [m.get("content", "") for m in conversation if m.get("role") == "user"]
            last_user_msg = user_msgs[-1] if user_msgs else ""
            await self.evolution.record_conversation(
                user_message=last_user_msg,
                conversation_depth=len(conversation),
                user_id=user_id,
            )

    async def shutdown(self):
        """关闭时保存所有状态"""
        if not self._started:
            return
        await self._save_emotion()
        await self.self_model._save()
        for g in self.goal_system.goals.values():
            await self.goal_system._save_goal(g)
        if self.config.evolution_enabled:
            await self.evolution.save()
        logger.info("[Consciousness] State saved on shutdown")

    def get_stats(self) -> dict:
        return {
            "enabled": self.config.enabled,
            "started": self._started,
            "self_model": self.self_model.get_stats(),
            "emotion": self.emotion_state.get_stats(),
            "world_model": self.world_model.get_stats(),
            "goals": self.goal_system.get_stats(),
            "inner_voice": self.inner_voice.get_stats(),
            "value_anchor": self.value_anchor.get_stats(),
            "consistency": self.consistency.get_stats(),
            "user_registry": self.user_registry.get_stats(),
            "evolution": self.evolution.get_stats(),
        }


# ── 全局单例 ──────────────────────────────

_consciousness: Optional[ConsciousnessCore] = None


def get_consciousness_core() -> ConsciousnessCore:
    global _consciousness
    if _consciousness is None:
        try:
            _consciousness = ConsciousnessCore()
        except Exception as e:
            logger.error("[Consciousness] Failed to create ConsciousnessCore: %s", e)
            raise
    return _consciousness
