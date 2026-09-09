// ─────────────────────────────────────────────────────────────
// Service Audit — journal d'audit (lecture seule, ROOT requis)
// ─────────────────────────────────────────────────────────────

import { api } from '../lib/api';
import type { AuditAction, AuditLogOut } from '../types/api';

export interface AuditLogFilters {
  actorId?: string;
  action?: AuditAction;
  entityType?: string;
  skip?: number;
  limit?: number;
}

export async function fetchAuditLogs(filters: AuditLogFilters = {}): Promise<AuditLogOut[]> {
  const params = new URLSearchParams();
  if (filters.actorId) params.set('actor_id', filters.actorId);
  if (filters.action) params.set('action', filters.action);
  if (filters.entityType) params.set('entity_type', filters.entityType);
  params.set('skip', String(filters.skip ?? 0));
  params.set('limit', String(filters.limit ?? 200));
  const data = await api.get<AuditLogOut[]>(`/audit/logs?${params.toString()}`);
  return data ?? [];
}