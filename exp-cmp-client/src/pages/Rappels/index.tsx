import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchAlerts, resolveAlert, subscribeToAlerts } from '@/services/mock';
import { useApiQuery } from '@/hooks/useApiQuery';
import type { Alert, AlertLevel } from '@/types';

const levelConfig: Record<AlertLevel, { label: string; color: string; bgColor: string; borderColor: string; dotColor: string }> = {
  urgent: { label: 'Urgent', color: 'text-red-700', bgColor: 'bg-red-50', borderColor: 'border-red-200', dotColor: 'bg-red-500' },
  today: { label: "Aujourd'hui", color: 'text-amber-700', bgColor: 'bg-amber-50', borderColor: 'border-amber-200', dotColor: 'bg-amber-500' },
  upcoming: { label: 'À venir', color: 'text-navy-700', bgColor: 'bg-navy-50', borderColor: 'border-navy-200', dotColor: 'bg-navy-400' },
  resolved: { label: 'Résolu', color: 'text-slate-600', bgColor: 'bg-slate-50', borderColor: 'border-slate-200', dotColor: 'bg-slate-400' },
};

export default function Rappels() {
  const [filter, setFilter] = useState<'all' | AlertLevel>('all');
  const [resolving, setResolving] = useState<string | null>(null);
  const navigate = useNavigate();

  const { data: rawAlerts, loading, refetch } = useApiQuery(fetchAlerts, []);

  useEffect(() => {
    const channel = subscribeToAlerts(refetch);
    return () => { channel.unsubscribe(); };
  }, [refetch]);

  const allAlerts: Alert[] = loading ? [] : (rawAlerts ?? []);

  const filtered = allAlerts.filter(a => filter === 'all' || a.level === filter);
  const byLevel = (level: AlertLevel) => allAlerts.filter(a => a.level === level && !a.resolved);

  const resolve = async (id: string) => {
    setResolving(id);
    try {
      await resolveAlert(id);
      refetch();
    } finally {
      setResolving(null);
    }
  };

  return (
    <div className="p-6 max-w-screen-xl mx-auto space-y-6">

      {/* Summary */}
      <div className="grid grid-cols-4 p-4">
        {(['urgent', 'today', 'upcoming', 'resolved'] as const).map(level => {
          const count = level === 'resolved'
            ? allAlerts.filter(a => a.resolved).length
            : byLevel(level).length;
          const cfg = levelConfig[level];
          return (
            <button
              key={level}
              onClick={() => setFilter(filter === level ? 'all' : level)}
              className={`p-4 rounded-xl border text-left transition-all ${
                filter === level ? `${cfg.bgColor} ${cfg.borderColor}` : 'bg-white border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className="flex items-center p-2 mb-2">
                <span className={`w-2 h-2 rounded-full ${cfg.dotColor}`} />
                <span className={`text-xs font-semibold ${cfg.color}`}>{cfg.label}</span>
              </div>
              <div className="font-financial text-2xl font-bold text-slate-800">
                {loading ? <span className="block w-6 h-6 rounded bg-slate-100 animate-pulse" /> : count}
              </div>
            </button>
          );
        })}
      </div>

      {/* Alerts list */}
      <div className="p-4">
        {loading && (
          <div className="text-center py-8 text-slate-400 text-sm">
            <div className="w-5 h-5 border-2 border-slate-200 border-t-navy-500 rounded-full animate-spin mx-auto mb-2" />
            Chargement des rappels…
          </div>
        )}

        {!loading && (['urgent', 'today', 'upcoming', 'resolved'] as const).map(level => {
          const items = filtered.filter(a => a.level === level);
          if (!items.length) return null;
          const cfg = levelConfig[level];
          return (
            <div key={level}>
              <div className="flex items-center gap-2 px-1 mb-2">
                <span className={`w-1.5 h-1.5 rounded-full ${cfg.dotColor}`} />
                <span className={`text-xs font-semibold uppercase tracking-wider ${cfg.color}`}>{cfg.label}</span>
                <span className="text-xs text-slate-400">({items.length})</span>
              </div>

              <div className="space-y-2">
                {items.map((alert: Alert) => (
                  <div
                    key={alert.id}
                    className={`rounded-xl border p-4 ${cfg.bgColor} ${cfg.borderColor} transition-all`}
                  >
                    <div className="flex items-start justify-between p-4">
                      <div className="flex-1">
                        <div className={`font-semibold text-sm ${cfg.color}`}>{alert.title}</div>
                        <div className={`text-xs mt-1 leading-relaxed ${alert.level === 'urgent' ? 'text-red-600' : alert.level === 'today' ? 'text-amber-600' : 'text-slate-600'}`}>
                          {alert.description}
                        </div>
                        <div className="flex items-center p-4 mt-2">
                          {alert.activity && (
                            <span className="text-xs text-slate-400 capitalize">{alert.activity}</span>
                          )}
                          <span className="text-xs text-slate-400">{alert.date}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        {alert.actionLabel && alert.actionPage && !alert.resolved && (
                          <button
                            onClick={() => navigate(alert.actionPage as string)}
                            className={`text-xs font-medium p-2 rounded border transition-colors ${
                              alert.level === 'urgent'
                                ? 'border-red-300 text-red-700 hover:bg-red-100'
                                : alert.level === 'today'
                                ? 'border-amber-300 text-amber-700 hover:bg-amber-100'
                                : 'border-navy-200 text-navy-700 hover:bg-navy-100'
                            }`}
                          >
                            {alert.actionLabel}
                          </button>
                        )}
                        {!alert.resolved && (
                          <button
                            onClick={() => resolve(alert.id)}
                            disabled={resolving === alert.id}
                            className="text-xs text-slate-400 hover:text-emerald-600 border border-slate-200 hover:border-emerald-200 rounded p-2 transition-colors disabled:opacity-50"
                          >
                            {resolving === alert.id ? '…' : 'Résoudre'}
                          </button>
                        )}
                        {alert.resolved && (
                          <span className="text-xs text-slate-400">✓ Résolu</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}

        {!loading && filtered.length === 0 && (
          <div className="text-center p-12 text-slate-400">
            <div className="text-3xl p-4">✓</div>
            <div className="text-sm font-medium">Aucune alerte dans cette catégorie</div>
          </div>
        )}
      </div>
    </div>
  );
}
