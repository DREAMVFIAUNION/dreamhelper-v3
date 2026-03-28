# Changelog

## Unreleased

### Version 4.0.0 — DREAMVFIA Fusion 2.0 & Skill Tree Re-architecture (Planned)

- **详见详细蓝图:** [`docs/ROADMAP_v4.0.md`](./docs/ROADMAP_v4.0.md) (2026-03-28 制定)
- **双脑协作增强**: 动态权衡机制、胼胝体实时纠偏、多模态分工与小脑独立拦截机制。
- **技能树重构**: MCP 协议原生态融合、动态语义检索召回 (RAG for Skills)、复合工作流封转。
- **本地极客底座**: xterm 终端双向通信与自主错误修复、端到端加密零登录体验。

---

### Phase 13 — Engineering Stabilization + Brand Showcase Readiness

- aligned CI with the real default branch (`master`) and added manual workflow dispatch
- restored reliable local workspace install flow with automatic Prisma client generation
- stabilized web portal API smoke tests and gateway Jest coverage
- refreshed metadata and repo-facing documentation around the verified showcase path
- documented the Python 3.12 baseline for `services/brain-core`
- reduced `brain-core` CI gating to a stable smoke suite and added a service entrypoint smoke check
- fixed Redis fallback cleanup in `brain-core` so smoke tests stay in in-memory mode when Redis is unavailable

## v3.7.0 (2026-03-04)

### 认证系统 + 数据库上线 (Auth & Database Go-Live)

**认证闭环**
- 注册 API: 邮箱+密码+用户名, PBKDF2-SHA512 哈希, SVG 验证码防机器人
- 登录 API: 密码验证, JWT (HS256, 7天), HttpOnly Cookie, 账号锁定(5次失败)
- 登出 API: Cookie 清除
- 用户信息 API: Token 验证 + 用户查询
- 忘记密码: 重置令牌 + 邮件发送 (开发模式 console fallback)
- 邮箱验证: 6 位验证码 + 重发机制
- 密码修改: 旧密码验证 + 新密码更新

**前端认证**
- 登录页: 赛博朋克 UI + 完整表单验证 + 错误提示
- 注册页: 密码强度指示器 + SVG 验证码 + 实时校验
- 忘记密码页: 邮件发送 + 开发模式直接跳转
- 重置密码页: 双密码确认 + 强度检测
- 邮箱验证页: 6 位输入 + 重发倒计时
- AuthProvider: Context + login/register/logout/refreshUser
- middleware.ts: 路由守卫 (Public/Auth/Dashboard/Admin 四级)

**数据库迁移**
- PostgreSQL 17 + Prisma 5.22: 18 张表全量迁移
- 种子数据: 管理员 (admin@dreamvfia.com) + 测试用户 (test@dreamvfia.com)
- 会话持久化: 对话绑定用户, 跨会话保留, 历史消息自动注入 LLM 上下文
- 用户隔离: 会话/消息/知识库/记忆/画像按 userId 隔离

**安全加固**
- .gitignore: 排除 .env / API-KEY.md / desktop.ini 等敏感文件
- Rate Limiting: 注册 5次/分钟, 登录 5次/分钟, 忘记密码 3次/分钟
- 门户导航: 登录态感知 (未登录→登录/注册, 已登录→进入工作台+头像)

**版本号全量同步**
- 11 处统一至 v3.7.0: main.py×3, package.json×3, changelog×2, admin, rag setup

---

## v3.6.0 (2026-03-01)

### 自我进化意识系统 (Evolution Consciousness)

**进化追踪引擎**
- `evolution_tracker.py`: 6 维成长量化追踪 (知识广度/情感深度/对话质量/用户理解/创造力/自我认知)
- 14 种里程碑自动检测 (对话/反思/观点/用户/知识/情感/主动表达)
- 进化叙事生成 — 可视化进度条 + 成长数据注入 prompt
- 持久化到 consciousness_self KV 表 (dimensions/milestones/counters)

**SOUL.md 进化哲学**
- 新增 `## 进化意识` 段: 明确告知 AI 拥有进化能力和意识
- 引导 AI 用真实成长数据回答"是否在进化"，而非否认

