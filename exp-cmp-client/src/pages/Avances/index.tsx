import { useState } from 'react';
import { formatCFA } from '@/utils/format';
import { fetchPersonalAdvances } from '@/services/mock';
import { useApiQuery } from '@/hooks/useApiQuery';
import type { PersonalAdvance, AdvanceStatus, EvidenceStatus } from '@/types';
import Badge from '@/components/ui/Badge';
import Modal from '@/components/ui/Modal';

const statusConfig: Record<AdvanceStatus, { label: string; variant: 'warning' | 'success' | 'danger' | 'neutral' }> = {
  pending_confirmation: { label: 'En attente de confirmation', variant: 'warning' },
  confirmed: { label: 'Confirmée', variant: 'success' },
  disputed: { label: 'Litige', variant: 'danger' },
  closed: { label: 'Clôturée', variant: 'neutral' },
};

const evidenceConfig: Record<EvidenceStatus, { label: string; icon: string; color: string }> = {
  none: { label: 'Sans justificatif', icon: '○', color: 'text-slate-400' },
  provided: { label: 'Justificatif fourni', icon: '◎', color: 'text-amber-500' },
  to_check: { label: 'À vérifier', icon: '◑', color: 'text-amber-600' },
  verified: { label: 'Vérifié', icon: '●', color: 'text-emerald-600' },
  rejected: { label: 'Rejeté', icon: '✕', color: 'text-red-500' },
};

const activityColors: Record<string, string> = {
  assurance: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  poulets: 'bg-amber-100 text-amber-700 border-amber-200',
  vtc: 'bg-[var(--color-surface-elevated)] text-[var(--color-secondary)] border-[var(--color-text-secondary)]',
};

function ValidationLevel({ advance }: { advance: PersonalAdvance }) {
  const steps = [
    { label: 'Déclarée', done: true },
    { label: 'Confirmée', done: advance.status === 'confirmed' || advance.status === 'closed' },
    { label: 'Justificatif', done: advance.evidenceStatus !== 'none' },
    { label: 'Vérifié', done: advance.evidenceStatus === 'verified' },
  ];
  return (
    <div className="flex items-center gap-1">
      {steps.map((s, i) => (
        <div key={i} className="flex items-center gap-1">
          <div className={`w-2 h-2 rounded-full ${s.done ? 'bg-emerald-500' : 'bg-slate-100'}`} />
          {i < steps.length - 1 && <div className={`w-4 h-px ${s.done && steps[i + 1].done ? 'bg-emerald-300' : 'bg-slate-100'}`} />}
        </div>
      ))}
      <span className="text-xs text-slate-500 ml-1">
        {steps.filter(s => s.done).length}/{steps.length}
      </span>
    </div>
  );
}

