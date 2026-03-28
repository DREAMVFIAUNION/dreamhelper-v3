"""工作流持久化层 — asyncpg 直连 PostgreSQL

表映射 (与 Prisma schema 完全一致):
  workflows          → Workflow
  workflow_executions → WorkflowExecution
  workflow_steps      → WorkflowStep
"""

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

import asyncpg

_SAFE_COL_RE = re.compile(r'^[a-z_]+$')

from ...common.config import settings

_pool: Optional[asyncpg.Pool] = None

# 系统工作流使用固定 UUID 作为 owner_id（需确保 users 表中存在此记录）
SYSTEM_USER_UUID = uuid.UUID("00000000-0000-0000-0000-000000000000")


async def get_pool() -> asyncpg.Pool:
    """获取/创建连接池 (懒初始化)"""
    global _pool
    if _pool is None or _pool._closed:
        _pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
    return _pool


async def close_pool():
    global _pool
    if _pool and not _pool._closed:
        await _pool.close()
        _pool = None


LOCAL_USER_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")

async def ensure_system_user():
    """确保系统用户存在 (用于无 JWT 上下文的工作流) 以及本地默认用户"""
    pool = await get_pool()
    exists = await pool.fetchval(
        "SELECT 1 FROM users WHERE id = $1", SYSTEM_USER_UUID,
    )
    if not exists:
        await pool.execute(
            """
            INSERT INTO users (id, email, username, password_hash, status, created_at, updated_at)
            VALUES ($1, 'system@dreamvfia.local', '_system_', 'nologin', 'system', NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
            """,
            SYSTEM_USER_UUID,
        )
        await pool.execute(
            """
            INSERT INTO users (id, email, username, password_hash, status, created_at, updated_at)
            VALUES ($1, 'local@dreamhelper.local', 'local', 'nologin', 'active', NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
            """,
            LOCAL_USER_UUID,
        )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _row_to_workflow(row: asyncpg.Record) -> dict:
    """将 DB 行转换为 API 响应格式 (camelCase)"""
    return {
        "id": str(row["id"]),
        "ownerId": str(row["owner_id"]),
        "name": row["name"],
        "description": row["description"] or "",
        "status": row["status"],
        "triggerType": row["trigger_type"],
        "triggerConfig": json.loads(row["trigger_config"]) if isinstance(row["trigger_config"], str) else row["trigger_config"],
        "nodes": json.loads(row["nodes"]) if isinstance(row["nodes"], str) else row["nodes"],
        "connections": json.loads(row["connections"]) if isinstance(row["connections"], str) else row["connections"],
        "viewport": json.loads(row["viewport"]) if isinstance(row["viewport"], str) else row["viewport"],
        "variables": json.loads(row["variables"]) if isinstance(row["variables"], str) else row["variables"],
        "tags": json.loads(row["tags"]) if isinstance(row["tags"], str) else row["tags"],
        "runCount": row["run_count"],
        "lastRunAt": row["last_run_at"].isoformat() if row["last_run_at"] else None,
        "lastRunStatus": row["last_run_status"],
        "metadata": json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"],
        "createdAt": row["created_at"].isoformat(),
        "updatedAt": row["updated_at"].isoformat(),
    }


def _row_to_execution(row: asyncpg.Record) -> dict:
    return {
        "id": str(row["id"]),
        "workflowId": str(row["workflow_id"]),
        "status": row["status"],
        "triggerType": row["trigger_type"],
        "triggerData": json.loads(row["trigger_data"]) if isinstance(row["trigger_data"], str) else row["trigger_data"],
        "error": row["error"],
        "totalNodes": row["total_nodes"],
        "completedNodes": row["completed_nodes"],
        "totalTokens": row["total_tokens"],
        "totalLatencyMs": row["total_latency_ms"],
        "metadata": json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"],
        "startedAt": row["started_at"].isoformat(),
        "finishedAt": row["finished_at"].isoformat() if row["finished_at"] else None,
    }


def _row_to_step(row: asyncpg.Record) -> dict:
    return {
        "id": str(row["id"]),
        "executionId": str(row["execution_id"]),
        "nodeId": row["node_id"],
        "nodeName": row["node_name"],
        "nodeType": row["node_type"],
        "status": row["status"],
        "inputData": json.loads(row["input_data"]) if isinstance(row["input_data"], str) else row["input_data"],
        "outputData": json.loads(row["output_data"]) if isinstance(row["output_data"], str) else row["output_data"],
        "error": row["error"],
        "tokens": row["tokens"],
        "latencyMs": row["latency_ms"],
        "startedAt": row["started_at"].isoformat() if row["started_at"] else None,
        "finishedAt": row["finished_at"].isoformat() if row["finished_at"] else None,
    }


