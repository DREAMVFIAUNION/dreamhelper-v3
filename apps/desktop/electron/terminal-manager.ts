/**
 * TerminalManager — PTY 终端会话管理
 *
 * 使用 node-pty 创建真实伪终端，支持:
 *  - 多终端会话并行
 *  - 数据流转发 (PTY → IPC → 渲染进程)
 *  - 窗口大小动态调整
 *  - 优雅关闭
 */

import os from 'node:os'

// node-pty 类型 (动态导入以避免打包问题)
interface IPty {
  pid: number
  cols: number
  rows: number
  write(data: string): void
  resize(cols: number, rows: number): void
  kill(signal?: string): void
  onData: (callback: (data: string) => void) => { dispose(): void }
  onExit: (callback: (e: { exitCode: number; signal?: number }) => void) => { dispose(): void }
}

interface PtySession {
  id: string
  pty: IPty
  cwd: string
  createdAt: number
  dataListeners: Array<(data: string) => void>
  exitListeners: Array<(exitCode: number) => void>
}

let ptyModule: any = null

async function getPty(): Promise<any> {
  if (!ptyModule) {
    ptyModule = await import('node-pty')
  }
  return ptyModule
}

let nextId = 1

export class TerminalManager {
  private sessions = new Map<string, PtySession>()

  /** 创建新终端会话 */
  create(options?: { cwd?: string; shell?: string }): string {
    const id = `term-${nextId++}`
    const cwd = options?.cwd || os.homedir()

    // 选择 shell
    const shell = options?.shell || this.defaultShell()

    // 同步启动 PTY (node-pty 需要同步)
    let pty: IPty
    try {
      // node-pty 必须同步 require（native module）
      const nodePty = require('node-pty')
      pty = nodePty.spawn(shell, [], {
        name: 'xterm-256color',
        cols: 120,
        rows: 30,
        cwd,
        env: { ...process.env, TERM: 'xterm-256color' } as Record<string, string>,
      })
    } catch (err) {
      console.error('[Terminal] Failed to spawn PTY:', err)
      throw err
    }

    const session: PtySession = {
      id,
      pty,
      cwd,
      createdAt: Date.now(),
      dataListeners: [],
      exitListeners: [],
    }

    // 绑定 PTY 事件
    pty.onData((data: string) => {
      for (const fn of session.dataListeners) {
        try { fn(data) } catch { /* ignore */ }
      }
    })

    pty.onExit(({ exitCode }: { exitCode: number }) => {
      for (const fn of session.exitListeners) {
        try { fn(exitCode) } catch { /* ignore */ }
      }
      this.sessions.delete(id)
    })

    this.sessions.set(id, session)
    console.log(`[Terminal] Created session ${id} (shell=${shell}, cwd=${cwd}, pid=${pty.pid})`)
    return id
  }

  /** 向终端写入数据 */
  write(id: string, data: string): void {
    const session = this.sessions.get(id)
    if (session) {
      session.pty.write(data)
    }
  }

  /** 调整终端大小 */
  resize(id: string, cols: number, rows: number): void {
    const session = this.sessions.get(id)
    if (session) {
      session.pty.resize(cols, rows)
    }
  }

  /** 关闭终端 */
  kill(id: string): void {
    const session = this.sessions.get(id)
    if (session) {
      session.pty.kill()
      this.sessions.delete(id)
      console.log(`[Terminal] Killed session ${id}`)
    }
  }

  /** 关闭所有终端 */
  killAll(): void {
    for (const [id, session] of this.sessions) {
      try {
        session.pty.kill()
      } catch { /* ignore */ }
      console.log(`[Terminal] Killed session ${id}`)
    }
    this.sessions.clear()
  }

  /** 注册数据监听器 */
  onData(id: string, callback: (data: string) => void): void {
    const session = this.sessions.get(id)
    if (session) {
      session.dataListeners.push(callback)
    }
  }

  /** 注册退出监听器 */
  onExit(id: string, callback: (exitCode: number) => void): void {
    const session = this.sessions.get(id)
    if (session) {
      session.exitListeners.push(callback)
    }
  }

  /** 列出活跃会话 */
  list(): Array<{ id: string; pid: number; cwd: string; createdAt: number }> {
    return Array.from(this.sessions.values()).map((s) => ({
      id: s.id,
      pid: s.pty.pid,
      cwd: s.cwd,
      createdAt: s.createdAt,
    }))
  }

  /** 获取默认 shell */
  private defaultShell(): string {
    if (process.platform === 'win32') {
      return process.env.COMSPEC || 'powershell.exe'
    }
    return process.env.SHELL || '/bin/bash'
  }
}
