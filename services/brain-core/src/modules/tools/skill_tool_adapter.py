"""SkillToolAdapter — 此文件已在 v4.0 重构中被淘汰

v4.0 引入了基于 RAG 的动态语义技能路由 (Semantic Skill Routing)。
原本将 100 个技能全部打包注入 prompt 的 `run_skill` 分发工具已被废弃，
相关逻辑现已转移到 `ToolRegistry.get_dynamic_tool_schemas()` 中以支持按需加载。
"""

def bridge_skills_to_tools():
    """兼容旧版本的调用钩子，但不再向 ToolRegistry 注册污染上下文的 run_skill。
    技能现由大模型执行时直接当做一个平铺的自然工具名返回，并在 ToolRegistry 的 execute 环节回溯动态截获。
    """
    import logging
    logging.getLogger(__name__).info("Skill vectorization integration enabled instead of legacy static dispatch tool.")
