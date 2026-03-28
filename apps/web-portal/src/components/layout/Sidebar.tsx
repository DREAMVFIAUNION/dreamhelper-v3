'use client'

import Link from 'next/link'
import Image from 'next/image'
import { usePathname } from 'next/navigation'
import {
  MessageSquare, Bot, Database, BarChart3, Settings, ChevronLeft, Shield, Workflow, Radio,
} from 'lucide-react'
import { useState, useEffect, useCallback } from 'react'
import { useTranslations } from 'next-intl'
import { cn } from '@/lib/utils'
import { useAuth } from '@/lib/auth/AuthProvider'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

const NAV_KEYS = [
  { href: '/chat',      icon: MessageSquare, key: 'chat',      tag: 'CHAT' },
  { href: '/agents',    icon: Bot,           key: 'agents',    tag: 'AGENTS' },
  { href: '/workflows', icon: Workflow,      key: 'workflows', tag: 'FLOW' },
  { href: '/knowledge', icon: Database,      key: 'knowledge', tag: 'KB' },
  { href: '/channels',  icon: Radio,         key: 'channels',  tag: 'CH' },
  { href: '/analytics', icon: BarChart3,     key: 'analytics', tag: 'DATA' },
  { href: '/settings',  icon: Settings,      key: 'settings',  tag: 'SETTINGS' },
] as const

export function Sidebar() {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)
  const { user } = useAuth()
  const t = useTranslations('nav')
  const isAdmin = (user?.tierLevel ?? 0) >= 9

  const toggle = useCallback(() => setCollapsed((c) => !c), [])

  useEffect(() => {
    // Set initial collapsed state after hydration to avoid SSR mismatch
    if (window.innerWidth < 768) setCollapsed(true)

    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
        e.preventDefault()
        toggle()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [toggle])

  return (
    <>
    <TooltipProvider delayDuration={0}>
      <aside aria-label="主导航" className={cn(
        'h-full bg-sidebar border-r border-sidebar-border flex flex-col transition-all duration-200',
        'max-md:fixed max-md:inset-y-0 max-md:left-0 max-md:z-40 max-md:w-56',
        'max-md:shadow-xl',
        collapsed ? 'w-14 max-md:-translate-x-full' : 'w-56 max-md:translate-x-0',
      )}>
        {/* LOGO */}
        <div className="h-14 flex items-center gap-2.5 px-3 border-b border-sidebar-border flex-shrink-0">
          <div className="relative w-7 h-7 flex-shrink-0">
            <Image src="/logo/logo.png" alt="DREAMVFIA" fill sizes="28px" className="object-contain" />
          </div>
          {!collapsed && (
            <span className="font-display text-xs font-bold text-primary tracking-[0.15em] truncate">
              DREAMVFIA
            </span>
          )}
        </div>

        {/* 导航 */}
        <ScrollArea className="flex-1">
          <nav className="py-2 space-y-1 px-2">
            {NAV_KEYS.map(({ href, icon: Icon, key }) => {
              const label = t(key)
              const active = pathname.startsWith(href)
              const linkContent = (
                <Link key={href} href={href}
                  className={cn(
                    'flex items-center gap-2.5 px-2.5 py-2 rounded-md text-sm font-medium transition-all duration-150',
                    active
                      ? 'bg-primary/10 text-primary border-l-2 border-primary shadow-[inset_0_0_12px_hsl(var(--primary)/0.06)]'
                      : 'text-sidebar-foreground hover:text-foreground hover:bg-sidebar-accent',
                    collapsed && 'justify-center px-0',
                  )}>
                  <Icon size={16} className={cn('shrink-0', active && 'drop-shadow-[0_0_4px_hsl(var(--primary)/0.5)]')} />
                  {!collapsed && (
                    <span className="font-mono text-xs tracking-wider truncate">{label}</span>
                  )}
                </Link>
              )

              if (collapsed) {
                return (
                  <Tooltip key={href}>
                    <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
                    <TooltipContent side="right" className="font-mono text-xs">
                      {label}
                    </TooltipContent>
                  </Tooltip>
                )
              }
              return linkContent
            })}
          </nav>
        </ScrollArea>

        {/* 底部快捷入口 */}
        <Separator className="bg-sidebar-border" />
        <div className="px-2 py-2 space-y-1">
          {[
            { href: '/admin', icon: Shield, label: t('admin'), show: isAdmin, accent: true },
          ].filter((i) => i.show).map(({ href, icon: Icon, label, accent }) => {
            const linkEl = (
              <Link key={href} href={href}
                className={cn(
                  'flex items-center gap-2.5 px-2.5 py-2 rounded-md text-sm transition-all duration-150',
                  accent
                    ? 'text-sidebar-foreground hover:text-primary hover:bg-primary/5'
                    : 'text-sidebar-foreground hover:text-foreground hover:bg-sidebar-accent',
                  collapsed && 'justify-center px-0',
                )}
              >
                <Icon size={16} className="shrink-0" />
                {!collapsed && <span className="font-mono text-xs tracking-wider">{label}</span>}
              </Link>
            )

            if (collapsed) {
              return (
                <Tooltip key={href}>
                  <TooltipTrigger asChild>{linkEl}</TooltipTrigger>
                  <TooltipContent side="right" className="font-mono text-xs">
                    {label}
                  </TooltipContent>
                </Tooltip>
              )
            }
            return linkEl
          })}
        </div>

        {/* 折叠按钮 */}
        <Separator className="bg-sidebar-border" />
        <div className="flex items-center justify-center py-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon-xs"
                onClick={toggle}
                className="text-muted-foreground hover:text-foreground"
              >
                <ChevronLeft size={14} className={cn('transition-transform', collapsed && 'rotate-180')} />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right" className="font-mono text-xs">
              {collapsed ? t('expand') : t('collapse')} <kbd className="ml-1 text-[9px] opacity-60">Ctrl+B</kbd>
            </TooltipContent>
          </Tooltip>
        </div>
      </aside>
    </TooltipProvider>
    {/* Mobile backdrop */}
    {!collapsed && (
      <div
        className="fixed inset-0 z-30 bg-black/50 md:hidden"
        onClick={toggle}
        aria-hidden="true"
      />
    )}
    </>
  )
}
