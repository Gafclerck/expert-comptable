import { useState } from 'react';
import { fetchPersons } from '@/services';
import { useApiQuery } from '@/hooks/useApiQuery';
import type { PersonOut, PersonStatus } from '@/types/api';
import Badge from '@/components/ui/Badge';
import Modal from '@/components/ui/Modal';

const statusLabel: Record<PersonStatus, { label: string; variant: 'success' | 'neutral' }> = {
  active: { label: 'Actif', variant: 'success' },
  inactive: { label: 'Inactif', variant: 'neutral' },
};

function initials(name: string) {
  return name.trim().split(/\s+/).map(n => n[0]).join('').slice(0, 2).toUpperCase();
}

function PersonCard({ person, onClick }: { person: PersonOut; onClick: () => void }) {
  const status = statusLabel[person.status];
  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-white rounded-xl border border-slate-200 p-6 hover:border-[var(--color-primary)] hover:shadow-sm transition-all group"
    >
      <div className="flex items-start gap-4">
        <div className="w-11 h-11 rounded-full bg-[var(--color-primary)] flex items-center justify-center shrink-0">
          <span className="text-white text-sm font-bold">{initials(person.full_name)}</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-slate-800 truncate">{person.full_name}</div>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <Badge variant={status.variant}>{status.label}</Badge>
            {person.phone && <span className="text-xs text-slate-400">{person.phone}</span>}
          </div>
        </div>
      </div>
      <div className="text-xs text-slate-400 mt-4 group-hover:text-[var(--color-secondary)] transition-colors">
        Voir la fiche →
      </div>
    </button>
  );
}

export default function Personnes() {
  const [selected, setSelected] = useState<PersonOut | null>(null);
  const [filterStatus, setFilterStatus] = useState<PersonStatus | 'all'>('all');

  const { data: rawPeople, loading } = useApiQuery<PersonOut[]>(() => fetchPersons(), []);

  if (loading) return <div className="p-6 text-center text-slate-400 text-sm">Chargement…</div>;

  const people = rawPeople ?? [];
  const filtered = filterStatus === 'all' ? people : people.filter(p => p.status === filterStatus);

  return (
    <div className="p-6 max-w-screen-xl mx-auto space-y-6">

      {/* Summary KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 p-4">
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide p-2">Personnes</div>
          <div className="font-financial text-xl font-semibold text-slate-800">{people.length}</div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide p-2">Actives</div>
          <div className="font-financial text-xl font-semibold text-emerald-600">
            {people.filter(p => p.status === 'active').length}
          </div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide p-2">Inactives</div>
          <div className="font-financial text-xl font-semibold text-slate-500">
            {people.filter(p => p.status === 'inactive').length}
          </div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide p-2">Avec téléphone</div>
          <div className="font-financial text-xl font-semibold text-slate-800">
            {people.filter(p => !!p.phone).length}
          </div>
        </div>
      </div>

      {/* Status filter */}
      <div className="flex items-center gap-2 flex-wrap">
        {([
          { id: 'all', label: 'Toutes' },
          { id: 'active', label: 'Actives' },
          { id: 'inactive', label: 'Inactives' },
        ] as const).map(r => (
          <button
            key={r.id}
            onClick={() => setFilterStatus(r.id as PersonStatus | 'all')}
            className={`p-2 rounded-full font-display text-xs font-medium transition-all ${
              filterStatus === r.id
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
        {filtered.length === 0 && (
          <div className="text-sm text-slate-400 text-center py-8 md:col-span-2 xl:col-span-3">
            Aucune personne enregistrée.
          </div>
        )}
      </div>

      {/* Person detail modal */}
      <Modal open={!!selected} onClose={() => setSelected(null)} title="Fiche personne" width="lg">
        {selected && (
          <div className="p-6 space-y-6">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-full bg-[var(--color-primary)] flex items-center justify-center shrink-0">
                <span className="text-white text-lg font-bold">{initials(selected.full_name)}</span>
              </div>
              <div>
                <div className="text-xl font-display text-slate-800">{selected.full_name}</div>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant={statusLabel[selected.status].variant}>{statusLabel[selected.status].label}</Badge>
                  {selected.phone && <span className="text-sm text-slate-500">{selected.phone}</span>}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-slate-50 rounded-lg p-4">
                <div className="text-xs text-slate-500 mb-1">Téléphone</div>
                <div className="text-slate-800 font-medium">{selected.phone ?? 'Non renseigné'}</div>
              </div>
              <div className="bg-slate-50 rounded-lg p-4">
                <div className="text-xs text-slate-500 mb-1">Créée le</div>
                <div className="text-slate-800 font-medium">{new Date(selected.created_at).toLocaleDateString('fr-FR')}</div>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
