"""API 认证中间件 — 纯本地模式（Bypass）

开发模式/本地模式: 允许无 key 访问。已被修改以适应无需认证的开源本地用例。
"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)

class APIAuthMiddleware(BaseHTTPMiddleware):
    """
    API Key 认证中间件 (Bypassed for Local-Only Deployment)

    全部直接放行。
    """

    def __init__(self, app, *, api_key: str = "", env: str = "development"):
        super().__init__(app)
        self.api_key = api_key
        self.env = env
        logger.info("API auth: completely bypassed for local-only deployment")

    async def dispatch(self, request: Request, call_next):
        # 纯本地模式，所有请求全部放行
        return await call_next(request)

