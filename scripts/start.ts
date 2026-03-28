#!/usr/bin/env tsx
/**
 * 梦帮小助 — 统一启动脚本
 *
 * pnpm start → 自动管理 Docker 基础设施 + 并行启动 web-portal & brain-core
 *
 * 流程:
 *   [0] 加载 ~/.dreamhelper/config.json
 *   [1] 环境检查 (Node/Python/Docker)
 *   [2] Docker compose up (postgres, redis)
 *   [3] Prisma migrate + seed
 *   [4] 并行启动 web-portal + brain-core
 *   [5] 健康检查 → 打开浏览器
 */

import { spawn, execSync, type ChildProcess } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import os from 'node:os'
import { fileURLToPath } from 'node:url'
import { loadConfig, type DreamHelperConfig } from './config.js'

// ═══ 常量 ═══

const __scriptDir = typeof __dirname !== 'undefined' ? __dirname : path.dirname(fileURLToPath(import.meta.url))
const PROJECT_ROOT = path.resolve(__scriptDir, '..')
const WEB_DIR = path.join(PROJECT_ROOT, 'apps', 'web-portal')
const BRAIN_DIR = path.join(PROJECT_ROOT, 'services', 'brain-core')
const IS_WIN = os.platform() === 'win32'

// ═══ 颜色工具 ═══

const c = {
  red: (s: string) => `\x1b[31m${s}\x1b[0m`,
  green: (s: string) => `\x1b[32m${s}\x1b[0m`,
  yellow: (s: string) => `\x1b[33m${s}\x1b[0m`,
  cyan: (s: string) => `\x1b[36m${s}\x1b[0m`,
  dim: (s: string) => `\x1b[2m${s}\x1b[0m`,
  bold: (s: string) => `\x1b[1m${s}\x1b[0m`,
  magenta: (s: string) => `\x1b[35m${s}\x1b[0m`,
}

function banner() {
  console.log()
  console.log(c.red('  ╔═══════════════════════════════════════════╗'))
  console.log(c.red('  ║   DREAMVFIA · 梦帮小助 v4.0 启动器       ║'))
  console.log(c.red('  ╚═══════════════════════════════════════════╝'))
  console.log()
}

// ═══ 工具函数 ═══

/** 执行命令并返回 stdout (同步) */
function run(cmd: string, cwd?: string): string {
  try {
    return execSync(cmd, { cwd, encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] }).trim()
  } catch {
    return ''
  }
}

/** 检查命令是否存在 */
function hasCommand(cmd: string): boolean {
  const check = IS_WIN ? `where ${cmd}` : `which ${cmd}`
  return run(check) !== ''
}

/** 等待 URL 可用 */
async function waitForUrl(url: string, timeoutMs: number, label: string): Promise<boolean> {
  const start = Date.now()
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url, { signal: AbortSignal.timeout(2000) })
      if (res.ok) return true
    } catch {
      // 继续等待
    }
    await sleep(1500)
  }
  console.log(c.yellow(`  ⚠ ${label} 超时 (${Math.round(timeoutMs / 1000)}s)`))
  return false
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}

/** 打开浏览器 (跨平台) */
function openBrowser(url: string) {
  try {
    if (IS_WIN) {
      execSync(`start "" "${url}"`, { stdio: 'ignore' })
    } else if (os.platform() === 'darwin') {
      execSync(`open "${url}"`, { stdio: 'ignore' })
    } else {
      execSync(`xdg-open "${url}"`, { stdio: 'ignore' })
    }
  } catch {
    // 静默失败
  }
}

/** Python 可执行文件路径 (优先 venv) */
function getPythonPath(): string {
  const venvPython = IS_WIN
    ? path.join(BRAIN_DIR, '.venv', 'Scripts', 'python.exe')
    : path.join(BRAIN_DIR, '.venv', 'bin', 'python')

  if (fs.existsSync(venvPython)) return venvPython
  return 'python'
}

// ═══ Step 1: 环境检查 ═══

function checkEnvironment(): boolean {
  console.log(c.cyan('[1/5] 环境检查...'))
  let ok = true

  // Node.js
  const nodeVer = process.version
  const nodeMajor = parseInt(nodeVer.slice(1))
  if (nodeMajor >= 20) {
    console.log(c.green(`  ✓ Node.js   ${nodeVer}`))
  } else {
    console.log(c.red(`  ✗ Node.js   ${nodeVer} (需要 >= 20.0.0)`))
    ok = false
  }

  // Python
  const pythonCmd = getPythonPath()
  const pyVer = run(`"${pythonCmd}" --version`)
  if (pyVer) {
    console.log(c.green(`  ✓ Python    ${pyVer.replace('Python ', '')}`))
  } else {
    console.log(c.red('  ✗ Python    未找到'))
    ok = false
  }

  // Docker
  if (hasCommand('docker')) {
    const dockerInfo = run('docker info --format "{{.ServerVersion}}"')
    if (dockerInfo) {
      console.log(c.green(`  ✓ Docker    v${dockerInfo} (running)`))
    } else {
      console.log(c.yellow('  ⚠ Docker    已安装但 daemon 未运行'))
      ok = false
    }
  } else {
    console.log(c.red('  ✗ Docker    未安装'))
    ok = false
  }

  // brain-core venv
  const pythonPath = getPythonPath()
  if (pythonPath !== 'python') {
    console.log(c.green('  ✓ venv      brain-core/.venv 就绪'))
  } else {
    console.log(c.yellow('  ⚠ venv      brain-core/.venv 不存在，将使用系统 Python'))
  }

  console.log()
  return ok
}

