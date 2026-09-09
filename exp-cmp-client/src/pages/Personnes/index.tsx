import { useState } from 'react';
import { formatCFA } from '@/utils/format';
import { fetchPeople, fetchPersonalAdvances } from '@/services/mock';
import { useApiQuery } from '@/hooks/useApiQuery';
import type { Person, PersonRole, PersonalAdvance } from '@/types';
import Modal from '@/components/ui/Modal';

const roleConfig: Record<PersonRole, { label: string; color: string }> = {
  root: { label: 'Root admin', color: 'bg-[var(--color-primary)] text-white' },
  member: { label: 'Famille', color: 'bg-[var(--color-surface-elevated)] text-[var(--color-secondary)]' },
  driver: { label: 'Chauffeur', color: 'bg-amber-100 text-amber-700' },
  supplier: { label: 'Fournisseur', color: 'bg-slate-100 text-slate-600' },
  other: { label: 'Autre', color: 'bg-slate-100 text-slate-500' },
};

function PersonCard({ person, onClick }: { person: Person; onClick: () => void }) {
  const stillOwed = person.totalAdvanced - person.totalRepaid;

  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-white rounded-xl border border-slate-200 p-6 hover:border-[var(--color-primary)] hover:shadow-sm transition-all group"
    >
      <div className="flex items-start gap-4 mb-4">
        <div className="w-11 h-11 rounded-full bg-[var(--color-primary)] flex items-center justify-center shrink-0">
          <span className="text-white text-sm font-bold">
            {person.name.split(' ').map(n => n[0]).join('').slice(0, 2)}
          </span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-slate-800">{person.name}</div>
          <div className="flex items-center gap-2 mt-1">
            <span className={`text-xs font-semibold rounded-full px-2 mt-1 ${roleConfig[person.role].color}`}>
              {roleConfig[person.role].label}
            </span>
            {person.phone && (
              <span className="text-xs text-slate-400">{person.phone}</span>
            )}
          </div>
        </div>
        {(person.pendingCount > 0 || person.disputedCount > 0) && (
          <div className="flex p-2 shrink-0">
            {person.disputedCount > 0 && (
              <span className="w-5 h-5 rounded-full bg-red-500 text-white text-xs font-bold flex items-center justify-center">
                {person.disputedCount}
              </span>
            )}
            {person.pendingCount > 0 && (
              <span className="w-5 h-5 rounded-full bg-amber-400 text-white text-xs font-bold flex items-center justify-center">
                {person.pendingCount}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Financial summary */}
      <div className="grid grid-cols-3 p-4">
        <div className="text-center">
          <div className="text-xs text-slate-400 mt-1">A avancé</div>
          <div className="font-financial text-sm font-semibold text-[var(--color-primary)]">{formatCFA(person.totalAdvanced)}</div>
        </div>
        <div className="text-center">
          <div className="text-xs text-slate-400 mt-1">Remboursé</div>
          <div className="font-financial text-sm font-semibold text-emerald-600">{formatCFA(person.totalRepaid)}</div>
        </div>
        <div className="text-center">
          <div className="text-xs text-slate-400 mt-1">Encore dû</div>
          <div className={`font-financial text-sm font-semibold ${stillOwed > 0 ? 'text-amber-600' : 'text-slate-400'}`}>
            {formatCFA(stillOwed)}
          </div>
        </div>
      </div>

      {/* Held + stats row */}
      <div className="flex items-center justify-between p-4 border-t border-slate-100">
        <div className="flex items-center gap-1">
          {person.totalHeld > 0 && (
            <span className="text-xs text-amber-600 font-medium">
              Détient {formatCFA(person.totalHeld)}
            </span>
          )}
        </div>
        <div className="flex items-center p-4 text-xs text-slate-400">
          <span className="text-emerald-600 font-semibold">{person.confirmedCount} conf.</span>
          {person.pendingCount > 0 && <span className="text-amber-600 font-semibold">{person.pendingCount} att.</span>}
          {person.disputedCount > 0 && <span className="text-red-500 font-semibold">{person.disputedCount} litige</span>}
        </div>
      </div>

      {(person.confirmedCount + person.pendingCount + person.disputedCount) > 0 && (
        <div className="text-xs text-slate-400 mt-2 group-hover:text-[var(--color-secondary)] transition-colors">
          {person.confirmedCount + person.pendingCount + person.disputedCount} avance(s) déclarée(s) · Voir le détail →
        </div>
      )}
    </button>
  );
}

export default function Personnes() {
  const [selected, setSelected] = useState<Person | null>(null);
  const [filterRole, setFilterRole] = useState<PersonRole | 'all'>('all');

  const { data: rawPeople, loading: loadingPeople } = useApiQuery<Person[]>(fetchPeople, []);
  const { data: rawAdvances, loading: loadingAdvances } = useApiQuery<PersonalAdvance[]>(fetchPersonalAdvances, []);

  if (loadingPeople || loadingAdvances) return <div className="p-6 text-center text-slate-400 text-sm">Chargement…</div>;

  const people = rawPeople ?? [];
  const personalAdvances = rawAdvances ?? [];

  const filtered = filterRole === 'all' ? people : people.filter(p => p.role === filterRole);

  const totalOwed = people.reduce((s, p) => s + Math.max(0, p.totalAdvanced - p.totalRepaid), 0);
  const totalHeld = people.reduce((s, p) => s + p.totalHeld, 0);

  const selectedAdvances = selected
    ? personalAdvances.filter(a => a.funderId === selected.id || a.holderId === selected.id)
    : [];

  return (
    <div className="p-6 max-w-screen-xl mx-auto space-y-6">

      {/* Summary KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 p-4">
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide p-2">Personnes</div>
          <div className="font-financial text-xl font-semibold text-slate-800">{people.length}</div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide p-2">Entreprise doit</div>
          <div className="font-financial text-xl font-semibold text-amber-600">{formatCFA(totalOwed)}</div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide p-2">Argent détenu</div>
          <div className="font-financial text-xl font-semibold text-[var(--color-primary)]">{formatCFA(totalHeld)}</div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide p-2">Litiges ouverts</div>
          <div className="font-financial text-xl font-semibold text-red-600">
            {people.reduce((s, p) => s + p.disputedCount, 0)}
          </div>
        </div>
      </div>

      {/* Role filter */}
      <div className="flex items-center gap-2 flex-wrap">
        {([
          { id: 'all', label: 'Toutes' },
          { id: 'root', label: 'Root' },
          { id: 'member', label: 'Famille' },
          { id: 'driver', label: 'Chauffeurs' },
          { id: 'supplier', label: 'Fournisseurs' },
          { id: 'other', label: 'Autres' },
        ] as const).map(r => (
          <button
            key={r.id}
            onClick={() => setFilterRole(r.id as PersonRole | 'all')}
            className={`p-2 rounded-full font-display text-xs font-medium transition-all ${
              filterRole === r.id
                ? 'bg-[var(--color-primary)] text-white shadow-sm'
                : 'bg-white border border-slate-200 text-slate-600 hover:border-[var(--color-primary)]'
            }`}
          >
            {r.label}
          </button>
        ))}
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map(p => (
          <PersonCard key={p.id} person={p} onClick={() => setSelected(p)} />
        ))}
      </div>

      {/* Person detail modal */}
      <Modal open={!!selected} onClose={() => setSelected(null)} title="Fiche personne" width="lg">
        {selected && (() => {
          const stillOwed = selected.totalAdvanced - selected.totalRepaid;
          return (
            <div className="p-6">
              {/* Identity */}
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-full bg-[var(--color-primary)] flex items-center justify-center shrink-0">
                  <span className="text-white text-lg font-bold">
                    {selected.name.split(' ').map(n => n[0]).join('').slice(0, 2)}
                  </span>
                </div>
                <div>
                  <div className="text-xl font-display text-slate-800">{selected.name}</div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`text-xs font-semibold rounded-full p-2 mt-1 ${roleConfig[selected.role].color}`}>
                      {roleConfig[selected.role].label}
                    </span>
                    {selected.phone && <span className="text-sm text-slate-500">{selected.phone}</span>}
                  </div>
                </div>
              </div>

              {/* Financial overview */}
              <div className="bg-slate-50 rounded-xl p-4">
                <div className="grid grid-cols-3 gap-4 text-center p-4">
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Avancé à l'entreprise</div>
                    <div className="font-financial text-xl font-bold text-[var(--color-primary)]">{formatCFA(selected.totalAdvanced)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Remboursé</div>
                    <div className="font-financial text-xl font-bold text-emerald-600">{formatCFA(selected.totalRepaid)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Encore dû</div>
                    <div className={`font-financial text-xl font-bold ${stillOwed > 0 ? 'text-amber-600' : 'text-slate-400'}`}>
                      {formatCFA(stillOwed)}
                    </div>
                  </div>
                </div>
                {selected.totalAdvanced > 0 && (
                  <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-emerald-500"
                      style={{ width: `${Math.min(100, (selected.totalRepaid / selected.totalAdvanced) * 100)}%` }}
                    />
                  </div>
                )}
              </div>

              {/* Held */}
              {selected.totalHeld > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm">
                  <div className="text-amber-700 font-medium">Argent actuellement détenu</div>
                  <div className="font-financial text-xl font-bold text-amber-600 mt-1">{formatCFA(selected.totalHeld)}</div>
                  <div className="text-xs text-amber-600 mt-1">À justifier ou restituer à l'entreprise</div>
                </div>
              )}

              {/* Stats */}
              <div className="grid grid-cols-3 p-4 text-center">
                <div className="bg-white border border-slate-200 rounded-lg p-4">
                  <div className="text-xs text-slate-400 mb-1">Déclarations</div>
                  <div className="font-financial text-lg font-bold text-slate-700">{selected.confirmedCount + selected.pendingCount + selected.disputedCount}</div>
                </div>
                <div className="bg-white border border-slate-200 rounded-lg p-4">
                  <div className="text-xs text-slate-400 mb-1">Confirmées</div>
                  <div className="font-financial text-lg font-bold text-emerald-600">{selected.confirmedCount}</div>
                </div>
                <div className="bg-white border border-slate-200 rounded-lg p-4">
                  <div className="text-xs text-slate-400 mb-1">En attente</div>
                  <div className="font-financial text-lg font-bold text-amber-600">{selected.pendingCount}</div>
                </div>
              </div>

              {/* Related advances */}
              {selectedAdvances.length > 0 && (
                <div>
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Avances liées</div>
                  <div className="space-y-2">
                    {selectedAdvances.map(adv => {
                      const spent = adv.movements.filter(m => m.type === 'expense').reduce((s, m) => s + m.amount, 0);
                      return (
                        <div key={adv.id} className="bg-slate-50 rounded-lg p-2 flex items-center justify-between">
                          <div>
                            <div className="text-xs font-mono text-slate-500">{adv.reference}</div>
                            <div className="text-sm text-slate-700">{adv.purpose}</div>
                            <div className="text-xs text-slate-400">{adv.date} · {adv.activity}</div>
                          </div>
                          <div className="text-right">
                            <div className="font-financial text-sm font-bold text-[var(--color-primary)]">{formatCFA(adv.amount)}</div>
                            <div className="text-xs text-emerald-600">Justifié : {formatCFA(spent)}</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          );
        })()}
      </Modal>
    </div>
  );
}