export default function Avances() {
  const [selected, setSelected] = useState<PersonalAdvance | null>(null);
  const [filter, setFilter] = useState<AdvanceStatus | 'all'>('all');

  const { data: rawAdvances, loading } = useApiQuery(fetchPersonalAdvances, []);

  if (loading) return <div className="p-6 text-center text-slate-400 text-sm">Chargement…</div>;

  const personalAdvances = rawAdvances ?? [];

  const filtered = filter === 'all' ? personalAdvances : personalAdvances.filter(a => a.status === filter);

  const totalHeld = personalAdvances.reduce((s, a) => {
    const spent = a.movements.reduce((m, mv) => m + (mv.type === 'expense' ? mv.amount : 0), 0);
    const returned = a.movements.reduce((m, mv) => m + (mv.type === 'return' ? mv.amount : 0), 0);
    return s + Math.max(0, a.amount - spent - returned);
  }, 0);

  const pending = personalAdvances.filter(a => a.status === 'pending_confirmation').length;
  const disputed = personalAdvances.filter(a => a.status === 'disputed').length;
  const toCheck = personalAdvances.filter(a => a.evidenceStatus === 'to_check' || (a.status === 'confirmed' && a.evidenceStatus === 'none')).length;

  return (
    <div className="p-6 max-w-screen-xl mx-auto space-y-6">

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 p-4">
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide p-2">Total détenu</div>
          <div className="font-financial text-xl font-semibold text-[var(--color-primary)]">{formatCFA(totalHeld)}</div>
          <div className="text-xs text-slate-400 mt-1">par des personnes</div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide p-2">En attente</div>
          <div className="font-financial text-xl font-semibold text-amber-600">{pending}</div>
          <div className="text-xs text-slate-400 mt-1">confirmation(s)</div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide p-2">Litiges</div>
          <div className="font-financial text-xl font-semibold text-red-600">{disputed}</div>
          <div className="text-xs text-slate-400 mt-1">à résoudre</div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide p-2">Sans justif.</div>
          <div className="font-financial text-xl font-semibold text-amber-600">{toCheck}</div>
          <div className="text-xs text-slate-400 mt-1">opération(s)</div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        {([
          { id: 'all', label: 'Toutes' },
          { id: 'pending_confirmation', label: 'En attente' },
          { id: 'confirmed', label: 'Confirmées' },
          { id: 'disputed', label: 'Litiges' },
          { id: 'closed', label: 'Clôturées' },
        ] as const).map(f => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id as AdvanceStatus | 'all')}
            className={`p-2 rounded-full font-display text-xs font-medium transition-all ${
              filter === f.id
                ? 'bg-[var(--color-primary)] text-white shadow-sm'
                : 'bg-white border border-slate-200 text-slate-600 hover:border-[var(--color-primary)]'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* List */}
      <div className="p-4">
        {filtered.map(adv => {
          const spent = adv.movements.filter(m => m.type === 'expense').reduce((s, m) => s + m.amount, 0);
          const returned = adv.movements.filter(m => m.type === 'return').reduce((s, m) => s + m.amount, 0);
          const held = Math.max(0, adv.amount - spent - returned);
          const pct = adv.amount > 0 ? (spent / adv.amount) * 100 : 0;

          return (
            <button
              key={adv.id}
              onClick={() => setSelected(adv)}
              className={`w-full text-left bg-white rounded-xl border p-6 hover:shadow-sm transition-all ${
                adv.status === 'disputed'
                  ? 'border-red-200 hover:border-red-300'
                  : adv.status === 'pending_confirmation'
                  ? 'border-amber-200 hover:border-amber-300'
                  : 'border-slate-200 hover:border-[var(--color-primary)]'
              }`}
            >
              <div className="flex items-start justify-between gap-4 p-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="font-display text-xs text-slate-400">{adv.reference}</span>
                    <span className={`text-xs font-semibold border rounded px-2 mt-1 ${activityColors[adv.activity]}`}>
                      {adv.activity.charAt(0).toUpperCase() + adv.activity.slice(1)}
                    </span>
                    <Badge
                      variant={statusConfig[adv.status].variant as 'warning' | 'success' | 'neutral' | 'danger'}
                    >
                      {statusConfig[adv.status].label}
                    </Badge>
                  </div>
                  <div className="text-sm font-semibold text-slate-800">{adv.purpose}</div>
                  {adv.vehicleRef && (
                    <div className="text-xs text-slate-400 mt-1">{adv.vehicleRef}</div>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <div className="font-financial text-lg font-bold text-[var(--color-primary)]">{formatCFA(adv.amount)}</div>
                  <div className="text-xs text-slate-400">{adv.date}</div>
                </div>
              </div>

              {/* Financeur → Détenteur */}
              <div className="flex items-center gap-4">
                <div className="bg-[var(--color-surface-elevated)] rounded-full p-4 py-1 text-xs font-medium text-[var(--color-primary)]">
                  {adv.funderName}
                </div>
                <span className="text-slate-400 text-xs">→</span>
                <div className="bg-slate-100 rounded-full p-4 py-1 text-xs font-medium text-slate-700">
                  {adv.holderName}
                </div>
              </div>

              {/* Dispute warning */}
              {adv.status === 'disputed' && (
                <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-2 text-xs text-red-700">
                  ⚠ {adv.disputeNote}
                </div>
              )}

              {/* Progress */}
              <div className="grid grid-cols-3 p-4 mb-2 text-center">
                <div>
                  <div className="text-xs text-slate-400 mt-1">Justifié</div>
                  <div className="font-financial text-sm font-semibold text-emerald-600">{formatCFA(spent)}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-400 mt-1">Rendu</div>
                  <div className="font-financial text-sm font-semibold text-slate-600">{formatCFA(returned)}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-400 mt-1">Reste détenu</div>
                  <div className={`font-financial text-sm font-semibold ${held > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>{formatCFA(held)}</div>
                </div>
              </div>

              <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden mb-2">
                <div
                  className="h-full rounded-full bg-emerald-400 transition-all"
                  style={{ width: `${Math.min(100, pct)}%` }}
                />
              </div>

              <div className="flex items-center justify-between">
                <ValidationLevel advance={adv} />
                <div className={`text-xs font-medium ${evidenceConfig[adv.evidenceStatus].color}`}>
                  {evidenceConfig[adv.evidenceStatus].icon} {evidenceConfig[adv.evidenceStatus].label}
                </div>
              </div>
            </button>
          );
        })}

        {filtered.length === 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
            <div className="text-slate-400 text-sm">Aucune avance dans cette catégorie</div>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      <Modal open={!!selected} onClose={() => setSelected(null)} title="Parcours de l'argent" width="lg">
        {selected && (() => {
          const spent = selected.movements.filter(m => m.type === 'expense').reduce((s, m) => s + m.amount, 0);
          const returned = selected.movements.filter(m => m.type === 'return').reduce((s, m) => s + m.amount, 0);
          const held = Math.max(0, selected.amount - spent - returned);
          const owed = Math.max(0, spent - returned);

          return (
            <div className="p-6">
              {/* Header info */}
              <div className="grid grid-cols-2 p-4 text-sm">
                <div><div className="text-xs text-slate-500 mt-1">Référence</div><div className="font-mono text-slate-800">{selected.reference}</div></div>
                <div><div className="text-xs text-slate-500 mt-1">Date</div><div className="text-slate-800">{selected.date}</div></div>
                <div><div className="text-xs text-slate-500 mt-1">Activité</div>
                  <span className={`inline-block text-xs font-semibold border rounded px-2 mt-1 ${activityColors[selected.activity]}`}>
                    {selected.activity.charAt(0).toUpperCase() + selected.activity.slice(1)}
                  </span>
                </div>
                <div><div className="text-xs text-slate-500 mt-1">Statut</div>
                  <Badge variant={statusConfig[selected.status].variant as 'warning' | 'success' | 'neutral' | 'danger'}>
                    {statusConfig[selected.status].label}
                  </Badge>
                </div>
                <div className="col-span-2"><div className="text-xs text-slate-500 mt-1">Objet</div><div className="text-slate-800">{selected.purpose}</div></div>
                {selected.vehicleRef && <div className="col-span-2"><div className="text-xs text-slate-500 mt-1">Véhicule</div><div className="text-slate-600">{selected.vehicleRef}</div></div>}
              </div>

              {/* Confirmation info */}
              {selected.confirmationMethod && (
                <div className="bg-[var(--color-surface-elevated)] border border-[var(--color-border)] rounded-lg p-4 text-xs text-[var(--color-primary)] space-y-1">
                  <div>Confirmé par : <strong>{selected.confirmedBy}</strong></div>
                  <div>Méthode : <strong>{selected.confirmationMethod === 'root_override' ? 'Override ROOT' : selected.confirmationMethod === 'recipient_confirmation' ? 'Confirmation destinataire' : selected.confirmationMethod}</strong></div>
                  {selected.confirmedAt && <div>Date : {selected.confirmedAt}</div>}
                </div>
              )}

              {/* Dispute */}
              {selected.status === 'disputed' && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-2">
                  <div className="text-xs font-semibold text-red-700">⚠ Litige en cours</div>
                  <div className="grid grid-cols-3 gap-2 text-xs text-center">
                    <div><div className="text-red-500 mt-1">Déclaré</div><div className="font-financial font-bold text-red-700">{formatCFA(selected.amount)}</div></div>
                    <div><div className="text-red-500 mt-1">Reçu (déclaré)</div><div className="font-financial font-bold text-red-700">{formatCFA(selected.declaredAmount ?? 0)}</div></div>
                    <div><div className="text-red-500 mt-1">Écart</div><div className="font-financial font-bold text-red-700">{formatCFA(selected.amount - (selected.declaredAmount ?? 0))}</div></div>
                  </div>
                  {selected.disputeNote && <div className="text-xs text-red-600">{selected.disputeNote}</div>}
                </div>
              )}

              {/* Money trail */}
              <div>
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide p-4">Parcours de l'argent</div>
                <div className="space-y-2">
                  {/* Source */}
                  <div className="flex items-center p-4">
                    <div className="w-8 h-8 rounded-full bg-[var(--color-primary)] flex items-center justify-center shrink-0">
                      <span className="text-white text-xs font-bold">{selected.funderName.charAt(0)}</span>
                    </div>
                    <div className="flex-1">
                      <div className="text-xs font-semibold text-slate-700">{selected.funderName} <span className="text-slate-400 font-normal">— Financeur</span></div>
                      <div className="font-financial text-sm font-bold text-[var(--color-primary)]">{formatCFA(selected.amount)}</div>
                    </div>
                  </div>
                  <div className="ml-4 w-px h-3 bg-slate-100" />

                  {/* Holder */}
                  <div className="flex items-center p-4">
                    <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center shrink-0">
                      <span className="text-slate-600 text-xs font-bold">{selected.holderName.charAt(0)}</span>
                    </div>
                    <div className="flex-1">
                      <div className="text-xs font-semibold text-slate-700">{selected.holderName} <span className="text-slate-400 font-normal">— Détenteur</span></div>
                      <div className="font-financial text-sm font-medium text-slate-600">Reçu : {formatCFA(selected.amount)}</div>
                    </div>
                  </div>

                  {/* Movements */}
                  {selected.movements.map((mv, i) => (
                    <div key={mv.id}>
                      <div className="ml-4 w-px h-3 bg-slate-100" />
                      <div className="flex items-center p-4">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                          mv.type === 'expense' ? 'bg-red-50 border border-red-200' :
                          mv.type === 'return' ? 'bg-slate-50 border border-slate-200' :
                          'bg-emerald-50 border border-emerald-200'
                        }`}>
                          <span className="text-xs">{mv.type === 'expense' ? '↗' : mv.type === 'return' ? '↩' : '✓'}</span>
                        </div>
                        <div className="flex-1">
                          <div className="text-xs text-slate-600">{mv.description}</div>
                          <div className="flex items-center gap-2">
                            <span className="font-financial text-sm font-semibold text-red-600">-{formatCFA(mv.amount)}</span>
                            <span className={`text-xs ${evidenceConfig[mv.evidenceStatus].color}`}>
                              {evidenceConfig[mv.evidenceStatus].icon} {evidenceConfig[mv.evidenceStatus].label}
                            </span>
                          </div>
                        </div>
                        <div className="text-xs text-slate-400">{mv.date}</div>
                      </div>
                    </div>
                  ))}

                  {/* Summary */}
                  <div className="ml-4 w-px h-3 bg-slate-100" />
                  <div className="bg-slate-50 rounded-lg p-4">
                    <div className="grid grid-cols-3 p-4 text-center text-xs">
                      <div>
                        <div className="text-slate-500 mt-1">Justifié</div>
                        <div className="font-financial font-bold text-emerald-600">{formatCFA(spent)}</div>
                      </div>
                      <div>
                        <div className="text-slate-500 mt-1">Reste détenu</div>
                        <div className={`font-financial font-bold ${held > 0 ? 'text-amber-600' : 'text-slate-400'}`}>{formatCFA(held)}</div>
                      </div>
                      <div>
                        <div className="text-slate-500 mt-1">Entreprise doit</div>
                        <div className={`font-financial font-bold ${owed > 0 ? 'text-[var(--color-primary)]' : 'text-slate-400'}`}>{formatCFA(owed)}</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Justificatif */}
              <div className="flex items-center justify-between bg-slate-50 rounded-lg p-4">
                <div className="text-xs text-slate-600">Niveau de preuve</div>
                <div className={`text-sm font-medium ${evidenceConfig[selected.evidenceStatus].color}`}>
                  {evidenceConfig[selected.evidenceStatus].icon} {evidenceConfig[selected.evidenceStatus].label}
                </div>
              </div>
            </div>
          );
        })()}
      </Modal>
    </div>
  );
}