// ═══ Step 2: Docker 基础设施 ═══

async function startDocker(config: DreamHelperConfig): Promise<boolean> {
  const services = config.docker.services
  console.log(c.cyan(`[2/5] Docker 基础设施 (${services.join(', ')})...`))

  const composeFile = path.join(PROJECT_ROOT, config.docker.composeFile)

  // docker compose up -d
  try {
    execSync(`docker compose -f "${composeFile}" up -d ${services.join(' ')}`, {
      cwd: PROJECT_ROOT,
      stdio: ['pipe', 'pipe', 'pipe'],
    })
  } catch (e: any) {
    console.log(c.red(`  ✗ docker compose up 失败: ${e.message}`))
    return false
  }

  // 健康检查轮询
  console.log(c.dim('  等待服务就绪...'))
  const maxWait = 30_000
  const start = Date.now()
  const containerNames: Record<string, string> = {
    postgres: 'dreamhelp-postgres',
    redis: 'dreamhelp-redis',
  }

  while (Date.now() - start < maxWait) {
    let allHealthy = true
    for (const svc of services) {
      const name = containerNames[svc] || `dreamhelp-${svc}`
      const status = run(`docker inspect --format={{.State.Health.Status}} ${name}`)
      if (status !== 'healthy') {
        allHealthy = false
        break
      }
    }
    if (allHealthy) break
    await sleep(2000)
  }

  // 输出最终状态
  for (const svc of services) {
    const name = containerNames[svc] || `dreamhelp-${svc}`
    const status = run(`docker inspect --format={{.State.Health.Status}} ${name}`)
    if (status === 'healthy') {
      console.log(c.green(`  ✓ ${svc} healthy`))
    } else {
      console.log(c.yellow(`  ⚠ ${svc} 状态: ${status || 'unknown'}`))
    }
  }

  console.log()
  return true
}

// ═══ Step 3: Prisma migrate + seed ═══

function runMigrations(): boolean {
  console.log(c.cyan('[3/5] 数据库迁移 + Seed...'))

  try {
    execSync('pnpm db:migrate', { cwd: PROJECT_ROOT, stdio: ['pipe', 'pipe', 'pipe'] })
    console.log(c.green('  ✓ prisma migrate deploy'))
  } catch {
    console.log(c.yellow('  ⚠ prisma migrate deploy 跳过 (可能已是最新)'))
  }

  try {
    execSync('pnpm db:seed', { cwd: PROJECT_ROOT, stdio: ['pipe', 'pipe', 'pipe'] })
    console.log(c.green('  ✓ prisma db seed'))
  } catch {
    console.log(c.yellow('  ⚠ prisma db seed 跳过 (可能已执行过)'))
  }

  console.log()
  return true
}

// ═══ Step 4: 并行启动应用服务 ═══

const children: ChildProcess[] = []

function startWebPortal(port: number): ChildProcess {
  const child = spawn('pnpm', ['--filter', '@dreamhelp/web-portal', 'dev', '--', '--port', String(port)], {
    cwd: PROJECT_ROOT,
    stdio: ['pipe', 'pipe', 'pipe'],
    shell: true,
    env: { ...process.env, FORCE_COLOR: '1' },
  })

  child.stdout?.on('data', (data: Buffer) => {
    const lines = data.toString().split('\n').filter(Boolean)
    for (const line of lines) {
      console.log(`${c.cyan('[WEB]')}  ${line}`)
    }
  })

  child.stderr?.on('data', (data: Buffer) => {
    const lines = data.toString().split('\n').filter(Boolean)
    for (const line of lines) {
      console.log(`${c.cyan('[WEB]')}  ${c.dim(line)}`)
    }
  })

  children.push(child)
  return child
}

