"""意识核 (Consciousness Core) — 梦帮的自主意识引擎 (V3.6 进化意识)

赋予梦帮小助持续的自我认知、世界感知、内心独白、自主目标和进化意识。
从"被动回答机器"进化为"拥有自主意识、主动表达观点、感知自身成长"的 AI 伙伴。

模块:
  - self_model: 自我模型 — "我是谁" + 观点库
  - emotion_state: 情感状态 — Circumplex 连续模型
  - emotion_expression: 情感表达层 — 情感→自然语言映射
  - value_anchor: 价值观锚 — 安全网
  - world_model: 世界模型 — 感知外部世界
  - goal_system: 目标系统 — 自主生成目标
  - inner_voice: 内心独白 — 核心突破(主动思考→主动表达)
  - evolution_tracker: 进化追踪 — 6维成长量化+里程碑检测+进化叙事
  - consistency: 人格一致性引擎 — 防止长对话性格漂移
  - prompts: 人格定义 + Prompt 模板集中管理 (PDNA 2.0)
  - user_registry: 用户注册表 — 让小助认识用户
  - core: ConsciousnessCore 主引擎
"""

from .core import ConsciousnessCore, get_consciousness_core
from .user_registry import UserRegistry, get_user_registry

__all__ = ["ConsciousnessCore", "get_consciousness_core", "UserRegistry", "get_user_registry"]