# ═══════════════════════════════════════════════════════════
# Workflow CRUD
# ═══════════════════════════════════════════════════════════

async def list_workflows(status: Optional[str] = None) -> list[dict]:
    pool = await get_pool()
    if status:
        rows = await pool.fetch(
            "SELECT * FROM workflows WHERE status = $1 ORDER BY updated_at DESC",
            status,
        )
    else:
        rows = await pool.fetch("SELECT * FROM workflows ORDER BY updated_at DESC")
    return [_row_to_workflow(r) for r in rows]


async def get_workflow(wf_id: str) -> Optional[dict]:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM workflows WHERE id = $1", uuid.UUID(wf_id))
    return _row_to_workflow(row) if row else None


async def create_workflow(
    owner_id: str,
    name: str,
    description: str = "",
    trigger_type: str = "manual",
    trigger_config: dict = None,
    nodes: list = None,
    connections: list = None,
    viewport: dict = None,
    variables: dict = None,
    tags: list = None,
) -> dict:
    pool = await get_pool()
    wf_id = uuid.uuid4()
    now = _now()
    # 解析 owner_id: 有效 UUID 直接使用，否则使用系统用户
    try:
        owner_uuid = uuid.UUID(owner_id) if owner_id != "system" else SYSTEM_USER_UUID
    except (ValueError, AttributeError):
        owner_uuid = SYSTEM_USER_UUID
    row = await pool.fetchrow(
        """
        INSERT INTO workflows (id, owner_id, name, description, status, trigger_type,
            trigger_config, nodes, connections, viewport, variables, tags,
            run_count, metadata, created_at, updated_at)
        VALUES ($1, $2, $3, $4, 'draft', $5, $6, $7, $8, $9, $10, $11, 0, '{}', $12, $12)
        RETURNING *
        """,
        wf_id,
        owner_uuid,
        name,
        description,
        trigger_type,
        json.dumps(trigger_config or {}),
        json.dumps(nodes or []),
        json.dumps(connections or []),
        json.dumps(viewport or {}),
        json.dumps(variables or {}),
        json.dumps(tags or []),
        now,
    )
    return _row_to_workflow(row)


async def update_workflow(wf_id: str, **kwargs) -> Optional[dict]:
    pool = await get_pool()
    # 构建动态 SET 子句
    field_map = {
        "name": "name",
        "description": "description",
        "status": "status",
        "triggerType": "trigger_type",
        "trigger_type": "trigger_type",
        "triggerConfig": "trigger_config",
        "trigger_config": "trigger_config",
        "nodes": "nodes",
        "connections": "connections",
        "viewport": "viewport",
        "variables": "variables",
        "tags": "tags",
        "runCount": "run_count",
        "run_count": "run_count",
        "lastRunAt": "last_run_at",
        "last_run_at": "last_run_at",
        "lastRunStatus": "last_run_status",
        "last_run_status": "last_run_status",
    }
    json_fields = {"trigger_config", "nodes", "connections", "viewport", "variables", "tags"}

    sets = ["updated_at = $2"]
    vals: list = [uuid.UUID(wf_id), _now()]
    idx = 3

    for py_key, db_col in field_map.items():
        if py_key in kwargs and kwargs[py_key] is not None:
            val = kwargs[py_key]
            if db_col in json_fields:
                val = json.dumps(val)
            elif db_col == "run_count":
                val = int(val)
            sets.append(f"{db_col} = ${idx}")
            vals.append(val)
            idx += 1

    if len(sets) == 1:
        # nothing to update besides updated_at
        pass

    for s in sets:
        col = s.split(' = ')[0]
        assert _SAFE_COL_RE.match(col), f"Invalid column name: {col}"
    sql = f"UPDATE workflows SET {', '.join(sets)} WHERE id = $1 RETURNING *"
    row = await pool.fetchrow(sql, *vals)
    return _row_to_workflow(row) if row else None


async def delete_workflow(wf_id: str) -> bool:
    pool = await get_pool()
    result = await pool.execute("DELETE FROM workflows WHERE id = $1", uuid.UUID(wf_id))
    return result == "DELETE 1"


# ═══════════════════════════════════════════════════════════
# WorkflowExecution CRUD
# ═══════════════════════════════════════════════════════════