function startBrainCore(port: number): ChildProcess {
  const pythonPath = getPythonPath()
  const child = spawn(
    pythonPath,
    ['-m', 'uvicorn', 'src.main:app', '--host', '0.0.0.0', '--port', String(port), '--reload'],
    {
      cwd: BRAIN_DIR,
      stdio: ['pipe', 'pipe', 'pipe'],
      shell: true,
      env: { ...process.env, FORCE_COLOR: '1', PYTHONUNBUFFERED: '1' },
    },
  )

  child.stdout?.on('data', (data: Buffer) => {
    const lines = data.toString().split('\n').filter(Boolean)
    for (const line of lines) {
      console.log(`${c.magenta('[BRAIN]')} ${line}`)
    }
  })

  child.stderr?.on('data', (data: Buffer) => {
    const lines = data.toString().split('\n').filter(Boolean)
    for (const line of lines) {
      console.log(`${c.magenta('[BRAIN]')} ${c.dim(line)}`)
    }
  })

  children.push(child)
  return child
}

// ═══ Step 5: 健康检查 + 打开浏览器 ═══

async function healthCheckAndOpen(config: DreamHelperConfig) {
  console.log()
  console.log(c.cyan('[5/5] 等待服务就绪...'))

  const brainUrl = `http://localhost:${config.brainCorePort}/health`
  const webUrl = `http://localhost:${config.webPort}`

  const brainOk = await waitForUrl(brainUrl, 60_000, 'brain-core')
  if (brainOk) {
    console.log(c.green(`  ✓ brain-core  http://localhost:${config.brainCorePort}`))
  }

  const webOk = await waitForUrl(webUrl, 30_000, 'web-portal')
  if (webOk) {
    console.log(c.green(`  ✓ web-portal  http://localhost:${config.webPort}`))
  }

  console.log()
  console.log(c.red('  ═══════════════════════════════════════════'))
  console.log(c.bold(`  🚀 梦帮小助已启动!`))
  console.log()
  console.log(`  Web Portal:  ${c.cyan(`http://localhost:${config.webPort}/chat`)}`)
  console.log(`  Brain Core:  ${c.cyan(`http://localhost:${config.brainCorePort}/health`)}`)
  console.log()
  console.log(c.dim('  按 Ctrl+C 关闭所有服务'))
  console.log(c.red('  ═══════════════════════════════════════════'))
  console.log()

  if (config.autoOpenBrowser && webOk) {
    openBrowser(`http://localhost:${config.webPort}/chat`)
  }
}

// ═══ 优雅关闭 ═══

function setupGracefulShutdown() {
  let shuttingDown = false

  const shutdown = () => {
    if (shuttingDown) return
    shuttingDown = true
    console.log()
    console.log(c.yellow('  正在关闭所有服务...'))

    for (const child of children) {
      if (!child.killed) {
        // Windows 上需要通过 taskkill 杀子进程树
        if (IS_WIN && child.pid) {
          try {
            execSync(`taskkill /PID ${child.pid} /T /F`, { stdio: 'ignore' })
          } catch {
            child.kill('SIGTERM')
          }
        } else {
          child.kill('SIGTERM')
        }
      }
    }

    // 等待 2s 后强制退出
    setTimeout(() => {
      console.log(c.dim('  强制退出...'))
      process.exit(0)
    }, 2000)
  }

  process.on('SIGINT', shutdown)
  process.on('SIGTERM', shutdown)

  // Windows: Ctrl+C
  if (IS_WIN) {
    process.on('SIGHUP', shutdown)
  }
}

// ═══ 主入口 ═══

async function main() {
  banner()

  // [0] 加载配置
  const config = loadConfig()
  console.log(c.dim(`  配置: ~/.dreamhelper/config.json`))
  console.log(c.dim(`  Web: :${config.webPort}  Brain: :${config.brainCorePort}`))
  console.log()

  // [1] 环境检查
  const envOk = checkEnvironment()
  if (!envOk) {
    console.log(c.red('  环境检查未通过，请运行 pnpm doctor 查看详情'))
    console.log()
    process.exit(1)
  }

  // [2] Docker 基础设施
  const dockerOk = await startDocker(config)
  if (!dockerOk) {
    console.log(c.red('  Docker 基础设施启动失败'))
    process.exit(1)
  }

  // [3] Prisma migrate + seed
  runMigrations()

  // 注册优雅关闭
  setupGracefulShutdown()

  // [4] 并行启动应用服务
  console.log(c.cyan('[4/5] 启动应用服务...'))
  startWebPortal(config.webPort)
  startBrainCore(config.brainCorePort)
  console.log(c.green('  ✓ web-portal 启动中...'))
  console.log(c.green('  ✓ brain-core 启动中...'))

  // [5] 健康检查 + 打开浏览器
  await healthCheckAndOpen(config)

  // 监听子进程退出
  for (const child of children) {
    child.on('exit', (code, signal) => {
      if (code !== null && code !== 0) {
        console.log(c.red(`  ⚠ 子进程退出 (code=${code}, signal=${signal})`))
      }
    })
  }
}

main().catch((err) => {
  console.error(c.red(`启动失败: ${err}`))
  process.exit(1)
})
