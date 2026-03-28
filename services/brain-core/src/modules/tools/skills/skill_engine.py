"""
技能引擎 — 安全沙箱执行 + 技能注册 + 参数校验

安全限制:
- 执行超时: 10秒
- 输出限制: 10KB
- 禁止 import (技能必须纯函数)
"""

import asyncio
import logging
import math
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel

from ...llm.embedding.batch_embedder import BatchEmbedder


class SkillSchema(BaseModel):
    """技能输入参数 Schema 基类"""
    pass


class BaseSkill(ABC):
    """技能基类"""
    name: str
    description: str
    category: str  # daily, office, coding, document, entertainment
    args_schema: Type[SkillSchema]
    version: str = "1.0.0"
    tags: list[str] = []

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        ...

    def to_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "version": self.version,
            "tags": self.tags,
            "parameters": self.args_schema.model_json_schema(),
        }


EXECUTION_TIMEOUT = 10  # seconds
MAX_OUTPUT_LENGTH = 10_000  # chars


class SkillEngine:
    """全局技能引擎"""

    _skills: Dict[str, BaseSkill] = {}
    _embeddings: Dict[str, List[float]] = {}
    _is_vectorized: bool = False

    @classmethod
    def register(cls, skill: BaseSkill):
        cls._skills[skill.name] = skill

    @classmethod
    def get(cls, name: str) -> Optional[BaseSkill]:
        return cls._skills.get(name)

    @classmethod
    def list_skills(cls) -> List[dict]:
        return [s.to_schema() for s in cls._skills.values()]

    @classmethod
    def list_by_category(cls, category: str) -> List[dict]:
        return [s.to_schema() for s in cls._skills.values() if s.category == category]

    @classmethod
    def search(cls, query: str) -> List[dict]:
        q = query.lower()
        results = []
        for s in cls._skills.values():
            if q in s.name.lower() or q in s.description.lower() or any(q in t.lower() for t in s.tags):
                results.append(s.to_schema())
        return results

    @classmethod
    def categories(cls) -> Dict[str, int]:
        cats: Dict[str, int] = {}
        for s in cls._skills.values():
            cats[s.category] = cats.get(s.category, 0) + 1
        return cats

    @classmethod
    async def vectorize_all_skills(cls):
        """预计算并缓存所有技能的 Embedding。
        此过程应在启动后异步执行一次。
        """
        if cls._is_vectorized or not cls._skills:
            return

        embedder = BatchEmbedder()
        names = list(cls._skills.keys())
        texts = [
            f"技能名称: {s.name}。分类: {s.category}。功能描述: {s.description}。标签: {','.join(s.tags)}"
            for s in cls._skills.values()
        ]
        
        try:
            logging.getLogger(__name__).info("开始为 %d 个技能计算语义向量...", len(texts))
            embeddings = await embedder.embed(texts)
            for idx, name in enumerate(names):
                cls._embeddings[name] = embeddings[idx]
            cls._is_vectorized = True
            logging.getLogger(__name__).info("✓ %d 技能向量化完成。", len(texts))
        except Exception as e:
            logging.getLogger(__name__).error("技能向量化失败 (降级为字符匹配): %s", e)

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm_a = math.sqrt(sum(a * a for a in vec1))
        norm_b = math.sqrt(sum(b * b for b in vec2))
        return 0.0 if (norm_a * norm_b) == 0 else dot_product / (norm_a * norm_b)

    @classmethod
    async def search_semantic(cls, query: str, top_k: int = 5) -> List[BaseSkill]:
        """动态语义召回技能：根据用户 query 选择最相关的前 K 个技能对象"""
        if not cls._skills:
            return []

        # 降级: 未提供向量化 (可能没有配置 LLM API) 或者只有少部分技能时，退化为文本规则搜索
        if not cls._is_vectorized:
            fallback_schemas = cls.search(query)
            matched_names = [s["name"] for s in fallback_schemas[:top_k]]
            return [cls._skills[n] for n in matched_names if n in cls._skills]

        # 计算 query 向量
        embedder = BatchEmbedder()
        try:
            query_vecs = await embedder.embed([query])
            if not query_vecs:
                return []
            q_vec = query_vecs[0]
        except Exception as e:
            logging.getLogger(__name__).error("查询向量化失败: %s", e)
            return []

        # 暴力计算相似度
        scores = []
        for name, emb in cls._embeddings.items():
            sim = cls._cosine_similarity(q_vec, emb)
            scores.append((sim, name))

        # 排序取 Top-K
        scores.sort(key=lambda x: x[0], reverse=True)
        top_skills = [
            cls._skills[name] 
            for sim, name in scores[:top_k] 
            if sim > 0.45  # 相似度阈值过滤(可选)
        ]
        
        # 如果过于严苛导致未命中任何，按文本再补一些
        if not top_skills:
            fallback = cls.search(query)
            if fallback:
                top_skills = [cls._skills[fallback[0]["name"]]]

        return top_skills

    @classmethod
    async def execute(cls, name: str, **kwargs: Any) -> dict:
        """安全执行技能 (带超时和输出限制)"""
        skill = cls._skills.get(name)
        if not skill:
            return {"success": False, "error": f"技能 '{name}' 不存在", "result": None}

        # 参数校验
        try:
            validated = skill.args_schema(**kwargs)
            params = validated.model_dump()
        except Exception as e:
            return {"success": False, "error": f"参数校验失败: {e}", "result": None}

        # 带超时执行
        try:
            result = await asyncio.wait_for(
                skill.execute(**params),
                timeout=EXECUTION_TIMEOUT,
            )

            # 输出截断
            if isinstance(result, str) and len(result) > MAX_OUTPUT_LENGTH:
                result = result[:MAX_OUTPUT_LENGTH] + "\n...(输出已截断)"

            return {"success": True, "error": None, "result": result, "skill": name}

        except asyncio.TimeoutError:
            return {"success": False, "error": f"执行超时 ({EXECUTION_TIMEOUT}s)", "result": None}
        except Exception as e:
            logging.getLogger(__name__).exception("Skill execution failed: %s", name)
            return {"success": False, "error": "技能执行失败", "result": None}
