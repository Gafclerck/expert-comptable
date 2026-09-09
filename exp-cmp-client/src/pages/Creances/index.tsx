import { useState } from 'react';
import { formatCFA } from '@/utils/format';
import { fetchCreances } from '@/services/mock';
import { useApiQuery } from '@/hooks/useApiQuery';
import type { Creance } from '@/types';
import Badge from '@/components/ui/Badge';
import Modal from '@/components/ui/Modal';

const categoryLabel: Record<Creance['category'], string> = {
  client_assurance: 'Client Assurance',
  client_poulets: 'Client Poulets',
  pret_familial: 'Prêt familial',
  fournisseur: 'Fournisseur',
  avance: 'Avance',
  autre: 'Autre',
};

const statusConfig: Record<Creance['status'], { label: string; variant: 'success' | 'warning' | 'danger' | 'neutral' | 'partial' | 'info' }> = {
  pending: { label: 'En attente', variant: 'neutral' },
  partial: { label: 'Partiel', variant: 'partial' },
  overdue: { label: 'En retard', variant: 'danger' },
  paid: { label: 'Soldé', variant: 'success' },
};

export default function Creances() {
  const { data: rawCreances, loading } = useApiQuery(fetchCreances, []);
  const creances: Creance[] = rawCreances ?? [];

  const [selected, setSelected] = useState<Creance | null>(null);
  const [filter, setFilter] = useState<'all' | Creance['status']>('all');

  const filtered = creances.filter(c => filter === 'all' || c.status === filter);
  const totalReceivable = creances.filter(c => c.status !== 'paid').reduce((s, c) => {
    const paid = c.payments.reduce((sp, p) => sp + p.amount, 0);
    return s + (c.initialAmount - paid);
  }, 0);
  const overdueTotal = creances.filter(c => c.status === 'overdue').reduce((s, c) => {
    const paid = c.payments.reduce((sp, p) => sp + p.amount, 0);
    return s + (c.initialAmount - paid);
  }, 0);

  return (
    <div className="p-6 max-w-screen-xl mx-auto space-y-6">

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 p-4">
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <div className="section-eyebrow p-2">Total à recevoir</div>
          {loading ? (
            <div className="h-6 w-32 bg-slate-100 rounded animate-pulse" />
          ) : (
            <div className="font-financial text-xl font-semibold text-amber-600">{formatCFA(totalReceivable)}</div>
          )}
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <div className="section-eyebrow p-2">En retard</div>
          {loading ? (
            <div className="h-6 w-32 bg-slate-100 rounded animate-pulse" />
          ) : (
            <div className="font-financial text-xl font-semibold text-red-600">{formatCFA(overdueTotal)}</div>
          )}
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <div className="section-eyebrow p-2">Créances actives</div>
          {loading ? (
            <div className="h-6 w-12 bg-slate-100 rounded animate-pulse" />
          ) : (
            <div className="font-financial text-xl font-semibold text-slate-800">{creances.filter(c => c.status !== 'paid').length}</div>
          )}
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <div className="section-eyebrow p-2">Soldées</div>
          {loading ? (
            <div className="h-6 w-12 bg-slate-100 rounded animate-pulse" />
          ) : (
            <div className="font-financial text-xl font-semibold text-emerald-600">{creances.filter(c => c.status === 'paid').length}</div>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        {(['all', 'overdue', 'partial', 'pending', 'paid'] as const).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`p-4 py-1 rounded-full text-xs font-medium border transition-all ${
              filter === f
                ? 'bg-navy-800 text-white border-navy-800'
                : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
            }`}
          >
            {f === 'all' ? 'Toutes' : statusConfig[f].label}
          </button>
        ))}
      </div>

      {/* List */}
      {loading ? (
        <div className="p-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-32 bg-slate-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-slate-400 text-sm">Aucune créance trouvée</div>
      ) : (
        <div className="p-4">
          {filtered.map(creance => {
            const paid = creance.payments.reduce((s, p) => s + p.amount, 0);
            const reste = creance.initialAmount - paid;
            const pct = creance.initialAmount > 0 ? (paid / creance.initialAmount) * 100 : 0;

            return (
              <button
                key={creance.id}
                onClick={() => setSelected(creance)}
                className="w-full text-left bg-white rounded-xl border border-slate-200 p-6 hover:border-slate-300 hover:shadow-sm transition-all group"
              >
                <div className="flex items-start justify-between p-4">
                  <div>
                    <div className="font-semibold text-slate-800">{creance.person}</div>
                    <div className="text-xs text-slate-500 mt-1 flex items-center gap-2">
                      <span>{categoryLabel[creance.category]}</span>
                      <span>·</span>
                      <span className="capitalize">{creance.sourceActivity}</span>
                      {creance.phone && <><span>·</span><span>{creance.phone}</span></>}
                    </div>
                  </div>
                  <Badge variant={statusConfig[creance.status].variant}>{statusConfig[creance.status].label}</Badge>
                </div>

                <div className="grid grid-cols-4 gap-4 p-4">
                  <div>
                    <div className="text-xs text-slate-400 mt-1">Montant initial</div>
                    <div className="font-financial text-sm font-semibold text-slate-700">{formatCFA(creance.initialAmount)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-400 mt-1">Payé</div>
                    <div className="font-financial text-sm font-semibold text-emerald-600">{formatCFA(paid)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-400 mt-1">Reste</div>
                    <div className={`font-financial text-sm font-semibold ${reste > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>{formatCFA(reste)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-400 mt-1">Échéance</div>
                    <div className={`text-xs font-medium ${creance.status === 'overdue' ? 'text-red-600' : 'text-slate-600'}`}>{creance.dueDate}</div>
                  </div>
                </div>

                {creance.initialAmount > 0 && (
                  <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        pct >= 100 ? 'bg-emerald-500' : pct > 0 ? 'bg-amber-400' : 'bg-slate-100'
                      }`}
                      style={{ width: `${Math.min(100, pct)}%` }}
                    />
                  </div>
                )}

                {creance.description && (
                  <div className="text-xs text-slate-500 mt-2">{creance.description}</div>
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* Detail modal */}
      <Modal open={!!selected} onClose={() => setSelected(null)} title={selected?.person ?? ''} width="md">
        {selected && (() => {
          const paid = selected.payments.reduce((s, p) => s + p.amount, 0);
          const reste = selected.initialAmount - paid;
          return (
            <div className="p-6">
              <div className="grid grid-cols-2 gap-4">
                <div><div className="text-xs text-slate-500 mt-1">Catégorie</div><div className="text-slate-800">{categoryLabel[selected.category]}</div></div>
                <div><div className="text-xs text-slate-500 mt-1">Activité source</div><div className="text-slate-800 capitalize">{selected.sourceActivity}</div></div>
                <div><div className="text-xs text-slate-500 mt-1">Échéance</div><div className={`font-medium ${selected.status === 'overdue' ? 'text-red-600' : 'text-slate-800'}`}>{selected.dueDate}</div></div>
                {selected.promiseDate && <div><div className="text-xs text-slate-500 mt-1">Promesse</div><div className="text-amber-600 font-medium">{selected.promiseDate}</div></div>}
                {selected.phone && <div><div className="text-xs text-slate-500 mt-1">Téléphone</div><div className="text-slate-800">{selected.phone}</div></div>}
              </div>

              <div className="bg-slate-50 rounded-lg p-4">
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Initial</div>
                    <div className="font-financial text-lg font-bold text-slate-800">{formatCFA(selected.initialAmount)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Payé</div>
                    <div className="font-financial text-lg font-bold text-emerald-600">{formatCFA(paid)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Reste</div>
                    <div className={`font-financial text-lg font-bold ${reste > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>{formatCFA(reste)}</div>
                  </div>
                </div>
                <div className="p-4 h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 rounded-full"
                    style={{ width: `${selected.initialAmount > 0 ? Math.min(100, (paid / selected.initialAmount) * 100) : 0}%` }}
                  />
                </div>
              </div>

              {selected.description && (
                <div className="text-sm text-slate-600 bg-slate-50 rounded p-4">{selected.description}</div>
              )}

              <div>
                <div className="text-sm font-semibold text-slate-700 p-4">Historique des paiements</div>
                {selected.payments.length === 0 ? (
                  <div className="text-sm text-slate-400 text-center py-4">Aucun paiement enregistré</div>
                ) : (
                  <div className="space-y-2">
                    {selected.payments.map(p => (
                      <div key={p.id} className="flex justify-between items-center py-2 border-b border-slate-100">
                        <div>
                          <div className="text-sm text-slate-700">{p.date}</div>
                          {p.note && <div className="text-xs text-slate-400">{p.note}</div>}
                        </div>
                        <div className="font-financial font-semibold text-emerald-600">{formatCFA(p.amount)}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })()}
      </Modal>
    </div>
  );
}
