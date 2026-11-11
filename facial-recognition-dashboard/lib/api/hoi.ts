import { authFetch, handleResponse, apiUrl } from './config';
import type { HoiIncidentItem } from '@/lib/types';

export async function fetchHoiIncidents(params?: {
  day?: number;
  severity?: string;
  zone?: string;
}): Promise<HoiIncidentItem[]> {
  const query = new URLSearchParams();
  if (params?.day !== undefined && params.day !== null) {
    query.append('day', params.day.toString());
  }
  if (params?.severity) {
    query.append('severity', params.severity);
  }
  if (params?.zone) {
    query.append('zone', params.zone);
  }

  const qs = query.toString() ? `?${query.toString()}` : '';
  const res = await authFetch(`/api/hoi/evidence/incidents${qs}`);
  return handleResponse<HoiIncidentItem[]>(res);
}

export async function fetchHoiDaySummary(day: number): Promise<Record<string, any>> {
  const res = await authFetch(`/api/hoi/evidence/summary/${day}`);
  return handleResponse<Record<string, any>>(res);
}

export function getHoiVideoUrl(day: number, clipFilename: string): string {
  return apiUrl(`/api/hoi/evidence/video/${day}/${encodeURIComponent(clipFilename)}`);
}

export function getHoiSnapshotUrl(day: number, snapshotFilename: string): string {
  return apiUrl(`/api/hoi/evidence/snapshot/${day}/${encodeURIComponent(snapshotFilename)}`);
}

