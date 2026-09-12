import { useState } from 'react';
import { fetchPersons, createPerson, updatePerson } from '@/services';
import { useApiQuery } from '@/hooks/useApiQuery';
import { useAuth } from '@/contexts/AuthContext';
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

type PersonFormMode = 'create' | 'edit';

export default function Personnes() {
  const { isRoot } = useAuth();
  const [selected, setSelected] = useState<PersonOut | null>(null);
  const [filterStatus, setFilterStatus] = useState<PersonStatus | 'all'>('all');

  const { data: rawPeople, loading, refetch } = useApiQuery<PersonOut[]>(() => fetchPersons(), []);

  // Formulaire créer/modifier
  const [formOpen, setFormOpen] = useState(false);
  const [formMode, setFormMode] = useState<PersonFormMode>('create');
  const [pName, setPName] = useState('');
  const [pPhone, setPPhone] = useState('');
  const [pStatus, setPStatus] = useState<PersonStatus>('active');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  function openCreate() {
    setFormMode('create'); setPName(''); setPPhone(''); setPStatus('active'); setFormError(null); setFormOpen(true);
  }

  function openEdit(person: PersonOut) {
    setFormMode('edit'); setPName(person.full_name); setPPhone(person.phone ?? ''); setPStatus(person.status); setFormError(null); setFormOpen(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!pName.trim()) { setFormError('Le nom est requis.'); return; }
    setSubmitting(true); setFormError(null);
    try {
      if (formMode === 'create') {
        await createPerson({ full_name: pName.trim(), phone: pPhone.trim() || null });
      } else if (selected) {
        await updatePerson(selected.id, { full_name: pName.trim(), phone: pPhone.trim() || null, status: pStatus });
      }
      setFormOpen(false); refetch();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Erreur lors de l\'enregistrement.');
    } finally {
      setSubmitting(false);
    }
  }

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
        {isRoot && (
          <button onClick={openCreate} className="ml-auto p-2 rounded-full font-display text-xs font-medium bg-navy-800 text-white border border-navy-800 hover:bg-navy-700 transition-all">
            + Nouvelle personne
          </button>
        )}
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

            {isRoot && (
              <div className="flex justify-end border-t border-slate-100 pt-4">
                <button onClick={() => openEdit(selected)} className="px-4 py-2 text-sm bg-navy-800 text-white rounded-lg hover:bg-navy-700 transition-colors">
                  Modifier la personne
                </button>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Form créer / modifier personne */}
      <Modal open={formOpen} onClose={() => !submitting && setFormOpen(false)} title={formMode === 'create' ? 'Nouvelle personne' : 'Modifier la personne'} width="md">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-slate-500 block p-2">Nom complet *</label>
            <input required value={pName} onChange={e => setPName(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500 block p-2">Téléphone</label>
            <input value={pPhone} onChange={e => setPPhone(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
          </div>
          {formMode === 'edit' && (
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Statut</label>
              <select value={pStatus} onChange={e => setPStatus(e.target.value as PersonStatus)} className="w-full border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white">
                <option value="active">Actif</option>
                <option value="inactive">Inactif</option>
              </select>
            </div>
          )}
          {formError && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{formError}</p>}
          <div className="flex gap-2 justify-end pt-2">
            <button type="button" onClick={() => setFormOpen(false)} disabled={submitting} className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50">Annuler</button>
            <button type="submit" disabled={submitting} className="px-4 py-2 text-sm bg-navy-800 text-white rounded-lg hover:bg-navy-700 disabled:opacity-50">{submitting ? (formMode === 'create' ? 'Création…' : 'Enregistrement…') : (formMode === 'create' ? 'Créer' : 'Enregistrer')}</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
