"""Agent 智能路由器 — 根据用户意图选择最合适的 Agent（Phase 5 + Phase 8 动态加载）"""

import json
import logging
from typing import Optional

from .base.base_agent import BaseAgent
from .implementations.react_agent import ReActAgent
from .implementations.code_agent import CodeAgent
from .implementations.writing_agent import WritingAgent
from .implementations.analysis_agent import AnalysisAgent
from .implementations.plan_execute_agent import PlanExecuteAgent
from .implementations.browser_agent import BrowserAgent
from .implementations.dynamic_agent import DynamicAgent
from .implementations.coding_agent import CodingAgent
from ..llm.llm_client import get_llm_client
from ..llm.types import LLMRequest

logger = logging.getLogger("agents.router")

# 所有可用 Agent（内置 + DB 动态）
_AGENTS: dict[str, BaseAgent] = {}
_db_loaded = False


def _init_builtin_agents():
    """注册内置硬编码 Agent"""
    global _AGENTS
    if _AGENTS:
        return
    _AGENTS = {
        "react_agent": ReActAgent(),
        "code_agent": CodeAgent(),
        "coding_agent": CodingAgent(),
        "writing_agent": WritingAgent(),
        "analysis_agent": AnalysisAgent(),
        "plan_execute_agent": PlanExecuteAgent(),
        "browser_agent": BrowserAgent(),
    }


async def load_db_agents():
    """从 DB 加载 active Agent 并注册到路由（启动时或刷新时调用）"""
    global _db_loaded
    _init_builtin_agents()
    try:
        from . import db as agent_db
        rows = await agent_db.list_agents(status="active")
        count = 0
        for row in rows:
            agent_id = row["id"]
            name = row.get("name", "")
            # 跳过与内置同名的 agent（内置优先）
            safe_name = name.lower().replace(" ", "_").replace("-", "_")
            if safe_name in _AGENTS:
                continue
            # P2-#7: 安全校验 — 防止 DB 投毒
            system_prompt = row.get("systemPrompt", "")
            if len(system_prompt) > 4000:
                logger.warning("[AgentRouter] Agent %s system_prompt too long (%d chars), truncating", agent_id, len(system_prompt))
                system_prompt = system_prompt[:4000]
            temperature = max(0.0, min(2.0, float(row.get("temperature", 0.7))))
            max_tokens = max(256, min(16384, int(row.get("maxTokens", 4096))))

            da = DynamicAgent(
                agent_id=agent_id,
                name=safe_name,
                description=row.get("description", "")[:500],
                system_prompt=system_prompt,
                model_provider=row.get("modelProvider", "minimax"),
                model_name=row.get("modelName", "nvidia/llama-3.1-nemotron-ultra-253b-v1"),
                temperature=temperature,
                max_tokens=max_tokens,
                tools=row.get("tools", []),
                capabilities=row.get("capabilities", []),
            )
            _AGENTS[safe_name] = da
            count += 1
        _db_loaded = True
        if count > 0:
            logger.info("[AgentRouter] Loaded %d dynamic agents from DB", count)
    except Exception as e:
        logger.warning("[AgentRouter] Failed to load DB agents: %s", e)


async def refresh_db_agents():
    """重新加载 DB Agent（用于 Agent CRUD 后刷新）"""
    # 移除旧的动态 agent
    to_remove = [k for k, v in _AGENTS.items() if isinstance(v, DynamicAgent)]
    for k in to_remove:
        del _AGENTS[k]
    await load_db_agents()


def get_agent(name: str) -> Optional[BaseAgent]:
    _init_builtin_agents()
    return _AGENTS.get(name)


def list_agents() -> list[dict]:
    _init_builtin_agents()
    return [
        {"name": a.name, "description": a.description, "dynamic": isinstance(a, DynamicAgent)}
        for a in _AGENTS.values()
    ]