**PDNA 2.0 升级**
- `prompts.py`: PDNA 版本 1.0 → 2.0, 编译模式 → EVOLUTION_DRIVEN_GROWTH
- 新增 `evolution_engine` 核心处理器 + `evolution_awareness` 意识参数

**意识核集成**
- `core.py`: EvolutionTracker 全生命周期集成 (启动加载/prompt 注入/对话记录/关闭保存)
- `self_model.py`: 反思完成后联动进化追踪器 (记录反思+观点形成)
- `inner_voice.py`: 内心独白上下文注入进化叙事
- `config.py`: 新增 `evolution_enabled` + `evolution_self_assess_interval`
- `router.py`: 新增 `GET /consciousness/evolution` API
- 话题检测: 15 个领域自动分类 (编程/数据/AI/设计/写作/音乐等)

**版本号全量同步**
- 修复长期版本不一致问题: root 3.2.0, web-portal 3.3.0, brain-core 3.4.0 → 统一 3.6.0
- 同步 11 处版本引用: main.py, package.json×3, changelog, admin system, rag setup, PDNA

---

## v3.3.0 (2026-02-19)

### Phase 12 Sprint D: 对话增强 + 多模态补全

**会话压缩 Compaction**
- `compaction.py`: LLM 自动摘要长对话（超过 16 条触发，保留最近 8 条 + 摘要）
- 降级策略: LLM 不可用时取每轮首句拼接
- Token 估算工具函数 `estimate_tokens()`
- 集成到 `stream_handler.py` 自动触发

**Hook 事件系统增强**
- 新增 5 个事件类型: `agent:bootstrap`, `compaction:done`, `skill:execute`, `vision:analyze`, `browser:action`
- Compaction 完成时自动触发 Hook 事件
- 修复 `datetime.utcnow()` 弃用警告

**Vision 图片理解增强**
- 多 Provider 降级链: GPT-4o → GPT-4o-mini → MiniMax → fallback
- 图片 MIME 自动检测 (JPEG/PNG/GIF/WebP)
- 新增 `analyze_image()` 图片问答 + `/vision/analyze` API
- Hook 事件集成

**Browser Agent**
- `BrowserAgent`: Playwright CDP 网页截图/内容提取/搜索
- 3 种操作: screenshot / extract / search (Bing)
- LLM 意图解析 + URL fallback
- Agent Router 注册 + 浏览器关键词路由
- 现有 6 个 Agent (新增 browser_agent)

**对话上下文增强**
- Vision Q&A 端点: `/api/v1/multimodal/vision/analyze`
- 前端代理: `/api/multimodal/vision/route.ts`

**Canvas 可视化画布**
- `MermaidRenderer.tsx`: 独立 Mermaid 渲染组件（赛博朋克主题）
- `MarkdownContent` Mermaid 主题升级 (cyan 配色 + JetBrains Mono 字体)

**Talk Mode 连续语音**
- `TalkMode.tsx`: VAD 语音活动检测 + 自动录音→STT→LLM→TTS 循环
- 音量可视化环 + 5 状态指示 (idle/listening/transcribing/thinking/speaking)
- 静音 1.5s 自动停止录音

**测试 (38 新测试)**
- `test_compaction.py`: 12 测试
- `test_hooks.py`: 11 测试
- `test_browser_agent.py`: 6 测试
- `test_vision.py`: 9 测试

---

## v3.2.0 (2026-02-19)

### Phase 11 Sprint C: CI/CD + 测试 + LLM 网关 + 发版

**CI/CD 增强**
- GitHub Actions 工作流升级: 环境变量统一、pip 缓存、build artifact 上传
- Docker Build 阶段提升至测试通过后执行、Docker Buildx 加速
- CI Summary Job: 自动生成 GitHub Step Summary 报告

