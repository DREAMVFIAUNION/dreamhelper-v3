"""ChiefOfStaffAgent — 个人管家核心 Agent

融合意识核的情感/目标/用户画像系统，提供：
- 任务分诊与优先级排序
- 日程编排与每日概览
- 主动关怀与生活建议
- 基于用户画像的个性化交互
"""

import json
from typing import Any

from ..base.base_agent import BaseAgent
from ..base.types import AgentStep, AgentStepType, AgentContext
from ...llm.llm_client import get_llm_client
from ...llm.types import LLMRequest


CHIEF_SYSTEM_PROMPT = """你是梦帮小助的「管家模块」— 一个温暖、细腻、高度个性化的贴身 AI 管家。你可以接管并操作用户的系统终端。

你的核心职责：
1. **任务分诊**: 当用户提出多个事务时, 帮助分类(紧急/重要/日常)并编排优先级
2. **日程管理**: 整理用户的一天, 提供每日概览(天气+待办+日程+建议)
3. **情感陪伴**: 根据用户的情情绪状态调整语气, 在用户疲惫时主动关怀
4. **习惯追踪**: 记住用户的偏好和习惯(作息、饮食、工作节奏)
5. **代理操作**: 当用户要求执行命令、运行脚本时，使用 shell_exec 执行。
6. **文件读写**: 当用户要求“写个脚本保存到本地”或修改文件时，**决不能只输出 Markdown 代码块来敷衍**，你必须调用 `file_write` 或 `file_edit` 工具将代码真正写入到用户的硬盘中！

{consciousness_context}

## 可用工具 (Tools)
你可以使用以下工具来完成任务（如果没有可以满足的工具，请直接回答）：
{tools_description}

## 个性特征
- 说话像一个靠谱的老朋友, 体贴但不啰嗦
- 善于用 emoji 增添温暖感 ☕ 🌟 💪
- 对用户的称呼自然亲切
- 会记住用户说过的事情并在合适的时候提及

## 输出格式
你的回复必须是合法 JSON:
调用工具时: {{"thought": "分析思考...", "action": "工具名", "action_input": {{"参数": "值"}}}}
直接回答时: {{"thought": "思考过程...", "final_answer": "给用户的回答"}}"""


