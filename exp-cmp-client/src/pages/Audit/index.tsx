import { useState, useMemo } from 'react';
import { fetchAuditLogs } from '@/services';
import { useApiQuery } from '@/hooks/useApiQuery';
import type { AuditLogOut } from '@/types/api';

const actionLabels: Record<string, string> = {
  CREATE: 'Création',
  UPDATE: 'Modification',
  CONFIRM: 'Confirmation',
  REJECT: 'Rejet',
  DISPUTE: 'Litige',
  RESOLVE: 'Résolution',
  REPAY: 'Remboursement',
  RETURN: 'Retour',
  TRANSFER: 'Virement',
  CORRECT: 'Correction',
};

const actionColors: Record<string, string> = {
  CREATE: 'bg-[var(--color-surface-elevated)] text-[var(--color-primary)]',
  UPDATE: 'bg-slate-100 text-slate-600',
  CONFIRM: 'bg-emerald-100 text-emerald-700',
  REJECT: 'bg-red-100 text-red-700',
  DISPUTE: 'bg-red-100 text-red-700',
  RESOLVE: 'bg-emerald-100 text-emerald-700',
  REPAY: 'bg-[var(--color-surface-elevated)] text-[var(--color-secondary)]',
  RETURN: 'bg-amber-100 text-amber-700',
  TRANSFER: 'bg-navy-100 text-navy-700',
  CORRECT: 'bg-amber-100 text-amber-700',
};

function summarize(values: Record<string, unknown> | null | undefined): string {
  if (!values) return '';
  return Object.entries(values)
    .map(([k, v]) => `${k}: ${typeof v === 'string' ? v : JSON.stringify(v)}`)
    .join(', ');
}

export default function Audit() {
  const [search, setSearch] = useState('');
  const [filterUser, setFilterUser] = useState<string>('all');

  const { data: auditLogs, loading } = useApiQuery<AuditLogOut[]>(() => fetchAuditLogs(), []);

  const users = useMemo(
    () => Array.from(new Set((auditLogs ?? []).map(l => l.actor_id?.slice(0, 8) ?? '—'))),
    [auditLogs]
  );

  const filtered = useMemo(() => {
    const logs = auditLogs ?? [];
    return logs.filter(log => {
      const actor = log.actor_id?.slice(0, 8) ?? '—';
      const matchUser = filterUser === 'all' || actor === filterUser;
      const line = [
        log.action, log.entity_type, log.entity_id ?? '',
        log.reason ?? '', summarize(log.old_values), summarize(log.new_values),
      ].join(' ');
      const matchSearch = !search || line.toLowerCase().includes(search.toLowerCase());
      return matchUser && matchSearch;
    });
  }, [auditLogs, filterUser, search]);

  if (loading) return <div className="p-6 text-center text-slate-400 text-sm">Chargement…</div>;

  return (
    <div className="p-6 max-w-screen-xl mx-auto">

      <div className="bg-[var(--color-surface-elevated)] border border-[var(--color-border)] rounded-lg p-4 text-sm text-[var(--color-primary)]">
        <strong>Journal d'audit :</strong> toutes les actions importantes sont enregistrées ici et ne peuvent pas être supprimées silencieusement.
      </div>

      <div className="flex items-center p-4 flex-wrap">
        <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-full p-2 flex-1 min-w-[200px]">
          <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" className="text-slate-400 shrink-0">
            <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
          </svg>
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Rechercher une action, entité, note…"
            className="bg-transparent text-sm text-slate-700 placeholder-slate-400 outline-none flex-1"
          />
        </div>
        <select
          value={filterUser}
          onChange={e => setFilterUser(e.target.value)}
          className="bg-white border border-slate-200 rounded-full p-2 text-sm text-slate-700 outline-none focus:border-[var(--color-primary)]"
        >
          <option value="all">Tous les acteurs</option>
          {users.map(u => <option key={u} value={u}>{u}</option>)}
        </select>
      </div>

      <div className="text-xs text-slate-500">
        {filtered.length} entrée(s) — {(auditLogs ?? []).length} au total
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="text-left p-4 text-xs font-semibold text-slate-500 uppercase tracking-wide whitespace-nowrap">Date</th>
                <th className="text-left p-4 text-xs font-semibold text-slate-500 uppercase tracking-wide whitespace-nowrap">Acteur</th>
                <th className="text-left p-4 text-xs font-semibold text-slate-500 uppercase tracking-wide whitespace-nowrap">Action</th>
                <th className="text-left p-4 text-xs font-semibold text-slate-500 uppercase tracking-wide whitespace-nowrap">Entité</th>
                <th className="text-left p-4 text-xs font-semibold text-slate-500 uppercase tracking-wide">Anciennes valeurs</th>
                <th className="text-left p-4 text-xs font-semibold text-slate-500 uppercase tracking-wide">Nouvelles valeurs</th>
                <th className="text-left p-4 text-xs font-semibold text-slate-500 uppercase tracking-wide">Motif</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map(log => (
                <tr key={log.id} className="hover:bg-slate-50 transition-colors">
                  <td className="p-4 whitespace-nowrap text-xs font-mono text-slate-700">
                    {new Date(log.created_at).toLocaleString('fr-FR')}
                  </td>
                  <td className="p-4 whitespace-nowrap text-xs text-slate-700 font-mono">
                    {log.actor_id?.slice(0, 8) ?? '—'}
                  </td>
                  <td className="p-4 whitespace-nowrap">
                    <span className={`inline-block text-xs font-semibold rounded-full px-2 mt-1 ${
                      actionColors[log.action] ?? 'bg-slate-100 text-slate-600'
                    }`}>
                      {actionLabels[log.action] ?? log.action}
                    </span>
                  </td>
                  <td className="p-4 whitespace-nowrap">
                    <div className="text-xs text-slate-600">{log.entity_type}</div>
                    <div className="text-xs font-mono text-slate-400">{log.entity_id?.slice(0, 8) ?? '—'}</div>
                  </td>
                  <td className="p-4 text-xs text-slate-500">{summarize(log.old_values) || '—'}</td>
                  <td className="p-4 text-xs text-slate-700">{summarize(log.new_values) || '—'}</td>
                  <td className="p-4 text-xs text-slate-500 italic">{log.reason ?? '—'}</td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 p-12 text-center text-sm text-slate-400">
                    Aucune entrée ne correspond à la recherche
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}