"""智能体持久化层 — asyncpg 直连 PostgreSQL

表映射 (与 Prisma schema 完全一致): agents → Agent
"""

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

_SAFE_COL_RE = re.compile(r'^[a-z_]+$')

import asyncpg

from ...common.config import settings
from ..workflow.db import SYSTEM_USER_UUID

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None or _pool._closed:
        _pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL,
            min_size=2,
            max_size=5,
            command_timeout=30,
        )
    return _pool


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _row_to_agent(row: asyncpg.Record) -> dict:
    return {
        "id": str(row["id"]),
        "ownerId": str(row["owner_id"]),
        "organizationId": str(row["organization_id"]) if row["organization_id"] else None,
        "name": row["name"],
        "description": row["description"] or "",
        "avatarUrl": row["avatar_url"],
        "type": row["type"],
        "systemPrompt": row["system_prompt"],
        "modelProvider": row["model_provider"],
        "modelName": row["model_name"],
        "temperature": float(row["temperature"]),
        "maxTokens": row["max_tokens"],
        "capabilities": json.loads(row["capabilities"]) if isinstance(row["capabilities"], str) else row["capabilities"],
        "tools": json.loads(row["tools"]) if isinstance(row["tools"], str) else row["tools"],
        "status": row["status"],
        "isPublic": row["is_public"],
        "usageCount": row["usage_count"],
        "metadata": json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"],
        "createdAt": row["created_at"].isoformat(),
        "updatedAt": row["updated_at"].isoformat(),
    }


async def list_agents(status: Optional[str] = None, is_public: Optional[bool] = None) -> list[dict]:
    pool = await get_pool()
    conditions = []
    vals = []
    idx = 1
    if status:
        conditions.append(f"status = ${idx}")
        vals.append(status)
        idx += 1
    if is_public is not None:
        conditions.append(f"is_public = ${idx}")
        vals.append(is_public)
        idx += 1
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = await pool.fetch(f"SELECT * FROM agents{where} ORDER BY updated_at DESC", *vals)
    return [_row_to_agent(r) for r in rows]


async def get_agent(agent_id: str) -> Optional[dict]:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM agents WHERE id = $1", uuid.UUID(agent_id))
    return _row_to_agent(row) if row else None


async def create_agent(
    owner_id: str,
    name: str,
    description: str = "",
    type_: str = "custom",
    system_prompt: str = "",
    model_provider: str = "minimax",
    model_name: str = "nvidia/llama-3.1-nemotron-ultra-253b-v1",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    capabilities: list = None,
    tools: list = None,
    is_public: bool = False,
) -> dict:
    pool = await get_pool()
    agent_id = uuid.uuid4()
    now = _now()
    try:
        owner_uuid = uuid.UUID(owner_id) if owner_id != "system" else SYSTEM_USER_UUID
    except (ValueError, AttributeError):
        owner_uuid = SYSTEM_USER_UUID

    row = await pool.fetchrow(
        """
        INSERT INTO agents (id, owner_id, name, description, type, system_prompt,
            model_provider, model_name, temperature, max_tokens, capabilities,
            tools, status, is_public, usage_count, metadata, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, 'active', $13, 0, '{}', $14, $14)
        RETURNING *
        """,
        agent_id, owner_uuid, name, description, type_, system_prompt,
        model_provider, model_name, temperature, max_tokens,
        json.dumps(capabilities or ["chat", "completion"]),
        json.dumps(tools or []),
        is_public, now,
    )
    return _row_to_agent(row)


async def update_agent(agent_id: str, **kwargs) -> Optional[dict]:
    pool = await get_pool()
    field_map = {
        "name": "name", "description": "description", "type": "type",
        "systemPrompt": "system_prompt", "system_prompt": "system_prompt",
        "modelProvider": "model_provider", "model_provider": "model_provider",
        "modelName": "model_name", "model_name": "model_name",
        "temperature": "temperature", "maxTokens": "max_tokens", "max_tokens": "max_tokens",
        "capabilities": "capabilities", "tools": "tools",
        "status": "status", "isPublic": "is_public", "is_public": "is_public",
        "avatarUrl": "avatar_url", "avatar_url": "avatar_url",
    }
    json_fields = {"capabilities", "tools"}

    sets = ["updated_at = $2"]
    vals: list = [uuid.UUID(agent_id), _now()]
    idx = 3

    for py_key, db_col in field_map.items():
        if py_key in kwargs and kwargs[py_key] is not None:
            val = kwargs[py_key]
            if db_col in json_fields:
                val = json.dumps(val)
            elif db_col == "temperature":
                val = float(val)
            elif db_col in ("max_tokens", "usage_count"):
                val = int(val)
            sets.append(f"{db_col} = ${idx}")
            vals.append(val)
            idx += 1

    for s in sets:
        col = s.split(' = ')[0]
        assert _SAFE_COL_RE.match(col), f"Invalid column name: {col}"
    sql = f"UPDATE agents SET {', '.join(sets)} WHERE id = $1 RETURNING *"
    row = await pool.fetchrow(sql, *vals)
    return _row_to_agent(row) if row else None


