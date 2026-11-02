import { authFetch, handleResponse } from './config';
import type { PipelineJob, PipelineJobStats } from '@/lib/types';

export async function submitPipelineJob(payload: {
  task_type: string;
  title?: string;
  day?: number;
  skip_completed?: boolean;
  workers?: number;
  params?: Record<string, any>;
}): Promise<PipelineJob> {
  const res = await authFetch('/api/pipeline/jobs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<PipelineJob>(res);
}

export async function fetchPipelineJobs(params?: {
  status?: string;
  limit?: number;
}): Promise<PipelineJob[]> {
  const query = new URLSearchParams();
  if (params?.status) query.append('status', params.status);
  if (params?.limit) query.append('limit', params.limit.toString());

  const qs = query.toString() ? `?${query.toString()}` : '';
  const res = await authFetch(`/api/pipeline/jobs${qs}`);
  return handleResponse<PipelineJob[]>(res);
}

export async function fetchPipelineJob(taskId: string): Promise<PipelineJob> {
  const res = await authFetch(`/api/pipeline/jobs/${encodeURIComponent(taskId)}`);
  return handleResponse<PipelineJob>(res);
}

export async function fetchPipelineJobStats(): Promise<PipelineJobStats> {
  const res = await authFetch('/api/pipeline/jobs/stats');
  return handleResponse<PipelineJobStats>(res);
}

export async function cancelPipelineJob(taskId: string): Promise<{ status: string; task_id: string }> {
  const res = await authFetch(`/api/pipeline/jobs/${encodeURIComponent(taskId)}/cancel`, {
    method: 'POST',
  });
  return handleResponse<{ status: string; task_id: string }>(res);
}

export async function clearFinishedPipelineJobs(): Promise<{ status: string; count: number }> {
  const res = await authFetch('/api/pipeline/jobs/clear-finished', {
    method: 'POST',
  });
  return handleResponse<{ status: string; count: number }>(res);
}
