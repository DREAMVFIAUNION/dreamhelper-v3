# 
```
██████╗ ███████╗████████╗██████╗  ██████╗ ██████╗  ██████╗  █████╗ ██████╗ ██████╗ 
██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔═══██╗██╔══██╗██╔═══██╗██╔══██╗██╔══██╗
██████╔╝█████╗     ██║   ██████╔╝██║   ██║██████╔╝██║   ██║██████╔╝██║  ██║
██╔══██╗██╔══╝     ██║   ██╔══██╗██║   ██║██╔══██╗██║   ██║██╔══██╗██║  ██║
██║  ██║███████╗   ██║   ██║  ██║╚██████╔╝██║  ██║╚██████╔╝██║  ██║██████╔╝
╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═════╝ 
```
---

<p align="center">
  <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&weight=600&size=32&pause=1000&color=00FF00&center=true&vCenter=true&width=435&lines=💻+DREAMVFIA+AI+Assistant;🚀+v3.7.0+Enterprise+Edition;🔮+100+Skills+%7C+5+Agents;⚡+800+TOPS+GPU+Power" alt="Typing SVG" />
</p>

<p align="center">
  <a href="https://github.com/DREAMVFIAUNION/dreamhelper-v3">
    <img src="https://img.shields.io/github/stars/DREAMVFIAUNION/dreamhelper-v3?style=flat&color=00ff00" alt="stars">
  </a>
  <a href="https://github.com/DREAMVFIAUNION/dreamhelper-v3">
    <img src="https://img.shields.io/github/forks/DREAMVFIAUNION/dreamhelper-v3?style=flat&color=00ff00" alt="forks">
  </a>
  <a href="https://github.com/DREAMVFIAUNION/dreamhelper-v3/releases">
    <img src="https://img.shields.io/github/v/release/DREAMVFIAUNION/dreamhelper-v3?color=00ff00&label=Version" alt="release">
  </a>
  <a href="https://github.com/DREAMVFIAUNION/dreamhelper-v3/blob/master/LICENSE">
    <img src="https://img.shields.io/badge/License-PROPRIETARY-00ff00" alt="license">
  </a>
  <img src="https://img.shields.io/badge/Docker-7+Containers-00ff00" alt="docker">
  <img src="https://img.shields.io/badge/Python-3.12+-00ff00" alt="python">
  <img src="https://img.shields.io/badge/Next.js-15-00ff00" alt="nextjs">
</p>

---

<p align="center">
  <b>🎯 企业级 AI 助手 · 赛博朋克主题 · 100+ 技能 · 5 智能体 · 本地 GPU 加速</b>
</p>

---

## 📺 演示 Demo

<p align="center">
  <img src="https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Laptop/3D/laptop_3d.png" width="120" />
</p>

---

## ✨ 核心特性

```
┌─────────────────────────────────────────────────────────────────────┐
│                      🌟 DREAMVFIA v3.7.0                           │
├─────────────────────────────────────────────────────────────────────┤
│  🤖 5 智能体          │  💯 100+ 技能      │  🎯 99.9% 可用率   │
│  ⚡ 800+ TOPS GPU       │  🔮 RAG 知识库      │  📡 WebSocket      │
│  🎨 赛博朋克 UI        │  🔐 企业级安全      │  🚀 一键部署       │
│  🎤 语音合成/识别      │  📊 Admin 面板       │  💾 会话持久化     │
└─────────────────────────────────────────────────────────────────────┘
```

### 🎭 智能体系统

| 智能体 | 能力 | 场景 |
|--------|------|------|
| 🔵 **ReAct** | 工具调用推理 | 多步骤任务 |
| 💻 **Code** | 代码生成/执行 | 编程开发 |
| ✍️ **Writing** | 文本创作 | 内容生成 |
| 📈 **Analysis** | 数据分析 | 商业智能 |
| 🧠 **PlanExecute** | 规划执行 | 复杂任务 |

### 🎨 赛博朋克 UI