# 快速关键词路由（不调用 LLM，速度快）
KEYWORD_ROUTES: list[tuple[list[str], str]] = [
    # 编程关键词 → CodeAgent
    (["代码", "编程", "函数", "bug", "调试", "debug", "实现", "写一个",
      "python", "javascript", "typescript", "java", "golang", "rust",
      "sql", "html", "css", "react", "vue", "api", "接口",
      "算法", "数据结构", "class", "def ", "import ", "function"],
     "coding_agent"),
    # 写作关键词 → WritingAgent
    (["写一篇", "文案", "翻译", "translate", "润色", "改写", "总结",
      "摘要", "邮件", "报告", "文章", "作文", "诗", "故事",
      "营销", "广告", "slogan", "标题", "大纲"],
     "writing_agent"),
    # 分析关键词 → AnalysisAgent
    (["分析", "对比", "评测", "优劣", "为什么", "原因", "趋势",
      "数据", "统计", "推理", "逻辑", "方案对比", "选择哪个",
      "利弊", "可行性", "评估"],
     "analysis_agent"),
    # 工具调用 / 技能调用关键词 → ReActAgent
    (["计算", "算一下", "帮我算", "几点", "什么时间", "几号", "星期几", "日期",
      "搜索", "查一下", "查询", "帮我查", "最新",
      "sqrt", "log", "sin", "cos", "多少天", "天后",
      # 实时联网数据工具触发词
      "天气", "气温", "下雨", "降雨", "降雪", "紫外线", "天气预报", "温度",
      "weather", "forecast", "几度",
      "股票", "股价", "股市", "大盘", "指数", "涨", "跌", "A股", "美股", "港股",
      "标普", "纳斯达克", "道琼斯", "上证", "恒生", "日经", "K线",
      "stock", "AAPL", "TSLA", "NVDA", "GOOGL", "MSFT",
      "苹果股", "特斯拉", "英伟达", "腾讯股", "阿里股",
      "比特币", "以太坊", "加密货币", "币价", "数字货币", "虚拟货币",
      "bitcoin", "btc", "ethereum", "eth", "crypto", "doge", "狗狗币",
      "sol", "solana", "币圈", "市值排行", "币安", "coinbase",
      "新闻", "头条", "热搜", "今日新闻", "最新消息", "资讯",
      "news", "headline", "trending",
      "全球时间", "世界时间", "时区", "纽约时间", "东京时间", "伦敦时间", "UTC",
      # 技能库常用触发词
      "生成密码", "密码", "转换", "单位", "汇率", "BMI", "卡路里",
      "base64", "编码", "解码", "哈希", "hash", "md5", "sha",
      "uuid", "jwt", "json格式", "格式化", "压缩图", "缩放图",
      "加密", "解密", "摩尔斯", "morse", "二维码", "qrcode",
      "抛硬币", "掷骰子", "随机", "倒计时", "记账", "待办",
      "番茄钟", "cron", "正则", "regex", "IP地址", "子网",
      "csv", "xml", "yaml", "markdown", "模板", "diff",
      "水印", "裁剪图", "旋转图", "缩略图", "拼图",
      "视频信息", "视频剪辑", "提取音频", "gif",
      # MCP 外接工具触发词
      "读文件", "写文件", "文件列表", "创建目录", "删除文件",
      "知识图谱", "记住", "回忆", "思维链", "分步思考",
      # MCP P1 扩展触发词
      "git log", "提交记录", "代码仓库", "分支", "commit", "git",
      "抓取网页", "提取正文", "读取链接",
      "搜索模型", "找模型", "数据集", "魔搭", "modelscope"],
     "react_agent"),
    # 规划执行关键词 → PlanExecuteAgent
    (["制定计划", "规划", "分步执行", "分步骤", "帮我规划", "执行方案",
      "多步骤", "步骤化", "拆解任务", "先...再...然后"],
     "plan_execute_agent"),
    # 浏览器关键词 → BrowserAgent
    (["打开网页", "截图", "screenshot", "网页截图", "抓取网页", "爬取",
      "浏览器", "访问网站", "提取网页", "网页内容"],
     "browser_agent"),
]


def route_by_keywords(content: str) -> Optional[str]:
    """关键词快速路由"""
    lower = content.lower()
    scores: dict[str, int] = {}
    for keywords, agent_name in KEYWORD_ROUTES:
        score = sum(1 for kw in keywords if kw in lower)
        if score > 0:
            scores[agent_name] = scores.get(agent_name, 0) + score

    if not scores:
        return None
    best = max(scores, key=scores.get)  # type: ignore
    # 匹配 1 个即路由（专业 Agent 关键词已足够明确）
    if scores[best] >= 1:
        return best
    return None


# LLM 路由 prompt
ROUTE_PROMPT = """你是一个意图分类器。根据用户的消息，判断应该由哪个 Agent 来处理。

可用 Agent：
- react_agent: 通用助手，支持工具调用（计算、时间查询、搜索）和 100 技能库（密码生成、编解码、格式化、图像处理等）。适合日常对话、简单问答、需要工具或技能的任务。
- coding_agent: 本地编程专家。适合代码生成、调试、直接编辑本地文件、运行终端测试等。
- writing_agent: 写作专家。适合文案创作、翻译、总结、改写。
- analysis_agent: 分析专家。适合数据分析、逻辑推理、方案对比、深度分析。
- plan_execute_agent: 规划执行专家。适合复杂多步骤任务、需要先拆解再逐步执行的场景。
- browser_agent: 浏览器控制专家。适合网页截图、内容提取、网页搜索。

用户消息：{message}

请只返回一个 Agent 名称，不要返回其他内容。例如：coding_agent"""


async def route_by_llm(content: str) -> str:
    """LLM 智能路由（更准确但更慢）"""
    try:
        client = get_llm_client()
        request = LLMRequest(
            messages=[{"role": "user", "content": ROUTE_PROMPT.format(message=content)}],
            model="nvidia/llama-3.1-nemotron-ultra-253b-v1",
            temperature=0.1,
            max_tokens=32,
            stream=False,
        )
        response = await client.complete(request)
        agent_name = response.content.strip().lower().replace('"', '').replace("'", "")
        # 验证返回的 agent 名称
        _init_builtin_agents()
        if agent_name in _AGENTS:
            return agent_name
    except Exception as e:
        print(f"  ⚠ LLM routing failed: {e}")

    return "react_agent"  # fallback


async def route(content: str, use_llm: bool = False) -> tuple[str, BaseAgent]:
    """路由用户消息到合适的 Agent

    Returns: (agent_name, agent_instance)
    """
    _init_builtin_agents()
    # 懒加载 DB 动态 Agent（首次调用时）
    if not _db_loaded:
        await load_db_agents()

    # 1. 先尝试关键词快速路由
    kw_result = route_by_keywords(content)
    if kw_result:
        return kw_result, _AGENTS[kw_result]

    # 2. 可选 LLM 路由
    if use_llm:
        llm_result = await route_by_llm(content)
        return llm_result, _AGENTS[llm_result]

    # 3. 默认 react_agent
    return "react_agent", _AGENTS["react_agent"]