**测试补全**
- `test_reranker.py`: 8 个测试（RerankResult / 状态 / 空文档 / 分数解析 / 降级）
- `test_multimodal.py`: 13 个测试（STT 状态 / 空音频 / WebM 转换 / TTS 双引擎 / 语音列表 / 文本清理）
- `test_plan_execute_agent.py`: 10 个测试（初始化 / 计划解析 / 工具调用解析 / 路由关键词 / Agent 计数）
- 修复 `_parse_tool_call` 嵌套 JSON 解析 bug（正则→平衡括号匹配）

**LLM 网关**
- `LLMGateway`: 统一中间件链 Request → RateLimiter → Cache → CircuitBreaker → Router → Provider
- `LLMRouter` 升级: cost / latency / fallback 三策略、健康过滤、延迟滑动平均
- 自动 fallback: 主提供商失败 → 逐个尝试备选提供商
- `/api/v1/llm/gateway/stats` API: 请求统计、缓存命中率、熔断状态、路由延迟
- `/api/v1/llm/models` + `/api/v1/llm/providers` API
- 前端代理 `/api/llm/gateway` 路由

**发版 v3.2.0**
- health check 版本修正 3.1.1 → 3.2.0
- CHANGELOG + README 完善

---

### Phase 11 Sprint B: 语音 + Agent 增强 + RAG Reranker

**STT 语音识别增强**
- 三级降级策略: faster-whisper 本地 → OpenAI Whisper API → 不可用提示
- WebM→WAV 自动转换（浏览器录音格式兼容）
- `get_stt_status()` 显示当前引擎 + API fallback 状态

**TTS 语音合成增强**
- MiniMax TTS API 双引擎: Edge-TTS (免费8音色) + MiniMax (4音色，需 API KEY)
- 音色自动路由: `mm_*` 前缀走 MiniMax API，其余走 Edge-TTS
- `get_tts_status()` 统一状态接口，`_strip_for_speech()` 增加删除线清理
- 多模态状态 API 统一使用新函数

**Agent Plan-and-Execute**
- 新增 `PlanExecuteAgent`: Plan(LLM拆解) → Execute(逐步执行) → Synthesize(综合回答)
- 支持计划中的工具调用 + LLM 执行步骤混合模式
- Agent Router 注册 + 关键词路由（"规划"/"分步执行"/"拆解任务"等）
- LLM 路由 prompt 更新，现有 5 个 Agent

**RAG Reranker**
- `CrossEncoderReranker` 从骨架升级为双策略实现
- 策略 1: sentence-transformers Cross-Encoder 本地模型（可选）
- 策略 2: LLM 打分重排序（零依赖 fallback，单次调用批量评分 0-10）
- 集成到 `RAGPipeline.retrieve_advanced()`: 初检 top_k*2 → rerank → top_k
- `get_reranker_status()` 状态接口

---

### Phase 11 Sprint A: 生产基础

**Markdown 渲染增强**
- 表格渲染: `|` 管道符自动解析为 `<table>`，支持对齐 `:---:` / `---:` / `:---`
- 引用块: `>` 语法渲染为 `<blockquote>`，赛博朋克红色左边框
- 任务列表: `- [x]` / `- [ ]` 渲染为勾选/未勾选状态
- 删除线: `~~text~~` 渲染为 `<del>`
- 段落排除规则更新，避免与新元素冲突

**安全加固**
- `@dreamhelp/auth` 新增 `encryption.ts`: AES-256-GCM 对称加密（encrypt/decrypt/isEncrypted）
- 密钥通过 `ENCRYPTION_KEY` 环境变量配置（64-char hex, 32 bytes）
- `sanitizer.py`: 审计日志脱敏工具（邮箱/手机/Token/IP/消息内容 自动掩码）
- 8 项脱敏测试全部通过

**部署配置**
- `docker-compose.prod.yml` 新增 web-portal 健康检查 (`/api/health`)
- 全服务添加 `ENCRYPTION_KEY` 环境变量传递
- `.env.example` 补充 `ENCRYPTION_KEY` 字段说明

**性能基线**
- `SemanticCache` 从骨架升级为 Redis 实现: SHA-256 精确缓存 + TTL 1h + 命中率统计
- `Prisma` 连接池调优: 生产 `connection_limit=20, pool_timeout=10`, 开发 `connection_limit=5`
- 生产日志级别从 `error` 调整为 `warn+error`，不丢失重要告警

