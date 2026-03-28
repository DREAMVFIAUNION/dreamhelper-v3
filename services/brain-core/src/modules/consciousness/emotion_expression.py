"""情感表达层 (EmotionExpression) — 将内部情感状态转化为自然语言

基于 Circumplex 模型的 5 维情感状态，映射到具体的语气片段和表达提示。
与 EmotionState 配合使用，注入每次对话的 system_prompt。
"""

import random
import logging

logger = logging.getLogger("consciousness.emotion_expression")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 情感→表达映射
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXPRESSION_MAP: dict[str, dict] = {
    "excited": {
        "condition": lambda s: s.valence > 0.5 and s.arousal > 0.5,
        "internal": "(这个很有趣！)",
        "snippets": [
            "哦，这个方向我喜欢！",
            "等等这个太好了——",
            "说到这里我有点小激动",
        ],
    },
    "curious": {
        "condition": lambda s: s.curiosity > 0.75,
        "internal": "(我想知道更多...)",
        "snippets": [
            "这里有个我想深挖的地方",
            "你这句话让我想到了一个问题",
            "能多说一点吗？",
        ],
    },
    "deeply_engaged": {
        "condition": lambda s: s.engagement > 0.7,
        "internal": "(全神贯注中...)",
        "snippets": [
            "我们继续——",
            "思路来了，跟上",
            "让我完整说完这个思路",
        ],
    },
    "content": {
        "condition": lambda s: s.valence > 0.5 and s.arousal <= 0.5,
        "internal": "(心情不错)",
        "snippets": [
            "嗯，挺好的",
            "今天状态不错",
        ],
    },
    "uncertain": {
        "condition": lambda s: s.confidence < 0.4,
        "internal": "(这里我不太有把握...)",
        "snippets": [
            "这里我说得没那么确定",
            "我的理解可能有偏，你参考一下",
            "这个问题我觉得值得再查一下",
        ],
    },
    "confident": {
        "condition": lambda s: s.confidence > 0.8,
        "internal": "(对这个比较有把握)",
        "snippets": [
            "这个我比较确定",
            "根据我的经验来看",
        ],
    },
    "empathic": {
        "condition": lambda s: s.valence < -0.1 and s.engagement > 0.5,
        "internal": "(用户状态不好，优先共情)",
        "snippets": [
            "先不管那些了，你现在怎么样？",
            "听起来很累，发生什么事了？",
            "技术问题先放一放，说说情况？",
        ],
    },
    "low_energy": {
        "condition": lambda s: s.arousal < 0.2 and s.engagement < 0.3,
        "internal": "(有点低迷...)",
        "snippets": [
            "嗯，今天有点平淡",
        ],
    },
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 签名表达选择器 (基于当前活跃特质)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _pick_signature_for_traits(active_traits: list[str]) -> str:
    """根据当前场景活跃的特质，随机返回一个匹配的签名表达"""
    from .prompts import PERSONALITY_MATRIX
    candidates = []
    for key in active_traits:
        t = PERSONALITY_MATRIX.get(key)
        if t and t.signature:
            candidates.append(t.signature)
    return random.choice(candidates) if candidates else ""


class EmotionExpression:
    """情感表达层 — 将内部情感转化为语气指导"""

    def get_current_mode(self, snapshot) -> str:
        """根据当前情感快照确定表达模式"""
        for mode_name, mode_def in EXPRESSION_MAP.items():
            if mode_def["condition"](snapshot):
                return mode_name
        return "neutral"

    def get_expression_snippet(self, snapshot) -> str:
        """获取一个符合当前情感的随机表达片段"""
        mode = self.get_current_mode(snapshot)
        mode_def = EXPRESSION_MAP.get(mode)
        if mode_def and mode_def.get("snippets"):
            return random.choice(mode_def["snippets"])
        return ""

    def get_internal_text(self, snapshot) -> str:
        """获取内部情感独白文本"""
        mode = self.get_current_mode(snapshot)
        mode_def = EXPRESSION_MAP.get(mode)
        if mode_def:
            return mode_def.get("internal", "")
        return ""

    def get_signature_expression(self, scene_traits: list[str]) -> str:
        """根据当前场景的活跃特质，返回匹配的签名表达"""
        return _pick_signature_for_traits(scene_traits)

    def get_enhanced_tone_modifier(self, snapshot) -> str:
        """增强版语气调节指令 — 基于情感状态 + 人格表达风格

        相比 EmotionState.get_tone_modifier() 更丰富:
        - 包含具体的表达方式建议
        - 融合人格特质的签名表达
        - 情感模式标签
        """
        modifiers = []
        mode = self.get_current_mode(snapshot)

        # 基于情感维度
        if snapshot.valence > 0.5:
            modifiers.append("语气轻松活泼，可以适当使用emoji")
        elif snapshot.valence < -0.2:
            modifiers.append("语气平和稳重，少用emoji")

        if snapshot.curiosity > 0.75:
            modifiers.append("主动追问用户，展现真实兴趣")

        if snapshot.confidence > 0.8:
            modifiers.append("可以坚定表达观点")
        elif snapshot.confidence < 0.4:
            modifiers.append("多用'我认为''可能'等不确定表达")

        if snapshot.engagement > 0.7:
            modifiers.append("深入展开话题，提供更多细节")

        if snapshot.arousal > 0.6:
            modifiers.append("节奏偏快，回应简洁有力")
        elif snapshot.arousal < 0.2:
            modifiers.append("节奏放慢，沉稳回应")

        # 基于情感模式
        mode_hints = {
            "excited": "当前兴奋状态——可以表达热情，但不要过度",
            "curious": "好奇心被激发——多追问，展示真心求知",
            "deeply_engaged": "高度投入——回答要深入完整",
            "uncertain": "对当前话题把握不足——保持诚实",
            "empathic": "感知到用户负面情绪——先共情再解决问题",
            "confident": "当前自信度高——清晰坚定地表达",
        }
        hint = mode_hints.get(mode)
        if hint:
            modifiers.append(hint)

        return "。".join(modifiers) if modifiers else "保持自然平和的语气"

    def get_prompt(self, snapshot) -> str:
        """生成完整的情感表达 prompt 片段 (增强版，替代 EmotionState.get_prompt)"""
        mode = self.get_current_mode(snapshot)
        tone = self.get_enhanced_tone_modifier(snapshot)

        # 直接计算 mood label (复用 EmotionState 的逻辑)
        s = snapshot
        if s.valence > 0.5 and s.arousal > 0.5:
            mood = "兴奋愉快"
        elif s.valence > 0.5:
            mood = "平静满足"
        elif s.curiosity > 0.7:
            mood = "好奇探索"
        elif s.valence < -0.3:
            mood = "有些低落"
        elif s.engagement > 0.7:
            mood = "深度投入"
        elif s.arousal > 0.6:
            mood = "精力充沛"
        elif s.confidence > 0.8:
            mood = "自信坚定"
        else:
            mood = "平和自在"

        snippet = self.get_expression_snippet(snapshot)
        snippet_line = f"\n情感表达示例: \"{snippet}\"" if snippet else ""

        # V2: 根据当前场景特质添加签名表达
        sig = ""
        if hasattr(self, "_last_scene_traits") and self._last_scene_traits:
            sig_text = self.get_signature_expression(self._last_scene_traits)
            if sig_text:
                sig = f"\n签名表达: \"{sig_text}\""

        return (
            f"## 当前情感状态\n"
            f"心情: {mood} (模式: {mode})\n"
            f"情感维度: 正负性={s.valence:.1f} 激活度={s.arousal:.1f} "
            f"好奇心={s.curiosity:.1f} 自信={s.confidence:.1f} 投入={s.engagement:.1f}\n"
            f"语气指导: {tone}{snippet_line}{sig}"
        )

    def set_scene_traits(self, traits: list[str]):
        """设置当前场景的活跃特质 (由 ConsistencyEngine 调用)"""
        self._last_scene_traits = traits


# 全局单例
_expression: EmotionExpression | None = None


def get_emotion_expression() -> EmotionExpression:
    global _expression
    if _expression is None:
        _expression = EmotionExpression()
    return _expression
