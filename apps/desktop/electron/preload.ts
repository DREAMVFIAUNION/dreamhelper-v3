/**
 * Preload 脚本 — 安全的 IPC 桥接层
 *
 * 通过 contextBridge 暴露受限 API 到渲染进程，
 * 遵循 Electron 安全最佳实践 (contextIsolation + 白名单 IPC)
 */

import { contextBridge, ipcRenderer } from 'electron'

const electronAPI = {
  // ── brain-core 管理 ────────────────────
  brain: {
    start: () => ipcRenderer.invoke('brain:start'),
    stop: () => ipcRenderer.invoke('brain:stop'),
    status: () => ipcRenderer.invoke('brain:status'),
    health: () => ipcRenderer.invoke('brain:health'),
  },

  // ── 终端 PTY ───────────────────────────
  terminal: {
    create: (options?: { cwd?: string; shell?: string }) =>
      ipcRenderer.invoke('terminal:create', options),
    write: (id: string, data: string) =>
      ipcRenderer.invoke('terminal:write', id, data),
    resize: (id: string, cols: number, rows: number) =>
      ipcRenderer.invoke('terminal:resize', id, cols, rows),
    kill: (id: string) =>
      ipcRenderer.invoke('terminal:kill', id),
    list: () =>
      ipcRenderer.invoke('terminal:list'),
    onData: (callback: (event: { id: string; data: string }) => void) => {
      const handler = (_e: unknown, event: { id: string; data: string }) => callback(event)
      ipcRenderer.on('terminal:data', handler)
      return () => ipcRenderer.removeListener('terminal:data', handler)
    },
    onExit: (callback: (event: { id: string; exitCode: number }) => void) => {
      const handler = (_e: unknown, event: { id: string; exitCode: number }) => callback(event)
      ipcRenderer.on('terminal:exit', handler)
      return () => ipcRenderer.removeListener('terminal:exit', handler)
    },
  },

  // ── 权限确认 ───────────────────────────
  permission: {
    request: (req: {
      type: string
      description: string
      details: string
      riskLevel: string
    }) => ipcRenderer.invoke('permission:request', req),
    requestBatch: (reqs: Array<{
      type: string
      description: string
      details: string
      riskLevel: string
    }>) => ipcRenderer.invoke('permission:requestBatch', reqs),
  },

  // ── 文件对话框 ──────────────────────────
  dialog: {
    openFile: (options?: Record<string, unknown>) =>
      ipcRenderer.invoke('dialog:openFile', options),
    openDirectory: (options?: Record<string, unknown>) =>
      ipcRenderer.invoke('dialog:openDirectory', options),
    saveFile: (options?: Record<string, unknown>) =>
      ipcRenderer.invoke('dialog:saveFile', options),
  },

  // ── 应用信息 ───────────────────────────
  app: {
    info: () => ipcRenderer.invoke('app:info'),
  },

  // ── 窗口控制 ───────────────────────────
  window: {
    minimize: () => ipcRenderer.invoke('window:minimize'),
    maximize: () => ipcRenderer.invoke('window:maximize'),
    close: () => ipcRenderer.invoke('window:close'),
  },

  // ── 通用事件监听 ───────────────────────
  on: (channel: string, callback: (...args: unknown[]) => void) => {
    const allowedChannels = ['action:newChat', 'brain:log', 'brain:statusChange']
    if (allowedChannels.includes(channel)) {
      const handler = (_e: unknown, ...args: unknown[]) => callback(...args)
      ipcRenderer.on(channel, handler)
      return () => ipcRenderer.removeListener(channel, handler)
    }
    return () => {}
  },
}

// 暴露到 window.electronAPI
contextBridge.exposeInMainWorld('electronAPI', electronAPI)

// TypeScript 类型声明
export type ElectronAPI = typeof electronAPI
