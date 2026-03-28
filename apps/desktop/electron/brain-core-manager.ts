/**
 * BrainCoreManager — brain-core Python 进程生命周期管理
 *
 * 职责:
 *  - 启动/停止 brain-core FastAPI 服务
 *  - 健康检查 (/api/v1/health)
 *  - 自动重启 (crash recovery)
 *  - 日志收集转发到渲染进程
 */

import { spawn, ChildProcess } from 'node:child_process'
import path from 'node:path'
import { app } from 'electron'

const BRAIN_CORE_PORT = 8000
const HEALTH_URL = `http://localhost:${BRAIN_CORE_PORT}/api/v1/health`
const HEALTH_CHECK_INTERVAL_MS = 15_000
const MAX_RESTART_ATTEMPTS = 3
const STARTUP_TIMEOUT_MS = 30_000

export interface BrainCoreStatus {
  running: boolean
  pid: number | null
  port: number
  uptime: number | null
  restartCount: number
  lastError: string | null
}

export class BrainCoreManager {
  private process: ChildProcess | null = null
  private startTime: number | null = null
  private restartCount = 0
  private lastError: string | null = null
  private healthTimer: ReturnType<typeof setInterval> | null = null
  private stopping = false

  /** brain-core 项目根目录 */
  private get brainCorePath(): string {
    if (app.isPackaged) {
      // 打包后: resources/brain-core/
      return path.join(process.resourcesPath, 'brain-core')
    }
    // 开发模式: monorepo 中的相对路径
    return path.resolve(__dirname, '../../../services/brain-core')
  }

  /** Python 可执行文件路径 */
  private get pythonPath(): string {
    const venvPython = process.platform === 'win32'
      ? path.join(this.brainCorePath, 'venv', 'Scripts', 'python.exe')
      : path.join(this.brainCorePath, 'venv', 'bin', 'python')
    return venvPython
  }

  async start(): Promise<{ success: boolean; error?: string }> {
    if (this.process && !this.process.killed) {
      return { success: true }
    }

    this.stopping = false
    this.lastError = null

    try {
      const cwd = this.brainCorePath
      const pythonExe = this.pythonPath

      console.log(`[BrainCore] Starting: ${pythonExe} -m uvicorn src.main:app --port ${BRAIN_CORE_PORT}`)
      console.log(`[BrainCore] CWD: ${cwd}`)

      this.process = spawn(pythonExe, [
        '-m', 'uvicorn',
        'src.main:app',
        '--host', '0.0.0.0',
        '--port', String(BRAIN_CORE_PORT),
        '--log-level', 'info',
      ], {
        cwd,
        env: {
          ...process.env,
          PYTHONUNBUFFERED: '1',
          PYTHONDONTWRITEBYTECODE: '1',
        },
        stdio: ['ignore', 'pipe', 'pipe'],
      })

      this.startTime = Date.now()

      // 收集日志
      this.process.stdout?.on('data', (data: Buffer) => {
        const text = data.toString().trim()
        if (text) console.log(`[BrainCore:stdout] ${text}`)
      })

      this.process.stderr?.on('data', (data: Buffer) => {
        const text = data.toString().trim()
        if (text) console.error(`[BrainCore:stderr] ${text}`)
      })

      this.process.on('exit', (code, signal) => {
        console.log(`[BrainCore] Exited: code=${code}, signal=${signal}`)
        this.process = null
        this.startTime = null

        // 自动重启 (非主动停止时)
        if (!this.stopping && this.restartCount < MAX_RESTART_ATTEMPTS) {
          this.restartCount++
          this.lastError = `Process exited (code=${code}, signal=${signal})`
          console.log(`[BrainCore] Auto-restart attempt ${this.restartCount}/${MAX_RESTART_ATTEMPTS}`)
          setTimeout(() => this.start(), 3000)
        }
      })

      this.process.on('error', (err) => {
        console.error('[BrainCore] Spawn error:', err.message)
        this.lastError = err.message
        this.process = null
      })

      // 等待服务就绪
      const ready = await this.waitForReady()
      if (!ready) {
        return { success: false, error: 'brain-core 启动超时，请检查 Python 环境' }
      }

      // 启动健康检查
      this.startHealthCheck()

      console.log(`[BrainCore] Ready on port ${BRAIN_CORE_PORT} (PID: ${this.process?.pid})`)
      return { success: true }

    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      this.lastError = msg
      return { success: false, error: msg }
    }
  }

  async stop(): Promise<{ success: boolean }> {
    this.stopping = true
    this.stopHealthCheck()

    if (!this.process) {
      return { success: true }
    }

    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        console.warn('[BrainCore] Force killing after timeout')
        this.process?.kill('SIGKILL')
        resolve({ success: true })
      }, 5000)

      this.process!.on('exit', () => {
        clearTimeout(timeout)
        this.process = null
        this.startTime = null
        resolve({ success: true })
      })

      // 优雅关闭
      if (process.platform === 'win32') {
        this.process!.kill()
      } else {
        this.process!.kill('SIGTERM')
      }
    })
  }

  getStatus(): BrainCoreStatus {
    return {
      running: this.process !== null && !this.process.killed,
      pid: this.process?.pid ?? null,
      port: BRAIN_CORE_PORT,
      uptime: this.startTime ? Date.now() - this.startTime : null,
      restartCount: this.restartCount,
      lastError: this.lastError,
    }
  }

  async healthCheck(): Promise<{ healthy: boolean; latencyMs: number; data?: unknown }> {
    const start = Date.now()
    try {
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 5000)

      const res = await fetch(HEALTH_URL, { signal: controller.signal })
      clearTimeout(timeout)

      const data = await res.json()
      return { healthy: res.ok, latencyMs: Date.now() - start, data }
    } catch {
      return { healthy: false, latencyMs: Date.now() - start }
    }
  }

  // ── 内部方法 ────────────────────────────────

  private async waitForReady(): Promise<boolean> {
    const deadline = Date.now() + STARTUP_TIMEOUT_MS
    while (Date.now() < deadline) {
      try {
        const controller = new AbortController()
        const timeout = setTimeout(() => controller.abort(), 2000)
        const res = await fetch(HEALTH_URL, { signal: controller.signal })
        clearTimeout(timeout)
        if (res.ok) return true
      } catch {
        // 服务尚未就绪
      }
      await new Promise((r) => setTimeout(r, 1000))
    }
    return false
  }

  private startHealthCheck(): void {
    this.stopHealthCheck()
    this.healthTimer = setInterval(async () => {
      const result = await this.healthCheck()
      if (!result.healthy && this.process && !this.stopping) {
        console.warn('[BrainCore] Health check failed, service may be unresponsive')
      }
    }, HEALTH_CHECK_INTERVAL_MS)
  }

  private stopHealthCheck(): void {
    if (this.healthTimer) {
      clearInterval(this.healthTimer)
      this.healthTimer = null
    }
  }
}