async def create_execution(
    workflow_id: str,
    trigger_type: str = "manual",
    trigger_data: dict = None,
    total_nodes: int = 0,
) -> dict:
    pool = await get_pool()
    exec_id = uuid.uuid4()
    now = _now()
    row = await pool.fetchrow(
        """
        INSERT INTO workflow_executions (id, workflow_id, status, trigger_type,
            trigger_data, total_nodes, completed_nodes, total_tokens,
            total_latency_ms, metadata, started_at)
        VALUES ($1, $2, 'pending', $3, $4, $5, 0, 0, 0, '{}', $6)
        RETURNING *
        """,
        exec_id,
        uuid.UUID(workflow_id),
        trigger_type,
        json.dumps(trigger_data or {}),
        total_nodes,
        now,
    )
    return _row_to_execution(row)


async def update_execution(exec_id: str, **kwargs) -> Optional[dict]:
    pool = await get_pool()
    field_map = {
        "status": "status",
        "error": "error",
        "completedNodes": "completed_nodes",
        "completed_nodes": "completed_nodes",
        "totalNodes": "total_nodes",
        "total_nodes": "total_nodes",
        "totalTokens": "total_tokens",
        "total_tokens": "total_tokens",
        "totalLatencyMs": "total_latency_ms",
        "total_latency_ms": "total_latency_ms",
        "finishedAt": "finished_at",
        "finished_at": "finished_at",
    }

    sets = []
    vals: list = [uuid.UUID(exec_id)]
    idx = 2

    for py_key, db_col in field_map.items():
        if py_key in kwargs and kwargs[py_key] is not None:
            val = kwargs[py_key]
            if db_col in ("completed_nodes", "total_tokens", "total_latency_ms"):
                val = int(val)
            elif db_col == "finished_at" and isinstance(val, str):
                val = datetime.fromisoformat(val.replace("Z", "+00:00"))
            sets.append(f"{db_col} = ${idx}")
            vals.append(val)
            idx += 1

    if not sets:
        return None

    for s in sets:
        col = s.split(' = ')[0]
        assert _SAFE_COL_RE.match(col), f"Invalid column name: {col}"
    sql = f"UPDATE workflow_executions SET {', '.join(sets)} WHERE id = $1 RETURNING *"
    row = await pool.fetchrow(sql, *vals)
    return _row_to_execution(row) if row else None


async def list_executions(workflow_id: str, limit: int = 20) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT * FROM workflow_executions WHERE workflow_id = $1 ORDER BY started_at DESC LIMIT $2",
        uuid.UUID(workflow_id),
        limit,
    )
    return [_row_to_execution(r) for r in rows]


async def get_execution(exec_id: str) -> Optional[dict]:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM workflow_executions WHERE id = $1",
        uuid.UUID(exec_id),
    )
    return _row_to_execution(row) if row else None


# ═══════════════════════════════════════════════════════════
# WorkflowStep CRUD
# ═══════════════════════════════════════════════════════════

async def save_steps(exec_id: str, steps: list[dict]):
    """批量保存执行步骤"""
    pool = await get_pool()
    execution_uuid = uuid.UUID(exec_id)

    for s in steps:
        started = None
        finished = None
        if s.get("startedAt"):
            try:
                started = datetime.fromisoformat(s["startedAt"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass
        if s.get("finishedAt"):
            try:
                finished = datetime.fromisoformat(s["finishedAt"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        await pool.execute(
            """
            INSERT INTO workflow_steps (id, execution_id, node_id, node_name, node_type,
                status, input_data, output_data, error, tokens, latency_ms, started_at, finished_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                output_data = EXCLUDED.output_data,
                error = EXCLUDED.error,
                tokens = EXCLUDED.tokens,
                latency_ms = EXCLUDED.latency_ms,
                finished_at = EXCLUDED.finished_at
            """,
            uuid.UUID(s.get("id", str(uuid.uuid4()))),
            execution_uuid,
            s.get("nodeId", ""),
            s.get("nodeName", ""),
            s.get("nodeType", ""),
            s.get("status", "pending"),
            json.dumps(s.get("inputData", {})),
            json.dumps(s.get("outputData", {})),
            s.get("error"),
            s.get("tokens", 0),
            s.get("latencyMs", 0),
            started,
            finished,
        )


async def get_steps(exec_id: str) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT * FROM workflow_steps WHERE execution_id = $1 ORDER BY started_at ASC NULLS LAST",
        uuid.UUID(exec_id),
    )
    return [_row_to_step(r) for r in rows]
