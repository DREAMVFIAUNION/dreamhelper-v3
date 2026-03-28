"""预置工作流模板 — 开箱即用的常见工作流

模板包含完整的节点定义和连线定义，用户可一键创建。
"""

import uuid
from typing import Any


def _id() -> str:
    return str(uuid.uuid4())[:8]


def _node(ntype: str, name: str, config: dict, x: float, y: float) -> dict:
    return {
        "id": _id(),
        "type": ntype,
        "name": name,
        "config": config,
        "position": {"x": x, "y": y},
    }


def _conn(source: str, target: str, source_handle: str = "output", target_handle: str = "input") -> dict:
    return {
        "id": _id(),
        "source": source,
        "target": target,
        "sourceHandle": source_handle,
        "targetHandle": target_handle,
    }


# ── 模板1: 智能客服 ──────────────────────────

def template_smart_customer_service() -> dict:
    """智能客服: Webhook触发 → LLM分析意图 → 多路分支 → 不同处理"""
    trigger = _node("trigger_webhook", "客户消息", {"path": "/cs"}, 0, 200)
    llm = _node("llm", "意图分析", {
        "prompt": "分析用户意图，输出JSON: {\"intent\": \"faq|complaint|order|other\", \"summary\": \"...\"}\n\n用户消息: {{input}}",
        "model": "nvidia/llama-3.1-nemotron-ultra-253b-v1",
        "temperature": 0.2,
    }, 300, 200)
    switch = _node("switch", "意图路由", {
        "field": "intent",
        "cases": [
            {"value": "faq", "operator": "equals"},
            {"value": "complaint", "operator": "equals"},
            {"value": "order", "operator": "equals"},
        ],
    }, 600, 200)
    faq_llm = _node("llm", "FAQ回答", {
        "prompt": "根据知识库回答用户FAQ问题: {{input}}",
        "model": "nvidia/llama-3.1-nemotron-ultra-253b-v1",
    }, 900, 50)
    complaint_notify = _node("notification", "投诉通知", {
        "channel": "email",
        "template": "收到用户投诉: {{input}}",
    }, 900, 200)
    order_http = _node("http", "查询订单", {
        "url": "https://api.example.com/orders",
        "method": "GET",
    }, 900, 350)

    nodes = [trigger, llm, switch, faq_llm, complaint_notify, order_http]
    connections = [
        _conn(trigger["id"], llm["id"]),
        _conn(llm["id"], switch["id"]),
        _conn(switch["id"], faq_llm["id"], "case_0"),
        _conn(switch["id"], complaint_notify["id"], "case_1"),
        _conn(switch["id"], order_http["id"], "case_2"),
    ]

    return {
        "name": "智能客服",
        "description": "Webhook接收消息 → LLM意图分析 → 多路分支处理",
        "category": "customer_service",
        "nodes": nodes,
        "connections": connections,
    }


# ── 模板2: 文档RAG处理 ──────────────────────────

def template_document_rag() -> dict:
    """文档RAG: 手动触发 → 文档处理 → LLM回答"""
    trigger = _node("trigger_manual", "开始", {}, 0, 200)
    transform = _node("transform", "提取问题", {
        "expression": "items[0].question",
        "output_key": "query",
    }, 250, 200)
    code = _node("code", "RAG检索", {
        "language": "python",
        "code": "from modules.rag.rag_pipeline import get_rag_pipeline\npipeline = get_rag_pipeline()\nresults = pipeline.retrieve(input_data['query'], top_k=3)\noutput = {'context': '\\n'.join(r.chunk.content for r in results)}",
    }, 500, 200)
    llm = _node("llm", "生成回答", {
        "prompt": "基于以下知识库内容回答用户问题。\n\n知识库:\n{{context}}\n\n问题: {{query}}",
        "model": "qwen3-235b-a22b",
        "temperature": 0.5,
    }, 750, 200)

    nodes = [trigger, transform, code, llm]
    connections = [
        _conn(trigger["id"], transform["id"]),
        _conn(transform["id"], code["id"]),
        _conn(code["id"], llm["id"]),
    ]

    return {
        "name": "文档RAG问答",
        "description": "手动输入问题 → RAG检索知识库 → LLM生成回答",
        "category": "rag",
        "nodes": nodes,
        "connections": connections,
    }


# ── 模板3: 定时日报 ──────────────────────────

