'use client'

import { useState, useRef, useEffect } from 'react'
import Link from 'next/link'
import { useAuth } from '@/lib/auth/AuthProvider'

export function AdminTopNav() {
  const { user } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <header className="h-12 bg-card border-b border-border flex items-center justify-between px-4">
      {/* 左侧: 返回工作台 */}
      <div className="flex items-center gap-3">
        <Link
          href="/chat"
          className="flex items-center gap-1.5 text-xs font-mono text-muted-foreground hover:text-primary transition-colors"
        >
          <span>←</span> 返回工作台
        </Link>
        <div className="w-px h-4 bg-border" />
        <span className="text-[10px] font-mono text-primary/60 tracking-widest">
          ADMIN MODE
        </span>
      </div>

      {/* 右侧: 管理员信息 */}
      <div className="relative" ref={menuRef}>
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className="flex items-center gap-2 text-xs font-mono text-muted-foreground hover:text-foreground transition-colors"
        >
          <div className="w-6 h-6 rounded bg-primary/20 border border-primary/40 flex items-center justify-center text-[10px] text-primary">
            {(user?.displayName || user?.username || 'A').charAt(0).toUpperCase()}
          </div>
          <span className="hidden sm:inline">{user?.displayName || user?.username}</span>
        </button>

        {menuOpen && (
          <div className="absolute right-0 mt-2 w-48 bg-card border border-border shadow-lg rounded-md z-50">
            <div className="p-3 border-b border-border">
              <div className="text-xs font-mono text-foreground truncate">
                {user?.email}
              </div>
              <div className="text-[10px] font-mono text-primary mt-0.5">管理员</div>
            </div>
            <div className="py-1">
              <Link
                href="/admin/system"
                onClick={() => setMenuOpen(false)}
                className="block px-3 py-2 text-xs font-mono text-muted-foreground hover:text-primary hover:bg-secondary"
              >
                ⚙ 系统设置
              </Link>
              <Link
                href="/chat"
                onClick={() => setMenuOpen(false)}
                className="block px-3 py-2 text-xs font-mono text-primary hover:bg-secondary"
              >
                ← 返回聊天
              </Link>
            </div>
          </div>
        )}
      </div>
    </header>
  )
}
