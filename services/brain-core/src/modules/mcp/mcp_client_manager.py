"""MCP Client Manager — 管理多个 MCP Server 的连接生命周期

职责:
- 启动/停止 MCP Server 子进程 (stdio transport)
- 维护 ClientSession 连接池
- 提供 list_tools / call_tool 统一接口
- 自动重连 + 健康检查
"""

import asyncio
import logging
import json
from typing import Any, Optional
from dataclasses import dataclass, field

from .mcp_config import MCPServerConfig

logger = logging.getLogger("mcp.client_manager")


@dataclass
class MCPConnection:
    """单个 MCP Server 连接状态"""
    config: MCPServerConfig
    session: Any = None          # mcp.ClientSession
    _read_stream: Any = None
    _write_stream: Any = None
    _cm_stdio: Any = None        # stdio context manager
    _cm_session: Any = None      # session context manager
    connected: bool = False
    tools: list[dict] = field(default_factory=list)
    error: str = ""


class MCPClientManager:
    """MCP 连接池管理器 — 全局单例"""

    _connections: dict[str, MCPConnection] = {}
    _initialized: bool = False

    @classmethod
    async def initialize(cls, configs: list[MCPServerConfig]):
        """启动所有已启用的 MCP Server 并建立连接（顺序启动避免 npx 冲突）"""
        if cls._initialized:
            return

        for cfg in configs:
            if not cfg.enabled:
                continue
            conn = MCPConnection(config=cfg)
            cls._connections[cfg.name] = conn

        # 顺序连接每个服务器，避免 Windows 上 npx 并发文件锁冲突
        for name in list(cls._connections.keys()):
            try:
                await asyncio.wait_for(cls._connect(name), timeout=60.0)
            except asyncio.TimeoutError:
                conn = cls._connections[name]
                conn.error = f"连接超时 (60s)"
                conn.connected = False
                logger.warning("MCP [%s] 连接超时", name)
            except Exception as e:
                logger.warning("MCP [%s] 初始化异常: %s", name, e)

        cls._initialized = True

    @classmethod
    async def _connect(cls, name: str):
        """建立到指定 MCP Server 的连接"""
        conn = cls._connections.get(name)
        if not conn:
            return

        cfg = conn.config
        try:
            if cfg.transport == "stdio":
                await cls._connect_stdio(conn)
            else:
                await cls._connect_http(conn)
        except Exception as e:
            conn.error = str(e)
            conn.connected = False
            logger.warning("MCP [%s] 连接失败: %s", name, e)

    @classmethod
    async def _connect_stdio(cls, conn: MCPConnection):
        """通过 stdio 传输连接到 MCP Server"""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        cfg = conn.config
        server_params = StdioServerParameters(
            command=cfg.command,
            args=cfg.args,
            env=cfg.env if cfg.env else None,
        )

        try:
            # 进入 stdio context manager
            conn._cm_stdio = stdio_client(server_params)
            read_stream, write_stream = await conn._cm_stdio.__aenter__()
            conn._read_stream = read_stream
            conn._write_stream = write_stream

            # 进入 session context manager
            conn._cm_session = ClientSession(read_stream, write_stream)
            session = await conn._cm_session.__aenter__()
            conn.session = session

            # 初始化协议
            await session.initialize()

            # 发现工具
            tools_result = await session.list_tools()
            conn.tools = [
                {
                    "name": t.name,
                    "description": getattr(t, "description", "") or "",
                    "input_schema": t.inputSchema if hasattr(t, "inputSchema") else {},
                }
                for t in tools_result.tools
            ]
            conn.connected = True
            conn.error = ""

            tool_names = [t["name"] for t in conn.tools]
            logger.info("MCP [%s] 已连接, %d 个工具: %s", cfg.name, len(conn.tools), tool_names)
            print(f"  ✓ MCP [{cfg.name}] connected: {len(conn.tools)} tools {tool_names}")

        except Exception as e:
            conn.connected = False
            conn.error = str(e)
            # 清理部分初始化的资源
            await cls._cleanup_conn(conn)
            raise

    @classmethod
    async def _connect_http(cls, conn: MCPConnection):
        """通过 Streamable HTTP 传输连接到 MCP Server"""
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        cfg = conn.config
        try:
            conn._cm_stdio = streamable_http_client(cfg.url)
            read_stream, write_stream, _ = await conn._cm_stdio.__aenter__()
            conn._read_stream = read_stream
            conn._write_stream = write_stream

            conn._cm_session = ClientSession(read_stream, write_stream)
            session = await conn._cm_session.__aenter__()
            conn.session = session

            await session.initialize()

            tools_result = await session.list_tools()
            conn.tools = [
                {
                    "name": t.name,
                    "description": getattr(t, "description", "") or "",
                    "input_schema": t.inputSchema if hasattr(t, "inputSchema") else {},
                }
                for t in tools_result.tools
            ]
            conn.connected = True
            conn.error = ""
            logger.info("MCP [%s] HTTP 已连接, %d 个工具", cfg.name, len(conn.tools))

        except Exception as e:
            conn.connected = False
            conn.error = str(e)
            await cls._cleanup_conn(conn)
            raise

    @classmethod
    async def call_tool(cls, server_name: str, tool_name: str, arguments: dict[str, Any] = None) -> str:
        """调用指定 MCP Server 的工具"""
        conn = cls._connections.get(server_name)
        if not conn:
            return f"MCP Server '{server_name}' 未注册"
        if not conn.connected or not conn.session:
            return f"MCP Server '{server_name}' 未连接: {conn.error or '未初始化'}"

        try:
            result = await asyncio.wait_for(
                conn.session.call_tool(tool_name, arguments=arguments or {}),
                timeout=conn.config.timeout,
            )
            # 提取文本内容
            parts = []
            for content in result.content:
                if hasattr(content, "text"):
                    parts.append(content.text)
                elif hasattr(content, "data"):
                    parts.append(f"[binary data: {len(content.data)} bytes]")
                else:
                    parts.append(str(content))
            return "\n".join(parts) if parts else "(空结果)"

        except asyncio.TimeoutError:
            return f"MCP [{server_name}].{tool_name} 执行超时 ({conn.config.timeout}s)"
        except Exception as e:
            logger.warning("MCP [%s].%s 调用失败: %s", server_name, tool_name, e)
            return f"MCP 工具调用失败: {e}"

    @classmethod
    def list_servers(cls) -> list[dict]:
        """返回所有已注册服务器的状态"""
        return [
            {
                "name": conn.config.name,
                "description": conn.config.description,
                "transport": conn.config.transport,
                "connected": conn.connected,
                "tools_count": len(conn.tools),
                "tools": [t["name"] for t in conn.tools],
                "error": conn.error,
            }
            for conn in cls._connections.values()
        ]

    @classmethod
    def list_all_tools(cls) -> list[dict]:
        """返回所有已连接服务器暴露的工具"""
        tools = []
        for conn in cls._connections.values():
            if not conn.connected:
                continue
            for t in conn.tools:
                tools.append({
                    "server": conn.config.name,
                    "name": t["name"],
                    "description": t["description"],
                })
        return tools

    @classmethod
    def get_connection(cls, name: str) -> Optional[MCPConnection]:
        return cls._connections.get(name)

    @classmethod
    async def _cleanup_conn(cls, conn: MCPConnection):
        """清理单个连接（容错：超时/取消不影响其他连接清理）"""
        try:
            if conn._cm_session:
                await asyncio.wait_for(
                    conn._cm_session.__aexit__(None, None, None),
                    timeout=5.0,
                )
        except (Exception, asyncio.CancelledError):
            pass
        try:
            if conn._cm_stdio:
                await asyncio.wait_for(
                    conn._cm_stdio.__aexit__(None, None, None),
                    timeout=5.0,
                )
        except (Exception, asyncio.CancelledError):
            pass
        conn.session = None
        conn._cm_session = None
        conn._cm_stdio = None
        conn._read_stream = None
        conn._write_stream = None
        conn.connected = False

    @classmethod
    async def shutdown(cls):
        """关闭所有 MCP 连接（容错：单个连接清理失败不影响其他）"""
        for name, conn in list(cls._connections.items()):
            try:
                logger.info("MCP [%s] 正在关闭...", name)
                await asyncio.wait_for(cls._cleanup_conn(conn), timeout=10.0)
            except (Exception, asyncio.CancelledError) as e:
                logger.warning("MCP [%s] 关闭异常 (已忽略): %s", name, e)
        cls._connections.clear()
        cls._initialized = False
        print("  ✓ MCP connections closed")

    @classmethod
    async def reconnect(cls, name: str):
        """重连指定服务器（带超时保护）"""
        conn = cls._connections.get(name)
        if not conn:
            return
        await cls._cleanup_conn(conn)
        try:
            await asyncio.wait_for(cls._connect(name), timeout=30.0)
        except asyncio.TimeoutError:
            conn = cls._connections.get(name)
            if conn:
                conn.error = f"重连超时 (30s)"
                conn.connected = False
            logger.warning("MCP [%s] 重连超时", name)
        except Exception as e:
            logger.warning("MCP [%s] 重连失败: %s", name, e)
