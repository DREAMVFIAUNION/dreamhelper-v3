'use client'

/**
 * BrainCorePanel — brain-core Python 服务状态面板
 *
 * 仅在 Electron 桌面客户端中显示。
 * 提供服务启停控制、健康状态、运行时间等信息。
 */

import { useEffect, useState, useCallback, memo } from 'react'
import { Brain, Power, RefreshCw, Activity } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useElectron } from '@/hooks/useElectron'

interface BrainStatus {
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
}

export const BrainCorePanel = memo(function BrainCorePanel() {
  const { isDesktop, api } = useElectron()
  const [status, setStatus] = useState<BrainStatus | null>(null)
  const [health, setHealth] = useState<HealthResult | null>(null)
  const [loading, setLoading] = useState(false)

  const refreshStatus = useCallback(async () => {
    if (!api) return
    const [s, h] = await Promise.all([
      api.brain.status(),
      api.brain.health(),
    ])
    setStatus(s)
    setHealth(h)
  }, [api])

  // 定时刷新
  useEffect(() => {
    if (!api) return
    refreshStatus()
    const timer = setInterval(refreshStatus, 10_000)
    return () => clearInterval(timer)
  }, [api, refreshStatus])

  const handleToggle = useCallback(async () => {
    if (!api || !status) return
    setLoading(true)
    try {
      if (status.running) {
        await api.brain.stop()
      } else {
        await api.brain.start()
      }
      await refreshStatus()
    } finally {
      setLoading(false)
    }
  }, [api, status, refreshStatus])

  if (!isDesktop) return null

  const formatUptime = (ms: number | null) => {
    if (!ms) return '—'
    const s = Math.floor(ms / 1000)
    const m = Math.floor(s / 60)
    const h = Math.floor(m / 60)
    if (h > 0) return `${h}h ${m % 60}m`
    if (m > 0) return `${m}m ${s % 60}s`
    return `${s}s`
  }

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-card/50 border-b border-border">
      <Brain size={12} className={cn(
        'transition-colors',
        status?.running ? 'text-emerald-400' : 'text-muted-foreground',
      )} />

      <span className="text-[10px] font-mono text-muted-foreground">brain-core</span>

      <Badge
        variant={status?.running ? 'success' : 'secondary'}
        className="text-[8px] px-1 py-0 h-3.5"
      >
        {status?.running ? 'RUNNING' : 'STOPPED'}
      </Badge>

      {health && status?.running && (
        <div className="flex items-center gap-1">
          <Activity size={9} className={cn(
            health.healthy ? 'text-emerald-400' : 'text-red-400',
          )} />
          <span className="text-[9px] font-mono text-muted-foreground">
            {health.latencyMs}ms
          </span>
        </div>
      )}

      {status?.running && (
        <span className="text-[9px] font-mono text-muted-foreground">
          ⏱ {formatUptime(status.uptime)}
        </span>
      )}

      {status?.lastError && (
        <span className="text-[9px] font-mono text-red-400 truncate max-w-32" title={status.lastError}>
          ⚠ {status.lastError}
        </span>
      )}

      <div className="ml-auto flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon-xs"
          onClick={refreshStatus}
          className="text-muted-foreground hover:text-primary"
          title="刷新状态"
        >
          <RefreshCw size={10} />
        </Button>
        <Button
          variant="ghost"
          size="icon-xs"
          onClick={handleToggle}
          disabled={loading}
          className={cn(
            'transition-colors',
            status?.running
              ? 'text-red-400 hover:text-red-300'
              : 'text-emerald-400 hover:text-emerald-300',
          )}
          title={status?.running ? '停止服务' : '启动服务'}
        >
          <Power size={10} />
        </Button>
      </div>
    </div>
  )
})
