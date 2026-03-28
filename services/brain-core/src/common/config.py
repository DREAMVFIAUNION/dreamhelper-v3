"""全局配置"""

import sys
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List


class Settings(BaseSettings):
    ENV: str = "development"
    LOG_LEVEL: str = "debug"

    # Database
    DATABASE_URL: str = "postgresql://dreamhelp:dev_password@localhost:5432/dreamhelp"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Milvus
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530

    # Elasticsearch
    ELASTICSEARCH_URL: str = "http://localhost:9200"

    # LLM
    MINIMAX_API_KEY: str = ""
    MINIMAX_GROUP_ID: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    QWEN_API_KEY: str = ""
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    GLM_API_KEY: str = ""
    GLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    KIMI_API_KEY: str = ""
    KIMI_BASE_URL: str = "https://api.moonshot.cn/v1"

    # NVIDIA NIM (免费无限量)
    NVIDIA_API_KEY: str = ""
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"

    # Embedding
    EMBEDDING_PROVIDER: str = "minimax"  # minimax | openai
    EMBEDDING_DIM: int = 1536

    # RAG
    RAG_MODE: str = "memory"  # memory | vector | hybrid

    # JWT — 生产环境必须通过环境变量设置
    JWT_SECRET: str = "dev-secret-DO-NOT-USE-IN-PRODUCTION"

    # API Auth — brain-core 接口保护（空值=开发模式跳过）
    BRAIN_API_KEY: str = ""
    BRAIN_ADMIN_KEY: str = ""  # P0-#4: 管理端点独立密钥（空值=开发模式跳过）

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    # Webhook
    WEBHOOK_SECRET: str = ""

    # Code Execution
    CODE_EXEC_TIMEOUT: int = 10
    CODE_EXEC_MAX_OUTPUT: int = 5000

    # Dual Brain (双脑融合)
    DUAL_BRAIN_ENABLED: bool = True
    DUAL_BRAIN_LEFT_MODEL: str = "z-ai/glm5"             # 左脑皮层: GLM-5 744B MoE via NVIDIA NIM
    DUAL_BRAIN_RIGHT_MODEL: str = "qwen/qwen3.5-397b-a17b" # 右脑皮层: Qwen-3.5 397B VLM via NVIDIA NIM
    DUAL_BRAIN_JUDGE_MODEL: str = "nvidia/llama-3.1-nemotron-ultra-253b-v1" # 竞争裁判: Nemotron Ultra via NVIDIA NIM
    DUAL_BRAIN_FUSION_MODEL: str = "z-ai/glm5"             # 前额叶融合: GLM-5 744B via NVIDIA NIM
    DUAL_BRAIN_LEFT_TIMEOUT: float = 60.0
    DUAL_BRAIN_RIGHT_TIMEOUT: float = 90.0

    # Thalamus (丘脑 — MiniMax 快速路由/分类)
    THALAMUS_MODEL: str = "nvidia/llama-3.1-nemotron-ultra-253b-v1"  # 丘脑: Nemotron Ultra via NVIDIA NIM
    THALAMUS_ENABLED: bool = True

    # Brainstem (脑干 — 快速响应 + 意图分析)
    BRAINSTEM_ENABLED: bool = True
    BRAINSTEM_MODEL: str = "z-ai/glm5"                      # 脑干分析: GLM-5 via NVIDIA NIM
    BRAINSTEM_RESPONSE_MODEL: str = "nvidia/llama-3.1-nemotron-ultra-253b-v1" # 脑干快速响应: Nemotron Ultra via NVIDIA NIM
    BRAINSTEM_TIMEOUT: float = 45.0

    # Cerebellum (小脑 — Kimi K2.5 Code 代码精度/技术校准)
    CEREBELLUM_ENABLED: bool = True
    CEREBELLUM_MODEL: str = "moonshotai/kimi-k2.5"          # 小脑: Kimi-K2.5 1T MoE via NVIDIA NIM
    CEREBELLUM_TIMEOUT: float = 45.0

    # Visual Cortex (视觉皮层 — NVIDIA Nemotron-12B-VL 图像/视频理解)
    VISUAL_CORTEX_ENABLED: bool = False
    VISUAL_CORTEX_MODEL: str = "nvidia/nemotron-nano-12b-v2-vl"
    VISUAL_CORTEX_TIMEOUT: float = 30.0

    # Hippocampus (海马体 — NVIDIA Nemotron-Nano-30B 1M上下文超长记忆)
    HIPPOCAMPUS_ENABLED: bool = False
    HIPPOCAMPUS_MODEL: str = "nvidia/nemotron-3-nano-30b-a3b"
    HIPPOCAMPUS_TIMEOUT: float = 45.0

    # Consciousness Core (意识核 — 自主思维引擎)
    CONSCIOUSNESS_ENABLED: bool = True
    CONSCIOUSNESS_MODEL: str = "nvidia/nemotron-3-nano-30b-a3b"
    CONSCIOUSNESS_WORLD_MODEL: str = "nvidia/cosmos-reason2-8b"
    CONSCIOUSNESS_THINK_INTERVAL: int = 900  # 内心独白间隔(秒)

    # MCP (Model Context Protocol) 外接工具服务
    MCP_ENABLED: bool = True
    MCP_SEQUENTIAL_THINKING: bool = True
    MCP_FILESYSTEM: bool = True
    MCP_FILESYSTEM_ALLOWED_DIRS: str = "C:/tmp/dreamhelp"
    MCP_MEMORY_GRAPH: bool = True
    MCP_WINDOWS: bool = False             # Windows 桌面自动化 (本地 Windows-MCP) — 默认关闭
    MCP_WINDOWS_DIR: str = "D:/Windows-MCP-main"
    MCP_GIT: bool = False                 # 需要 GITHUB_PERSONAL_ACCESS_TOKEN
    GITHUB_PERSONAL_ACCESS_TOKEN: str = ""
    MCP_MODELSCOPE: bool = False          # 需要 MODELSCOPE_API_TOKEN
    MODELSCOPE_API_TOKEN: str = ""
    MCP_AGENTBAY: bool = False             # 无影 AgentBay 云环境
    AGENTBAY_API_KEY: str = ""
    AGENTBAY_IMAGE_ID: str = "code_latest"  # code_latest | linux_latest | browser_latest | windows_latest

    # GitNexus Code Intelligence (代码知识图谱)
    GITNEXUS_ENABLED: bool = True
    MCP_GITNEXUS: bool = False             # MCP 连接 GitNexus (默认关闭, 避免 KuzuDB 锁冲突)
    GITNEXUS_MCP_CMD: str = "npx"
    GITNEXUS_MCP_ARGS: str = "-y gitnexus@latest mcp"
    GITNEXUS_DEFAULT_REPO: str = ""        # 默认仓库名 (空=自动检测)

    # Observability (监控可观测性)
    SENTRY_DSN: str = ""                   # Sentry DSN, 空值=禁用
    SENTRY_TRACES_SAMPLE_RATE: float = 0.2 # 采样率 0.0-1.0
    METRICS_ENABLED: bool = True           # 启用内置指标收集

    def validate_production(self) -> None:
        """生产环境启动前强制校验关键配置"""
        if self.ENV != "development":
            errors = []
            if "DO-NOT-USE" in self.JWT_SECRET or len(self.JWT_SECRET) < 32:
                errors.append("JWT_SECRET must be set to a secure value (>=32 chars) in production")
            if "dev_password" in self.DATABASE_URL:
                errors.append("DATABASE_URL contains default dev password")
            if not self.MINIMAX_API_KEY:
                errors.append("MINIMAX_API_KEY is required")
            if not self.BRAIN_API_KEY or len(self.BRAIN_API_KEY) < 16:
                errors.append("BRAIN_API_KEY must be set (>=16 chars) in production")
            if errors:
                for e in errors:
                    print(f"  \u2718 CONFIG ERROR: {e}", file=sys.stderr)
                raise SystemExit(1)

    model_config = ConfigDict(
        env_file="../../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
