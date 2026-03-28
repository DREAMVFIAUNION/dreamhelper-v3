#!/usr/bin/env tsx
/**
 * 梦帮小助 — 首次安装脚本 (跨平台)
 *
 * pnpm setup → 自动完成:
 *   1. 创建 ~/.dreamhelper/config.json
 *   2. 创建 brain-core/.venv + pip install
 *   3. 创建 .env (如不存在)
 *   4. docker compose up -d postgres redis
 *   5. prisma migrate deploy + seed
 */

import { execSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import os from 'node:os'
import { fileURLToPath } from 'node:url'
import { loadConfig, getConfigPath, ensureConfigDir } from './config.js'

const __scriptDir = typeof __dirname !== 'undefined' ? __dirname : path.dirname(fileURLToPath(import.meta.url))
const PROJECT_ROOT = path.resolve(__scriptDir, '..')
const BRAIN_DIR = path.join(PROJECT_ROOT, 'services', 'brain-core')
const IS_WIN = os.platform() === 'win32'

// ═══ 颜色 ═══

const c = {
  red: (s: string) => `\x1b[31m${s}\x1b[0m`,
  green: (s: string) => `\x1b[32m${s}\x1b[0m`,
  yellow: (s: string) => `\x1b[33m${s}\x1b[0m`,
  cyan: (s: string) => `\x1b[36m${s}\x1b[0m`,
  dim: (s: string) => `\x1b[2m${s}\x1b[0m`,
  bold: (s: string) => `\x1b[1m${s}\x1b[0m`,
}

function run(cmd: string, opts: { cwd?: string; stdio?: 'inherit' | 'pipe' } = {}) {
  const { cwd = PROJECT_ROOT, stdio = 'inherit' } = opts
  execSync(cmd, { cwd, stdio, encoding: 'utf-8' })
}

function runQuiet(cmd: string, cwd?: string): string {
  try {
    return execSync(cmd, { cwd, encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] }).trim()
  } catch {
    return ''
  }
}

function step(n: number, total: number, msg: string) {
  console.log(c.cyan(`[${n}/${total}] ${msg}`))
}

// ═══ 主流程 ═══