<p align="center">
  <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&size=14&pause=500&color=00FF00&background=0D1117&lines=◈+Neon+Glow+Effects;◈+Dark+Mode+First;◈+Animated+Components;◈+Cyber+Theme" alt="features">
</p>

---

## 🏗️ 系统架构

```
                    ┌─────────────────────────────────────┐
                    │         🚀 Next.js 15 Frontend      │
                    │    (React 19 + TailwindCSS)         │
                    └──────────────────┬──────────────────┘
                                       │ 
                    ┌──────────────────▼──────────────────┐
                    │        ⚡ NestJS Gateway            │
                    │    (Fastify + WebSocket)            │
                    └──────────────────┬──────────────────┘
                                       │
        ┌───────────────────────────────┼───────────────────────────────┐
        │                               │                               │
        ▼                               ▼                               ▼
┌───────────────┐           ┌───────────────────┐           ┌───────────────────┐
│   🧠 Brain    │           │   💾 PostgreSQL   │           │    📦 Redis      │
│   Core (AI)   │           │   (Database)      │           │   (Cache)         │
│   FastAPI     │           │   Prisma ORM      │           │   Pub/Sub         │
│   Python      │           │                   │           │                   │
└───────────────┘           └───────────────────┘           └───────────────────┘
        │
        ▼
┌───────────────┐  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│  📚 Milvus    │  │  🔍 Elasticsearch │  │    🖼️ MinIO     │  │   💻 GPU         │
│  (Vector)     │  │   (Full-text)     │  │   (Storage)      │  │   (Compute)      │
└───────────────┘  └───────────────────┘  └───────────────────┘  └───────────────────┘
```

---

## 🛠️ 技术栈

<div align="center">

| 层级 | 技术 |
|------|------|
| 🖥️ **前端** | Next.js 15 · React 19 · TailwindCSS · Framer Motion |
| 🌐 **网关** | NestJS 10 · Fastify · WebSocket |
| 🧠 **AI 核心** | Python 3.12 · FastAPI · Pydantic |
| 💾 **数据库** | PostgreSQL 17 · Prisma ORM · Redis 8 |
| 🔎 **检索** | Milvus 2.4 · Elasticsearch 8 |
| 🐳 **部署** | Docker Compose (7 容器) |
| 🧪 **测试** | Vitest · Pytest · Playwright |

</div>

---

## 📦 100+ 技能一览

```
╔═══════════════════════════════════════════════════════════════════════╗
║                        🎯 技能生态系统                                 ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                       ║
║  📱 日常    [15]  calculator · unit_converter · password_generator   ║
║                bmi_calculator · random_generator · countdown_timer    ║
║                                                                       ║
║  💼 办公    [15]  todo_manager · pomodoro_timer · json_formatter    ║
║                csv_analyzer · schedule_planner · invoice_generator    ║
║                                                                       ║
║  💻 编程    [15]  base64_codec · url_codec · hash_generator          ║
║                jwt_decoder · sql_formatter · code_formatter           ║
║                                                                       ║
║  📄 文档    [13]  markdown_processor · text_statistics · pdf_       ║
║                text_summarizer · word_counter                         ║
║                                                                       ║
║  🎮 娱乐    [12]  fortune_teller · name_generator · ascii_art        ║
║                sudoku_solver · rock_paper_scissors                   ║
║                                                                       ║
║  🖼️ 图像    [12]  image_resize · image_watermark · qrcode_           ║
║                image_filter · image_collage                           ║
║                                                                       ║
║  🎵 音频    [10]  audio_convert · audio_trim · audio_merge            ║
║                audio_volume · audio_speed                            ║
║                                                                       ║
║  🎬 视频    [8]   video_thumbnail · video_trim · video_merge          ║
║                video_to_gif · video_extract_audio                   ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
```

---

## 🚀 快速开始

### 前置要求

```
✅ Node.js ≥ 20      ✅ pnpm ≥ 9        ✅ Python ≥ 3.12
✅ Docker           ✅ Docker Compose
```

