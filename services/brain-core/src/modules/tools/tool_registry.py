"""工具注册与执行系统（第一章 1.4）"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Type
from pydantic import BaseModel


class BaseTool(ABC):
    name: str
    description: str
    args_schema: Type[BaseModel]

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        ...

    def to_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.args_schema.model_json_schema(),
        }


class ToolRegistry:
    """全局工具注册中心"""

    _tools: Dict[str, BaseTool] = {}

    @classmethod
    def register(cls, tool: BaseTool):
        cls._tools[tool.name] = tool

    @classmethod
    def get(cls, name: str) -> BaseTool | None:
        tool = cls._tools.get(name)
        if tool:
            return tool
        # Fallback pseudo-tool logic for skill validation
        from .skills.skill_engine import SkillEngine
        skill = SkillEngine.get(name)
        if skill:
            return skill # BaseSkill duck-types with BaseTool close enough for truthiness check
        return None



    @classmethod
    def list_tools(cls) -> list[dict]:
        return [t.to_schema() for t in cls._tools.values()]

    @classmethod
    async def get_dynamic_tool_schemas(cls, query: str = "", top_k: int = 5) -> list[dict]:
        """动态合成本次对话可用的工具集，包含静态的基础 Tool 和按语义召回的 Top-K Skills。"""
        schemas = cls.list_tools()
        if not query:
            return schemas
            
        from .skills.skill_engine import SkillEngine
        try:
            skills = await SkillEngine.search_semantic(query, top_k)
            for s in skills:
                schemas.append(s.to_schema())
        except Exception:
            pass
            
        return schemas

    @classmethod
    async def execute(cls, name: str, **kwargs: Any) -> str:
        tool = cls._tools.get(name)
        if tool:
            return await tool.execute(**kwargs)
            
        # Fallback to dynamic skill execution
        from .skills.skill_engine import SkillEngine
        skill = SkillEngine.get(name)
        if skill:
            result = await SkillEngine.execute(name, **kwargs)
            if result.get("success"):
                return str(result.get("result"))
            return f"Error executing skill: {result.get('error', 'Unknown error')}"

        raise ValueError(f"Tool '{name}' not found")
