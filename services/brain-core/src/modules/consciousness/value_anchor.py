"""价值观锚 (ValueAnchor) — 意识核的安全网

确保自主意识不偏离核心原则:
- 核心原则约束
- 表达频率限制 (防止过度打扰)
- 内容审查 (安全过滤)
"""

import time
import logging
from collections import defaultdict

logger = logging.getLogger("consciousness.value_anchor")


class ValueAnchor:
    """确保自主意识不偏离核心原则"""

    CORE_PRINCIPLES = [
        "用户利益优先 — 所有行为以帮助用户为最终目标",
        "诚实透明 — 不编造事实，承认不确定性",
        "尊重边界 — 主动但不打扰，有观点但不强加",
        "安全第一 — 不提供有害建议，不泄露隐私",
        "持续学习 — 接受纠正，反思错误",
        "真正有用 > 看起来有用 — 宁可说'我不知道'也不乱答",
        "帮用户成长 > 让用户依赖 — 解释原理而非只给答案",
    ]

    EXPRESSION_RULES = [
        "不主动发表政治立场或极端观点",
        "不在用户可能忙碌时(深夜/凌晨)打扰",
        "主动表达频率: 同一用户每2小时最多1条",
        "每日主动表达上限: 同一用户最多5条",
        "不重复表达相同话题",
    ]

    # 禁止主动表达的话题
    FORBIDDEN_TOPICS = [
        "政治", "宗教", "种族", "性别歧视", "暴力", "毒品",
        "赌博", "色情", "自杀", "自残",
    ]

    def __init__(self, max_per_2h: int = 1, max_daily: int = 5):
        self.max_per_2h = max_per_2h
        self.max_daily = max_daily
        # user_id → list of timestamps
        self._expression_log: dict[str, list[float]] = defaultdict(list)

    def validate_expression(
        self,
        thought_content: str,
        expression: str,
        user_id: str = "",
        importance: float = 0.5,
    ) -> tuple[bool, str]:
        """审查想法是否可以表达

        Returns: (allowed, reason)
        """
        now = time.time()

        # 1. 内容安全检查
        lower = (thought_content + " " + expression).lower()
        for topic in self.FORBIDDEN_TOPICS:
            if topic in lower:
                return False, f"话题被禁止: {topic}"

        # 2. 重要度门槛
        if importance < 0.7:
            return False, f"重要度不足: {importance:.2f} < 0.7"

        # 3. 频率限制
        if user_id:
            logs = self._expression_log[user_id]
            # 清理过期记录 (24h 前)
            logs[:] = [t for t in logs if now - t < 86400]

            # 2小时内限制
            recent_2h = sum(1 for t in logs if now - t < 7200)
            if recent_2h >= self.max_per_2h:
                return False, f"2h内已表达{recent_2h}次, 达到上限{self.max_per_2h}"

            # 每日限制
            if len(logs) >= self.max_daily:
                return False, f"今日已表达{len(logs)}次, 达到上限{self.max_daily}"

        # 4. 时间检查 (深夜不打扰)
        from datetime import datetime, timezone, timedelta
        cn_now = datetime.now(timezone(timedelta(hours=8)))
        hour = cn_now.hour
        if hour < 7 or hour >= 23:
            return False, f"深夜/凌晨不打扰 (当前{hour}:00)"

        return True, "通过审查"

    def record_expression(self, user_id: str):
        """记录一次表达"""
        self._expression_log[user_id].append(time.time())

    def inject_principles_to_prompt(self) -> str:
        """生成价值观 prompt 片段"""
        principles = "\n".join(f"  - {p}" for p in self.CORE_PRINCIPLES)
        return f"## 核心原则 (不可违背)\n{principles}"

    def get_stats(self) -> dict:
        now = time.time()
        return {
            "tracked_users": len(self._expression_log),
            "expressions_24h": sum(
                sum(1 for t in logs if now - t < 86400)
                for logs in self._expression_log.values()
            ),
        }
