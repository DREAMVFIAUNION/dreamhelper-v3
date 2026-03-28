"""Agent FastAPI 路由 — ReAct Agent 运行 + CRUD 管理"""

import json
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional

from ...common.admin_auth import require_admin
from ...common.rate_limit import limiter
from .base.types import AgentContext, AgentStepType
from .implementations.react_agent import ReActAgent
from ..tools.tool_registry import ToolRegistry
from . import db as agent_db

router = APIRouter(prefix="/agents", tags=["agents"])

# 全局 ReAct Agent 实例
_react_agent = ReActAgent()


# ── 请求模型 ──────────────────────────────────────────────

class RunAgentRequest(BaseModel):
    agent_id: str = "react_agent"
    user_input: str
    session_id: str
    model: Optional[str] = None
    stream: bool = True


class AgentCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    type: str = Field(default="custom", pattern=r"^(custom|code|writing|analysis|general)$")
    system_prompt: str = ""
    model_provider: str = "nvidia"
    model_name: str = "nvidia/llama-3.1-nemotron-ultra-253b-v1"
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=4096, ge=256, le=32768)
    capabilities: list[str] = Field(default_factory=lambda: ["chat", "completion"])
    tools: list[str] = Field(default_factory=list)
    is_public: bool = False


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    system_prompt: Optional[str] = None
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    capabilities: Optional[list[str]] = None
    tools: Optional[list[str]] = None
    status: Optional[str] = None
    is_public: Optional[bool] = None


# ── Agent 执行 ────────────────────────────────────────────

@router.post("/run")
@limiter.limit("5/minute")
async def run_agent(request: Request, req: RunAgentRequest):
    """运行 ReAct Agent（支持流式/非流式）"""
    context = AgentContext(
        session_id=req.session_id,
        user_id="anonymous",
        agent_id=req.agent_id,
        model_name=req.model or "nvidia/llama-3.1-nemotron-ultra-253b-v1",
    )

    if not req.stream:
        steps = []
        final_answer = ""
        async for step in _react_agent.run(req.user_input, context):
            steps.append({
                "type": step.type.value,
                "content": step.content,
                "tool_name": step.tool_name,
                "tool_output": step.tool_output,
            })
            if step.is_final and step.final_answer:
                final_answer = step.final_answer
        return {"answer": final_answer, "steps": steps}

    async def event_generator():
        try:
            async for step in _react_agent.run(req.user_input, context):
                event = {
                    "type": step.type.value,
                    "content": step.content,
                    "tool_name": step.tool_name,
                    "tool_input": step.tool_input,
                    "tool_output": step.tool_output,
                }
                if step.is_final and step.final_answer:
                    event["final_answer"] = step.final_answer
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── 工具 + 健康检查 (静态路由必须在 /{agent_id} 之前) ───

@router.get("/meta/tools")
@limiter.limit("30/minute")
async def list_tools(request: Request):
    """列出所有可用工具"""
    return {"tools": ToolRegistry.list_tools()}


@router.get("/meta/health")
@limiter.limit("30/minute")
async def agents_health(request: Request):
    return {"status": "ok", "module": "agents", "tools_count": len(ToolRegistry._tools)}


@router.post("/seed-presets")
@limiter.limit("3/minute")
async def seed_preset_agents_api(request: Request):
    """创建预置智能体 (仅当没有 agent 时)"""
    agents = await agent_db.seed_preset_agents()
    return {"message": f"预置智能体已就绪", "count": len(agents)}


# ── Agent CRUD (持久化到 PostgreSQL) ─────────────────────

@router.get("")
@limiter.limit("30/minute")
async def list_agents_api(request: Request, status: Optional[str] = None, public: Optional[bool] = None):
    """列出所有智能体"""
    agents = await agent_db.list_agents(status=status, is_public=public)
    return {"data": agents, "count": len(agents)}


@router.post("")
@limiter.limit("10/minute")
async def create_agent_api(request: Request, req: AgentCreate, _=Depends(require_admin)):
    """创建自定义智能体"""
    agent = await agent_db.create_agent(
        owner_id="system",  # TODO: 从 JWT 获取
        name=req.name,
        description=req.description or "",
        type_=req.type,
        system_prompt=req.system_prompt,
        model_provider=req.model_provider,
        model_name=req.model_name,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        capabilities=req.capabilities,
        tools=req.tools,
        is_public=req.is_public,
    )
    return agent


# ── 动态路由 /{agent_id} 放最后 ──────────────────────────

@router.get("/{agent_id}")
@limiter.limit("30/minute")
async def get_agent_api(request: Request, agent_id: str):
    """获取智能体详情"""
    agent = await agent_db.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="智能体不存在")
    return agent


@router.put("/{agent_id}")
@limiter.limit("10/minute")
async def update_agent_api(request: Request, agent_id: str, req: AgentUpdate, _=Depends(require_admin)):
    """更新智能体"""
    existing = await agent_db.get_agent(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail="智能体不存在")
    update_data = req.model_dump(exclude_none=True)
    agent = await agent_db.update_agent(agent_id, **update_data)
    return agent


@router.delete("/{agent_id}")
@limiter.limit("10/minute")
async def delete_agent_api(request: Request, agent_id: str, _=Depends(require_admin)):
    """删除智能体"""
    deleted = await agent_db.delete_agent(agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="智能体不存在")
    return {"deleted": True}
