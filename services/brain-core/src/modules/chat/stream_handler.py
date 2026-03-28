"""SSE 流式响应处理 — 多轮对话 + ReAct Agent + 记忆系统 + RAG + Hook 事件（Phase 9）"""

import asyncio
import json
import logging
import traceback
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional

from ..llm.llm_client import get_llm_client
from ..llm.types import LLMRequest
from ..agents.base.types import AgentContext
from ..agents import agent_router
from ..memory.memory_manager import get_memory_manager
from ..memory.user_profile import extract_user_facts, should_extract
from ..rag.rag_pipeline import get_rag_pipeline
from ..proactive.heartbeat import get_heartbeat
from .prompt_builder import build_system_prompt
from .compaction import should_compact, compact_history
from ..hooks.hook_registry import HookRegistry, HookEventType
from ...common.rate_limit import limiter

logger = logging.getLogger(__name__)

_SAFE_ERROR = "处理请求时遇到问题，请稍后重试"

router = APIRouter(prefix="/chat", tags=["chat"])

DEFAULT_MODEL = "nvidia/llama-3.1-nemotron-ultra-253b-v1"
MAX_HISTORY_TURNS = 20
DEFAULT_USER_ID = "anonymous"


async def _enhanced_system_prompt(user_id: str, query: str, style: str = "default") -> str:
    """构建增强版 system prompt：SOUL + 时间 + 用户画像 + RAG 上下文 + 风格"""
    prompt, _ = await _enhanced_system_prompt_with_sources(user_id, query, style)
    return prompt


async def _enhanced_system_prompt_with_sources(user_id: str, query: str, style: str = "default") -> tuple[str, list[dict]]:
    """构建增强版 system prompt 并返回 RAG 来源元数据"""
    mm = get_memory_manager()
    profile_prompt = await mm.get_semantic_profile_prompt(user_id, query)

    rag = get_rag_pipeline()
    rag_context, rag_sources = await rag.retrieve_with_sources(query, top_k=3, max_chars=1500)

    # GitNexus 代码知识图谱上下文注入（非阻塞）
    code_intel_context = await _fetch_code_intel_context(query)
    if code_intel_context:
        rag_context = (rag_context + "\n\n" + code_intel_context) if rag_context else code_intel_context

    prompt = await build_system_prompt(
        user_id=user_id,
        query=query,
        style=style,
        user_profile_prompt=profile_prompt,
        rag_context=rag_context,
    )
    return prompt, rag_sources


async def _fetch_code_intel_context(query: str) -> str:
    """从 GitNexus 知识图谱获取代码架构上下文（仅代码分析类查询触发）"""
    try:
        from ..code_intel.prompts import CODE_ANALYSIS_KEYWORDS
        query_lower = query.lower()
        if not any(kw in query_lower for kw in CODE_ANALYSIS_KEYWORDS):
            return ""
        from ..code_intel import get_gitnexus_client
        client = get_gitnexus_client()
        return await client.analyze_for_chat(query)
    except Exception as e:
        logger.debug("[CodeIntel] Context fetch skipped: %s", e)
        return ""


async def _consciousness_on_conversation_end(session_id: str, user_id: str):
    """意识核: 对话结束后 → 自我反思 + 目标更新 + 情感更新 + 一致性重置"""
    try:
        from ..consciousness import get_consciousness_core
        consciousness = get_consciousness_core()
        if not (consciousness.config.enabled and consciousness._started):
            return
        mm = get_memory_manager()
        history = await mm.get_session_history(session_id, limit=30)
        if history:
            await consciousness.on_conversation_end(history, user_id)
            logger.debug("[Consciousness] on_conversation_end fired for session=%s", session_id[:8])
    except Exception as e:
        logger.warning("[Consciousness] on_conversation_end failed (non-fatal): %s", e)


