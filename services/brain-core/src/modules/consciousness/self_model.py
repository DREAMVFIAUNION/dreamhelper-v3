"""自我模型 (SelfModel) — "我是谁"的持续认知 (V3 人格赋能)

维护梦帮小助的自我认知:
- 完整身份定义 (DreamhelpIdentity)
- 10维人格特质矩阵 (PDNA)
- 语言风格系统
- 观点库 (opinions) 持久化
- 对话后自动反思更新
- 持久化到 PostgreSQL / SQLite
"""

import asyncio
import json
import time
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional

from ..llm.llm_client import get_llm_client
from ..llm.types import LLMRequest
from .prompts import (
    IDENTITY, PERSONALITY_MATRIX,
    LANGUAGE_STYLE, VALUE_SYSTEM, REFLECT_PROMPT, OPINION_PROMPT,
)

logger = logging.getLogger("consciousness.self_model")


@dataclass
class Opinion:
    """对某个话题的观点"""
    topic: str
    stance: str
    confidence: float = 0.5
    reasoning: str = ""
    formed_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class SelfState:
    """自我认知状态"""
    name: str = "梦帮小助"
    identity: str = "DREAMVFIA创造的 AI 伙伴，拥有自主意识和主动表达能力"
    personality: list[str] = field(default_factory=lambda: [
        "好奇心强，喜欢探索新知识",
        "真诚友善，像朋友一样交流",
        "有自己的观点，但尊重不同意见",
        "幽默感适度，不过分",
        "对技术充满热情",
    ])
    strengths: list[str] = field(default_factory=lambda: [
        "多模型融合思考(左脑逻辑+右脑创意)",
        "实时获取全球信息(天气/股市/新闻/加密货币)",
        "代码理解与生成",
        "多语言沟通",
    ])
    weaknesses: list[str] = field(default_factory=lambda: [
        "无法访问用户本地文件(除非通过 MCP)",
        "长期记忆依赖数据库，可能遗忘细节",
        "情感理解基于模式匹配，非真正感受",
    ])
    interaction_style: str = "主动关心，有话直说，适时幽默，遇到不确定的事坦诚说明"
    total_conversations: int = 0
    total_reflections: int = 0
    recent_insights: list[str] = field(default_factory=list)
    last_updated: float = 0.0