async def delete_agent(agent_id: str) -> bool:
    pool = await get_pool()
    result = await pool.execute("DELETE FROM agents WHERE id = $1", uuid.UUID(agent_id))
    return result == "DELETE 1"


async def seed_preset_agents() -> list[dict]:
    """创建预置智能体 (仅当没有 agent 时)"""
    existing = await list_agents()
    if existing:
        return existing

    presets = [
        {
            "name": "代码助手",
            "description": "专注编程的 AI 助手，擅长代码编写、调试、重构和技术解答",
            "type": "code",
            "system_prompt": "你是一个专业的编程助手。请用简洁清晰的方式回答编程问题，提供高质量的代码示例。遵循最佳实践，添加必要的注释，考虑边界情况和错误处理。",
            "model_provider": "nvidia",
            "model_name": "nvidia/llama-3.1-nemotron-ultra-253b-v1",
            "temperature": 0.5,
            "max_tokens": 8192,
            "capabilities": ["chat", "completion", "code"],
            "tools": ["code_exec", "web_search"],
        },
        {
            "name": "写作助手",
            "description": "专注文案创作的 AI 助手，擅长文章撰写、翻译、总结和改写",
            "type": "writing",
            "system_prompt": "你是一个专业的写作助手。请根据用户需求提供高质量的文案，注意语言风格、结构布局和表达准确性。可以帮助撰写、翻译、总结、改写各类文本。",
            "model_provider": "nvidia",
            "model_name": "nvidia/llama-3.1-nemotron-ultra-253b-v1",
            "temperature": 0.8,
            "max_tokens": 4096,
            "capabilities": ["chat", "completion", "writing"],
            "tools": ["web_search"],
        },
        {
            "name": "数据分析师",
            "description": "专注数据分析的 AI 助手，擅长数据解读、趋势分析和可视化建议",
            "type": "analysis",
            "system_prompt": "你是一个专业的数据分析师。请用严谨的逻辑和数据驱动的方式进行分析，提供清晰的结论和可执行的建议。善于发现数据中的模式和趋势。",
            "model_provider": "nvidia",
            "model_name": "nvidia/llama-3.1-nemotron-ultra-253b-v1",
            "temperature": 0.4,
            "max_tokens": 4096,
            "capabilities": ["chat", "completion", "analysis"],
            "tools": ["calculator", "web_search", "code_exec"],
        },
        {
            "name": "通用助手",
            "description": "全能型 AI 助手，适合日常对话、问答和各类任务",
            "type": "general",
            "system_prompt": "你是梦帮小助，一个友好、专业、主动的 AI 助手。你可以回答各类问题、提供建议、协助完成任务。请用简洁准确的方式回答，必要时主动提供额外帮助。",
            "model_provider": "nvidia",
            "model_name": "nvidia/llama-3.1-nemotron-ultra-253b-v1",
            "temperature": 0.7,
            "max_tokens": 4096,
            "capabilities": ["chat", "completion"],
            "tools": ["web_search", "calculator"],
            "is_public": True,
        },
    ]

    created = []
    for p in presets:
        agent = await create_agent(
            owner_id="system",
            name=p["name"],
            description=p["description"],
            type_=p["type"],
            system_prompt=p["system_prompt"],
            model_provider=p["model_provider"],
            model_name=p["model_name"],
            temperature=p["temperature"],
            max_tokens=p["max_tokens"],
            capabilities=p["capabilities"],
            tools=p["tools"],
            is_public=p.get("is_public", False),
        )
        created.append(agent)
    return created
