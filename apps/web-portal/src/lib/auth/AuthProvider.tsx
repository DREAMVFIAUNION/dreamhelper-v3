'use client'

/**
 * AuthProvider — 本地模式 (免注册)
 *
 * 始终注入固定的本地用户，无需登录。
 * 保留 useAuth hook 接口以兼容现有组件。
 */

import { createContext, useCallback, useContext } from 'react'
import type { AuthContextValue, AuthUser } from './types'
import { LOCAL_USER } from '@/lib/local-user'

const localUser: AuthUser = { ...LOCAL_USER, avatarUrl: null }

const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>')
  return ctx
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const refreshUser = useCallback(async () => {}, [])

  const login = useCallback(
    async () => ({ success: true as const }),
    [],
  )

  const register = useCallback(
    async () => ({ success: true as const }),
    [],
  )

  const logout = useCallback(async () => {}, [])

  return (
    <AuthContext.Provider value={{ user: localUser, loading: false, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}
