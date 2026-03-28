"""Plan-and-Execute Agent — 先规划后执行（Phase 11）

与 ReAct 的区别:
- ReAct: Think → Act → Observe → Think → ... (每步即时决策)
- Plan-and-Execute: Plan → Execute Step 1 → Execute Step 2 → ... → Synthesize

适用场景:
- 复杂多步骤任务（如"帮我分析这份数据并生成报告"）
- 需要明确拆解的任务
- 减少 LLM 调用次数（规划一次，执行多次）
"""

import json
import logging
from typing import AsyncGenerator, Any

from ..base.base_agent import BaseAgent
from ..base.types import AgentContext, AgentStep, AgentStepType

logger = logging.getLogger(__name__)

PLAN_SYSTEM_PROMPT = """你是一个任务规划专家。用户会给你一个任务，请将其拆解为有序的执行步骤。

输出规则:
1. 返回一个 JSON 数组，每个元素是一个步骤对象
2. 每个步骤包含: "step"(序号), "action"(具体行动), "tool"(需要的工具名,可选), "tool_input"(工具参数,可选)
3. 步骤数量 2-6 个，不要过多
4. 最后一个步骤应该是"综合结果并回答用户"
5. 如果任务简单不需要工具，步骤里的 tool 为 null

可用工具列表: {tools}

示例输出:
```json
[
  {{"step": 1, "action": "计算 2+3*4 的结果", "tool": "calculator", "tool_input": {{"expression": "2+3*4"}}}},
  {{"step": 2, "action": "综合结果回答用户", "tool": null, "tool_input": null}}
]
```

只返回 JSON 数组，不要返回其他内容。"""

EXECUTE_SYSTEM_PROMPT = """你正在执行一个多步骤计划。当前任务的完整计划如下:

{plan_summary}

你现在需要执行第 {step_num} 步: {step_action}

{previous_results}

请直接执行这一步并给出结果。如果需要调用工具，请按以下 JSON 格式回复:
```json
{{"tool": "工具名", "input": {{...参数...}}}}
```

如果不需要工具，直接给出这一步的结果文本。"""


