'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Bell, Search, Settings, Shield, Globe } from 'lucide-react'
import { useAuth } from '@/lib/auth/AuthProvider'
import { useLocale, useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'

export function TopNav() {
  const { user } = useAuth()
  const locale = useLocale()
  const tNav = useTranslations('topnav')
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  const isAdmin = (user?.tierLevel ?? 0) >= 9
  const roleLabel = isAdmin ? 'Admin' : 'User'
  const initial = (user?.displayName ?? user?.username)?.[0]?.toUpperCase() ?? 'U'

  return (
    <header className="h-14 bg-card border-b border-border flex items-center justify-between px-4 flex-shrink-0">
      {/* 左侧：搜索 */}
      <div className="flex items-center gap-2 flex-1 max-w-md">
        <Search size={14} className="text-muted-foreground" />
        <Input
          type="text"
          placeholder={tNav('searchPlaceholder')}
          className="h-8 border-0 bg-transparent shadow-none font-mono text-xs placeholder:text-muted-foreground/50 focus-visible:ring-0"
        />
      </div>

      {/* 右侧：通知 + 用户菜单 */}
      <div className="flex items-center gap-2">
        <Badge variant="outline" className="text-[9px] font-mono px-1.5 py-0 h-5">
          <Globe size={9} className="mr-0.5" />
          {locale === 'zh-CN' ? 'ZH' : 'EN'}
        </Badge>

        <Popover>
          <PopoverTrigger asChild>
            <Button variant="ghost" size="icon-sm" className="relative text-muted-foreground hover:text-primary">
              <Bell size={16} />
            </Button>
          </PopoverTrigger>
          <PopoverContent align="end" sideOffset={8} className="w-72 p-0">
            <div className="px-4 py-3 border-b border-border">
              <h4 className="text-xs font-mono font-bold tracking-wider">{tNav('notifications') ?? '通知'}</h4>
            </div>
            <div className="px-4 py-8 text-center">
              <Bell size={20} className="mx-auto mb-2 text-muted-foreground/40" />
              <p className="text-xs text-muted-foreground">暂无新通知</p>
            </div>
          </PopoverContent>
        </Popover>

        <Separator orientation="vertical" className="h-5" />

        {/* 用户菜单 — Radix DropdownMenu (client-only to avoid hydration id mismatch) */}
        {mounted ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" className="gap-2 px-2 text-muted-foreground hover:text-foreground">
                <Avatar className="h-6 w-6">
                  {user?.avatarUrl && <AvatarImage src={user.avatarUrl} alt="" />}
                  <AvatarFallback className="bg-primary/20 text-primary text-[10px] font-bold border border-primary/40">
                    {initial}
                  </AvatarFallback>
                </Avatar>
                <span className="text-xs font-mono hidden sm:block max-w-[80px] truncate">
                  {user?.displayName ?? user?.username ?? 'User'}
                </span>
              </Button>
            </DropdownMenuTrigger>

            <DropdownMenuContent className="w-56" align="end" sideOffset={8}>
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-mono font-medium leading-none truncate">
                    {user?.displayName ?? user?.username}
                  </p>
                  <p className="text-xs font-mono text-muted-foreground truncate">
                    {user?.email}
                  </p>
                  <Badge variant="cyber" className="w-fit mt-1 text-[9px] px-1.5 py-0">
                    {roleLabel}
                  </Badge>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuGroup>
                <DropdownMenuItem asChild className="cursor-pointer font-mono text-xs">
                  <Link href="/settings">
                    <Settings size={14} />
                    {tNav('accountSettings')}
                  </Link>
                </DropdownMenuItem>
                {isAdmin && (
                  <DropdownMenuItem asChild className="cursor-pointer font-mono text-xs">
                    <Link href="/admin">
                      <Shield size={14} />
                      {tNav('adminPanel')}
                    </Link>
                  </DropdownMenuItem>
                )}
              </DropdownMenuGroup>
            </DropdownMenuContent>
          </DropdownMenu>
        ) : (
          <Button variant="ghost" size="sm" className="gap-2 px-2 text-muted-foreground">
            <Avatar className="h-6 w-6">
              <AvatarFallback className="bg-primary/20 text-primary text-[10px] font-bold border border-primary/40">
                {initial}
              </AvatarFallback>
            </Avatar>
            <span className="text-xs font-mono hidden sm:block max-w-[80px] truncate">
              {user?.displayName ?? user?.username ?? 'User'}
            </span>
          </Button>
        )}
      </div>
    </header>
  )
}