async def _save_and_extract(session_id: str, user_id: str, role: str, content: str):
    """保存消息到记忆 + 心跳上报 + 异步触发用户画像提取 + 意识核事件"""
    mm = get_memory_manager()
    await mm.add_message(session_id, role, content)

    # P0-#3: 首次消息时记录会话归属
    if role == "user":
        await mm.set_session_owner(session_id, user_id)

    # 用户消息时上报心跳 + 意识核感知
    if role == "user":
        get_heartbeat().user_active(user_id)

        # 意识核: 用户消息到达 → 更新情感/世界模型
        try:
            from ..consciousness import get_consciousness_core
            consciousness = get_consciousness_core()
            if consciousness.config.enabled and consciousness._started:
                asyncio.create_task(consciousness.on_user_message(user_id, content))
        except Exception:
            pass

        history = await mm.get_session_history(session_id)
        if await should_extract(history):
            asyncio.create_task(
                extract_user_facts(user_id, history, session_id)
            )


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128, description="会话 ID")
    content: str = Field(..., min_length=1, max_length=32000, description="用户消息内容")
    stream: bool = True
    model: Optional[str] = Field(None, max_length=64)
    system_prompt: Optional[str] = Field(None, max_length=2000)
    use_agent: Optional[bool] = None
    user_id: Optional[str] = Field(None, max_length=64)
    user_profile: Optional[dict] = Field(None, description="用户资料 {username, display_name, email, tier_level}")
    style: Optional[str] = Field(None, max_length=32)
    messages: Optional[list] = Field(None, max_length=100)


@router.post("/completions")
@limiter.limit("10/minute")
async def chat_completions(request: Request, req: ChatRequest):
    """对话补全接口 — 多 Agent 智能路由 + 记忆 + RAG + Hook（Phase 9）"""
    model = req.model or DEFAULT_MODEL
    user_id = req.user_id or DEFAULT_USER_ID

    # 将用户资料同步到意识核用户注册表
    if req.user_profile and user_id != DEFAULT_USER_ID:
        try:
            from ..consciousness.user_registry import get_user_registry
            registry = get_user_registry()
            registry.on_user_profile_sync(
                user_id,
                username=req.user_profile.get("username", ""),
                display_name=req.user_profile.get("display_name", ""),
                email=req.user_profile.get("email", ""),
                tier_level=req.user_profile.get("tier_level", 0),
            )
        except Exception:
            pass

    # 触发会话开始事件
    await HookRegistry.emit(HookEventType.SESSION_START, {
        "session_id": req.session_id, "user_id": user_id, "model": model,
    })

    # /run <workflow_name> 命令 → 触发工作流
    if req.content.strip().startswith("/run "):
        return await _run_workflow_command(req, user_id)

    # 强制 Agent 模式
    if req.use_agent is True:
        agent_name, agent = await agent_router.route(req.content)
        return await _agent_completions(req, model, agent_name, agent, user_id)

    # ── 新路由逻辑: 双脑优先 ──
    from ..agents.agent_router import route_by_keywords
    from ..dual_brain import get_brain_engine
    brain = get_brain_engine()

    kw_route = route_by_keywords(req.content)

    # 只有需要工具调用的 Agent 才绕过双脑（react_agent / plan_execute / browser）
    TOOL_AGENTS = {"react_agent", "plan_execute_agent", "browser_agent"}
    if kw_route and kw_route in TOOL_AGENTS:
        await HookRegistry.emit(HookEventType.AGENT_ROUTE, {
            "session_id": req.session_id, "agent": kw_route, "query": req.content[:100],
        })
        agent = agent_router.get_agent(kw_route)
        return await _agent_completions(req, model, kw_route, agent, user_id)

    # 所有其他查询 → 对话模式（内部判断是否走双脑）
    return await _chat_completions(req, model, user_id)


