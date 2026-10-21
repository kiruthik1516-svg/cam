import { authFetch, handleResponse, strOrEmpty, numOrZero, boolOrFalse } from './config'
import type {
  UserAccount,
  UserRole,
  SecurityAuditLog,
  DeviceApiKeyItem,
  DeviceApiKeyCreated,
  BiometricRetentionStatus,
  BiometricPurgeResult,
} from '../types'

// ==================== User Accounts (RBAC) ====================

export async function fetchUsers(): Promise<UserAccount[]> {
  const response = await authFetch('/api/users')
  const raw = await handleResponse<any>(response)
  try {
    const list = Array.isArray(raw) ? raw : []
    return list.map((item: any) => ({
      id: strOrEmpty(item.id),
      username: strOrEmpty(item.username),
      fullName: item.full_name || item.fullName || null,
      role: (item.role as UserRole) || 'viewer',
      isActive: boolOrFalse(item.is_active ?? item.isActive ?? true),
      createdAt: item.created_at || item.createdAt || null,
      lastLogin: item.last_login || item.lastLogin || null,
    }))
  } catch (e) {
    console.error('fetchUsers adapt failed:', e)
    return []
  }
}

export async function createUser(payload: {
  username: string
  password: string
  fullName?: string
  role?: UserRole
  isActive?: boolean
}): Promise<UserAccount> {
  const response = await authFetch('/api/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: payload.username.trim(),
      password: payload.password,
      full_name: payload.fullName?.trim() || null,
      role: payload.role || 'viewer',
      is_active: payload.isActive ?? true,
    }),
  })
  const raw = await handleResponse<any>(response)
  return {
    id: strOrEmpty(raw.id),
    username: strOrEmpty(raw.username),
    fullName: raw.full_name || raw.fullName || null,
    role: (raw.role as UserRole) || 'viewer',
    isActive: boolOrFalse(raw.is_active ?? raw.isActive ?? true),
    createdAt: raw.created_at || raw.createdAt || null,
    lastLogin: raw.last_login || raw.lastLogin || null,
  }
}

export async function updateUser(
  userId: string,
  payload: {
    fullName?: string
    password?: string
    role?: UserRole
    isActive?: boolean
  },
): Promise<UserAccount> {
  const body: Record<string, any> = {}
  if (payload.fullName !== undefined) body.full_name = payload.fullName.trim() || null
  if (payload.password) body.password = payload.password
  if (payload.role !== undefined) body.role = payload.role
  if (payload.isActive !== undefined) body.is_active = payload.isActive

  const response = await authFetch(`/api/users/${encodeURIComponent(userId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const raw = await handleResponse<any>(response)
  return {
    id: strOrEmpty(raw.id),
    username: strOrEmpty(raw.username),
    fullName: raw.full_name || raw.fullName || null,
    role: (raw.role as UserRole) || 'viewer',
    isActive: boolOrFalse(raw.is_active ?? raw.isActive ?? true),
    createdAt: raw.created_at || raw.createdAt || null,
    lastLogin: raw.last_login || raw.lastLogin || null,
  }
}

export async function deleteUser(userId: string): Promise<{ deleted: boolean; userId: string; username: string }> {
  const response = await authFetch(`/api/users/${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  })
  const raw = await handleResponse<any>(response)
  return {
    deleted: boolOrFalse(raw.deleted),
    userId: strOrEmpty(raw.user_id ?? raw.userId),
    username: strOrEmpty(raw.username),
  }
}

// ==================== Security Audit Ledger ====================

export async function fetchAuditLogs(params?: {
  limit?: number
  action?: string
  username?: string
  resourceType?: string
}): Promise<SecurityAuditLog[]> {
  const query = new URLSearchParams()
  if (params?.limit) query.set('limit', String(params.limit))
  if (params?.action) query.set('action', params.action)
  if (params?.username) query.set('username', params.username)
  if (params?.resourceType) query.set('resource_type', params.resourceType)

  const queryString = query.toString() ? `?${query.toString()}` : ''
  const response = await authFetch(`/api/audit-logs${queryString}`)
  const raw = await handleResponse<any>(response)
  try {
    const list = Array.isArray(raw) ? raw : []
    return list.map((item: any) => ({
      id: strOrEmpty(item.id),
      timestamp: strOrEmpty(item.timestamp),
      userId: item.user_id || item.userId || null,
      username: strOrEmpty(item.username),
      role: item.role || null,
      action: strOrEmpty(item.action),
      resourceType: item.resource_type || item.resourceType || null,
      resourceId: item.resource_id || item.resourceId || null,
      clientIp: item.client_ip || item.clientIp || null,
      details: item.details || null,
    }))
  } catch (e) {
    console.error('fetchAuditLogs adapt failed:', e)
    return []
  }
}

