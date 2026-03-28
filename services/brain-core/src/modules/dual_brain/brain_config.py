"""仿生大脑配置"""

from dataclasses import dataclass
from ...common.config import settings


@dataclass
class BrainConfig:
    """仿生大脑配置 — 丘脑(MiniMax路由) + 左脑皮层(GLM推理) + 右脑皮层(Qwen创意) + 脑干(MiniMax快速) + 小脑(Kimi精度) + 视觉皮层(Nemotron-VL) + 海马体(Nemotron-30B) + 意识核"""

    # 半球模型分配
    left_model: str = ""
    right_model: str = ""

    # 融合裁判模型（轻量级，用于评估/融合）
    judge_model: str = ""
    fusion_model: str = ""

    # 丘脑 — MiniMax 快速路由/分类
    thalamus_model: str = ""
    thalamus_enabled: bool = True
    thalamus_timeout: float = 10.0

    # 脑干 — MiniMax 快速响应 (简单查询直答)
    brainstem_model: str = ""
    brainstem_enabled: bool = True
    brainstem_timeout: float = 30.0
    brainstem_response_model: str = ""  # 脑干快速响应用的模型

    # 小脑 — Kimi K2.5 Code 代码精度/技术校准
    cerebellum_model: str = ""
    cerebellum_enabled: bool = True
    cerebellum_timeout: float = 30.0

    # 视觉皮层 — NVIDIA Nemotron-12B-VL 图像/视频理解
    visual_cortex_model: str = ""
    visual_cortex_enabled: bool = False
    visual_cortex_timeout: float = 30.0

    # 海马体 — NVIDIA Nemotron-Nano-30B 1M上下文超长记忆
    hippocampus_model: str = ""
    hippocampus_enabled: bool = False
    hippocampus_timeout: float = 45.0

    # 意识核 — 自主思维引擎
    consciousness_model: str = ""
    consciousness_enabled: bool = False
    consciousness_think_interval: int = 900

    # 模式控制
    enabled: bool = True
    fallback_to_single: bool = True

    # 性能调优
    left_timeout: float = 15.0
    right_timeout: float = 25.0
    fusion_timeout: float = 15.0

    # 智能切换阈值
    simple_query_threshold: int = 20
    min_confidence: float = 0.5

    def __post_init__(self):
        """从全局 settings 填充未设置的字段"""
        if not self.left_model:
            self.left_model = settings.DUAL_BRAIN_LEFT_MODEL
        if not self.right_model:
            self.right_model = settings.DUAL_BRAIN_RIGHT_MODEL
        if not self.judge_model:
            self.judge_model = settings.DUAL_BRAIN_JUDGE_MODEL
        if not self.fusion_model:
            self.fusion_model = settings.DUAL_BRAIN_FUSION_MODEL
        # 丘脑
        if not self.thalamus_model:
            self.thalamus_model = getattr(settings, 'THALAMUS_MODEL', 'nvidia/llama-3.1-nemotron-ultra-253b-v1')
        self.thalamus_enabled = getattr(settings, 'THALAMUS_ENABLED', True)
        # 脑干
        if not self.brainstem_model:
            self.brainstem_model = settings.BRAINSTEM_MODEL
        self.brainstem_enabled = settings.BRAINSTEM_ENABLED
        self.brainstem_timeout = settings.BRAINSTEM_TIMEOUT
        if not self.brainstem_response_model:
            self.brainstem_response_model = getattr(settings, 'BRAINSTEM_RESPONSE_MODEL', 'nvidia/llama-3.1-nemotron-ultra-253b-v1')
        if not self.cerebellum_model:
            self.cerebellum_model = settings.CEREBELLUM_MODEL
        self.cerebellum_enabled = settings.CEREBELLUM_ENABLED
        self.cerebellum_timeout = settings.CEREBELLUM_TIMEOUT
        # 视觉皮层
        if not self.visual_cortex_model:
            self.visual_cortex_model = settings.VISUAL_CORTEX_MODEL
        self.visual_cortex_enabled = settings.VISUAL_CORTEX_ENABLED
        self.visual_cortex_timeout = settings.VISUAL_CORTEX_TIMEOUT
        # 海马体
        if not self.hippocampus_model:
            self.hippocampus_model = settings.HIPPOCAMPUS_MODEL
        self.hippocampus_enabled = settings.HIPPOCAMPUS_ENABLED
        self.hippocampus_timeout = settings.HIPPOCAMPUS_TIMEOUT
        # 意识核
        if not self.consciousness_model:
            self.consciousness_model = settings.CONSCIOUSNESS_MODEL
        self.consciousness_enabled = settings.CONSCIOUSNESS_ENABLED
        self.consciousness_think_interval = settings.CONSCIOUSNESS_THINK_INTERVAL
        self.enabled = settings.DUAL_BRAIN_ENABLED
        self.left_timeout = settings.DUAL_BRAIN_LEFT_TIMEOUT
        self.right_timeout = settings.DUAL_BRAIN_RIGHT_TIMEOUT