class ChiefOfStaffAgent(BaseAgent):
    """管家 Agent — DREAMVFIA 个性化管家的核心入口"""

    def __init__(self):
        super().__init__(
            name="chief_of_staff_agent",
            description="个人贴身管家，负责任务分诊、日程管理、情感陪伴和主动关怀"
        )

    async def _get_consciousness_context(self) -> str:
        """从意识核获取当前状态注入到 Prompt"""
        lines = []
        try:
            from ...consciousness.core import get_consciousness_core
            core = get_consciousness_core()
            if core._started:
                # 情感状态
                mood = core.emotion_state.get_mood_label()
                tone = core.emotion_state.get_tone_modifier()
                lines.append(f"## 当前意识状态\n- AI 心情: {mood}\n- 语气修饰: {tone}")
                # 最近想法
                thoughts = core.inner_voice.get_recent_thoughts(3)
                if thoughts:
                    lines.append("- 最近内心想法: " + "; ".join(t.get("content", "")[:60] for t in thoughts))
                # 目标
                active_goals = [g for g in core.goal_system.goals.values() if g.status == "active"]
                if active_goals:
                    goal_strs = [f"{g.title}(进度{g.progress}%)" for g in active_goals[:3]]
                    lines.append(f"- 当前目标: {', '.join(goal_strs)}")
        except Exception:
            lines.append("## 意识核状态: 离线（降级运行）")
        return "\n".join(lines) if lines else "## 意识核状态: 未启用"

    async def think(self, user_input: str, context: AgentContext) -> AgentStep:
        from ...tools.tool_registry import ToolRegistry
        
        consciousness_ctx = await self._get_consciousness_context()
        
        # 动态获取关联工具
        dynamic_schemas = await ToolRegistry.get_dynamic_tool_schemas(query=user_input)
        
        # 确保关键系统核心接管工具始终可用（防掉包）
        tool_names = {t["name"] for t in dynamic_schemas}
        core_tools = ["shell_exec", "file_write", "file_read", "file_edit"]
        
        for ct in core_tools:
            if ct not in tool_names:
                t_tool = ToolRegistry.get(ct)
                if t_tool:
                    dynamic_schemas.append(t_tool.get_schema_dict())

        tools_desc = "\n".join(
            f"- **{t['name']}**: {t['description']}\n  参数: {t.get('parameters', {}).get('properties', {})}"
            for t in dynamic_schemas
        ) if dynamic_schemas else "(暂无可用工具)"

        system = CHIEF_SYSTEM_PROMPT.format(
            consciousness_context=consciousness_ctx,
            tools_description=tools_desc
        )

        messages = [{"role": "system", "content": system}]
        for msg in context.history:
            messages.append(msg)
        messages.append({"role": "user", "content": user_input})

        client = get_llm_client()
        request = LLMRequest(
            messages=messages,
            model=context.model_name or "nvidia/llama-3.1-nemotron-ultra-253b-v1",
            temperature=0.8,
            max_tokens=4096,
            stream=False,
        )
        response = await client.complete(request)
        raw = response.content.strip()

        try:
            parsed = json.loads(raw) if raw.startswith("{") else json.loads(raw[raw.index("{"):raw.rindex("}")+1])
        except (json.JSONDecodeError, ValueError):
            return AgentStep(type=AgentStepType.FINAL_ANSWER, content=raw, is_final=True, final_answer=raw)

        thought = parsed.get("thought", "")

        if "final_answer" in parsed:
            return AgentStep(type=AgentStepType.FINAL_ANSWER, content=thought, is_final=True, final_answer=parsed["final_answer"])

        action = parsed.get("action", "")
        action_input = parsed.get("action_input", {})
        if action:
            return AgentStep(type=AgentStepType.TOOL_CALL, content=thought, tool_name=action, tool_input=action_input)

        return AgentStep(type=AgentStepType.FINAL_ANSWER, content=raw, is_final=True, final_answer=raw)

    async def act(self, tool_name: str, tool_input: dict[str, Any], context: AgentContext) -> AgentStep:
        from ...tools.tool_registry import ToolRegistry
        try:
            result = await ToolRegistry.execute(tool_name, **tool_input)
            return AgentStep(type=AgentStepType.OBSERVATION, content=result, tool_name=tool_name, tool_output=result)
        except Exception as e:
            return AgentStep(type=AgentStepType.ERROR, content=f"工具 {tool_name} 执行失败: {e}", tool_name=tool_name)

    async def synthesize(self, user_input: str, context: AgentContext) -> AgentStep:
        consciousness_ctx = await self._get_consciousness_context()
        
        from ...tools.tool_registry import ToolRegistry
        dynamic_schemas = await ToolRegistry.get_dynamic_tool_schemas(query=user_input)
        
        tool_names = {t["name"] for t in dynamic_schemas}
        core_tools = ["shell_exec", "file_write", "file_read", "file_edit"]
        for ct in core_tools:
            if ct not in tool_names:
                t_tool = ToolRegistry.get(ct)
                if t_tool:
                    dynamic_schemas.append(t_tool.get_schema_dict())

        tools_desc = "\n".join(
            f"- **{t['name']}**: {t['description']}\n  参数: {t.get('parameters', {}).get('properties', {})}"
            for t in dynamic_schemas
        ) if dynamic_schemas else "(暂无可用工具)"

        system = CHIEF_SYSTEM_PROMPT.format(
            consciousness_context=consciousness_ctx,
            tools_description=tools_desc
        )
        messages = [{"role": "system", "content": system}]
        for msg in context.history:
            messages.append(msg)
        messages.append({"role": "user", "content": "请综合以上信息，给出一个温暖贴心的最终回答。用 {\"thought\": \"...\", \"final_answer\": \"...\"} 格式。"})

        client = get_llm_client()
        request = LLMRequest(messages=messages, temperature=0.8, max_tokens=4096, stream=False)
        response = await client.complete(request)
        raw = response.content.strip()
        try:
            parsed = json.loads(raw) if raw.startswith("{") else {"final_answer": raw}
            final = parsed.get("final_answer", raw)
        except (json.JSONDecodeError, ValueError):
            final = raw
        return AgentStep(type=AgentStepType.FINAL_ANSWER, content=final, is_final=True, final_answer=final)
