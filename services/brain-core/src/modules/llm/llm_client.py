"""LLM 客户端 — 统一入口（第三章 3.8）"""

import logging
from typing import AsyncGenerator, List
from .types import LLMRequest, LLMResponse
from .providers.base_provider import BaseProvider
from .providers.minimax_provider import MiniMaxProvider
from .providers.openai_provider import OpenAIProvider
from .providers.deepseek_provider import DeepSeekProvider
from .providers.qwen_provider import QwenProvider
from .providers.glm_provider import GLMProvider
from .providers.kimi_provider import KimiProvider
from .providers.nvidia_provider import NvidiaProvider
from ...common.config import settings

logger = logging.getLogger(__name__)

# 全局单例
_llm_client: "LLMClient | None" = None


def get_llm_client() -> "LLMClient":
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


class LLMClient:
    """所有 LLM 调用的统一入口 — 支持多提供商 (动态 BYOK 改版)"""

    def __init__(self):
        self.providers: List[BaseProvider] = []
        self._cache_time = 0
        self._ttl_seconds = 10  # 缓存 10 秒

    async def _ensure_dynamic_providers(self):
        """动态加载用户在前端配置的 API Key 覆盖本地 .env"""
        import time
        if time.time() - self._cache_time < self._ttl_seconds and self.providers:
            return

        from ...modules.workflow.db import get_pool
        try:
            pool = await get_pool()
            rows = await pool.fetch("SELECT key, value FROM system_configs WHERE key LIKE '%_API_KEY'")
            dynamic_keys = {r["key"]: r["value"] for r in rows}
        except Exception as e:
            logger.warning("Failed to fetch dynamic API keys: %s", e)
            dynamic_keys = {}

        minimax_key = dynamic_keys.get("MINIMAX_API_KEY") or settings.MINIMAX_API_KEY
        openai_key = dynamic_keys.get("OPENAI_API_KEY") or settings.OPENAI_API_KEY
        deepseek_key = dynamic_keys.get("DEEPSEEK_API_KEY") or settings.DEEPSEEK_API_KEY
        qwen_key = dynamic_keys.get("QWEN_API_KEY") or settings.QWEN_API_KEY
        glm_key = dynamic_keys.get("GLM_API_KEY") or settings.GLM_API_KEY
        kimi_key = dynamic_keys.get("KIMI_API_KEY") or settings.KIMI_API_KEY
        nvidia_key = dynamic_keys.get("NVIDIA_API_KEY") or settings.NVIDIA_API_KEY

        self.providers = []
        if minimax_key:
            self.providers.append(MiniMaxProvider(api_key=str(minimax_key)))
        if openai_key:
            self.providers.append(OpenAIProvider(api_key=str(openai_key), base_url=settings.OPENAI_BASE_URL))
        if deepseek_key:
            self.providers.append(DeepSeekProvider(api_key=str(deepseek_key), base_url=settings.DEEPSEEK_BASE_URL))
        if qwen_key:
            self.providers.append(QwenProvider(api_key=str(qwen_key), base_url=settings.QWEN_BASE_URL))
        if glm_key:
            self.providers.append(GLMProvider(api_key=str(glm_key), base_url=settings.GLM_BASE_URL))
        if kimi_key:
            self.providers.append(KimiProvider(api_key=str(kimi_key), base_url=settings.KIMI_BASE_URL))
        if nvidia_key:
            self.providers.append(NvidiaProvider(api_key=str(nvidia_key), base_url=settings.NVIDIA_BASE_URL))

        self._cache_time = time.time()

    def _get_provider(self, model: str) -> BaseProvider:
        """智能路由: NVIDIA(免费) 优先 → 原厂(付费) → fallback"""
        nvidia_provider = None
        original_provider = None

        for provider in self.providers:
            if provider.supports_model(model):
                if provider.name == "nvidia":
                    nvidia_provider = provider
                else:
                    original_provider = provider

        if nvidia_provider:
            return nvidia_provider
        if original_provider:
            return original_provider
        if self.providers:
            return self.providers[0]
        raise ValueError(f"No provider supports model: {model}")

    def list_models(self) -> List[dict]:
        """列出所有可用模型"""
        models = []
        for p in self.providers:
            from .providers.minimax_provider import MINIMAX_MODELS
            from .providers.openai_provider import OPENAI_MODELS
            from .providers.deepseek_provider import DEEPSEEK_MODELS
            from .providers.qwen_provider import QWEN_MODELS

            if p.name == "minimax":
                for m in MINIMAX_MODELS:
                    models.append({"id": m, "provider": "minimax"})
            elif p.name == "openai":
                for m in OPENAI_MODELS:
                    models.append({"id": m, "provider": "openai"})
            elif p.name == "deepseek":
                for m in DEEPSEEK_MODELS:
                    models.append({"id": m, "provider": "deepseek"})
            elif p.name == "qwen":
                for m in QWEN_MODELS:
                    models.append({"id": m, "provider": "qwen"})
            elif p.name == "glm":
                from .providers.glm_provider import GLM_MODELS
                for m in GLM_MODELS:
                    models.append({"id": m, "provider": "glm"})
            elif p.name == "kimi":
                from .providers.kimi_provider import KIMI_MODELS
                for m in KIMI_MODELS:
                    models.append({"id": m, "provider": "kimi"})
            elif p.name == "nvidia":
                from .providers.nvidia_provider import NVIDIA_MODELS
                for m in NVIDIA_MODELS:
                    models.append({"id": m, "provider": "nvidia"})
        return models

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """非流式补全"""
        await self._ensure_dynamic_providers()
        provider = self._get_provider(request.model)
        return await provider.complete(request)

    async def stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """流式补全"""
        await self._ensure_dynamic_providers()
        provider = self._get_provider(request.model)
        async for chunk in provider.stream(request):
            yield chunk
