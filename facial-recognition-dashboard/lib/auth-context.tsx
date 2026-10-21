'use client'

import React, { createContext, useContext, useEffect, useState, useMemo, useCallback } from 'react'
import type { UserRole } from './types'
import { logout as apiLogout } from './api/config'

export interface CurrentUserSession {
  username: string
  role: UserRole
  userId: string
  token: string | null
  isAuthenticated: boolean
  isLoaded: boolean
  isAdmin: boolean
  isOperator: boolean
  isViewer: boolean
  canEdit: boolean
  canAdmin: boolean
  logout: () => Promise<void>
  refreshSession: () => void
}

const AuthContext = createContext<CurrentUserSession | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null)
  const [username, setUsername] = useState<string>('admin')
  const [role, setRole] = useState<UserRole>('admin')
  const [userId, setUserId] = useState<string>('')
  const [isLoaded, setIsLoaded] = useState(false)

  const syncFromStorage = useCallback(() => {
    if (typeof window === 'undefined') return
    const storedToken = localStorage.getItem('sentinel_token')
    const storedUser = localStorage.getItem('sentinel_username') || 'admin'
    const storedRole = (localStorage.getItem('sentinel_role') as UserRole) || 'admin'
    const storedId = localStorage.getItem('sentinel_user_id') || ''

    setToken(storedToken)
    setUsername(storedUser)
    setRole(['admin', 'operator', 'viewer'].includes(storedRole) ? storedRole : 'admin')
    setUserId(storedId)
    setIsLoaded(true)
  }, [])

  useEffect(() => {
    syncFromStorage()
    const handleStorage = (e: StorageEvent) => {
      if (e.key?.startsWith('sentinel_')) {
        syncFromStorage()
      }
    }
    window.addEventListener('storage', handleStorage)
    return () => window.removeEventListener('storage', handleStorage)
  }, [syncFromStorage])

  const handleLogout = useCallback(async () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('sentinel_token')
      localStorage.removeItem('sentinel_username')
      localStorage.removeItem('sentinel_role')
      localStorage.removeItem('sentinel_user_id')
    }
    setToken(null)
    await apiLogout()
  }, [])

  const value = useMemo<CurrentUserSession>(() => {
    const isAuthenticated = Boolean(token)
    const isAdmin = role === 'admin'
    const isOperator = role === 'operator'
    const isViewer = role === 'viewer'
    const canEdit = isAdmin || isOperator
    const canAdmin = isAdmin

    return {
      username,
      role,
      userId,
      token,
      isAuthenticated,
      isLoaded,
      isAdmin,
      isOperator,
      isViewer,
      canEdit,
      canAdmin,
      logout: handleLogout,
      refreshSession: syncFromStorage,
    }
  }, [token, username, role, userId, isLoaded, handleLogout, syncFromStorage])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useCurrentUser(): CurrentUserSession {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    // Graceful fallback for components rendered outside AuthProvider (e.g. tests or isolated SSR)
    return {
      username: 'admin',
      role: 'admin',
      userId: 'root-admin',
      token: null,
      isAuthenticated: false,
      isLoaded: true,
      isAdmin: true,
      isOperator: false,
      isViewer: false,
      canEdit: true,
      canAdmin: true,
      logout: async () => {},
      refreshSession: () => {},
    }
  }
  return ctx
}
