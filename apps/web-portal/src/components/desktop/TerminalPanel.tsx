'use client'

/**
 * TerminalPanel — 桌面客户端内嵌终端
 *
 * 仅在 Electron 环境下渲染。使用 xterm.js + IPC 桥接到 node-pty。
 * 支持多终端标签、动态缩放、主题适配。
 */

import { useEffect, useRef, useState, useCallback, memo } from 'react'
import { Plus, X, Terminal as TerminalIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { useElectron } from '@/hooks/useElectron'

interface TerminalTab {
  id: string
  title: string
}

export const TerminalPanel = memo(function TerminalPanel() {
  const { isDesktop, api } = useElectron()
  const [tabs, setTabs] = useState<TerminalTab[]>([])
  const [activeTab, setActiveTab] = useState<string | null>(null)
  const [isCollapsed, setIsCollapsed] = useState(true)
  const termContainerRef = useRef<HTMLDivElement>(null)
  const termInstanceRef = useRef<any>(null)
  const fitAddonRef = useRef<any>(null)

  // 创建新终端
  const createTerminal = useCallback(async () => {
    if (!api) return

    const id = await api.terminal.create()
    const newTab: TerminalTab = { id, title: `终端 ${tabs.length + 1}` }
    setTabs((prev) => [...prev, newTab])
    setActiveTab(id)
    setIsCollapsed(false)
  }, [api, tabs.length])

  // 关闭终端
  const closeTerminal = useCallback(async (id: string) => {
    if (!api) return

    await api.terminal.kill(id)
    setTabs((prev) => {
      const next = prev.filter((t) => t.id !== id)
      if (activeTab === id) {
        setActiveTab(next.length > 0 ? next[next.length - 1]!.id : null)
      }
      if (next.length === 0) setIsCollapsed(true)
      return next
    })
  }, [api, activeTab])

  // 初始化 xterm.js
  useEffect(() => {
    if (!activeTab || !termContainerRef.current || !api) return

    let term: any = null
    let fitAddon: any = null
    let cleanupData: (() => void) | null = null

    const initTerm = async () => {
      // 动态导入 xterm.js
      const { Terminal } = await import('@xterm/xterm')
      const { FitAddon } = await import('@xterm/addon-fit')
      await import('@xterm/xterm/css/xterm.css')

      // 清理旧实例
      if (termInstanceRef.current) {
        termInstanceRef.current.dispose()
      }

      term = new Terminal({
        cursorBlink: true,
        fontSize: 13,
        fontFamily: 'JetBrains Mono, Fira Code, Consolas, monospace',
        theme: {
          background: '#0a0e1a',
          foreground: '#e0e0ff',
          cursor: '#00f0ff',
          cursorAccent: '#0a0e1a',
          selectionBackground: '#00f0ff33',
          black: '#0a0e1a',
          red: '#ff5555',
          green: '#50fa7b',
          yellow: '#f1fa8c',
          blue: '#6272a4',
          magenta: '#ff79c6',
          cyan: '#00f0ff',
          white: '#e0e0ff',
        },
        allowTransparency: true,
        scrollback: 5000,
      })

      fitAddon = new FitAddon()
      term.loadAddon(fitAddon)

      termContainerRef.current!.innerHTML = ''
      term.open(termContainerRef.current!)
      fitAddon.fit()

      termInstanceRef.current = term
      fitAddonRef.current = fitAddon

      // 用户输入 → PTY
      term.onData((data: string) => {
        api.terminal.write(activeTab, data)
      })

      // PTY 输出 → xterm
      cleanupData = api.terminal.onData((event) => {
        if (event.id === activeTab && term) {
          term.write(event.data)
        }
      })

      // 通知 PTY 窗口大小
      api.terminal.resize(activeTab, term.cols, term.rows)

      // 窗口大小变化时重新适配
      const resizeObserver = new ResizeObserver(() => {
        if (fitAddon && term) {
          fitAddon.fit()
          api.terminal.resize(activeTab, term.cols, term.rows)
        }
      })
      if (termContainerRef.current) {
        resizeObserver.observe(termContainerRef.current)
      }

      return () => {
        resizeObserver.disconnect()
      }
    }

    let resizeCleanup: (() => void) | undefined
    initTerm().then((cleanup) => {
      resizeCleanup = cleanup
    }).catch(console.error)

    return () => {
      cleanupData?.()
      resizeCleanup?.()
      if (term) term.dispose()
      termInstanceRef.current = null
      fitAddonRef.current = null
    }
  }, [activeTab, api])

  // 不在 Electron 环境中不渲染
  if (!isDesktop) return null

  return (
    <div className={cn(
      'border-t border-border bg-background transition-all',
      isCollapsed ? 'h-9' : 'h-72',
    )}>
      {/* 标签栏 */}
      <div className="flex items-center h-9 bg-card border-b border-border px-2 gap-1">
        <Button
          variant="ghost"
          size="icon-xs"
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="text-muted-foreground hover:text-primary"
        >
          <TerminalIcon size={12} />
        </Button>

        <span className="text-[10px] font-mono text-muted-foreground mr-2">终端</span>

        {/* 标签 */}
        <div className="flex items-center gap-0.5 overflow-x-auto scrollbar-none flex-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => { setActiveTab(tab.id); setIsCollapsed(false) }}
              className={cn(
                'flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono rounded transition-colors',
                activeTab === tab.id
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:text-foreground hover:bg-secondary',
              )}
            >
              <span>{tab.title}</span>
              <X
                size={10}
                className="opacity-50 hover:opacity-100"
                onClick={(e) => { e.stopPropagation(); closeTerminal(tab.id) }}
              />
            </button>
          ))}
        </div>

        <Button
          variant="ghost"
          size="icon-xs"
          onClick={createTerminal}
          className="text-muted-foreground hover:text-primary"
        >
          <Plus size={12} />
        </Button>
      </div>

      {/* 终端内容 */}
      {!isCollapsed && (
        <div
          ref={termContainerRef}
          className="w-full flex-1"
          style={{ height: 'calc(100% - 36px)' }}
        />
      )}
    </div>
  )
})
