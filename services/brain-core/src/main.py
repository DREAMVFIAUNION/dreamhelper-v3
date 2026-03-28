"""梦帮小助 v3.7.0 · brain-core 服务入口"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .common.errors import AppError
from .modules.agents.router import router as agents_router
from .modules.chat.stream_handler import router as chat_router
from .modules.proactive.router import router as proactive_router
from .modules.multimodal.router import router as multimodal_router
from .modules.tools.skills.skills_router import router as skills_router
from .modules.rag.router import router as rag_router
from .modules.webhook.router import router as webhook_router
from .modules.llm.llm_api_router import router as llm_router
from .modules.workflow.router import router as workflow_router
from .modules.memory.router import router as memory_router
from .modules.dual_brain.router import router as brain_router
from .modules.mcp.mcp_router import router as mcp_router
from .modules.consciousness.router import router as consciousness_router
from .modules.code_intel.router import router as code_intel_router
from .common.config import settings
from .common.security_middleware import SecurityHeadersMiddleware
from .common.api_auth import APIAuthMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # 结构化日志初始化
    from .common.logging_config import setup_logging
    setup_logging(env=settings.ENV, log_level=settings.LOG_LEVEL)
    # 生产环境配置校验
    settings.validate_production()
    # Sentry 错误追踪初始化
    from .common.sentry_setup import init_sentry
    if init_sentry():
        print("  ✓ Sentry error tracking enabled")
    # 启动时初始化
    print(f"🚀 brain-core v4.0.0-alpha starting in {settings.ENV} mode")
    from .modules.tools.setup import register_all_tools
    register_all_tools()
    from .modules.rag.setup import seed_knowledge_base, sync_documents_from_db
    seed_knowledge_base()
    await sync_documents_from_db()
    from .modules.proactive.setup import register_proactive_tasks
    register_proactive_tasks()
    from .modules.tools.skills.setup import register_all_skills
    register_all_skills()
    
    # 异步预计算 100+ 技能的向量特征
    from .modules.tools.skills.skill_engine import SkillEngine
    print("  ⏳ 正在为 100+ 技能计算向量特征 (RAG for Skills)...")
    try:
        # 使用不阻塞后续核心 DB 加载的方式 (如果实在慢可以放后端)
        # 这里为了稳妥还是等待一下，保证 Agent 启动就有能力
        await asyncio.wait_for(SkillEngine.vectorize_all_skills(), timeout=25.0)
    except Exception as e:
        print(f"  ⚠ 技能向量化失败或超时: {e}")
        
    from .modules.workflow.setup import register_workflow_nodes
    register_workflow_nodes()
    # 初始化工作流 DB 连接池 + 确保系统用户存在
    from .modules.workflow.db import get_pool, close_pool, ensure_system_user
    app.state.workflow_db_ok = False
    try:
        await get_pool()
        await ensure_system_user()
        app.state.workflow_db_ok = True
    except Exception as e:
        print(f"  ⚠ Workflow DB unavailable (degraded mode): {e}")
    # 初始化记忆 DB 连接池 + 预热长期记忆
    from .modules.memory.db import get_pool as mem_get_pool, close_pool as mem_close_pool
    app.state.memory_db_ok = False
    try:
        await mem_get_pool()
        from .modules.memory.memory_manager import get_memory_manager
        await get_memory_manager().warm_up()
        app.state.memory_db_ok = True
    except Exception as e:
        print(f"  ⚠ Memory DB unavailable (degraded mode): {e}")
    from .modules.proactive.scheduler import get_scheduler
    await get_scheduler().start()
    # 初始化仿生大脑引擎
    from .modules.dual_brain import get_brain_engine
    brain = get_brain_engine()
    thalamus_info = f"丘脑={brain.config.thalamus_model}" if brain.config.thalamus_enabled else "丘脑=OFF"
    brainstem_info = f"脑干={brain.config.brainstem_response_model}"
    left_info = f"左脑={brain.config.left_model}"
    right_info = f"右脑={brain.config.right_model}"
    cerebellum_info = f"小脑={brain.config.cerebellum_model}" if brain.config.cerebellum_enabled else "小脑=OFF"
    fusion_info = f"前额叶={brain.config.fusion_model}"
    visual_info = f"视觉皮层={brain.config.visual_cortex_model}" if brain.config.visual_cortex_enabled else "视觉皮层=OFF"
    hippo_info = f"海马体={brain.config.hippocampus_model}" if brain.config.hippocampus_enabled else "海马体=OFF"
    print(f"  🧠 仿生大脑: {'enabled' if brain.config.enabled else 'disabled'}")
    print(f"     {thalamus_info} | {brainstem_info}")
    print(f"     {left_info} | {right_info}")
    print(f"     {cerebellum_info} | {fusion_info}")
    print(f"     {visual_info} | {hippo_info}")
    # 初始化意识核 (Consciousness Core)
    from .modules.consciousness import get_consciousness_core
    consciousness = get_consciousness_core()
    await consciousness.startup()
    # 意识核定时任务通过 scheduler 热注册机制自动启动

    # 初始化 MCP 外接工具服务（非阻塞容错：MCP 故障不影响核心服务）
    if settings.MCP_ENABLED:
        try:
            from .modules.mcp.setup import initialize_mcp
            await initialize_mcp()
        except Exception as e:
            print(f"  ⚠ MCP 初始化失败 (降级运行，核心功能不受影响): {e}")
    yield
    # ── 关闭时清理（每步独立容错，防止级联失败）──
    try:
        await consciousness.shutdown()
    except Exception as e:
        print(f"  ⚠ Consciousness shutdown error (ignored): {e}")
    try:
        if settings.MCP_ENABLED:
            from .modules.mcp.setup import shutdown_mcp
            await shutdown_mcp()
    except Exception as e:
        print(f"  ⚠ MCP shutdown error (ignored): {e}")
    try:
        await get_scheduler().stop()
    except Exception as e:
        print(f"  ⚠ Scheduler stop error (ignored): {e}")
    try:
        from .modules.memory.redis_store import close_redis
        await close_redis()
    except Exception as e:
        print(f"  ⚠ Redis close error (ignored): {e}")
    try:
        if app.state.memory_db_ok:
            await mem_close_pool()
    except Exception as e:
        print(f"  ⚠ Memory DB close error (ignored): {e}")
    try:
        if app.state.workflow_db_ok:
            await close_pool()
    except Exception as e:
        print(f"  ⚠ Workflow DB close error (ignored): {e}")
    print("brain-core shutting down")


from .common.rate_limit import limiter

APP_VERSION = "4.0.0-alpha"

app = FastAPI(
    title="DREAMVFIA Brain Core",
    description="梦帮小助 AI 核心推理服务",
    version=APP_VERSION,
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """统一业务异常处理 — 返回结构化错误响应"""
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

app.add_middleware(SecurityHeadersMiddleware, env=settings.ENV)
app.add_middleware(APIAuthMiddleware, api_key=settings.BRAIN_API_KEY, env=settings.ENV)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"] if settings.ENV == "development" else settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(proactive_router, prefix="/api/v1")
app.include_router(multimodal_router, prefix="/api/v1")
app.include_router(skills_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")
app.include_router(webhook_router, prefix="/api/v1")
app.include_router(llm_router, prefix="/api/v1")
app.include_router(workflow_router, prefix="/api/v1")
app.include_router(memory_router, prefix="/api/v1")
app.include_router(brain_router, prefix="/api/v1")
app.include_router(mcp_router, prefix="/api/v1")
app.include_router(consciousness_router, prefix="/api/v1")
app.include_router(code_intel_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """深度健康检查 — 探活 DB / Redis / Milvus / ES"""
    checks: dict = {}
    all_ok = True

    # DB (PostgreSQL)
    try:
        import httpx
        # 简单 TCP 连通性检测
        db_host = settings.DATABASE_URL.split("@")[-1].split("/")[0] if "@" in settings.DATABASE_URL else "localhost:5432"
        host, port = (db_host.split(":") + ["5432"])[:2]
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, int(port)), timeout=3
        )
        writer.close()
        await writer.wait_closed()
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"error: {e}"
        all_ok = False

    # Redis
    try:
        redis_host = settings.REDIS_URL.replace("redis://", "").split("/")[0]
        rhost, rport = (redis_host.split(":") + ["6379"])[:2]
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(rhost, int(rport)), timeout=3
        )
        writer.close()
        await writer.wait_closed()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        all_ok = False

    # Milvus (仅 vector/hybrid 模式)
    if settings.RAG_MODE in ("vector", "hybrid"):
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(settings.MILVUS_HOST, settings.MILVUS_PORT), timeout=3
            )
            writer.close()
            await writer.wait_closed()
            checks["milvus"] = "ok"
        except Exception as e:
            checks["milvus"] = f"error: {e}"
            all_ok = False

    # Elasticsearch (仅 hybrid 模式)
    if settings.RAG_MODE == "hybrid":
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{settings.ELASTICSEARCH_URL}/_cluster/health")
                if resp.status_code == 200:
                    checks["elasticsearch"] = "ok"
                else:
                    checks["elasticsearch"] = f"http {resp.status_code}"
                    all_ok = False
        except Exception as e:
            checks["elasticsearch"] = f"error: {e}"
            all_ok = False

    return {
        "status": "ok" if all_ok else "degraded",
        "service": "brain-core",
        "version": APP_VERSION,
        "checks": checks,
    }


@app.get("/metrics")
async def prometheus_metrics():
    from fastapi.responses import PlainTextResponse
    from .modules.common.prometheus import metrics
    return PlainTextResponse(metrics.export_text(), media_type="text/plain")


@app.get("/metrics/json")
async def metrics_json():
    from .modules.common.prometheus import metrics
    return metrics.to_dict()


@app.get("/metrics/brain")
async def brain_metrics():
    """三脑引擎专用指标 — 融合缓存/权重追踪/运行统计"""
    from .modules.dual_brain import get_brain_engine
    from .modules.rag.rag_pipeline import get_rag_pipeline
    from .common.metrics import get_metrics

    brain = get_brain_engine()
    rag = get_rag_pipeline()
    m = get_metrics()

    return {
        "brain": brain.get_stats(),
        "rag": rag.get_stats(),
        "metrics": m.snapshot(),
    }
