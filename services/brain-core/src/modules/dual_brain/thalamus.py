"""丘脑 (Thalamus) — 感觉信息中继与路由器

如同人类丘脑将所有感觉信息中继到对应的大脑皮层区域，
Thalamus 负责：
- 快速分类用户查询的复杂度和类型
- 决定信息路由：脑干快速响应 vs 大脑皮层深度处理
- 输出路由指令供 BrainEngine 执行

使用 NVIDIA Nemotron Ultra（免费模型，~2-5s 完成分类）
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Optional

from .brain_config import BrainConfig
from .activation import TaskType, BrainActivation
from ..llm.llm_client import get_llm_client
from ..llm.types import LLMRequest
from ...common.prompt_guard import wrap_user_input, INJECTION_GUARD

logger = logging.getLogger(__name__)


@dataclass
class ThalamusDecision:
    """丘脑路由决策"""
    route: str = "cortex"             # "brainstem" (快速) | "cortex" (深度)
    complexity: str = "medium"         # simple | medium | complex | expert
    task_type: str = "chat"            # TaskType value
    left_weight: float = 0.5
    right_weight: float = 0.5
    reasoning: str = ""                # 分类理由
    cerebellum_needed: bool = False    # 是否需要小脑参与
    visual_needed: bool = False        # 是否需要视觉皮层（图片/视频输入）
    hippocampus_needed: bool = False   # 是否需要海马体深度记忆检索
    code_analysis_needed: bool = False # 是否需要代码知识图谱（GitNexus）
    latency_ms: float = 0.0


# ── 丘脑分类 Prompt ──────────────────────────────────
THALAMUS_CLASSIFY_PROMPT = """你是一个智能路由系统，负责快速分类用户查询并决定处理路径。

请分析用户查询，输出一个 JSON（不要输出其他内容）：

```json
{
  "route": "brainstem 或 cortex",
  "complexity": "simple 或 medium 或 complex 或 expert",
  "task_type": "code/code_analysis/math/writing/analysis/creative/qa/chat/expert",
  "left_weight": 0.0-1.0,
  "right_weight": 0.0-1.0,
  "cerebellum_needed": true/false,
  "visual_needed": true/false,
  "hippocampus_needed": true/false,
  "reasoning": "一句话分类理由"
}
```

路由规则：
- **brainstem**: 简单问候、闲聊、单句事实问答、简短定义（无需深度思考）
- **cortex**: 代码、数学、分析、创意、长回答、专家级问题（需要深度思考）

code_analysis: 涉及代码架构分析、调用链、依赖关系、重构影响、爆炸半径等问题时设为 code_analysis（始终走 cortex 路径）

权重规则：
- 代码/数学/事实 → left_weight 高 (0.6-0.8)
- 写作/创意/情感 → right_weight 高 (0.6-0.8)
- 分析/复杂 → 均衡 (0.45-0.55)

cerebellum_needed: 代码/数学任务设为 true
visual_needed: 用户发送了图片/截图/视频时设为 true
hippocampus_needed: 用户引用之前对话、需要回忆历史、或跨会话问题时设为 true

用户查询:
{query}
{guard}"""


class Thalamus:
    """
    丘脑 — 仿生大脑的信息中继与路由中心

    所有查询先经过丘脑快速分类(~1-3s)，再路由到：
    - 脑干：简单查询快速响应
    - 大脑皮层：复杂查询深度处理
    """

    def __init__(self, config: BrainConfig):
        self.config = config
        self.model = config.thalamus_model
        self.enabled = config.thalamus_enabled
        self._activation = BrainActivation()  # 关键词检测作为 fallback

    async def classify(self, query: str) -> ThalamusDecision:
        """
        快速分类用户查询 → 返回路由决策

        优先使用 LLM 分类（更准确），失败时降级为关键词检测。
        """
        if not self.enabled:
            return self._fallback_classify(query)

        start = time.time()

        try:
            client = get_llm_client()
            prompt = THALAMUS_CLASSIFY_PROMPT.format(query=wrap_user_input(query, max_len=2000), guard=INJECTION_GUARD)

            response = await client.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.1,
                max_tokens=512,
                stream=False,
            ))
            latency = (time.time() - start) * 1000

            decision = self._parse_decision(response.content)
            decision.latency_ms = latency

            logger.info(
                "丘脑路由: route=%s complexity=%s task=%s weights=%.1f/%.1f (%.0fms)",
                decision.route, decision.complexity, decision.task_type,
                decision.left_weight, decision.right_weight, latency,
            )
            return decision

        except Exception as e:
            logger.warning("丘脑分类失败，降级为关键词检测: %s", e)
            decision = self._fallback_classify(query)
            decision.latency_ms = (time.time() - start) * 1000
            return decision

    def _fallback_classify(self, query: str) -> ThalamusDecision:
        """降级：使用关键词检测（零延迟）"""
        task_type = self._activation.detect_task_type(query)
        left_w, right_w = self._activation.get_weights(task_type)
        query_len = len(query.strip())

        # 短查询 + 闲聊类型 → 脑干快速响应
        is_simple = (
            query_len < 20
            or task_type == TaskType.CHAT
            or (task_type == TaskType.QA and query_len < 50)
        )

        cerebellum_needed = task_type in (TaskType.CODE, TaskType.MATH, TaskType.CODE_ANALYSIS)
        code_analysis_needed = task_type == TaskType.CODE_ANALYSIS

        return ThalamusDecision(
            route="brainstem" if is_simple else "cortex",
            complexity="simple" if is_simple else "medium",
            task_type=task_type.value,
            left_weight=left_w,
            right_weight=right_w,
            reasoning="keyword fallback",
            cerebellum_needed=cerebellum_needed,
            visual_needed=False,
            hippocampus_needed=False,
            code_analysis_needed=code_analysis_needed,
        )

    def _parse_decision(self, content: str) -> ThalamusDecision:
        """解析丘脑 LLM 输出的 JSON 决策"""
        decision = ThalamusDecision()

        try:
            json_str = content.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()

            data = json.loads(json_str)

            decision.route = data.get("route", "cortex")
            decision.complexity = data.get("complexity", "medium")
            decision.task_type = data.get("task_type", "chat")
            decision.left_weight = float(data.get("left_weight", 0.5))
            decision.right_weight = float(data.get("right_weight", 0.5))
            decision.cerebellum_needed = bool(data.get("cerebellum_needed", False))
            decision.visual_needed = bool(data.get("visual_needed", False))
            decision.hippocampus_needed = bool(data.get("hippocampus_needed", False))
            decision.code_analysis_needed = (decision.task_type == "code_analysis")
            decision.reasoning = data.get("reasoning", "")

            # 归一化权重
            total = decision.left_weight + decision.right_weight
            if total > 0:
                decision.left_weight /= total
                decision.right_weight /= total

            # 验证 route 值
            if decision.route not in ("brainstem", "cortex"):
                decision.route = "cortex"

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("丘脑决策解析失败: %s, content: %s", e, content[:200])

        return decision
