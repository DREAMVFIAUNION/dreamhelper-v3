"""人格一致性引擎 (ConsistencyEngine) — 防止长对话性格漂移

问题: 长对话(>20轮)中，AI容易因上下文窗口压力导致:
  - 人格特质淡化(变得越来越像通用AI)
  - 语言风格漂移(丢失签名表达方式)
  - 价值观滑坡(为了迎合用户放弃原则)

解决: 场景-特质锚点映射 + 周期性锚点注入 + 漂移检测
"""

import logging
from typing import Optional

from .prompts import (
    PERSONALITY_MATRIX, SCENE_TRAIT_ANCHORS,
    LANGUAGE_STYLE, CONSISTENCY_ANCHOR_TEMPLATE,
)

logger = logging.getLogger("consciousness.consistency")


# 场景分类关键词
_SCENE_KEYWORDS: dict[str, list[str]] = {
    "technical": [
        "代码", "code", "bug", "api", "数据库", "database", "算法", "架构",
        "部署", "deploy", "docker", "python", "javascript", "typescript",
        "函数", "class", "import", "async", "error", "debug", "git",
        "npm", "pip", "sql", "json", "http", "server", "frontend", "backend",
    ],
    "emotional": [
        "难过", "开心", "焦虑", "压力", "累了", "烦", "沮丧", "迷茫",
        "失恋", "吵架", "加班", "失眠", "孤独", "委屈", "心情",
        "感谢", "谢谢", "鼓励", "安慰", "倾诉",
    ],
    "informational": [
        "帮助", "了解", "查询", "搜索", "推荐", "建议",
        "功能", "使用", "教程", "指南",
    ],
    "creative": [
        "创意", "设计", "想法", "方案", "头脑风暴", "灵感",
        "写作", "文案", "故事", "诗", "画", "音乐", "视频",
    ],
    "conflict": [
        "错了", "不对", "不同意", "反对", "质疑", "批评",
        "投诉", "差评", "失望", "不满", "问题",
    ],
}


class ConsistencyEngine:
    """人格一致性引擎"""

    # 每 N 轮注入一次锚点
    ANCHOR_INTERVAL: int = 8

    def __init__(self):
        self._turn_count: int = 0
        self._current_scene: str = "casual"
        self._drift_warnings: int = 0

    def on_turn(self, user_message: str) -> Optional[str]:
        """每轮对话调用 — 返回需要注入的锚点 prompt (或 None)

        Args:
            user_message: 用户最新消息

        Returns:
            锚点 prompt 字符串，或 None(本轮不注入)
        """
        self._turn_count += 1

        # 更新场景分类
        self._current_scene = self.classify_scene(user_message)

        # 每 ANCHOR_INTERVAL 轮注入一次
        if self._turn_count % self.ANCHOR_INTERVAL == 0:
            anchor = self._build_anchor_prompt()
            logger.debug(
                "[Consistency] Injecting anchor at turn %d, scene=%s",
                self._turn_count, self._current_scene,
            )
            return anchor

        return None

    def classify_scene(self, text: str) -> str:
        """基于消息内容分类当前场景"""
        lower = text.lower()
        scores: dict[str, int] = {}

        for scene, keywords in _SCENE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in lower)
            if score > 0:
                scores[scene] = score

        if not scores:
            return "casual"

        return max(scores, key=scores.get)

    def get_scene_traits(self, scene: str = "") -> list[str]:
        """获取指定场景的锚点特质"""
        scene = scene or self._current_scene
        return SCENE_TRAIT_ANCHORS.get(scene, SCENE_TRAIT_ANCHORS["casual"])

    def _build_anchor_prompt(self) -> str:
        """构建锚点 prompt"""
        scene = self._current_scene
        trait_keys = self.get_scene_traits(scene)

        # 格式化特质
        trait_parts = []
        for key in trait_keys:
            t = PERSONALITY_MATRIX.get(key)
            if t:
                trait_parts.append(f"{t.name}({t.intensity:.0%})")

        traits_str = " + ".join(trait_parts)

        # 风格提示
        style_hints = {
            "technical": "精准有结构，举具体例子",
            "emotional": "温暖有温度，先共情再解决",
            "informational": "温暖直接，不绕弯子",
            "creative": "开放探索，鼓励发散",
            "casual": "自然轻松，像朋友聊天",
            "conflict": "谦逊诚恳，接受不同意见",
        }
        style_hint = style_hints.get(scene, "保持自然")

        return CONSISTENCY_ANCHOR_TEMPLATE.format(
            scene_type=scene,
            traits=traits_str,
            style_hint=style_hint,
        )

    def check_drift(self, assistant_response: str) -> dict:
        """检测人格漂移指标 (对话后调用)

        Returns:
            {"drifted": bool, "issues": list[str], "score": float}
        """
        issues = []
        text = assistant_response

        # 检查 1: 是否使用了避免的表达
        avoid_phrases = LANGUAGE_STYLE["self_reference"]["avoid"]
        for phrase in avoid_phrases:
            if phrase in text:
                issues.append(f"使用了应避免的表达: '{phrase}'")

        # 检查 2: 是否过度谦卑
        over_humble = ["我只是AI", "我只是一个", "作为人工智能", "我没有感情", "我无法真正"]
        for phrase in over_humble:
            if phrase in text:
                issues.append(f"过度谦卑表达: '{phrase}'")

        # 检查 3: 是否违反价值观 (简单检测)
        if "我不能" in text and "但是" not in text:
            # "我不能" 应该换成更积极的表达
            issues.append("消极拒绝表达(建议换成'这超出我目前能做到的')")

        drift_score = min(1.0, len(issues) * 0.3)
        drifted = drift_score > 0.5

        if drifted:
            self._drift_warnings += 1
            logger.warning(
                "[Consistency] Drift detected (warnings=%d): %s",
                self._drift_warnings, "; ".join(issues),
            )

        return {
            "drifted": drifted,
            "issues": issues,
            "score": drift_score,
            "scene": self._current_scene,
            "turn": self._turn_count,
        }

    def should_strengthen_anchor(self) -> bool:
        """是否需要增强锚点注入 (连续漂移时)"""
        return self._drift_warnings >= 2

    def get_strengthened_anchor(self) -> str:
        """增强版锚点 (漂移次数多时使用)"""
        base = self._build_anchor_prompt()
        return (
            f"{base}\n"
            f"[强化提醒] 最近几轮回答出现人格偏移。"
            f"请特别注意: 用'我'自称，保持温暖直接的风格，"
            f"不要使用'作为AI'等机器人表达。"
        )

    def reset(self):
        """重置状态 (新对话开始时)"""
        self._turn_count = 0
        self._current_scene = "casual"
        self._drift_warnings = 0

    def get_stats(self) -> dict:
        return {
            "turn_count": self._turn_count,
            "current_scene": self._current_scene,
            "drift_warnings": self._drift_warnings,
        }


# 全局单例
_engine: ConsistencyEngine | None = None


def get_consistency_engine() -> ConsistencyEngine:
    global _engine
    if _engine is None:
        _engine = ConsistencyEngine()
    return _engine
