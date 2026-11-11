import { authFetch, handleResponse, apiUrl } from './config';

export interface OfficialReportItem {
  filename: string;
  stem: string;
  title: string;
  description: string;
  category: string;
  format: string;
  size_bytes: number;
  size_formatted: string;
  modified_at: string;
  download_url: string;
}

export interface AuditSummaryMetrics {
  facility: string;
  camera_id: string;
  monitoring_period: string;
  total_calendar_hours: number;
  total_recorded_hours: number;
  coverage_pct: number;
  total_raw_clips: number;
  total_timeline_gaps: number;
  total_blackout_hours: number;
  scheduled_reboot_count: number;
  scheduled_reboot_duration_min: number;
  total_incidents: number;
  switch_contact_events: number;
  real_personas_identified: number;
  duplicate_days_detected: string[];
  audit_status: string;
}

export async function fetchOfficialReports(format?: string): Promise<OfficialReportItem[]> {
  const qs = format ? `?format=${encodeURIComponent(format)}` : '';
  const res = await authFetch(`/api/reports${qs}`);
  return handleResponse<OfficialReportItem[]>(res);
}

export async function fetchAuditSummaryMetrics(): Promise<AuditSummaryMetrics> {
  const res = await authFetch('/api/reports/summary/metrics');
  return handleResponse<AuditSummaryMetrics>(res);
}

export function getReportDownloadUrl(filename: string): string {
  return apiUrl(`/api/reports/${encodeURIComponent(filename)}/download`);
}
