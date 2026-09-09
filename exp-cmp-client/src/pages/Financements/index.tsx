import { useState } from 'react';
import { formatCFA } from '@/utils/format';
import { fetchInternalFundings } from '@/services/mock';
import { useApiQuery } from '@/hooks/useApiQuery';
import type { InternalFunding } from '@/types';
import Badge from '@/components/ui/Badge';
import Modal from '@/components/ui/Modal';

const activityColors: Record<string, string> = {
  assurance: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  poulets: 'bg-amber-100 text-amber-700 border-amber-200',
  vtc: 'bg-navy-100 text-navy-700 border-navy-200',
};

const statusConfig: Record<InternalFunding['status'], { label: string; variant: 'success' | 'warning' | 'neutral' }> = {
  active: { label: 'En cours', variant: 'warning' },
  partial: { label: 'Partiellement remboursé', variant: 'warning' },
  completed: { label: 'Remboursé', variant: 'success' },
};

export default function Financements() {
  const { data: rawFundings, loading } = useApiQuery(fetchInternalFundings, []);
  const internalFundings: InternalFunding[] = rawFundings ?? [];

  const [selected, setSelected] = useState<InternalFunding | null>(null);

  const active = internalFundings.filter(f => f.status !== 'completed');
  const totalOutstanding = active.reduce((s, f) => s + (f.initialAmount - f.repaid), 0);

  // Flux dynamique calculé depuis les données du backend
  const activityFlows = internalFundings
    .filter(f => f.status !== 'completed')
    .reduce<Record<string, { preted: number; emprunte: number }>>((acc, f) => {
      if (!acc[f.lenderActivity]) acc[f.lenderActivity] = { preted: 0, emprunte: 0 };
      if (!acc[f.borrowerActivity]) acc[f.borrowerActivity] = { preted: 0, emprunte: 0 };
      const remaining = f.initialAmount - f.repaid;
      acc[f.lenderActivity].preted += remaining;
      acc[f.borrowerActivity].emprunte += remaining;
      return acc;
    }, {});

  const allActivities = ['assurance', 'poulets', 'vtc'];

  return (
    <div className="p-6 max-w-screen-xl mx-auto space-y-6">

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 p-4">
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide p-2">Financements actifs</div>
          {loading ? (
            <div className="h-6 w-12 bg-slate-100 rounded animate-pulse" />
          ) : (
            <div className="font-financial text-xl font-semibold text-slate-800">{active.length}</div>
          )}
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide p-2">Montant non remboursé</div>
          {loading ? (
            <div className="h-6 w-32 bg-slate-100 rounded animate-pulse" />
          ) : (
            <div className="font-financial text-xl font-semibold text-amber-600">{formatCFA(totalOutstanding)}</div>
          )}
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide p-2">Remboursés</div>
          {loading ? (
            <div className="h-6 w-12 bg-slate-100 rounded animate-pulse" />
          ) : (
            <div className="font-financial text-xl font-semibold text-emerald-600">{internalFundings.filter(f => f.status === 'completed').length}</div>
          )}
        </div>
      </div>

      {/* Important note */}
      <div className="bg-navy-50 border border-navy-200 rounded-lg p-4 text-sm text-navy-800">
        <strong>Note :</strong> Un financement interne n&apos;est ni un chiffre d&apos;affaires ni un bénéfice. Il représente un transfert temporaire de trésorerie entre activités, avec obligation de remboursement.
      </div>

      {/* Flow visualization */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <div className="text-sm font-semibold text-slate-700 mb-4">Flux en cours entre activités</div>
        <div className="flex items-center justify-around">
          {allActivities.map(actId => {
            const flow = activityFlows[actId] ?? { preted: 0, emprunte: 0 };
            return (
              <div key={actId} className="text-center">
                <div className={`inline-flex items-center border rounded-lg p-4 ${activityColors[actId] ?? 'bg-slate-100 text-slate-700 border-slate-200'}`}>
                  <span className="text-sm font-semibold capitalize">{actId}</span>
                </div>
                <div className="mt-2 space-y-1">
                  {flow.preted > 0 && (
                    <div className="text-xs text-slate-600">
                      Prêté : <span className="font-financial font-medium text-emerald-600">{formatCFA(flow.preted)}</span>
                    </div>
                  )}
                  {flow.emprunte > 0 && (
                    <div className="text-xs text-slate-600">
                      Emprunté : <span className="font-financial font-medium text-amber-600">{formatCFA(flow.emprunte)}</span>
                    </div>
                  )}
                  {flow.preted === 0 && flow.emprunte === 0 && (
                    <div className="text-xs text-slate-400">Aucun flux actif</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Fundings list */}
      {loading ? (
        <div className="p-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-32 bg-slate-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : internalFundings.length === 0 ? (
        <div className="text-center py-12 text-slate-400 text-sm">Aucun financement trouvé</div>
      ) : (
        <div className="p-4">
          {internalFundings.map(funding => {
            const reste = funding.initialAmount - funding.repaid;
            const pct = funding.initialAmount > 0 ? (funding.repaid / funding.initialAmount) * 100 : 0;
            return (
              <button
                key={funding.id}
                onClick={() => setSelected(funding)}
                className="w-full text-left bg-white rounded-xl border border-slate-200 p-6 hover:border-slate-300 hover:shadow-sm transition-all"
              >
                <div className="flex items-start justify-between p-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs font-semibold border rounded px-2 mt-1 ${activityColors[funding.lenderActivity] ?? 'bg-slate-100 text-slate-700 border-slate-200'}`}>
                        {funding.lenderActivity.charAt(0).toUpperCase() + funding.lenderActivity.slice(1)}
                      </span>
                      <span className="text-slate-400 text-sm">→</span>
                      <span className={`text-xs font-semibold border rounded px-2 mt-1 ${activityColors[funding.borrowerActivity] ?? 'bg-slate-100 text-slate-700 border-slate-200'}`}>
                        {funding.borrowerActivity.charAt(0).toUpperCase() + funding.borrowerActivity.slice(1)}
                      </span>
                    </div>
                    <div className="text-sm text-slate-600">{funding.purpose}</div>
                    <div className="text-xs text-slate-400 mt-1">{funding.date}{funding.relatedLotId ? ` · Lot ${funding.relatedLotId}` : ''}</div>
                  </div>
                  <Badge variant={statusConfig[funding.status].variant}>{statusConfig[funding.status].label}</Badge>
                </div>

                <div className="grid grid-cols-3 gap-4 p-4">
                  <div>
                    <div className="text-xs text-slate-400 mt-1">Montant initial</div>
                    <div className="font-financial text-sm font-semibold text-slate-800">{formatCFA(funding.initialAmount)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-400 mt-1">Remboursé</div>
                    <div className="font-financial text-sm font-semibold text-emerald-600">{formatCFA(funding.repaid)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-400 mt-1">Reste dû</div>
                    <div className={`font-financial text-sm font-semibold ${reste > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>{formatCFA(reste)}</div>
                  </div>
                </div>

                <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${pct >= 100 ? 'bg-emerald-500' : 'bg-amber-400'}`}
                    style={{ width: `${Math.min(100, pct)}%` }}
                  />
                </div>
              </button>
            );
          })}
        </div>
      )}

      <Modal open={!!selected} onClose={() => setSelected(null)} title="Détail du financement" width="md">
        {selected && (() => {
          const reste = selected.initialAmount - selected.repaid;
          return (
            <div className="p-6">
              <div className="flex items-center p-4">
                <span className={`text-sm font-semibold border rounded-lg p-2 ${activityColors[selected.lenderActivity] ?? 'bg-slate-100 text-slate-700 border-slate-200'}`}>
                  {selected.lenderActivity.charAt(0).toUpperCase() + selected.lenderActivity.slice(1)}
                </span>
                <span className="text-slate-600 font-medium">prête à</span>
                <span className={`text-sm font-semibold border rounded-lg p-2 ${activityColors[selected.borrowerActivity] ?? 'bg-slate-100 text-slate-700 border-slate-200'}`}>
                  {selected.borrowerActivity.charAt(0).toUpperCase() + selected.borrowerActivity.slice(1)}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div><div className="text-xs text-slate-500 mt-1">Date</div><div className="text-slate-800">{selected.date}</div></div>
                <div><div className="text-xs text-slate-500 mt-1">Statut</div><Badge variant={statusConfig[selected.status].variant}>{statusConfig[selected.status].label}</Badge></div>
                <div className="col-span-2"><div className="text-xs text-slate-500 mt-1">Objet</div><div className="text-slate-800">{selected.purpose}</div></div>
                {selected.relatedLotId && <div><div className="text-xs text-slate-500 mt-1">Lot concerné</div><div className="font-mono text-slate-800">{selected.relatedLotId}</div></div>}
              </div>

              <div className="bg-slate-50 rounded-lg p-4">
                <div className="grid grid-cols-3 gap-4 text-center p-4">
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Montant avancé</div>
                    <div className="font-financial text-xl font-bold text-navy-800">{formatCFA(selected.initialAmount)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Remboursé</div>
                    <div className="font-financial text-xl font-bold text-emerald-600">{formatCFA(selected.repaid)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Reste dû</div>
                    <div className={`font-financial text-xl font-bold ${reste > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>{formatCFA(reste)}</div>
                  </div>
                </div>
                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${selected.repaid >= selected.initialAmount ? 'bg-emerald-500' : 'bg-amber-400'}`}
                    style={{ width: `${selected.initialAmount > 0 ? Math.min(100, (selected.repaid / selected.initialAmount) * 100) : 0}%` }}
                  />
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  {selected.initialAmount > 0 ? Math.round((selected.repaid / selected.initialAmount) * 100) : 0}% remboursé
                </div>
              </div>

              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-xs text-amber-800">
                <strong>Rappel :</strong> Ce financement n&apos;impacte pas le chiffre d&apos;affaires ni le résultat de l&apos;activité prêteuse. Il représente uniquement un mouvement de trésorerie avec créance de remboursement.
              </div>
            </div>
          );
        })()}
      </Modal>
    </div>
  );
}
