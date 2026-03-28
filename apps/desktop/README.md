# 梦帮小助 — 桌面客户端

Electron 桌面应用，将梦帮小助打包为本地 AI Agent 编程助手。

## 架构

```
apps/desktop/
├── electron/
│   ├── main.ts                 # 主进程: 窗口管理、IPC 路由
│   ├── preload.ts              # 安全 IPC 桥接 (contextIsolation)
│   ├── brain-core-manager.ts   # brain-core Python 进程生命周期
│   ├── terminal-manager.ts     # PTY 终端会话 (node-pty)
│   ├── permission-dialog.ts    # 原生权限确认对话框
│   ├── tray.ts                 # 系统托盘 + 右键菜单
│   ├── env.d.ts                # TypeScript 全局类型
│   └── tsconfig.json
├── resources/                  # 图标、静态资源
├── electron-builder.yml        # 打包配置
├── electron-vite.config.ts     # Vite 构建配置
└── package.json
```

## 功能

- **brain-core 进程管理** — 自动启动/停止 Python FastAPI 服务，健康检查，崩溃自动重启
- **内嵌终端** — 基于 node-pty + xterm.js 的真实伪终端，支持多标签
- **权限网关** — 高危操作（文件删除、Shell 命令）弹出原生确认对话框
- **系统托盘** — 最小化到托盘，`Ctrl+Shift+D` 全局快捷键呼出
- **单实例锁** — 防止重复启动

## 开发

```bash
# 1. 安装依赖
pnpm install

# 2. 启动 web-portal 开发服务器（另一个终端）
pnpm --filter @dreamhelp/web-portal dev

# 3. 启动 Electron 开发模式
pnpm --filter @dreamhelp/desktop dev
```

## 打包

```bash
# Windows
pnpm --filter @dreamhelp/desktop dist:win

# macOS
pnpm --filter @dreamhelp/desktop dist:mac

# Linux
pnpm --filter @dreamhelp/desktop dist:linux
```

## 前端集成

桌面专属组件通过 `useElectron` hook 检测运行环境:

```tsx
import { useElectron } from '@/hooks/useElectron'

function MyComponent() {
  const { isDesktop, api } = useElectron()
  
  if (!isDesktop) return null // 浏览器中不渲染
  
  return <TerminalPanel />
}
```

## 依赖

| 包 | 用途 |
|---|------|
| `electron` | 桌面框架 |
| `electron-vite` | Vite 构建集成 |
| `electron-builder` | 多平台打包 |
| `node-pty` | 伪终端 |
| `@xterm/xterm` | 终端 UI (web-portal 侧) |
| `@xterm/addon-fit` | 终端自适应大小 |
