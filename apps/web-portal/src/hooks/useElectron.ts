/**
 * useElectron — 检测 Electron 环境并提供桌面 API 访问
 *
 * 在浏览器中运行时返回 null，在 Electron 中返回完整 API。
 * 所有组件通过此 hook 安全地访问桌面功能。
 */

'use client'

import { useMemo } from 'react'

interface BrainCoreStatus {
  running: boolean
  pid: number | null
  port: number
  uptime: number | null
  restartCount: number
  lastError: string | null
}

interface HealthResult {
  healthy: boolean
  latencyMs: number
  data?: unknown
}

interface TerminalSession {
  id: string
  pid: number
  cwd: string
  createdAt: number
}

interface PermissionRequest {
  type: string
  description: string
  details: string
  riskLevel: string
}

interface AppInfo {
  version: string
  platform: string
  arch: string
  isDev: boolean
  paths: {
    userData: string
    home: string
    documents: string
  }
}

export interface ElectronAPI {
  brain: {
    start: () => Promise<{ success: boolean; error?: string }>
    stop: () => Promise<{ success: boolean }>
    status: () => Promise<BrainCoreStatus>
    health: () => Promise<HealthResult>
  }
  terminal: {
    create: (options?: { cwd?: string; shell?: string }) => Promise<string>
    write: (id: string, data: string) => Promise<void>
    resize: (id: string, cols: number, rows: number) => Promise<void>
    kill: (id: string) => Promise<void>
    list: () => Promise<TerminalSession[]>
    onData: (callback: (event: { id: string; data: string }) => void) => () => void
    onExit: (callback: (event: { id: string; exitCode: number }) => void) => () => void
  }
  permission: {
    request: (req: PermissionRequest) => Promise<{ approved: boolean }>
    requestBatch: (reqs: PermissionRequest[]) => Promise<{ approved: boolean }>
  }
  dialog: {
    openFile: (options?: Record<string, unknown>) => Promise<string[]>
    openDirectory: (options?: Record<string, unknown>) => Promise<string[]>
    saveFile: (options?: Record<string, unknown>) => Promise<string | undefined>
  }
  app: {
    info: () => Promise<AppInfo>
  }
  window: {
    minimize: () => Promise<void>
    maximize: () => Promise<void>
    close: () => Promise<void>
  }
  on: (channel: string, callback: (...args: unknown[]) => void) => () => void
}

/** 检测是否在 Electron 环境中运行 */
export function isElectron(): boolean {
  return typeof window !== 'undefined' && 'electronAPI' in window
}

/** 获取 Electron API（非 Electron 环境返回 null） */
export function getElectronAPI(): ElectronAPI | null {
  if (!isElectron()) return null
  return (window as any).electronAPI as ElectronAPI
}

/** React hook: 获取 Electron API */
export function useElectron(): {
  isDesktop: boolean
  api: ElectronAPI | null
} {
  const result = useMemo(() => {
    const api = getElectronAPI()
    return { isDesktop: api !== null, api }
  }, [])
  return result
}