def template_daily_report() -> dict:
    """定时日报: 定时触发 → 收集数据 → LLM生成日报 → 发送通知"""
    trigger = _node("trigger_cron", "每日触发", {"cron": "0 9 * * 1-5"}, 0, 200)
    http = _node("http", "获取统计数据", {
        "url": "http://localhost:8000/api/v1/chat/memory/stats",
        "method": "GET",
    }, 300, 200)
    llm = _node("llm", "生成日报", {
        "prompt": "根据以下系统统计数据，生成一份简洁的每日运营日报（中文）:\n\n{{input}}\n\n包含: 今日活跃度、关键指标变化、建议。",
        "model": "nvidia/llama-3.1-nemotron-ultra-253b-v1",
        "temperature": 0.6,
    }, 600, 200)
    notify = _node("notification", "发送日报", {
        "channel": "email",
        "template": "📊 每日运营日报\n\n{{input}}",
    }, 900, 200)

    nodes = [trigger, http, llm, notify]
    connections = [
        _conn(trigger["id"], http["id"]),
        _conn(http["id"], llm["id"]),
        _conn(llm["id"], notify["id"]),
    ]

    return {
        "name": "每日运营日报",
        "description": "工作日9:00自动生成运营日报并发送邮件",
        "category": "automation",
        "nodes": nodes,
        "connections": connections,
    }


# ── 模板4: 批量文档摘要 ──────────────────────────

def template_batch_summary() -> dict:
    """批量摘要: 手动触发 → 循环处理 → LLM生成摘要 → 合并结果"""
    trigger = _node("trigger_manual", "输入文档列表", {}, 0, 200)
    loop = _node("loop", "遍历文档", {
        "item_key": "documents",
        "max_iterations": 20,
        "output_mode": "collect",
    }, 250, 200)
    llm = _node("llm", "生成摘要", {
        "prompt": "请为以下文档生成100字以内的中文摘要:\n\n{{value}}",
        "model": "nvidia/llama-3.1-nemotron-ultra-253b-v1",
        "temperature": 0.3,
    }, 500, 200)
    merge = _node("merge", "合并摘要", {
        "mode": "concat",
    }, 750, 200)

    nodes = [trigger, loop, llm, merge]
    connections = [
        _conn(trigger["id"], loop["id"]),
        _conn(loop["id"], llm["id"], "item"),
        _conn(llm["id"], merge["id"]),
    ]

    return {
        "name": "批量文档摘要",
        "description": "输入多个文档 → 逐一生成摘要 → 合并为报告",
        "category": "document",
        "nodes": nodes,
        "connections": connections,
    }


# ── 模板5: 多模型对比 ──────────────────────────

def template_model_comparison() -> dict:
    """多模型对比: 同一问题分别发给不同LLM → 合并对比"""
    trigger = _node("trigger_manual", "输入问题", {}, 0, 200)
    llm_left = _node("llm", "MiniMax回答", {
        "prompt": "{{input}}",
        "model": "nvidia/llama-3.1-nemotron-ultra-253b-v1",
    }, 300, 100)
    llm_right = _node("llm", "Qwen回答", {
        "prompt": "{{input}}",
        "model": "qwen3-235b-a22b",
    }, 300, 300)
    merge = _node("merge", "合并对比", {
        "mode": "object",
    }, 600, 200)
    llm_judge = _node("llm", "评估对比", {
        "prompt": "对比以下两个AI模型的回答，评估各自优劣:\n\nMiniMax: {{a}}\n\nQwen: {{b}}\n\n请给出评分(1-10)和分析。",
        "model": "glm-4.7",
        "temperature": 0.3,
    }, 900, 200)

    nodes = [trigger, llm_left, llm_right, merge, llm_judge]
    connections = [
        _conn(trigger["id"], llm_left["id"]),
        _conn(trigger["id"], llm_right["id"]),
        _conn(llm_left["id"], merge["id"], "output", "input_a"),
        _conn(llm_right["id"], merge["id"], "output", "input_b"),
        _conn(merge["id"], llm_judge["id"]),
    ]

    return {
        "name": "多模型对比",
        "description": "同一问题发给多个LLM，对比回答质量",
        "category": "evaluation",
        "nodes": nodes,
        "connections": connections,
    }


# ── 模板注册表 ──────────────────────────

WORKFLOW_TEMPLATES: dict[str, dict[str, Any]] = {}


def get_all_templates() -> list[dict]:
    """获取所有可用的工作流模板"""
    templates = [
        template_smart_customer_service(),
        template_document_rag(),
        template_daily_report(),
        template_batch_summary(),
        template_model_comparison(),
    ]
    return [
        {
            "id": f"tpl_{i}",
            "name": t["name"],
            "description": t["description"],
            "category": t["category"],
            "node_count": len(t["nodes"]),
            "connection_count": len(t["connections"]),
        }
        for i, t in enumerate(templates)
    ]


def get_template_detail(template_id: str) -> dict | None:
    """获取模板详情（含完整节点和连线）"""
    templates = [
        template_smart_customer_service(),
        template_document_rag(),
        template_daily_report(),
        template_batch_summary(),
        template_model_comparison(),
    ]
    idx = template_id.replace("tpl_", "")
    try:
        return templates[int(idx)]
    except (ValueError, IndexError):
        return None