// ==================== Scoped Edge Device Keys ====================

export async function fetchDeviceApiKeys(): Promise<DeviceApiKeyItem[]> {
  const response = await authFetch('/api/edge-keys')
  const raw = await handleResponse<any>(response)
  try {
    const list = Array.isArray(raw) ? raw : []
    return list.map((item: any) => ({
      id: strOrEmpty(item.id),
      name: strOrEmpty(item.name),
      keyPrefix: strOrEmpty(item.key_prefix ?? item.keyPrefix),
      allowedCameras: item.allowed_cameras ?? item.allowedCameras ?? null,
      isActive: boolOrFalse(item.is_active ?? item.isActive ?? true),
      createdAt: item.created_at || item.createdAt || null,
      lastUsedAt: item.last_used_at || item.lastUsedAt || null,
    }))
  } catch (e) {
    console.error('fetchDeviceApiKeys adapt failed:', e)
    return []
  }
}

export async function createDeviceApiKey(payload: {
  name: string
  allowedCameras?: string[]
}): Promise<DeviceApiKeyCreated> {
  const response = await authFetch('/api/edge-keys', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: payload.name.trim(),
      allowed_cameras: payload.allowedCameras && payload.allowedCameras.length > 0 ? payload.allowedCameras : null,
    }),
  })
  const raw = await handleResponse<any>(response)
  return {
    id: strOrEmpty(raw.id),
    name: strOrEmpty(raw.name),
    key: strOrEmpty(raw.key),
    keyPrefix: strOrEmpty(raw.key_prefix ?? raw.keyPrefix),
    allowedCameras: raw.allowed_cameras ?? raw.allowedCameras ?? null,
    isActive: boolOrFalse(raw.is_active ?? raw.isActive ?? true),
    createdAt: raw.created_at || raw.createdAt || null,
  }
}

export async function revokeDeviceApiKey(keyId: string): Promise<{ revoked: boolean; keyId: string; name: string }> {
  const response = await authFetch(`/api/edge-keys/${encodeURIComponent(keyId)}`, {
    method: 'DELETE',
  })
  const raw = await handleResponse<any>(response)
  return {
    revoked: boolOrFalse(raw.revoked),
    keyId: strOrEmpty(raw.key_id ?? raw.keyId),
    name: strOrEmpty(raw.name),
  }
}

// ==================== Biometric Retention & Purge ====================

export async function fetchRetentionStatus(): Promise<BiometricRetentionStatus> {
  const response = await authFetch('/api/system/retention/status')
  const raw = await handleResponse<any>(response)
  return {
    retentionDays: numOrZero(raw.retention_days ?? raw.retentionDays),
    isEnabled: boolOrFalse(raw.is_enabled ?? raw.isEnabled),
    workerIntervalSeconds: numOrZero(raw.worker_interval_seconds ?? raw.workerIntervalSeconds),
    cutoffTimestamp: raw.cutoff_timestamp || raw.cutoffTimestamp || null,
    totalDetections: numOrZero(raw.total_detections ?? raw.totalDetections),
    detectionsWithFaceCrops: numOrZero(raw.detections_with_face_crops ?? raw.detectionsWithFaceCrops),
    faceCropsEligibleForPurge: numOrZero(raw.face_crops_eligible_for_purge ?? raw.faceCropsEligibleForPurge),
    preservedAlertFaceCrops: numOrZero(raw.preserved_alert_face_crops ?? raw.preservedAlertFaceCrops),
    enrolledProfilesProtected: numOrZero(raw.enrolled_profiles_protected ?? raw.enrolledProfilesProtected),
  }
}

export async function triggerRetentionPurge(payload?: {
  retentionDays?: number
  preserveFlaggedAlerts?: boolean
}): Promise<BiometricPurgeResult> {
  const body: Record<string, any> = {
    preserve_flagged_alerts: payload?.preserveFlaggedAlerts ?? true,
  }
  if (payload?.retentionDays !== undefined) {
    body.retention_days = payload.retentionDays
  }

  const response = await authFetch('/api/system/retention/purge', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const raw = await handleResponse<any>(response)
  return {
    purgedFaceCropsCount: numOrZero(raw.purged_face_crops_count ?? raw.purgedFaceCropsCount),
    retainedFaceCropsCount: numOrZero(raw.retained_face_crops_count ?? raw.retainedFaceCropsCount),
    purgedProvenanceCount: numOrZero(raw.purged_provenance_count ?? raw.purgedProvenanceCount),
    cutoffTimestamp: raw.cutoff_timestamp || raw.cutoffTimestamp || null,
    retentionDays: numOrZero(raw.retention_days ?? raw.retentionDays),
    preserveFlaggedAlerts: boolOrFalse(raw.preserve_flagged_alerts ?? raw.preserveFlaggedAlerts ?? true),
  }
}