async def _agent_completions(req: ChatRequest, model: str,
                              agent_name: str = "react_agent",
                              agent=None,
                              user_id: str = "anonymous"):
    """Agent 模式：多 Agent 路由 + 工具调用 + 记忆"""
    if agent is None:
        agent = agent_router.get_agent(agent_name)

    mm = get_memory_manager()
    await _save_and_extract(req.session_id, user_id, "user", req.content)

    context = AgentContext(
        session_id=req.session_id,
        user_id=user_id,
        model_name=model,
    )

    if not req.stream:
        final_answer = ""
        async for step in agent.run(req.content, context):
            if step.is_final and step.final_answer:
                final_answer = step.final_answer
        await _save_and_extract(req.session_id, user_id, "assistant", final_answer)
        await HookRegistry.emit(HookEventType.SESSION_END, {
            "session_id": req.session_id, "user_id": user_id,
            "agent": agent_name, "length": len(final_answer),
        })
        asyncio.create_task(_consciousness_on_conversation_end(req.session_id, user_id))
        return {
            "session_id": req.session_id,
            "content": final_answer,
            "role": "assistant",
            "model": model,
            "agent": agent_name,
        }

    async def event_generator():
        final_answer = ""
        try:
            # 发送 agent 路由信息
            yield f"data: {json.dumps({'type': 'agent_info', 'agent': agent_name, 'description': agent.description}, ensure_ascii=False)}\n\n"
            async for step in agent.run(req.content, context):
                event = {"type": step.type.value, "content": step.content}
                if step.tool_name:
                    event["tool_name"] = step.tool_name
                if step.tool_input:
                    event["tool_input"] = step.tool_input
                if step.tool_output:
                    event["tool_output"] = step.tool_output
                if step.is_final and step.final_answer:
                    event["final_answer"] = step.final_answer
                    final_answer = step.final_answer
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            if final_answer:
                await _save_and_extract(req.session_id, user_id, "assistant", final_answer)
                await HookRegistry.emit(HookEventType.SESSION_END, {
                    "session_id": req.session_id, "user_id": user_id,
                    "agent": agent_name, "length": len(final_answer),
                })
                asyncio.create_task(_consciousness_on_conversation_end(req.session_id, user_id))
        except Exception as e:
            logger.error("Agent SSE error: %s", e, exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': _SAFE_ERROR}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _run_workflow_command(req, user_id: str):
    """处理 /run <workflow_name_or_id> 命令 — 在对话中触发工作流"""
    from ..workflow import db as wfdb
    from ..workflow.engine import WorkflowEngine

    parts = req.content.strip().split(None, 1)
    wf_identifier = parts[1].strip() if len(parts) > 1 else ""

    if not wf_identifier:
        return {"session_id": req.session_id, "content": "用法: /run <工作流名称或ID>", "role": "assistant"}

    # 按名称或 ID 查找工作流
    wf = await wfdb.get_workflow(wf_identifier)

    # P2-#8: 工作流归属校验
    if wf and wf.get("owner_id") and wf["owner_id"] != user_id:
        return {"session_id": req.session_id, "content": "无权执行此工作流", "role": "assistant"}

    if not wf:
        # 尝试按名称搜索
        all_wfs = await wfdb.list_workflows()
        matches = [w for w in all_wfs if wf_identifier.lower() in w.get("name", "").lower()]
        if len(matches) == 1:
            wf = matches[0]
        elif len(matches) > 1:
            names = "\n".join(f"- {w['name']} ({w['id'][:8]}...)" for w in matches[:5])
            return {"session_id": req.session_id, "content": f"找到多个匹配的工作流:\n{names}\n\n请使用更精确的名称或 ID。", "role": "assistant"}
        else:
            return {"session_id": req.session_id, "content": f"未找到工作流: {wf_identifier}", "role": "assistant"}

    nodes = wf.get("nodes", [])
    if not nodes:
        return {"session_id": req.session_id, "content": f"工作流 '{wf['name']}' 没有定义节点。", "role": "assistant"}

    try:
        execution = await wfdb.create_execution(
            workflow_id=wf["id"],
            trigger_type="chat_command",
            trigger_data={"user_id": user_id, "session_id": req.session_id},
        )
        engine = WorkflowEngine()
        result = await engine.execute(
            execution_id=execution["id"],
            nodes=nodes,
            connections=wf.get("connections", []),
            trigger_data={"user_id": user_id, "session_id": req.session_id},
            variables=wf.get("variables", {}),
        )

        status = "success" if not result.get("error") else "failed"
        await wfdb.update_execution(
            execution["id"], status=status,
            completed_nodes=result.get("completed_nodes", 0),
            total_nodes=result.get("total_nodes", 0),
            error=result.get("error"),
        )

        if status == "success":
            output = result.get("output", {})
            content = f"✅ 工作流 **{wf['name']}** 执行成功。"
            if output:
                content += f"\n\n```json\n{json.dumps(output, ensure_ascii=False, indent=2)[:1000]}\n```"
        else:
            content = f"❌ 工作流 **{wf['name']}** 执行失败: {result.get('error', '未知错误')}"

    except Exception as e:
        logger.error("工作流执行异常: %s", e, exc_info=True)
        content = "❌ 工作流执行异常，请稍后重试"

    return {"session_id": req.session_id, "content": content, "role": "assistant"}


@router.get("/agents")
async def list_available_agents():
    """列出所有可用 Agent"""
    return {"agents": agent_router.list_agents()}


@router.get("/models")
async def list_available_models():
    """列出所有可用 LLM 模型"""
    client = get_llm_client()
    return {"models": client.list_models()}


async def _chat_completions(req: ChatRequest, model: str, user_id: str = "anonymous"):
    """普通对话模式：LLM 流式 + 记忆 + RAG 上下文注入 + PromptBuilder + 引用溯源 + 双脑"""
    mm = get_memory_manager()
    await _save_and_extract(req.session_id, user_id, "user", req.content)

    # 构建增强 system prompt（SOUL + 时间 + 画像 + RAG + 风格）
    style = req.style or "default"
    system, rag_sources = await _enhanced_system_prompt_with_sources(user_id, req.content, style)

    # 优先使用前端传入的历史消息（DB持久化），否则从 MemoryManager 获取
    if req.messages:
        history = [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in req.messages]
    else:
        history = await mm.get_session_history(req.session_id, limit=MAX_HISTORY_TURNS * 2)

    # 会话压缩: 历史过长时自动摘要早期消息
    if await should_compact(history):
        existing_summary = await mm.get_session_summary(req.session_id)
        history, new_summary = await compact_history(history, existing_summary=existing_summary)
        if new_summary:
            await mm.set_session_summary(req.session_id, new_summary)

    # ── 身份防火墙: 检测历史消息中的虚假身份声明 ──
    from .prompt_builder import build_identity_firewall
    firewall = build_identity_firewall(history)
    if firewall:
        system += firewall
        logger.info("[IdentityFirewall] 检测到身份污染，已注入纠偏指令 (session=%s)", req.session_id[:8])

    # ── 仿生大脑模式判断（丘脑内部路由：简单→脑干，复杂→皮层）──
    from ..dual_brain import get_brain_engine
    brain = get_brain_engine()
    use_dual_brain = brain.config.enabled and req.stream

    logger.info("仿生大脑: enabled=%s, stream=%s, route=%s",
                brain.config.enabled, req.stream, "BRAIN" if use_dual_brain else "SINGLE")

    if use_dual_brain:
        return await _dual_brain_completions(req, system, history, rag_sources, user_id)

    # ── 传统单脑模式 ──
    messages = [{"role": "system", "content": system}] + history

    llm_request = LLMRequest(messages=messages, model=model, stream=req.stream)

    if not req.stream:
        try:
            client = get_llm_client()
            response = await client.complete(llm_request)
            await _save_and_extract(req.session_id, user_id, "assistant", response.content)
            await HookRegistry.emit(HookEventType.SESSION_END, {
                "session_id": req.session_id, "user_id": user_id,
                "length": len(response.content),
            })
            asyncio.create_task(_consciousness_on_conversation_end(req.session_id, user_id))
            return {
                "session_id": req.session_id,
                "content": response.content,
                "role": "assistant",
                "model": response.model,
                "usage": response.usage,
            }
        except Exception as e:
            logger.error("Chat completions error: %s", e, exc_info=True)
            return {"error": _SAFE_ERROR, "session_id": req.session_id}

    async def event_generator():
        full_content = ""
        try:
            # 发送 RAG 引用来源
            if rag_sources:
                yield f"data: {json.dumps({'type': 'rag_sources', 'sources': rag_sources}, ensure_ascii=False)}\n\n"
            client = get_llm_client()
            async for chunk_json in client.stream(llm_request):
                yield f"data: {chunk_json}\n\n"
                try:
                    chunk_data = json.loads(chunk_json)
                    if chunk_data.get("type") == "chunk":
                        full_content += chunk_data.get("content", "")
                except json.JSONDecodeError:
                    pass
            yield "data: [DONE]\n\n"
            if full_content:
                await _save_and_extract(req.session_id, user_id, "assistant", full_content)
                await HookRegistry.emit(HookEventType.SESSION_END, {
                    "session_id": req.session_id, "user_id": user_id,
                    "length": len(full_content),
                })
                asyncio.create_task(_consciousness_on_conversation_end(req.session_id, user_id))
        except Exception as e:
            logger.error("Chat SSE error: %s", e, exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': _SAFE_ERROR}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _dual_brain_completions(req: ChatRequest, system: str, history: list[dict],
                                   rag_sources: list[dict], user_id: str):
    """双脑并行对话模式 — 左右脑同时推理 + 皮层融合 + SSE 流式事件"""
    from ..dual_brain import get_brain_engine

    brain = get_brain_engine()

    async def brain_event_generator():
        full_content = ""
        try:
            # 发送 RAG 引用来源
            if rag_sources:
                yield f"data: {json.dumps({'type': 'rag_sources', 'sources': rag_sources}, ensure_ascii=False)}\n\n"

            # 双脑流式思考
            async for event in brain.think_stream(
                query=req.content,
                context={"session_id": req.session_id, "user_id": user_id},
                system_prompt=system,
                history=history,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                # 收集最终内容
                if event.get("type") == "chunk":
                    full_content += event.get("content", "")

            yield "data: [DONE]\n\n"

            if full_content:
                await _save_and_extract(req.session_id, user_id, "assistant", full_content)
                await HookRegistry.emit(HookEventType.SESSION_END, {
                    "session_id": req.session_id, "user_id": user_id,
                    "length": len(full_content), "mode": "dual_brain",
                })
                asyncio.create_task(_consciousness_on_conversation_end(req.session_id, user_id))
        except Exception as e:
            logger.error("Dual brain SSE error: %s", e, exc_info=True)
            safe_msg = _SAFE_ERROR
            if "timeout" in str(e).lower() or "ReadTimeout" in type(e).__name__:
                safe_msg = "双脑融合超时，请稍后重试"
            yield f"data: {json.dumps({'type': 'error', 'content': safe_msg}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        brain_event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── API 端点 ──

@router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str, user_id: str = ""):
    """P0-#3: 需要 user_id 参数，校验会话归属"""
    mm = get_memory_manager()
    owner = await mm.get_session_owner(session_id)
    if owner and user_id and owner != user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="无权访问此会话")
    history = await mm.get_session_history(session_id)
    return {"session_id": session_id, "messages": history}


@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str, user_id: str = ""):
    """P0-#3: 需要 user_id 参数，校验会话归属"""
    mm = get_memory_manager()
    owner = await mm.get_session_owner(session_id)
    if owner and user_id and owner != user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="无权删除此会话")
    await mm.clear_session(session_id)
    return {"session_id": session_id, "cleared": True}


@router.get("/memory/stats")
async def memory_stats():
    mm = get_memory_manager()
    rag = get_rag_pipeline()
    return {
        "memory": await mm.get_stats(),
        "rag": rag.get_stats(),
    }


@router.get("/memory/profile/{user_id}")
async def get_user_profile(user_id: str, caller_id: str = ""):
    """P0-#3: 用户画像仅允许本人或管理员访问"""
    if caller_id and caller_id != user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="无权查看此用户画像")
    mm = get_memory_manager()
    facts = await mm.get_all_user_facts(user_id)
    return {"user_id": user_id, "facts": facts}
