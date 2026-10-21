'use client'

import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchUsers,
  createUser,
  updateUser,
  deleteUser,
  fetchAuditLogs,
  fetchDeviceApiKeys,
  createDeviceApiKey,
  revokeDeviceApiKey,
  fetchRetentionStatus,
  triggerRetentionPurge,
} from '@/lib/api'
import { useCurrentUser } from '@/lib/auth-context'
import type { UserAccount, UserRole, DeviceApiKeyCreated } from '@/lib/types'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { cn } from '@/lib/utils'
import { formatTime } from '@/lib/format'
import {
  Users,
  UserPlus,
  Shield,
  ShieldAlert,
  Key,
  FileText,
  Trash2,
  RefreshCw,
  Copy,
  Check,
  Calendar,
  Lock,
  Layers,
  HardDrive,
  Info,
  CheckCircle2,
  XCircle,
  Eye,
  UserCog,
} from 'lucide-react'

export function AccessControlPanel() {
  const { role, username: currentUsername, canAdmin, isViewer } = useCurrentUser()
  const queryClient = useQueryClient()
  const [subTab, setSubTab] = useState<'users' | 'audit' | 'keys' | 'retention'>('users')

  // --- Users State ---
  const [showAddUserModal, setShowAddUserModal] = useState(false)
  const [newUsername, setNewUsername] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newFullName, setNewFullName] = useState('')
  const [newRole, setNewRole] = useState<UserRole>('viewer')
  const [userError, setUserError] = useState('')

  // --- Edge Keys State ---
  const [showAddKeyModal, setShowAddKeyModal] = useState(false)
  const [keyName, setKeyName] = useState('')
  const [allowedCamerasStr, setAllowedCamerasStr] = useState('')
  const [createdKeySecret, setCreatedKeySecret] = useState<DeviceApiKeyCreated | null>(null)
  const [copiedKey, setCopiedKey] = useState(false)
  const [keyError, setKeyError] = useState('')

  // --- Audit Filters State ---
  const [auditActionFilter, setAuditActionFilter] = useState('')
  const [auditUserFilter, setAuditUserFilter] = useState('')

  // --- Retention Purge State ---
  const [purgeSuccessMsg, setPurgeSuccessMsg] = useState('')

  // Queries
  const { data: users = [], isLoading: loadingUsers } = useQuery({
    queryKey: ['access-control-users'],
    queryFn: () => fetchUsers(),
  })

  const { data: auditLogs = [], isLoading: loadingAudit, refetch: refetchAudit } = useQuery({
    queryKey: ['access-control-audit', auditActionFilter, auditUserFilter],
    queryFn: () => fetchAuditLogs({
      limit: 100,
      action: auditActionFilter || undefined,
      username: auditUserFilter || undefined,
    }),
  })

  const { data: deviceKeys = [], isLoading: loadingKeys } = useQuery({
    queryKey: ['access-control-keys'],
    queryFn: () => fetchDeviceApiKeys(),
  })

  const { data: retentionStatus, isLoading: loadingRetention, refetch: refetchRetention } = useQuery({
    queryKey: ['access-control-retention'],
    queryFn: () => fetchRetentionStatus(),
  })

  // Mutations
  const createUserMutation = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['access-control-users'] })
      queryClient.invalidateQueries({ queryKey: ['access-control-audit'] })
      setShowAddUserModal(false)
      setNewUsername('')
      setNewPassword('')
      setNewFullName('')
      setNewRole('viewer')
      setUserError('')
    },
    onError: (err: any) => {
      setUserError(err?.message || 'Failed to create user account')
    },
  })

  const updateUserMutation = useMutation({
    mutationFn: ({ userId, payload }: { userId: string; payload: any }) =>
      updateUser(userId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['access-control-users'] })
      queryClient.invalidateQueries({ queryKey: ['access-control-audit'] })
    },
  })

  const deleteUserMutation = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['access-control-users'] })
      queryClient.invalidateQueries({ queryKey: ['access-control-audit'] })
    },
  })

  const createKeyMutation = useMutation({
    mutationFn: createDeviceApiKey,
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['access-control-keys'] })
      queryClient.invalidateQueries({ queryKey: ['access-control-audit'] })
      setCreatedKeySecret(res)
      setKeyName('')
      setAllowedCamerasStr('')
      setKeyError('')
    },
    onError: (err: any) => {
      setKeyError(err?.message || 'Failed to generate edge key')
    },
  })

  const revokeKeyMutation = useMutation({
    mutationFn: revokeDeviceApiKey,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['access-control-keys'] })
      queryClient.invalidateQueries({ queryKey: ['access-control-audit'] })
    },
  })

  const purgeRetentionMutation = useMutation({
    mutationFn: triggerRetentionPurge,
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['access-control-retention'] })
      queryClient.invalidateQueries({ queryKey: ['access-control-audit'] })
      setPurgeSuccessMsg(
        `Retention purge executed: ${res.purgedFaceCropsCount} expired face crops pruned (${res.retainedFaceCropsCount} crops retained).`,
      )
    },
  })

  const handleCreateUser = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newUsername.trim() || !newPassword) return
    createUserMutation.mutate({
      username: newUsername.trim(),
      password: newPassword,
      fullName: newFullName.trim() || undefined,
      role: newRole,
    })
  }

  const handleCreateKey = (e: React.FormEvent) => {
    e.preventDefault()
    if (!keyName.trim()) return
    const cameras = allowedCamerasStr
      ? allowedCamerasStr.split(',').map((s) => s.trim()).filter(Boolean)
      : undefined
    createKeyMutation.mutate({
      name: keyName.trim(),
      allowedCameras: cameras,
    })
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedKey(true)
    setTimeout(() => setCopiedKey(false), 2500)
  }

  return (
    <div className="space-y-4">
      {/* Top Banner if Viewer */}
      {isViewer && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-400">
          <Info className="size-4 shrink-0" />
          <span>
            <strong>Read-Only Access:</strong> You are logged in with the <strong>viewer</strong> role. Administrative actions (user creation, edge key generation, retention purging) are disabled.
          </span>
        </div>
      )}

      {/* Access Control Sub-Nav Header */}
      <Card className="border-border/60 bg-card/40 backdrop-blur-md">
        <CardHeader className="p-4 pb-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-base font-bold">
                <Shield className="size-4.5 text-primary" />
                Security Administration & Access Control
              </CardTitle>
              <CardDescription className="text-xs">
                Role-Based Access Control (RBAC), Edge Device Scoped Keys, Audit Ledger & Retention Policies
              </CardDescription>
            </div>

            {/* Sub-Tabs Nav */}
            <div className="flex flex-wrap items-center rounded-lg border border-border/80 bg-muted/60 p-1 shadow-inner">
              <button
                type="button"
                onClick={() => setSubTab('users')}
                className={cn(
                  'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-all',
                  subTab === 'users'
                    ? 'bg-background text-foreground shadow-sm ring-1 ring-border'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                <Users className="size-3.5" />
                <span>Accounts ({users.length})</span>
              </button>

              <button
                type="button"
                onClick={() => setSubTab('audit')}
                className={cn(
                  'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-all',
                  subTab === 'audit'
                    ? 'bg-background text-foreground shadow-sm ring-1 ring-border'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                <FileText className="size-3.5" />
                <span>Audit Ledger</span>
              </button>

              <button
                type="button"
                onClick={() => setSubTab('keys')}
                className={cn(
                  'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-all',
                  subTab === 'keys'
                    ? 'bg-background text-foreground shadow-sm ring-1 ring-border'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                <Key className="size-3.5" />
                <span>Edge Keys ({deviceKeys.length})</span>
              </button>

              <button
                type="button"
                onClick={() => setSubTab('retention')}
                className={cn(
                  'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-all',
                  subTab === 'retention'
                    ? 'bg-background text-foreground shadow-sm ring-1 ring-border'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                <HardDrive className="size-3.5" />
                <span>Biometric Retention</span>
              </button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* ==================== SUB-TAB 1: USERS (RBAC) ==================== */}
      {subTab === 'users' && (
        <Card className="border-border/60 bg-card/40 backdrop-blur-md">
          <CardHeader className="flex flex-row items-center justify-between p-4 pb-2 border-b border-border/40">
            <div>
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Users className="size-4 text-primary" />
                Registered System Operators & Administrators
              </h3>
              <p className="text-[11px] text-muted-foreground">
                Manage console privileges: Admin (full root control), Operator (vector & stream operations), Viewer (read-only).
              </p>
            </div>
            {canAdmin && (
              <Button
                size="sm"
                onClick={() => setShowAddUserModal(true)}
                className="gap-1.5 h-8 text-xs font-semibold"
              >
                <UserPlus className="size-3.5" />
                Add User Account
              </Button>
            )}
          </CardHeader>
          <CardContent className="p-0">
            {loadingUsers ? (
              <div className="p-8 text-center text-xs text-muted-foreground animate-pulse font-mono">
                Loading system credentials...
              </div>
            ) : users.length === 0 ? (
              <div className="p-8 text-center text-xs text-muted-foreground">
                No registered user accounts found.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-border/50 bg-muted/40 font-mono text-[10px] uppercase text-muted-foreground">
                    <tr>
                      <th className="px-4 py-2.5">User Identity</th>
                      <th className="px-4 py-2.5">Assigned Role</th>
                      <th className="px-4 py-2.5">Account Status</th>
                      <th className="px-4 py-2.5">Created</th>
                      <th className="px-4 py-2.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/30">
                    {users.map((u) => {
                      const isSelf = u.username === currentUsername
                      const isRootAdmin = u.username === 'admin' || u.id === 'root-admin'

                      return (
                        <tr key={u.id} className="transition-colors hover:bg-muted/20">
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2.5">
                              <div className="flex size-7 items-center justify-center rounded-full bg-primary/10 font-mono text-xs font-bold text-primary">
                                {u.username.slice(0, 2).toUpperCase()}
                              </div>
                              <div>
                                <p className="font-semibold text-foreground">{u.username}</p>
                                {u.fullName && (
                                  <p className="text-[10px] text-muted-foreground">{u.fullName}</p>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            {canAdmin && !isSelf ? (
                              <select
                                value={u.role}
                                onChange={(e) =>
                                  updateUserMutation.mutate({
                                    userId: u.id,
                                    payload: { role: e.target.value as UserRole },
                                  })
                                }
                                className="h-7 rounded border border-border/70 bg-background/80 px-2 font-mono text-[11px] capitalize focus:outline-none focus:ring-1 focus:ring-primary"
                              >
                                <option value="admin">admin</option>
                                <option value="operator">operator</option>
                                <option value="viewer">viewer</option>
                              </select>
                            ) : (
                              <Badge
                                variant="outline"
                                className={cn(
                                  'font-mono text-[10px] uppercase font-bold',
                                  u.role === 'admin'
                                    ? 'border-primary/40 bg-primary/10 text-primary'
                                    : u.role === 'operator'
                                      ? 'border-info/40 bg-info/10 text-info'
                                      : 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400',
                                )}
                              >
                                {u.role}
                              </Badge>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            {canAdmin && !isSelf ? (
                              <button
                                type="button"
                                onClick={() =>
                                  updateUserMutation.mutate({
                                    userId: u.id,
                                    payload: { isActive: !u.isActive },
                                  })
                                }
                                className={cn(
                                  'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold transition-all',
                                  u.isActive
                                    ? 'bg-success/15 text-success hover:bg-success/25'
                                    : 'bg-destructive/15 text-destructive hover:bg-destructive/25',
                                )}
                              >
                                <span
                                  className={cn(
                                    'size-1.5 rounded-full',
                                    u.isActive ? 'bg-success' : 'bg-destructive',
                                  )}
                                />
                                {u.isActive ? 'Active' : 'Suspended'}
                              </button>
                            ) : (
                              <span
                                className={cn(
                                  'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold',
                                  u.isActive
                                    ? 'bg-success/15 text-success'
                                    : 'bg-destructive/15 text-destructive',
                                )}
                              >
                                <span
                                  className={cn(
                                    'size-1.5 rounded-full',
                                    u.isActive ? 'bg-success' : 'bg-destructive',
                                  )}
                                />
                                {u.isActive ? 'Active' : 'Suspended'}
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 font-mono text-[11px] text-muted-foreground">
                            {u.createdAt ? formatTime(u.createdAt) : 'System default'}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {canAdmin && !isSelf && !isRootAdmin && (
                              <Button
                                size="xs"
                                variant="ghost"
                                onClick={() => {
                                  if (confirm(`Permanently revoke and delete account for "${u.username}"?`)) {
                                    deleteUserMutation.mutate(u.id)
                                  }
                                }}
                                className="h-7 text-destructive hover:bg-destructive/10 hover:text-destructive"
                              >
                                <Trash2 className="size-3.5" />
                              </Button>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ==================== SUB-TAB 2: AUDIT LEDGER ==================== */}
      {subTab === 'audit' && (
        <Card className="border-border/60 bg-card/40 backdrop-blur-md">
          <CardHeader className="p-4 pb-3 border-b border-border/40">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                  <FileText className="size-4 text-primary" />
                  Tamper-Resistant Security Audit Ledger
                </h3>
                <p className="text-[11px] text-muted-foreground">
                  Immutable audit records tracking authentication, credential modifications, camera configurations, and biometric purges.
                </p>
              </div>

              {/* Audit Controls & Filters */}
              <div className="flex flex-wrap items-center gap-2">
                <Input
                  placeholder="Filter by action..."
                  value={auditActionFilter}
                  onChange={(e) => setAuditActionFilter(e.target.value)}
                  className="h-8 w-36 text-xs font-mono"
                />
                <Input
                  placeholder="Filter by user..."
                  value={auditUserFilter}
                  onChange={(e) => setAuditUserFilter(e.target.value)}
                  className="h-8 w-32 text-xs font-mono"
                />
                <Button
                  size="xs"
                  variant="outline"
                  onClick={() => refetchAudit()}
                  className="h-8 gap-1 text-xs"
                >
                  <RefreshCw className="size-3" />
                  Refresh
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {loadingAudit ? (
              <div className="p-8 text-center text-xs text-muted-foreground animate-pulse font-mono">
                Querying security audit logs...
              </div>
            ) : auditLogs.length === 0 ? (
              <div className="p-8 text-center text-xs text-muted-foreground">
                No audit ledger records match the selected criteria.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-border/50 bg-muted/40 font-mono text-[10px] uppercase text-muted-foreground">
                    <tr>
                      <th className="px-4 py-2.5">Timestamp (IST)</th>
                      <th className="px-4 py-2.5">Action Event</th>
                      <th className="px-4 py-2.5">Actor</th>
                      <th className="px-4 py-2.5">Target Resource</th>
                      <th className="px-4 py-2.5">Client IP</th>
                      <th className="px-4 py-2.5">Event Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/30 font-mono text-[11px]">
                    {auditLogs.map((log) => {
                      const isAuth = log.action.startsWith('auth.')
                      const isDelete = log.action.includes('delete') || log.action.includes('purge') || log.action.includes('revoke')
                      const isCreate = log.action.includes('create')

                      return (
                        <tr key={log.id} className="transition-colors hover:bg-muted/20">
                          <td className="px-4 py-2.5 whitespace-nowrap text-muted-foreground">
                            {formatTime(log.timestamp)}
                          </td>
                          <td className="px-4 py-2.5">
                            <span
                              className={cn(
                                'inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-bold uppercase',
                                isDelete
                                  ? 'bg-destructive/15 text-destructive border border-destructive/30'
                                  : isCreate
                                    ? 'bg-success/15 text-success border border-success/30'
                                    : isAuth
                                      ? 'bg-primary/15 text-primary border border-primary/30'
                                      : 'bg-muted text-foreground border border-border',
                              )}
                            >
                              {log.action}
                            </span>
                          </td>
                          <td className="px-4 py-2.5 text-foreground font-semibold">
                            {log.username}
                            {log.role && (
                              <span className="text-[10px] text-muted-foreground font-normal ml-1">
                                ({log.role})
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-2.5 text-muted-foreground">
                            {log.resourceType ? `${log.resourceType}` : 'system'}
                          </td>
                          <td className="px-4 py-2.5 text-muted-foreground">
                            {log.clientIp || '127.0.0.1'}
                          </td>
                          <td className="px-4 py-2.5 text-foreground/80 max-w-xs truncate" title={log.details || ''}>
                            {log.details || '—'}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ==================== SUB-TAB 3: EDGE DEVICE KEYS ==================== */}
      {subTab === 'keys' && (
        <Card className="border-border/60 bg-card/40 backdrop-blur-md">
          <CardHeader className="flex flex-row items-center justify-between p-4 pb-2 border-b border-border/40">
            <div>
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Key className="size-4 text-primary" />
                Scoped Edge Device API Keys (S8)
              </h3>
              <p className="text-[11px] text-muted-foreground">
                Issue scoped API tokens for edge inference nodes and CCTV gateways restricted to specific camera streams.
              </p>
            </div>
            {canAdmin && (
              <Button
                size="sm"
                onClick={() => setShowAddKeyModal(true)}
                className="gap-1.5 h-8 text-xs font-semibold"
              >
                <Key className="size-3.5" />
                Generate Scoped Key
              </Button>
            )}
          </CardHeader>

          {/* Flash Secret Key Notification if newly created */}
          {createdKeySecret && (
            <div className="m-4 rounded-lg border border-success/40 bg-success/10 p-3 text-xs">
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-success flex items-center gap-1.5">
                  <CheckCircle2 className="size-4" /> Edge Key Generated Successfully
                </span>
                <Button
                  size="xs"
                  variant="outline"
                  onClick={() => copyToClipboard(createdKeySecret.key)}
                  className="gap-1 text-[11px] h-6"
                >
                  {copiedKey ? <Check className="size-3 text-success" /> : <Copy className="size-3" />}
                  {copiedKey ? 'Copied' : 'Copy Plaintext Secret'}
                </Button>
              </div>
              <p className="text-muted-foreground text-[11px]">
                Copy this key now. For cryptographic safety, it will <strong>never</strong> be displayed again.
              </p>
              <div className="mt-2 rounded bg-black/60 p-2 font-mono text-[11px] text-primary break-all border border-border/50">
                {createdKeySecret.key}
              </div>
            </div>
          )}

          <CardContent className="p-0">
            {loadingKeys ? (
              <div className="p-8 text-center text-xs text-muted-foreground animate-pulse font-mono">
                Loading edge credentials...
              </div>
            ) : deviceKeys.length === 0 ? (
              <div className="p-8 text-center text-xs text-muted-foreground">
                No edge device API keys registered.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-border/50 bg-muted/40 font-mono text-[10px] uppercase text-muted-foreground">
                    <tr>
                      <th className="px-4 py-2.5">Key Name / Device</th>
                      <th className="px-4 py-2.5">Key Prefix</th>
                      <th className="px-4 py-2.5">Allowed Camera Scopes</th>
                      <th className="px-4 py-2.5">Status</th>
                      <th className="px-4 py-2.5">Created</th>
                      <th className="px-4 py-2.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/30">
                    {deviceKeys.map((k) => (
                      <tr key={k.id} className="transition-colors hover:bg-muted/20">
                        <td className="px-4 py-3 font-semibold text-foreground">
                          {k.name}
                        </td>
                        <td className="px-4 py-3 font-mono text-[11px] text-primary">
                          {k.keyPrefix}
                        </td>
                        <td className="px-4 py-3 font-mono text-[11px]">
                          {k.allowedCameras ? (
                            <span className="rounded bg-muted/60 px-2 py-0.5 border border-border/50 text-foreground">
                              {k.allowedCameras}
                            </span>
                          ) : (
                            <span className="text-muted-foreground italic">
                              Unrestricted (All Cameras)
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={cn(
                              'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold',
                              k.isActive
                                ? 'bg-success/15 text-success'
                                : 'bg-muted text-muted-foreground line-through',
                            )}
                          >
                            <span
                              className={cn(
                                'size-1.5 rounded-full',
                                k.isActive ? 'bg-success' : 'bg-muted-foreground',
                              )}
                            />
                            {k.isActive ? 'Active' : 'Revoked'}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-mono text-[11px] text-muted-foreground">
                          {k.createdAt ? formatTime(k.createdAt) : '—'}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {canAdmin && k.isActive && (
                            <Button
                              size="xs"
                              variant="ghost"
                              onClick={() => {
                                if (confirm(`Revoke edge key for "${k.name}"? This will immediately disconnect the node.`)) {
                                  revokeKeyMutation.mutate(k.id)
                                }
                              }}
                              className="h-7 text-destructive hover:bg-destructive/10 hover:text-destructive"
                            >
                              Revoke
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ==================== SUB-TAB 4: BIOMETRIC RETENTION ==================== */}
      {subTab === 'retention' && (
        <div className="space-y-4">
          <Card className="border-border/60 bg-card/40 backdrop-blur-md">
            <CardHeader className="p-4 pb-3 border-b border-border/40">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                    <HardDrive className="size-4 text-primary" />
                    Biometric Retention Policy & Storage Pruning (S4)
                  </h3>
                  <p className="text-[11px] text-muted-foreground">
                    Enforces legal privacy compliance by purging raw face crops older than the retention threshold while preserving full tamper-resistant event logs and permanent enrollment galleries.
                  </p>
                </div>
                {canAdmin && (
                  <Button
                    size="sm"
                    onClick={() => {
                      if (confirm('Execute biometric data retention purge now? Raw face crop thumbnails older than policy will be removed.')) {
                        purgeRetentionMutation.mutate({ preserveFlaggedAlerts: true })
                      }
                    }}
                    disabled={purgeRetentionMutation.isPending}
                    className="gap-1.5 h-8 text-xs font-semibold bg-amber-600 hover:bg-amber-700 text-white"
                  >
                    <Trash2 className="size-3.5" />
                    {purgeRetentionMutation.isPending ? 'Purging Crops...' : 'Run Manual Purge'}
                  </Button>
                )}
              </div>
            </CardHeader>

            {purgeSuccessMsg && (
              <div className="m-4 rounded-lg border border-success/40 bg-success/10 p-3 text-xs text-success flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <CheckCircle2 className="size-4 shrink-0" />
                  {purgeSuccessMsg}
                </span>
                <button
                  type="button"
                  onClick={() => setPurgeSuccessMsg('')}
                  className="text-muted-foreground hover:text-foreground text-xs"
                >
                  Dismiss
                </button>
              </div>
            )}

            <CardContent className="p-4">
              {loadingRetention ? (
                <div className="p-8 text-center text-xs text-muted-foreground animate-pulse font-mono">
                  Loading retention metrics...
                </div>
              ) : !retentionStatus ? (
                <div className="p-8 text-center text-xs text-muted-foreground">
                  Unable to load retention policy status.
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <div className="rounded-lg border border-border/50 bg-muted/20 p-3.5">
                    <span className="text-[11px] font-medium text-muted-foreground block">
                      Retention Policy Window
                    </span>
                    <span className="font-mono text-xl font-bold text-foreground">
                      {retentionStatus.retentionDays} Days
                    </span>
                    <span className="text-[10px] text-success block mt-1">
                      ● Background auto-purge active
                    </span>
                  </div>

                  <div className="rounded-lg border border-border/50 bg-muted/20 p-3.5">
                    <span className="text-[11px] font-medium text-muted-foreground block">
                      Active Face Crops Stored
                    </span>
                    <span className="font-mono text-xl font-bold text-primary">
                      {retentionStatus.detectionsWithFaceCrops}
                    </span>
                    <span className="text-[10px] text-muted-foreground block mt-1">
                      Across {retentionStatus.totalDetections} event detections
                    </span>
                  </div>

                  <div className="rounded-lg border border-border/50 bg-muted/20 p-3.5">
                    <span className="text-[11px] font-medium text-muted-foreground block">
                      Preserved Flagged Alerts
                    </span>
                    <span className="font-mono text-xl font-bold text-amber-400">
                      {retentionStatus.preservedAlertFaceCrops}
                    </span>
                    <span className="text-[10px] text-muted-foreground block mt-1">
                      Protected forensic evidence
                    </span>
                  </div>

                  <div className="rounded-lg border border-border/50 bg-muted/20 p-3.5">
                    <span className="text-[11px] font-medium text-muted-foreground block">
                      Enrolled Gallery Profiles
                    </span>
                    <span className="font-mono text-xl font-bold text-emerald-400">
                      {retentionStatus.enrolledProfilesProtected}
                    </span>
                    <span className="text-[10px] text-muted-foreground block mt-1">
                      Permanent reference vectors
                    </span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* ==================== MODAL: ADD USER ACCOUNT ==================== */}
      <Dialog open={showAddUserModal} onOpenChange={setShowAddUserModal}>
        <DialogContent className="max-w-md border-border/70 bg-card/95 backdrop-blur-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <UserPlus className="size-4.5 text-primary" />
              Register System User
            </DialogTitle>
            <DialogDescription className="text-xs">
              Create an operator or administrative credential for the Sentinel console.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreateUser} className="space-y-3.5">
            <div className="space-y-1.5">
              <Label className="text-xs">Username / Operator Handle</Label>
              <Input
                placeholder="e.g. j_doe"
                value={newUsername}
                onChange={(e) => setNewUsername(e.target.value)}
                required
                className="h-8 text-xs font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs">Full Name / Badge Tag</Label>
              <Input
                placeholder="e.g. Jane Doe"
                value={newFullName}
                onChange={(e) => setNewFullName(e.target.value)}
                className="h-8 text-xs"
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs">Initial Password (min 6 chars)</Label>
              <Input
                type="password"
                placeholder="••••••••"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                className="h-8 text-xs"
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs">Access Role</Label>
              <select
                value={newRole}
                onChange={(e) => setNewRole(e.target.value as UserRole)}
                className="h-8 w-full rounded-md border border-border bg-background px-2 font-mono text-xs capitalize"
              >
                <option value="viewer">Viewer (Read-only observation)</option>
                <option value="operator">Operator (Vectors, alerts, camera thresholds)</option>
                <option value="admin">Admin (Full administrative & key control)</option>
              </select>
            </div>

            {userError && (
              <div className="text-xs text-destructive bg-destructive/10 p-2 rounded border border-destructive/30">
                {userError}
              </div>
            )}

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setShowAddUserModal(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={createUserMutation.isPending}
                className="gap-1.5"
              >
                {createUserMutation.isPending ? 'Registering...' : 'Create Account'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ==================== MODAL: ADD SCOPED EDGE KEY ==================== */}
      <Dialog open={showAddKeyModal} onOpenChange={setShowAddKeyModal}>
        <DialogContent className="max-w-md border-border/70 bg-card/95 backdrop-blur-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <Key className="size-4.5 text-primary" />
              Generate Scoped Edge Device Key
            </DialogTitle>
            <DialogDescription className="text-xs">
              Generate an authenticated token for an edge processing gateway or CCTV camera rig.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreateKey} className="space-y-3.5">
            <div className="space-y-1.5">
              <Label className="text-xs">Device / Host Description</Label>
              <Input
                placeholder="e.g. Edge Jetson AGX Orin - North Entrance"
                value={keyName}
                onChange={(e) => setKeyName(e.target.value)}
                required
                className="h-8 text-xs"
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs">Allowed Camera Scopes (comma-separated, optional)</Label>
              <Input
                placeholder="e.g. CAM-01, CAM-02 (leave empty for unrestricted)"
                value={allowedCamerasStr}
                onChange={(e) => setAllowedCamerasStr(e.target.value)}
                className="h-8 text-xs font-mono"
              />
              <p className="text-[10px] text-muted-foreground">
                If provided, requests using this key will only be authorized to submit inferences and telemetry for these specific camera IDs.
              </p>
            </div>

            {keyError && (
              <div className="text-xs text-destructive bg-destructive/10 p-2 rounded border border-destructive/30">
                {keyError}
              </div>
            )}

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setShowAddKeyModal(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={createKeyMutation.isPending}
                className="gap-1.5"
              >
                {createKeyMutation.isPending ? 'Generating...' : 'Generate Secret'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