function main() {
  console.log()
  console.log(c.red('  ╔═══════════════════════════════════════════╗'))
  console.log(c.red('  ║   DREAMVFIA · 梦帮小助 v4.0 首次安装      ║'))
  console.log(c.red('  ╚═══════════════════════════════════════════╝'))
  console.log()

  const TOTAL = 5

  // ═══ 1. 配置文件 ═══
  step(1, TOTAL, '创建配置文件...')
  ensureConfigDir()
  const config = loadConfig()
  console.log(c.green(`  ✓ ${getConfigPath()}`))
  console.log()

  // ═══ 2. Python venv ═══
  step(2, TOTAL, 'Python 虚拟环境...')
  const venvDir = path.join(BRAIN_DIR, '.venv')
  const venvPython = IS_WIN
    ? path.join(venvDir, 'Scripts', 'python.exe')
    : path.join(venvDir, 'bin', 'python')
  const venvPip = IS_WIN
    ? path.join(venvDir, 'Scripts', 'pip.exe')
    : path.join(venvDir, 'bin', 'pip')

  if (!fs.existsSync(venvDir)) {
    console.log(c.dim('  创建 .venv...'))
    try {
      run('python -m venv .venv', { cwd: BRAIN_DIR })
      console.log(c.green('  ✓ .venv 已创建'))
    } catch {
      console.log(c.yellow('  ⚠ 无法创建 venv，请手动运行: cd services/brain-core && python -m venv .venv'))
    }
  } else {
    console.log(c.green('  ✓ .venv 已存在'))
  }

  if (fs.existsSync(venvPip)) {
    console.log(c.dim('  安装 Python 依赖...'))
    try {
      run(`"${venvPip}" install -r requirements.txt`, { cwd: BRAIN_DIR })
      console.log(c.green('  ✓ Python 依赖已安装'))
    } catch {
      console.log(c.yellow('  ⚠ pip install 失败，请手动运行'))
    }
  }
  console.log()

  // ═══ 3. .env 文件 ═══
  step(3, TOTAL, '环境变量文件...')
  const envPath = path.join(PROJECT_ROOT, '.env')
  const envExamplePath = path.join(PROJECT_ROOT, '.env.example')

  if (!fs.existsSync(envPath)) {
    if (fs.existsSync(envExamplePath)) {
      fs.copyFileSync(envExamplePath, envPath)
      console.log(c.green('  ✓ 已从 .env.example 创建 .env'))
      console.log(c.yellow('  ⚠ 请编辑 .env 填写 LLM API Key'))
    } else {
      // 生成最小 .env
      const defaultEnv = [
        '# ═══ 梦帮小助 — 环境变量 ═══',
        '',
        '# 必填: 至少填写一个 LLM API Key',
        'MINIMAX_API_KEY=',
        'DEEPSEEK_API_KEY=',
        'OPENAI_API_KEY=',
        '',
        '# 数据库 (默认值适用于 Docker 开发环境)',
        'DATABASE_URL=postgresql://dreamhelp:dev_password@localhost:5432/dreamhelp',
        '',
        '# brain-core URL (pnpm start 自动启动)',
        'BRAIN_CORE_URL=http://localhost:8000',
        '',
      ].join('\n')
      fs.writeFileSync(envPath, defaultEnv, 'utf-8')
      console.log(c.green('  ✓ 已创建默认 .env'))
      console.log(c.yellow('  ⚠ 请编辑 .env 填写 LLM API Key'))
    }
  } else {
    console.log(c.green('  ✓ .env 已存在'))
  }
  console.log()

  // ═══ 4. Docker 基础设施 ═══
  step(4, TOTAL, 'Docker 基础设施...')
  const dockerRunning = runQuiet('docker info --format "{{.ServerVersion}}"')
  if (dockerRunning) {
    try {
      const services = config.docker.services.join(' ')
      run(`docker compose up -d ${services}`, { cwd: PROJECT_ROOT })
      console.log(c.green(`  ✓ Docker 服务已启动: ${config.docker.services.join(', ')}`))

      // 等待健康检查
      console.log(c.dim('  等待服务就绪...'))
      const maxWait = 30
      let waited = 0
      while (waited < maxWait) {
        const pgOk = runQuiet('docker inspect --format={{.State.Health.Status}} dreamhelp-postgres') === 'healthy'
        const redisOk = runQuiet('docker inspect --format={{.State.Health.Status}} dreamhelp-redis') === 'healthy'
        if (pgOk && redisOk) break
        waited += 2
        execSync('timeout /t 2 >nul 2>&1 || sleep 2', { stdio: 'ignore' })
      }
      console.log(c.green('  ✓ 基础设施就绪'))
    } catch {
      console.log(c.yellow('  ⚠ Docker compose 启动失败'))
    }
  } else {
    console.log(c.yellow('  ⚠ Docker daemon 未运行，跳过'))
    console.log(c.dim('  请先启动 Docker Desktop，然后重新运行 pnpm setup'))
  }
  console.log()

  // ═══ 5. 数据库迁移 + Seed ═══
  step(5, TOTAL, '数据库迁移 + Seed...')
  try {
    run('pnpm db:migrate', { cwd: PROJECT_ROOT })
    console.log(c.green('  ✓ prisma migrate deploy'))
  } catch {
    console.log(c.yellow('  ⚠ migrate 跳过 (数据库可能未就绪或已是最新)'))
  }

  try {
    run('pnpm db:seed', { cwd: PROJECT_ROOT })
    console.log(c.green('  ✓ prisma db seed'))
  } catch {
    console.log(c.yellow('  ⚠ seed 跳过'))
  }

  // ═══ 完成 ═══
  console.log()
  console.log(c.red('  ═══════════════════════════════════════════'))
  console.log(c.bold('  ✓ 安装完成!'))
  console.log()
  console.log(`  1. 编辑 ${c.cyan('.env')} 填写 LLM API Key (如尚未填写)`)
  console.log(`  2. 运行 ${c.cyan('pnpm start')} 一键启动所有服务`)
  console.log(`  3. 运行 ${c.cyan('pnpm doctor')} 检查环境状态`)
  console.log(c.red('  ═══════════════════════════════════════════'))
  console.log()
}

main()