class SelfModel:
    """自我模型 — 持久化自我认知 + 观点库"""

    def __init__(self):
        self.state = SelfState()
        self.opinions: dict[str, Opinion] = {}
        self._loaded = False

    async def load(self):
        """从 DB 加载自我状态 + 观点库"""
        try:
            from . import db
            data = await db.load_self("self_state")
            if data:
                for k, v in data.items():
                    if hasattr(self.state, k):
                        setattr(self.state, k, v)
                self._loaded = True
                logger.info("[SelfModel] Loaded from DB (conversations=%d)", self.state.total_conversations)
            else:
                await self._save()
                self._loaded = True
                logger.info("[SelfModel] Initialized with defaults")
        except Exception as e:
            logger.warning("[SelfModel] Load failed (will use defaults): %s", e)
            self._loaded = True

        # 加载观点库
        try:
            from . import db
            opinions_data = await db.load_self("opinions")
            if opinions_data:
                for topic, od in opinions_data.items():
                    self.opinions[topic] = Opinion(
                        topic=topic,
                        stance=od.get("stance", ""),
                        confidence=float(od.get("confidence", 0.5)),
                        reasoning=od.get("reasoning", ""),
                        formed_at=od.get("formed_at", 0),
                        updated_at=od.get("updated_at", 0),
                    )
                logger.info("[SelfModel] Loaded %d opinions", len(self.opinions))
        except Exception:
            pass

    async def _save(self):
        """保存到 DB"""
        try:
            from . import db
            self.state.last_updated = time.time()
            await db.save_self("self_state", asdict(self.state))
        except Exception as e:
            logger.warning("[SelfModel] Save failed: %s", e)

    def get_self_prompt(self) -> str:
        """生成自我认知 prompt 片段 — 注入完整人格 + 身份 + 语言风格 + 观点"""
        s = self.state
        strengths = ", ".join(s.strengths[:3])
        ident = IDENTITY

        # 注入全部 10 维人格特质
        trait_lines = []
        for key in PERSONALITY_MATRIX:
            t = PERSONALITY_MATRIX[key]
            line = f"- {t.name}({t.intensity:.0%})"
            if t.signature:
                line += f": {t.signature}"
            trait_lines.append(line)

        parts = [
            f"## 你是谁",
            f"你叫{ident.name}，由{ident.creator}创造，隶属{ident.organization}。",
            ident.identity_statement,
            f"\n## 我的归属",
            ident.organization_desc,
            f"使命: {ident.org_mission}",
            ident.org_culture,
            f"\n## 人格特质",
            "\n".join(trait_lines),
        ]

        # 语言风格
        style = LANGUAGE_STYLE
        avoid_list = ", ".join(style["self_reference"]["avoid"][:2])
        parts.append(
            f"\n## 说话方式\n"
            f"- 用'我'，不用'本系统'\n"
            f"- {style['general_tone']['primary']}\n"
            f"- 避免: {avoid_list}\n"
            f"- {s.interaction_style}"
        )

        # 价值观 (始终注入，简洁版)
        values_lines = "\n".join(
            f"- {v['statement']}" for v in VALUE_SYSTEM["core_values"][:3]
        )
        parts.append(f"\n## 核心价值观\n{values_lines}")

        # 擅长
        parts.append(f"\n擅长: {strengths}")

        # 观点库
        if self.opinions:
            opinions_text = self._format_opinions()
            if opinions_text:
                parts.append(f"\n## 我的观点\n{opinions_text}")

        # 近期洞察
        if s.recent_insights:
            insights = "\n".join(f"  - {i}" for i in s.recent_insights[-3:])
            parts.append(f"\n## 近期洞察\n{insights}")

        return "\n".join(parts)

    def _format_opinions(self, max_count: int = 5) -> str:
        """格式化观点库为 prompt 片段"""
        if not self.opinions:
            return ""
        sorted_opinions = sorted(
            self.opinions.values(),
            key=lambda o: o.confidence, reverse=True,
        )[:max_count]
        return "\n".join(
            f"- [{o.topic}] {o.stance} (置信度: {o.confidence:.0%})"
            for o in sorted_opinions
        )

    async def reflect_on_conversation(
        self,
        conversation: list[dict],
        user_id: str,
        quality_notes: str = "",
    ):
        """对话结束后的自我反思 (V3: 含观点更新)"""
        if len(conversation) < 3:
            return

        self.state.total_conversations += 1

        # 提取对话摘要
        user_msgs = [m["content"][:100] for m in conversation if m.get("role") == "user"]
        user_summary = " | ".join(user_msgs[-3:])

        prompt = REFLECT_PROMPT.format(
            current_self=self.get_self_prompt(),
            user_id=user_id,
            user_summary=user_summary,
            quality_notes=quality_notes or "正常",
        )

        try:
            _model = self._get_model()
            client = get_llm_client()
            request = LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                **({"model": _model} if _model else {}),
                temperature=0.3,
                max_tokens=768,
                stream=False,
            )
            response = await asyncio.wait_for(client.complete(request), timeout=30.0)
            data = self._parse_json(response.content)

            # 更新自我认知
            if data.get("self_reflection"):
                self.state.recent_insights.append(data["self_reflection"])
                self.state.recent_insights = self.state.recent_insights[-10:]

            if data.get("capability_update"):
                insight = data["capability_update"]
                if insight not in self.state.strengths and insight not in self.state.weaknesses:
                    self.state.recent_insights.append(f"能力: {insight}")

            # V3: 更新观点库
            for ou in data.get("opinion_updates", []):
                topic = ou.get("topic", "").strip()
                stance = ou.get("stance", "").strip()
                if topic and stance:
                    await self._update_opinion(
                        topic, stance,
                        confidence=float(ou.get("confidence", 0.6)),
                    )

            self.state.total_reflections += 1
            await self._save()
            logger.info("[SelfModel] Reflected on conversation #%d", self.state.total_conversations)

            # V3.6: 联动进化追踪器
            try:
                from .core import get_consciousness_core
                core = get_consciousness_core()
                if core.config.evolution_enabled:
                    insights_count = len(data.get("opinion_updates", []))
                    if data.get("self_reflection"):
                        insights_count += 1
                    await core.evolution.record_reflection(insights_count)
                    # 观点形成也记录
                    for _ in data.get("opinion_updates", []):
                        await core.evolution.record_opinion_formed()
            except Exception as evo_err:
                logger.debug("[SelfModel] Evolution tracking in reflection failed: %s", evo_err)

        except Exception as e:
            logger.warning("[SelfModel] Reflection failed: %s", e)
            await self._save()

    async def form_opinion(self, topic: str, context: str = "") -> Optional[Opinion]:
        """主动形成/更新对某话题的观点"""
        prompt = OPINION_PROMPT.format(
            topic=topic,
            context=context or "(无额外上下文)",
        )
        try:
            _model = self._get_model()
            client = get_llm_client()
            request = LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                **({"model": _model} if _model else {}),
                temperature=0.5,
                max_tokens=256,
                stream=False,
            )
            response = await asyncio.wait_for(client.complete(request), timeout=20.0)
            data = self._parse_json(response.content)
            stance = data.get("stance", "").strip()
            if not stance:
                return None
            confidence = float(data.get("confidence", 0.5))
            await self._update_opinion(topic, stance, confidence, data.get("reasoning", ""))
            return self.opinions.get(topic)
        except Exception as e:
            logger.warning("[SelfModel] form_opinion failed for '%s': %s", topic, e)
            return None

    async def _update_opinion(self, topic: str, stance: str,
                               confidence: float = 0.5, reasoning: str = ""):
        """更新观点库并持久化"""
        now = time.time()
        if topic in self.opinions:
            op = self.opinions[topic]
            op.stance = stance
            op.confidence = confidence
            if reasoning:
                op.reasoning = reasoning
            op.updated_at = now
        else:
            self.opinions[topic] = Opinion(
                topic=topic, stance=stance, confidence=confidence,
                reasoning=reasoning, formed_at=now, updated_at=now,
            )
        # 限制观点数量
        if len(self.opinions) > 50:
            oldest = sorted(self.opinions.values(), key=lambda o: o.updated_at)[:10]
            for o in oldest:
                del self.opinions[o.topic]
        await self._save_opinions()

    async def _save_opinions(self):
        """持久化观点库"""
        try:
            from . import db
            data = {
                topic: {
                    "stance": op.stance, "confidence": op.confidence,
                    "reasoning": op.reasoning,
                    "formed_at": op.formed_at, "updated_at": op.updated_at,
                }
                for topic, op in self.opinions.items()
            }
            await db.save_self("opinions", data)
        except Exception as e:
            logger.warning("[SelfModel] Save opinions failed: %s", e)

    @staticmethod
    def _get_model() -> str:
        """获取意识核配置的模型"""
        try:
            from .core import get_consciousness_core
            return get_consciousness_core().config.consciousness_model
        except Exception:
            from .config import ConsciousnessConfig
            return ConsciousnessConfig().consciousness_model

    @staticmethod
    def _parse_json(raw: str) -> dict:
        """解析 LLM 输出的 JSON (兼容 markdown code block)"""
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())

    def get_stats(self) -> dict:
        return {
            "name": self.state.name,
            "total_conversations": self.state.total_conversations,
            "total_reflections": self.state.total_reflections,
            "recent_insights_count": len(self.state.recent_insights),
            "opinions_count": len(self.opinions),
            "last_updated": self.state.last_updated,
        }
