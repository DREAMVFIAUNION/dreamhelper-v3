#!/usr/bin/env tsx
/**
 * 梦帮小助 — 环境诊断工具
 *
 * pnpm doctor → 逐项检查开发环境并输出诊断表
 */

import { execSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import os from 'node:os'
import { fileURLToPath } from 'node:url'
import { getConfigPath, loadConfig } from './config.js'

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
}

function run(cmd: string): string {
  try {
    return execSync(cmd, { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] }).trim()
  } catch {
    return ''
  }
}

function hasCommand(cmd: string): boolean {
  const check = IS_WIN ? `where ${cmd}` : `which ${cmd}`
  return run(check) !== ''
}

// ═══ 诊断项 ═══

interface CheckResult {
  label: string
  status: 'ok' | 'warn' | 'fail'
  detail: string
}

function checkNode(): CheckResult {
  const ver = process.version
  const major = parseInt(ver.slice(1))
  if (major >= 20) {
    return { label: 'Node.js', status: 'ok', detail: ver }
  }
  return { label: 'Node.js', status: 'fail', detail: `${ver} (需要 >= 20.0.0)` }
}

function checkPnpm(): CheckResult {
  const ver = run('pnpm --version')
  if (!ver) return { label: 'pnpm', status: 'fail', detail: '未安装' }
  const major = parseInt(ver.split('.')[0])
  if (major >= 9) return { label: 'pnpm', status: 'ok', detail: `v${ver}` }
  return { label: 'pnpm', status: 'fail', detail: `v${ver} (需要 >= 9.0.0)` }
}

function checkPython(): CheckResult {
  // 优先检查 venv
  const venvPython = IS_WIN
    ? path.join(BRAIN_DIR, '.venv', 'Scripts', 'python.exe')
    : path.join(BRAIN_DIR, '.venv', 'bin', 'python')

  let pyCmd = fs.existsSync(venvPython) ? `"${venvPython}"` : 'python'
  const ver = run(`${pyCmd} --version`)

  if (!ver) return { label: 'Python', status: 'fail', detail: '未找到' }

  const match = ver.match(/(\d+)\.(\d+)/)
  if (match) {
    const [, major, minor] = match.map(Number)
    if (major >= 3 && minor >= 11) {
      return { label: 'Python', status: 'ok', detail: ver.replace('Python ', 'v') }
    }
    return { label: 'Python', status: 'fail', detail: `${ver} (需要 >= 3.11)` }
  }
  return { label: 'Python', status: 'warn', detail: ver }
}

function checkDocker(): CheckResult {
  if (!hasCommand('docker')) {
    return { label: 'Docker', status: 'fail', detail: '未安装' }
  }
  const ver = run('docker info --format "{{.ServerVersion}}"')
  if (ver) return { label: 'Docker', status: 'ok', detail: `v${ver} (running)` }
  return { label: 'Docker', status: 'warn', detail: '已安装但 daemon 未运行' }
}

function checkDockerCompose(): CheckResult {
  const ver = run('docker compose version --short')
  if (ver) return { label: 'Compose', status: 'ok', detail: `v${ver}` }
  return { label: 'Compose', status: 'fail', detail: '未安装' }
}

function checkVenv(): CheckResult {
  const venvDir = path.join(BRAIN_DIR, '.venv')
  if (fs.existsSync(venvDir)) {
    return { label: 'venv', status: 'ok', detail: 'brain-core/.venv 存在' }
  }
  return { label: 'venv', status: 'warn', detail: '不存在 (运行 pnpm setup 创建)' }
}

function checkConfig(): CheckResult {
  const configPath = getConfigPath()
  if (fs.existsSync(configPath)) {
    return { label: 'config', status: 'ok', detail: configPath }
  }
  return { label: 'config', status: 'warn', detail: '不存在 (运行 pnpm start 自动创建)' }
}

function checkEnvFile(): CheckResult {
  const envPath = path.join(PROJECT_ROOT, '.env')
  if (fs.existsSync(envPath)) {
    return { label: '.env', status: 'ok', detail: '存在' }
  }
  return { label: '.env', status: 'warn', detail: '不存在 (复制 .env.example 并填写 API keys)' }
}

function checkApiKeys(): CheckResult {
  const keys = ['MINIMAX_API_KEY', 'DEEPSEEK_API_KEY', 'OPENAI_API_KEY', 'NVIDIA_API_KEY']
  const set = keys.filter((k) => process.env[k] && process.env[k]!.length > 0)

  // 也尝试从 .env 文件读取
  const envPath = path.join(PROJECT_ROOT, '.env')
  if (fs.existsSync(envPath)) {
    const content = fs.readFileSync(envPath, 'utf-8')
    for (const key of keys) {
      if (!set.includes(key)) {
        const match = content.match(new RegExp(`^${key}=(.+)`, 'm'))
        if (match && match[1].trim().length > 0) {
          set.push(key)
        }
      }
    }
  }

  if (set.length > 0) {
    return { label: 'API Keys', status: 'ok', detail: `${set.join(', ')} 已设置` }
  }
  return { label: 'API Keys', status: 'warn', detail: '未设置任何 LLM API Key' }
}

function checkDockerContainers(): CheckResult {
  const pgStatus = run('docker inspect --format={{.State.Health.Status}} dreamhelp-postgres')
  const redisStatus = run('docker inspect --format={{.State.Health.Status}} dreamhelp-redis')

  if (pgStatus === 'healthy' && redisStatus === 'healthy') {
    return { label: 'Containers', status: 'ok', detail: 'postgres ✓ redis ✓' }
  }
  const parts: string[] = []
  if (pgStatus) parts.push(`pg:${pgStatus}`)
  else parts.push('pg:未运行')
  if (redisStatus) parts.push(`redis:${redisStatus}`)
  else parts.push('redis:未运行')
  return { label: 'Containers', status: 'warn', detail: parts.join(' / ') }
}

// ═══ 主入口 ═══

function main() {
  console.log()
  console.log(c.red('  ╔═══════════════════════════════════════════╗'))
  console.log(c.red('  ║   DREAMVFIA · 梦帮小助 环境诊断           ║'))
  console.log(c.red('  ╚═══════════════════════════════════════════╝'))
  console.log()

  const checks: CheckResult[] = [
    checkNode(),
    checkPnpm(),
    checkPython(),
    checkDocker(),
    checkDockerCompose(),
    checkVenv(),
    checkConfig(),
    checkEnvFile(),
    checkApiKeys(),
    checkDockerContainers(),
  ]

  const icons = { ok: c.green('✓'), warn: c.yellow('⚠'), fail: c.red('✗') }

  for (const check of checks) {
    const icon = icons[check.status]
    const label = check.label.padEnd(12)
    console.log(`  ${icon} ${label} ${check.detail}`)
  }

  const fails = checks.filter((c) => c.status === 'fail')
  const warns = checks.filter((c) => c.status === 'warn')

  console.log()
  if (fails.length > 0) {
    console.log(c.red(`  ${fails.length} 个错误需要修复`))
  }
  if (warns.length > 0) {
    console.log(c.yellow(`  ${warns.length} 个警告 (可选修复)`))
  }
  if (fails.length === 0 && warns.length === 0) {
    console.log(c.green('  ✓ 所有检查通过! 运行 pnpm start 启动服务'))
  }
  console.log()

  process.exit(fails.length > 0 ? 1 : 0)
}

main()