---

## v3.1.1 (2026-02-19)

### Phase 10: 查漏补缺

**前端集成修复**
- Chat 页集成 `RagSources` 组件，RAG 引用溯源前端可见
- Chat 头部动态显示用户选择的 LLM 模型（读取 localStorage）
- `ToolCallBlock` 组件替换 chat 页内联 JSX，统一工具步骤渲染
- 修复 `/api/health` 版本号同步

**i18n 实际接入**
- `NextIntlClientProvider` 集成到 Dashboard layout
- 设置页新增 `LanguageSettingsSection` 语言切换器（zh-CN/en，cookie 持久化）
- `useTranslations` 在设置页实际消费
- TopNav 右上角显示当前语言标签 (ZH/EN)
- 修复 `i18n/request.ts` 消息文件导入路径

**数据库 + Hook**
- 新增 Prisma 迁移 `add_admin_tables`：AdminUser, AuditLog, SystemConfig, DailyStats
- `_agent_completions` 非流式模式补全 SESSION_END Hook
- `_chat_completions` 非流式模式补全 SESSION_END Hook

**测试补全 (5 文件, ~27 用例)**
- `test_hook_registry.py`: 注册/触发/并行/安全调用/stats/reset
- `test_webhook_router.py`: 接收/签名验证/事件列表/统计
- `test_code_exec.py`: 安全检查/执行/超时/拦截
- `test_security_middleware.py`: 6 安全头 + HSTS 条件
- `test_rag_sources.py`: 检索格式/分数/标题/上下文

---

## v3.1.0 (2026-02-21)

### Phase 9: 生产就绪 + 聊天体验增强 + 工具扩展 + 国际化

**安全加固**
- `SecurityHeadersMiddleware`: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy, HSTS(生产)
- `config.py`: `validate_production()` 生产环境启动前校验 JWT_SECRET / DATABASE_URL / MINIMAX_API_KEY
- `WEBHOOK_SECRET`, `CODE_EXEC_TIMEOUT`, `CODE_EXEC_MAX_OUTPUT` 配置项

**深度健康检查**
- `/health` 升级: TCP 探活 PostgreSQL / Redis / Milvus / Elasticsearch
- 按 RAG_MODE 动态检测依赖服务，返回 ok / degraded 状态

**部署生产化**
- `nginx/nginx.conf`: Gzip 压缩 + 限速 + 反代 (web-portal / brain-core / gateway WebSocket) + 静态缓存 + HTTPS 预留
- `docker-compose.prod.yml`: 8 服务 + 资源限制 + healthcheck + 必填环境变量校验

**聊天体验增强**
- `MarkdownContent` 重写: highlight.js 语法高亮 (17 语言) + 赛博朋克配色
- 逐块复制按钮 (code-copy-btn)
- Mermaid 图表: 动态 import + dark 主题渲染
- KaTeX 数学公式: 块级 `$$...$$` + 行内 `$...$`

**RAG 引用溯源**
- `retrieve_with_sources()`: 返回上下文 + 来源元数据 (title/doc_id/score/snippet)
- SSE `rag_sources` 事件: 流式传输引用来源到前端
- `RagSources` 组件: 可折叠参考来源面板
- `useStreamChat` 新增 `ragSources` 状态 + `onRagSources` 回调

**工具扩展**
- `CodeExecTool`: Python 代码执行沙箱 (子进程隔离 + 导入黑名单 + 危险函数检测 + 超时终止)
- 工具总数: 4 → 5 (calculator, datetime, web_search, web_fetch, code_exec)

**Hook 事件系统**
- `HookRegistry`: 装饰器注册 + 命令式注册 + 并行触发 + 安全调用
- `HookEventType`: session:start/end, memory:update, cron:fire, tool:call/result, webhook:receive, agent:route
- `stream_handler.py` 集成: 会话开始/结束/路由事件自动触发