### 1. 克隆项目

```bash
git clone https://github.com/DREAMVFIAUNION/dreamhelper-v3.git
cd dreamhelper-v3
```

### 2. 安装依赖

```bash
# 安装前端依赖
pnpm install

# 安装 AI 核心依赖
cd services/brain-core
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入配置
```

### 4. 启动 Docker 服务

```bash
docker compose up -d postgres redis milvus es minio
```

### 5. 初始化数据库

```bash
pnpm db:migrate
pnpm db:seed
```

### 6. 启动开发服务

```bash
# 前端 (http://localhost:3000)
pnpm --filter web-portal dev

# AI 核心 (http://localhost:8000)
cd services/brain-core
uvicorn src.main:app --reload --port 8000

# 网关 (可选) (http://localhost:3001)
pnpm --filter gateway dev
```

### 7. 一键启动 (Docker)

```bash
docker compose up -d
# 访问 http://localhost:3000
```

---

## 📡 API 接口

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            🌐 API 端点                                    │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  🔐 /api/auth/*      │  认证系统                                        │
│     POST /login      │  用户登录                                        │
│     POST /register   │  用户注册                                        │
│     POST /logout    │  退出登录                                        │
│     PUT /password   │  修改密码                                        │
│                                                                          │
│  💬 /api/chat/*     │  对话系统                                        │
│     POST completion │  AI 对话                                          │
│     GET/POST session│  会话管理                                        │
│                                                                          │
│  📚 /api/knowledge  │  知识库                                          │
│     POST /upload    │  上传文档                                        │
│     GET /list      │  获取列表                                        │
│                                                                          │
│  🎤 /api/multimodal │  语音处理                                        │
│     POST /stt       │  语音转文字                                      │
│     POST /tts       │  文字转语音                                      │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 🎮 功能演示

### 💬 智能对话

```python
# 用户输入
user: "帮我写一首关于星空的诗"

# AI 回复
✨ 星光点点夜空深，银河倒映梦幻心。
   浩瀚宇宙无穷已，地上仰望思绪沉。
```

### 🖼️ 图像处理

```bash
# 用户: "帮我给图片添加水印"
# → 自动调用 image_watermark 技能
# → 返回处理后的图片
```

### 📊 数据分析

```bash
# 用户: "分析这份销售数据"
# → AI 自动调用 csv_analyzer
# → 返回可视化报告
```

---

## 🌍 访问我们

<p align="center">
  <a href="https://github.com/DREAMVFIAUNION">
    <img src="https://img.shields.io/badge/GitHub-DREAMVFIAUNION-00ff00?style=for-the-badge&logo=github" alt="github">
  </a>
</p>

---

## 📊 项目统计

<p align="center">

![GitHub Stars](https://img.shields.io/github/stars/DREAMVFIAUNION/dreamhelper-v3)
![GitHub Forks](https://img.shields.io/github/forks/DREAMVFIAUNION/dreamhelper-v3)
![Contributors](https://img.shields.io/github/contributors/DREAMVFIAUNION/dreamhelper-v3)
![Last Commit](https://img.shields.io/github/last-commit/DREAMVFIAUNION/dreamhelper-v3)

</p>

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

```bash
# 1. Fork 项目
# 2. 创建特性分支
git checkout -b feature/AmazingFeature
# 3. 提交更改
git commit -m 'Add some AmazingFeature'
# 4. 推送分支
git push origin feature/AmazingFeature
# 5. 打开 Pull Request
```

---

## 📄 许可证

```
© 2026 DREAMVFIA UNION
All Rights Reserved
```

---

<p align="center">
  <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&size=12&pause=1000&color=00FF00&center=true&vCenter=true&width=380&lines=Made+with+❤️+by+DREAMVFIA+UNION;Building+the+Future+of+AI+Assistants" alt="footer">
</p>

<p align="center">
  <sub>Copyright © 2026 DREAMVFIA UNION · Built with 🔥 and ⚡</sub>
</p>