class PlanExecuteAgent(BaseAgent):
    """Plan-and-Execute Agent: 先生成计划，再逐步执行"""

    def __init__(self):
        super().__init__(
            name="plan_execute_agent",
            description="规划执行专家 — 先拆解任务为步骤，再逐步执行",
        )
        self._plan: list[dict] = []
        self._step_results: list[str] = []

    async def run(
        self, user_input: str, context: AgentContext
    ) -> AsyncGenerator[AgentStep, None]:
        """Plan-and-Execute 主循环"""
        from ...llm.llm_client import get_llm_client
        from ...tools.tool_registry import get_tool_registry

        llm = get_llm_client()
        registry = get_tool_registry()
        dynamic_schemas = await registry.get_dynamic_tool_schemas(query=user_input)
        tool_names = [t["name"] for t in dynamic_schemas]

        # ── Phase 1: 生成计划 ──
        yield AgentStep(
            type=AgentStepType.THINKING,
            content="正在分析任务并制定执行计划...",
            metadata={"phase": "planning"},
        )

        plan_prompt = PLAN_SYSTEM_PROMPT.format(tools=", ".join(tool_names) if tool_names else "无")
        plan_response = await llm.complete(
            messages=[
                {"role": "system", "content": plan_prompt},
                {"role": "user", "content": user_input},
            ],
            model=context.model_name,
            temperature=0.3,
            max_tokens=2048,
        )

        plan = self._parse_plan(plan_response)
        if not plan:
            yield AgentStep(
                type=AgentStepType.FINAL_ANSWER,
                content="任务规划失败，将直接回答。",
                is_final=True,
                final_answer=plan_response,
            )
            return

        self._plan = plan
        self._step_results = []

        plan_summary = "\n".join(
            f"  {s['step']}. {s['action']}" for s in plan
        )
        yield AgentStep(
            type=AgentStepType.THINKING,
            content=f"制定了 {len(plan)} 步执行计划:\n{plan_summary}",
            metadata={"phase": "plan_ready", "plan": plan},
        )

        # ── Phase 2: 逐步执行 ──
        for i, step in enumerate(plan):
            step_num = step.get("step", i + 1)
            action = step.get("action", "")
            tool = step.get("tool")
            tool_input = step.get("tool_input")

            # 如果计划中指定了工具，直接执行
            if tool and tool_input and registry.get(tool):
                yield AgentStep(
                    type=AgentStepType.TOOL_CALL,
                    content=f"步骤 {step_num}: {action}",
                    tool_name=tool,
                    tool_input=tool_input,
                    metadata={"phase": "executing", "step": step_num},
                )

                try:
                    result = await registry.execute(tool, tool_input)
                    result_str = json.dumps(result, ensure_ascii=False) if isinstance(result, dict) else str(result)
                except Exception as e:
                    result_str = f"工具执行出错: {e}"

                yield AgentStep(
                    type=AgentStepType.OBSERVATION,
                    content=result_str,
                    tool_name=tool,
                    tool_output=result_str,
                    metadata={"phase": "observation", "step": step_num},
                )
                self._step_results.append(f"步骤{step_num} ({action}): {result_str}")
                continue

            # 非工具步骤 → LLM 执行
            prev_text = "\n".join(self._step_results) if self._step_results else "（暂无前置结果）"
            exec_prompt = EXECUTE_SYSTEM_PROMPT.format(
                plan_summary=plan_summary,
                step_num=step_num,
                step_action=action,
                previous_results=f"前置步骤结果:\n{prev_text}",
            )

            exec_response = await llm.complete(
                messages=[
                    {"role": "system", "content": exec_prompt},
                    {"role": "user", "content": user_input},
                ],
                model=context.model_name,
                temperature=context.temperature,
                max_tokens=4096,
            )

            # 检查 LLM 是否要求调用工具
            parsed_tool = self._parse_tool_call(exec_response)
            if parsed_tool and registry.get(parsed_tool["tool"]):
                t_name = parsed_tool["tool"]
                t_input = parsed_tool["input"]

                yield AgentStep(
                    type=AgentStepType.TOOL_CALL,
                    content=f"步骤 {step_num}: 调用 {t_name}",
                    tool_name=t_name,
                    tool_input=t_input,
                    metadata={"phase": "executing", "step": step_num},
                )

                try:
                    result = await registry.execute(t_name, t_input)
                    result_str = json.dumps(result, ensure_ascii=False) if isinstance(result, dict) else str(result)
                except Exception as e:
                    result_str = f"工具执行出错: {e}"

                yield AgentStep(
                    type=AgentStepType.OBSERVATION,
                    content=result_str,
                    tool_name=t_name,
                    tool_output=result_str,
                    metadata={"phase": "observation", "step": step_num},
                )
                self._step_results.append(f"步骤{step_num} ({action}): {result_str}")
            else:
                self._step_results.append(f"步骤{step_num} ({action}): {exec_response}")
                yield AgentStep(
                    type=AgentStepType.THINKING,
                    content=f"步骤 {step_num} 完成: {exec_response[:200]}",
                    metadata={"phase": "step_done", "step": step_num},
                )

        # ── Phase 3: 综合最终回答 ──
        all_results = "\n\n".join(self._step_results)
        final_response = await llm.complete(
            messages=[
                {"role": "system", "content": "你是梦帮小助，根据以下执行结果，给用户一个完整、清晰的回答。"},
                {"role": "user", "content": f"用户问题: {user_input}\n\n执行结果:\n{all_results}"},
            ],
            model=context.model_name,
            temperature=context.temperature,
            max_tokens=4096,
        )

        yield AgentStep(
            type=AgentStepType.FINAL_ANSWER,
            content=final_response,
            is_final=True,
            final_answer=final_response,
            metadata={"phase": "final", "steps_executed": len(plan)},
        )

    def _parse_plan(self, response: str) -> list[dict]:
        """从 LLM 响应中解析 JSON 计划"""
        import re
        # 尝试提取 JSON 数组
        json_match = re.search(r'\[[\s\S]*?\]', response)
        if json_match:
            try:
                plan = json.loads(json_match.group())
                if isinstance(plan, list) and len(plan) >= 1:
                    return plan
            except json.JSONDecodeError:
                pass
        logger.warning(f"Failed to parse plan from: {response[:200]}")
        return []

    def _parse_tool_call(self, response: str) -> dict | None:
        """从 LLM 响应中解析工具调用 JSON（支持嵌套对象）"""
        # 找到包含 "tool" 的最外层 { ... }
        start = response.find("{")
        while start != -1:
            depth = 0
            for i in range(start, len(response)):
                if response[i] == "{":
                    depth += 1
                elif response[i] == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = response[start:i + 1]
                        try:
                            data = json.loads(candidate)
                            if isinstance(data, dict) and "tool" in data and "input" in data:
                                return data
                        except json.JSONDecodeError:
                            pass
                        break
            start = response.find("{", start + 1)
        return None

    # BaseAgent 接口 — Plan-and-Execute 不使用这些，但必须实现
    async def think(self, user_input: str, context: AgentContext) -> AgentStep:
        return AgentStep(type=AgentStepType.THINKING, content="Plan-and-Execute mode")

    async def act(self, tool_name: str, tool_input: dict[str, Any], context: AgentContext) -> AgentStep:
        return AgentStep(type=AgentStepType.OBSERVATION, content="")

    async def synthesize(self, user_input: str, context: AgentContext) -> AgentStep:
        return AgentStep(type=AgentStepType.FINAL_ANSWER, content="", is_final=True, final_answer="")