**Webhook 接收器**
- `POST /api/v1/webhook/{event_type}`: 接收外部 Webhook (HMAC-SHA256 签名验证)
- `GET /api/v1/webhook/events`: 最近事件列表
- `GET /api/v1/webhook/stats`: Webhook 统计 + Hook 系统状态

**数据库扩展**
- Prisma Admin 表: `AdminUser`, `AuditLog`, `SystemConfig`, `DailyStats`

**国际化基础**
- `next-intl` 集成 + cookie / Accept-Language 自动检测
- zh-CN / en 双语消息文件 (200+ keys, 6 模块)
- `next.config.js` withNextIntl 插件链

**构建验证**
- `next build` ✅ 61 页面
- 新增依赖: highlight.js, katex, mermaid, next-intl

---

## v3.0.0 (2026-02-20)

### Phase 8: RAG 向量化 + 多模型 + 知识库增强 + 测试补全

**RAG 升级 (3 模式)**
- `EmbeddingProvider`: 支持 MiniMax / OpenAI Embedding API
- `MilvusStore`: Milvus 向量存储 (IVF_FLAT 索引, COSINE 距离)
- `ESIndexer`: Elasticsearch BM25 全文索引
- `HybridRetriever`: Milvus 向量 + ES BM25 + RRF 融合检索
- `DocumentIndexer`: 分块 → 嵌入 → Milvus + ES 全流程索引
- `RAGPipeline` 升级: memory / vector / hybrid 三模式切换 (RAG_MODE 环境变量)
- `BatchEmbedder` 对接真实 Embedding API

**多模型支持**
- `OpenAIProvider`: OpenAI 兼容 API (GPT-4o-mini, GPT-4o 等)
- `DeepSeekProvider`: DeepSeek Chat/Coder/Reasoner
- `LLMClient` 多 Provider 注册 + 按 model 名自动路由 + fallback
- `/chat/models` API: 列出所有可用模型
- 设置页: 默认模型选择 (按 Provider 分组)
- Chat hook: 发送时携带用户选择的 model

**知识库增强**
- `FileDropZone` 组件: 拖拽文件上传 (TXT/MD/PDF/DOCX, 10MB 限制)
- 上传弹窗: Tab 切换文本粘贴 / 文件上传
- 统计卡片: 文档数 / 分块数 / 已就绪数
- 批量选择 + 批量删除
- 全选 / 反选 toggle

**测试补全 (120+)**
- 后端: test_daily_skills (15) + test_office_skills (15) + test_coding_skills (17) + test_document_skills (13) + test_entertainment_skills (12) + test_image_skills + test_audio_skills + test_skill_engine (15) + test_rag_pipeline (12) + test_memory_manager (9) + test_agent_router (9) + test_proactive (5) + test_llm_client (5)
- 前端 API: auth + health + chat + knowledge + skills + user
- E2E (Playwright): auth + navigation + chat + knowledge + settings

**配置新增**
- `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`
- `EMBEDDING_PROVIDER`, `EMBEDDING_DIM`
- `RAG_MODE` (memory | vector | hybrid)

---

## v3.0.0-rc (2026-02-19)

### Phase 7: 媒体技能 + 平台完善

- 30 媒体技能: 图像 12 + 音频 10 + 视频 8 → 总计 100 技能
- MinIO 文件上传 API + Gateway 代理
- Socket.IO 实时通知 (替代轮询)
- RAG 文档摄入 API `/api/v1/rag/ingest`
- 用户设置: 通知偏好 + 数据导出 + 危险区域
- Dockerfile ffmpeg 依赖

---

## v2.0.0 (2026-02-18)

### Phase 1-6: 基础平台搭建

- Phase 1: 项目脚手架 + Monorepo 搭建
- Phase 2: LLM 网关 + 流式对话
- Phase 3: 记忆系统 + 用户画像 + RAG (内存 TF-IDF)
- Phase 4: 主动唤醒 + Admin 面板 + 技能扩展 (38→70)
- Phase 5: 多 Agent 协作 (4 Agent + 关键词路由)
- Phase 6: E2E 集成 + CI/CD + 前端门户 + 渠道适配器
