"""查询增强 — LLM查询改写 + 关键词提取 + 多查询扩展

策略:
1. 关键词提取: 从用户查询中提取核心关键词（无需LLM, 即时）
2. 查询改写: 用LLM将模糊查询改写为更精确的检索查询
3. 多查询扩展: 生成多个不同角度的查询，提升召回率
"""

import re
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 中文停用词（高频低信息量）
_STOPWORDS = frozenset([
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些",
    "什么", "怎么", "如何", "为什么", "可以", "能", "吗", "呢", "啊",
    "帮我", "请", "告诉", "介绍", "关于", "一下", "请问",
])

REWRITE_PROMPT = """你是一个搜索查询优化专家。请将用户的自然语言问题改写为更适合知识库检索的查询。

用户原始问题: {query}

请输出一个JSON对象（不要输出其他内容）:
```json
{{
  "rewritten": "改写后的精确查询（去除口语化表述，保留核心意图）",
  "keywords": ["关键词1", "关键词2", "关键词3"],
  "alternatives": ["替代查询1", "替代查询2"]
}}
```

要求:
- rewritten: 更精确、更适合检索的表述
- keywords: 3-5个核心关键词
- alternatives: 1-2个不同角度的替代查询（用于多路召回）"""


class QueryEnhancer:
    """查询增强器 — 提升RAG检索质量"""

    def __init__(self, use_llm: bool = True):
        self._use_llm = use_llm

    def extract_keywords(self, query: str) -> list[str]:
        """即时关键词提取（无需LLM, <1ms）"""
        # 中文: 按字符ngram + 排除停用词
        words = []
        # 英文词
        for w in re.findall(r'[a-zA-Z]{2,}', query.lower()):
            words.append(w)
        # 中文: 2-4字 ngram（简单但有效）
        cn_chars = [ch for ch in query if '\u4e00' <= ch <= '\u9fff']
        for n in (4, 3, 2):
            for i in range(len(cn_chars) - n + 1):
                gram = "".join(cn_chars[i:i + n])
                if gram not in _STOPWORDS:
                    words.append(gram)

        # 去除停用词和过短的词
        filtered = [w for w in words if w not in _STOPWORDS and len(w) >= 2]

        # 去重保序
        seen = set()
        result = []
        for w in filtered:
            if w not in seen:
                seen.add(w)
                result.append(w)

        return result[:8]  # 最多8个关键词

    async def enhance(self, query: str) -> list[str]:
        """返回增强后的查询列表（原始 + 改写 + 关键词）"""
        queries = [query]

        # 1. 关键词增强（即时）
        keywords = self.extract_keywords(query)
        if keywords:
            kw_query = " ".join(keywords)
            if kw_query != query:
                queries.append(kw_query)

        # 2. LLM 改写（异步, 可选）
        if self._use_llm and len(query) > 10:
            try:
                rewritten = await self._llm_rewrite(query)
                if rewritten:
                    queries.extend(rewritten)
            except Exception as e:
                logger.debug("LLM查询改写跳过: %s", e)

        # 去重
        seen = set()
        unique = []
        for q in queries:
            q_norm = q.strip().lower()
            if q_norm and q_norm not in seen:
                seen.add(q_norm)
                unique.append(q.strip())

        return unique[:5]  # 最多5个查询变体

    async def _llm_rewrite(self, query: str) -> list[str]:
        """使用LLM改写查询"""
        from ..llm.llm_client import get_llm_client
        from ..llm.types import LLMRequest

        client = get_llm_client()
        prompt = REWRITE_PROMPT.format(query=query)

        response = await client.complete(LLMRequest(
            messages=[{"role": "user", "content": prompt}],
            model="nvidia/llama-3.1-nemotron-ultra-253b-v1",  # NVIDIA 免费模型
            temperature=0.2,
            max_tokens=512,
            stream=False,
        ))

        result = self._parse_response(response.content)
        queries = []
        if result.get("rewritten"):
            queries.append(result["rewritten"])
        queries.extend(result.get("alternatives", []))
        return queries

    @staticmethod
    def _parse_response(content: str) -> dict:
        """解析LLM返回的JSON"""
        try:
            text = content.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return {}
