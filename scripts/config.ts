/**
 * 梦帮小助 — ~/.dreamhelper/config.json 配置管理
 *
 * 首次运行自动创建默认配置文件；后续读取时 merge 默认值 → 用户自定义值。
 */

import fs from 'node:fs'
import path from 'node:path'
import os from 'node:os'

// ═══ 类型定义 ═══

export interface DreamHelperConfig {
  webPort: number
  brainCorePort: number
  language: string
  model: string
  style: string
  dataDir: string
  autoOpenBrowser: boolean
  docker: {
    services: string[]
    composeFile: string
  }
}

// ═══ 默认值 ═══

const DEFAULT_CONFIG: DreamHelperConfig = {
  webPort: 3000,
  brainCorePort: 8000,
  language: 'zh-CN',
  model: 'minimax/MiniMax-M1',
  style: 'default',
  dataDir: '~/.dreamhelper',
  autoOpenBrowser: true,
  docker: {
    services: ['postgres', 'redis'],
    composeFile: 'docker-compose.yml',
  },
}

// ═══ 路径工具 ═══

/** 解析 ~ 为用户主目录 */
function expandHome(p: string): string {
  if (p.startsWith('~')) {
    return path.join(os.homedir(), p.slice(1))
  }
  return p
}

/** 配置目录: ~/.dreamhelper */
export function getConfigDir(): string {
  return path.join(os.homedir(), '.dreamhelper')
}

/** 配置文件路径: ~/.dreamhelper/config.json */
export function getConfigPath(): string {
  return path.join(getConfigDir(), 'config.json')
}

// ═══ 核心 API ═══

/** 确保 ~/.dreamhelper/ 目录存在 */
export function ensureConfigDir(): void {
  const dir = getConfigDir()
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true })
  }
}

/**
 * 加载配置 — merge 默认值 + 用户自定义值
 * 配置文件不存在时自动创建默认版本。
 */
export function loadConfig(): DreamHelperConfig {
  ensureConfigDir()
  const configPath = getConfigPath()

  if (!fs.existsSync(configPath)) {
    // 首次运行: 写入默认配置
    fs.writeFileSync(configPath, JSON.stringify(DEFAULT_CONFIG, null, 2), 'utf-8')
    return { ...DEFAULT_CONFIG }
  }

  try {
    const raw = fs.readFileSync(configPath, 'utf-8')
    const userConfig = JSON.parse(raw) as Partial<DreamHelperConfig>

    // 深度 merge: 默认值 ← 用户自定义
    return {
      ...DEFAULT_CONFIG,
      ...userConfig,
      docker: {
        ...DEFAULT_CONFIG.docker,
        ...(userConfig.docker ?? {}),
      },
    }
  } catch {
    // 配置文件损坏: 使用默认值
    console.warn('[config] ⚠ config.json 解析失败，使用默认配置')
    return { ...DEFAULT_CONFIG }
  }
}

/** 保存配置到 ~/.dreamhelper/config.json */
export function saveConfig(config: DreamHelperConfig): void {
  ensureConfigDir()
  fs.writeFileSync(getConfigPath(), JSON.stringify(config, null, 2), 'utf-8')
}

/** 解析 dataDir (展开 ~) */
export function resolveDataDir(config: DreamHelperConfig): string {
  return expandHome(config.dataDir)
}

// ═══ 直接运行时打印当前配置 ═══

if (process.argv[1] && process.argv[1].endsWith('config.ts')) {
  const config = loadConfig()
  console.log('\n  ╔═══════════════════════════════════════════╗')
  console.log('  ║   DREAMVFIA · 当前配置                    ║')
  console.log('  ╚═══════════════════════════════════════════╝\n')
  console.log(`  配置文件: ${getConfigPath()}`)
  console.log(`  数据目录: ${resolveDataDir(config)}`)
  console.log()
  console.log(JSON.stringify(config, null, 2))
  console.log()
}
