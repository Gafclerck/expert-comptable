import { useState, useMemo } from 'react';
import type { FormEvent } from 'react';
import { formatCFA } from '@/utils/format';
import { createTransfer, fetchAccounts, fetchCategories } from '@/services';
import { getCachedBusinesses } from '@/services/identity';
import { useApiQuery } from '@/hooks/useApiQuery';
import { useTransactions } from '@/hooks/useTransactions';
import type { TransactionCreate, TransactionOut, TransactionType } from '@/types/api';
import Badge from '@/components/ui/Badge';
import Modal from '@/components/ui/Modal';

const TYPE_OPTIONS: Array<{ id: TransactionType; label: string }> = [
  { id: 'revenue', label: 'Recette' },
  { id: 'expense', label: 'Dépense' },
];

function typeLabels(type: TransactionType): string {
  const found = TYPE_OPTIONS.find(t => t.id === type);
  return found?.label ?? type;
}

const typeVariants: Record<TransactionType, 'success' | 'danger'> = {
  revenue: 'success',
  expense: 'danger',
};

function statusColor(status: string): string {
  if (status === 'posted') return 'bg-emerald-50 text-emerald-700';
  if (status === 'confirmed') return 'bg-amber-50 text-amber-700';
  return 'bg-slate-100 text-slate-600';
}

function toLocalInputValue(d: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

const inputClass =
  'border border-slate-200 rounded p-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white w-full';

export default function Transactions() {
  const [selectedTx, setSelectedTx] = useState<TransactionOut | null>(null);
  const [filterBusiness, setFilterBusiness] = useState<string>('all');
  const [filterType, setFilterType] = useState<string>('all');
  const [search, setSearch] = useState('');

  const { transactions, loading, error, refetch, create, creating, createError, resetCreateError } = useTransactions();
  const { data: accountsData } = useApiQuery(() => fetchAccounts(), []);
  const { data: categoriesData } = useApiQuery(() => fetchCategories(), []);

  const accounts = accountsData ?? [];
  const categories = categoriesData ?? [];
  const accountLabel = useMemo(() => {
    const map = new Map<string, string>();
    accounts.forEach(a => map.set(a.id, a.name));
    return map;
  }, [accounts]);
  const categoryName = useMemo(() => {
    const map = new Map<string, string>();
    categories.forEach(c => map.set(c.id, c.name));
    return map;
  }, [categories]);
  const businessLabel = useMemo(() => {
    const map = new Map<string, string>();
    getCachedBusinesses().forEach(b => map.set(b.id, b.name));
    return map;
  }, []);
  const businessOptions = useMemo(() => getCachedBusinesses(), []);

  const filtered = useMemo(() => {
    return transactions.filter(tx => {
      if (filterBusiness !== 'all' && tx.business_id !== filterBusiness) return false;
      if (filterType !== 'all' && tx.type !== filterType) return false;
      if (search) {
        const q = search.toLowerCase();
        return (tx.description ?? '').toLowerCase().includes(q) ||
          (tx.lines?.[0]?.description ?? '').toLowerCase().includes(q);
      }
      return true;
    });
  }, [transactions, filterBusiness, filterType, search]);

  const isInflow = (tx: TransactionOut) => tx.type === 'revenue';
  const isOutflow = (tx: TransactionOut) => tx.type === 'expense';

  const totalIn = filtered.filter(isInflow).reduce((s, t) => s + Number(t.amount), 0);
  const totalOut = filtered.filter(isOutflow).reduce((s, t) => s + Number(t.amount), 0);

  // ─── Saisie d'une nouvelle écriture ───────────────────────────
  const [formOpen, setFormOpen] = useState(false);
  const [formType, setFormType] = useState<TransactionType>('revenue');
  const [formBusiness, setFormBusiness] = useState('');
  const [formAccount, setFormAccount] = useState('');
  const [formCategory, setFormCategory] = useState('');
  const [formAmount, setFormAmount] = useState('');
  const [formDescription, setFormDescription] = useState('');
  const [formOccurredAt, setFormOccurredAt] = useState(toLocalInputValue());

  const accountsForBusiness = accounts.filter(a => a.business_id === formBusiness && a.active);
  const categoriesForType = categories.filter(c => c.type === (formType === 'revenue' ? 'credit' : 'debit'));
  const effectiveAccount = accountsForBusiness.some(a => a.id === formAccount)
    ? formAccount
    : accountsForBusiness[0]?.id ?? '';
  const effectiveCategory = categoriesForType.some(c => c.id === formCategory)
    ? formCategory
    : categoriesForType[0]?.id ?? '';
  const canSubmit = !!(formBusiness && effectiveAccount && effectiveCategory && Number(formAmount) > 0);

  function openForm() {
    const preferred = filterBusiness !== 'all' ? filterBusiness : businessOptions[0]?.id ?? '';
    setFormType('revenue');
    setFormBusiness(preferred);
    setFormAccount('');
    setFormCategory('');
    setFormAmount('');
    setFormDescription('');
    setFormOccurredAt(toLocalInputValue());
    resetCreateError();
    setFormOpen(true);
  }

  async function handleSubmit() {
    if (!canSubmit) return;
    const amount = Number(formAmount);
    const payload: TransactionCreate = {
      business_id: formBusiness,
      account_id: effectiveAccount,
      type: formType,
      amount,
      description: formDescription.trim() || null,
      occurred_at: formOccurredAt ? new Date(formOccurredAt).toISOString() : undefined,
      lines: [{
        category_id: effectiveCategory,
        amount,
        direction: formType === 'revenue' ? 'credit' : 'debit',
      }],
    };
    try {
      await create(payload);
      setFormOpen(false);
    } catch {
      // createError est affiché dans le modal
    }
  }

  // ─── Nouveau transfert entre caisses ─────────────────────────
  const [transferOpen, setTransferOpen] = useState(false);
  const [tFrom, setTFrom] = useState('');
  const [tTo, setTTo] = useState('');
  const [tAmount, setTAmount] = useState('');
  const [tReference, setTReference] = useState('');
  const [tOccurredAt, setTOccurredAt] = useState(toLocalInputValue());
  const [transferSubmitting, setTransferSubmitting] = useState(false);
  const [transferError, setTransferError] = useState<string | null>(null);

  const accountOptions = accounts.filter(a => a.active);
  const accountLabelFull = (id: string) => {
    const name = accountLabel.get(id) ?? '—';
    const acc = accounts.find(a => a.id === id);
    const biz = acc ? businessLabel.get(acc.business_id) : null;
    return biz ? `${name} · ${biz}` : name;
  };

  function openTransfer() {
    const first = accountOptions[0];
    const second = accountOptions.find(a => a.id !== first?.id) ?? first;
    setTFrom(first?.id ?? ''); setTTo(second?.id ?? '');
    setTAmount(''); setTReference(''); setTOccurredAt(toLocalInputValue());
    setTransferError(null); setTransferOpen(true);
  }

  async function handleTransferSubmit(e: FormEvent) {
    e.preventDefault();
    const amount = Number(tAmount);
    if (!tFrom || !tTo || tFrom === tTo || !Number.isFinite(amount) || amount <= 0) {
      setTransferError('Choisissez deux comptes différents et un montant supérieur à 0.');
      return;
    }
    setTransferSubmitting(true); setTransferError(null);
    try {
      await createTransfer({
        source_account_id: tFrom,
        destination_account_id: tTo,
        amount,
        occurred_at: tOccurredAt ? new Date(tOccurredAt).toISOString() : undefined,
        reference: tReference.trim() || null,
      });
      setTransferOpen(false); refetch();
    } catch (err) { setTransferError(err instanceof Error ? err.message : 'Erreur.'); setTransferSubmitting(false); }
  }

  return (
    <div className="p-6 max-w-screen-xl mx-auto">

      {/* Header */}
      <div className="flex items-center justify-between px-4 pt-2 pb-4">
        <h1 className="text-xl font-semibold text-slate-800">Transactions</h1>
        <div className="flex gap-2">
          <button
            onClick={openTransfer}
            className="bg-white border border-slate-200 hover:border-slate-300 text-slate-700 text-sm font-medium rounded-lg px-4 py-2 transition-colors"
          >
            Nouveau transfert
          </button>
          <button
            onClick={openForm}
            className="bg-navy-600 hover:bg-navy-700 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
          >
            Nouvelle écriture
          </button>
        </div>
      </div>

      {/* Summary row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 p-4">
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <div className="section-eyebrow p-2">Entrées (filtré)</div>
          <div className="font-financial text-xl font-semibold text-emerald-600">{formatCFA(totalIn)}</div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <div className="section-eyebrow p-2">Sorties (filtré)</div>
          <div className="font-financial text-xl font-semibold text-red-600">{formatCFA(totalOut)}</div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <div className="section-eyebrow p-2">Solde (filtré)</div>
          <div className={`font-financial text-xl font-semibold ${totalIn - totalOut >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
            {totalIn - totalOut >= 0 ? '+' : ''}{formatCFA(totalIn - totalOut)}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="flex flex-wrap p-4 items-center gap-2">
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Rechercher dans les transactions…"
            className="border border-slate-200 rounded p-2 text-sm text-slate-700 placeholder-slate-400 outline-none focus:border-navy-400 flex-1 min-w-[200px]"
          />

          <select
            value={filterBusiness}
            onChange={e => setFilterBusiness(e.target.value)}
            className="border border-slate-200 rounded p-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white"
          >
            <option value="all">Toutes activités</option>
            {businessOptions.map(b => (
              <option key={b.id} value={b.id}>{b.name}</option>
            ))}
          </select>

          <select
            value={filterType}
            onChange={e => setFilterType(e.target.value)}
            className="border border-slate-200 rounded p-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white"
          >
            <option value="all">Tous les types</option>
            {TYPE_OPTIONS.map(t => (
              <option key={t.id} value={t.id}>{t.label}</option>
            ))}
          </select>

          {(filterBusiness !== 'all' || filterType !== 'all' || search) && (
            <button
              onClick={() => { setFilterBusiness('all'); setFilterType('all'); setSearch(''); }}
              className="text-xs text-slate-500 hover:text-slate-700 underline"
            >
              Réinitialiser
            </button>
          )}

          <div className="text-xs text-slate-400 ml-auto flex items-center gap-2">
            {loading && <span className="w-3 h-3 border-2 border-slate-300 border-t-navy-500 rounded-full animate-spin" />}
            {filtered.length} transaction{filtered.length > 1 ? 's' : ''}
          </div>
        </div>

        {error && (
          <div className="mx-4 mb-4 flex items-center justify-between gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <span>Impossible de charger les transactions : {error}</span>
            <button onClick={refetch} className="shrink-0 text-xs font-semibold underline">
              Réessayer
            </button>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-400 text-sm">
            <div className="w-5 h-5 border-2 border-slate-200 border-t-navy-500 rounded-full animate-spin mx-auto p-4" />
            Chargement des transactions…
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="text-left p-4 text-xs font-semibold text-slate-500 uppercase tracking-wide">Date</th>
                <th className="text-left p-4 text-xs font-semibold text-slate-500 uppercase tracking-wide">Description</th>
                <th className="text-left p-4 text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">Activité</th>
                <th className="text-left p-4 text-xs font-semibold text-slate-500 uppercase tracking-wide hidden lg:table-cell">Type</th>
                <th className="text-right p-4 text-xs font-semibold text-slate-500 uppercase tracking-wide">Montant</th>
                <th className="text-left p-4 text-xs font-semibold text-slate-500 uppercase tracking-wide hidden lg:table-cell">Statut</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(tx => {
                const inflow = isInflow(tx);
                const outflow = isOutflow(tx);
                return (
                  <tr
                    key={tx.id}
                    className="border-b border-slate-50 hover:bg-slate-50 cursor-pointer transition-colors"
                    onClick={() => setSelectedTx(tx)}
                  >
                    <td className="p-4 text-slate-500 text-xs whitespace-nowrap">
                      {new Date(tx.occurred_at).toLocaleDateString('fr-FR')}
                    </td>
                    <td className="p-4">
                      <div className="text-slate-800 font-medium text-sm leading-snug">{tx.description ?? '—'}</div>
                    </td>
                    <td className="p-4 hidden md:table-cell">
                      <span className="text-xs text-slate-600">{businessLabel.get(tx.business_id) ?? '—'}</span>
                    </td>
                    <td className="p-4 hidden lg:table-cell">
                      <Badge variant={typeVariants[tx.type]}>
                        {typeLabels(tx.type)}
                      </Badge>
                    </td>
                    <td className="p-4 text-right font-financial text-sm">
                      {inflow ? (
                        <span className="text-emerald-600 font-semibold">+{formatCFA(Number(tx.amount))}</span>
                      ) : outflow ? (
                        <span className="text-red-600 font-semibold">−{formatCFA(Number(tx.amount))}</span>
                      ) : (
                        <span className="text-slate-600 font-semibold">{formatCFA(Number(tx.amount))}</span>
                      )}
                    </td>
                    <td className="p-4 hidden lg:table-cell">
                      <span className={`text-xs font-semibold rounded-full px-2 mt-1 ${statusColor(tx.status)}`}>
                        {tx.status}
                      </span>
                    </td>
                  </tr>
                );
              })}
              {filtered.length === 0 && !loading && (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400 text-sm">
                    Aucune transaction ne correspond aux filtres sélectionnés
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          </div>
        )}
      </div>

      {/* Transaction detail panel */}
      <Modal
        open={!!selectedTx}
        onClose={() => setSelectedTx(null)}
        title="Détail de la transaction"
        width="md"
      >
        {selectedTx && (() => {
          const inflow = isInflow(selectedTx);
          const outflow = isOutflow(selectedTx);
          return (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-slate-500 mt-1">Date</div>
                  <div className="text-slate-800">{new Date(selectedTx.occurred_at).toLocaleString('fr-FR')}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mt-1">Type</div>
                  <Badge variant={typeVariants[selectedTx.type]}>
                    {typeLabels(selectedTx.type)}
                  </Badge>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mt-1">Activité</div>
                  <div className="text-slate-800">{businessLabel.get(selectedTx.business_id) ?? '—'}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mt-1">Compte</div>
                  <div className="text-slate-800">{accountLabel.get(selectedTx.account_id) ?? '—'}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mt-1">Référence</div>
                  <div className="font-mono text-xs text-slate-700">{selectedTx.id.slice(0, 8)}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mt-1">Statut</div>
                  <span className={`text-xs font-semibold rounded-full px-2 mt-1 ${statusColor(selectedTx.status)}`}>
                    {selectedTx.status}
                  </span>
                </div>
                <div className="col-span-2">
                  <div className="text-xs text-slate-500 mt-1">Écritures</div>
                  {selectedTx.lines?.length ? (
                    <div className="space-y-1">
                      {selectedTx.lines.map(line => (
                        <div key={line.id} className="flex items-center justify-between text-sm bg-slate-50 rounded p-2">
                          <span className="text-slate-600">
                            {categoryName.get(line.category_id) ?? line.category_id.slice(0, 8)}
                            {line.description ? ` — ${line.description}` : ''}
                          </span>
                          <span className={`font-financial font-semibold ${line.direction === 'credit' ? 'text-emerald-600' : 'text-red-600'}`}>
                            {line.direction === 'credit' ? '+' : '−'}{formatCFA(Number(line.amount))}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-slate-400 text-sm">—</div>
                  )}
                </div>
              </div>
              <div className="bg-slate-50 rounded-lg p-4 text-center">
                <div className="text-xs text-slate-500 mb-1">
                  {inflow ? 'Montant reçu' : outflow ? 'Montant décaissé' : 'Montant'}
                </div>
                <div className={`font-financial text-3xl font-bold ${inflow ? 'text-emerald-600' : outflow ? 'text-red-600' : 'text-slate-700'}`}>
                  {outflow && '−'}{formatCFA(Number(selectedTx.amount))}
                </div>
              </div>
            </div>
          );
        })()}
      </Modal>

      {/* New transaction modal */}
      <Modal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title="Nouvelle écriture"
        width="md"
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Type</label>
              <div className="flex gap-2">
                {TYPE_OPTIONS.map(opt => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => { setFormType(opt.id); setFormCategory(''); }}
                    className={`flex-1 rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                      formType === opt.id
                        ? opt.id === 'revenue'
                          ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
                          : 'border-red-500 bg-red-50 text-red-700'
                        : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Date</label>
              <input
                type="datetime-local"
                value={formOccurredAt}
                onChange={e => setFormOccurredAt(e.target.value)}
                className={inputClass}
              />
            </div>
          </div>

          <div>
            <label className="text-xs text-slate-500 mb-1 block">Activité</label>
            <select
              value={formBusiness}
              onChange={e => { setFormBusiness(e.target.value); setFormAccount(''); }}
              className={inputClass}
            >
              <option value="" disabled>Sélectionner une activité…</option>
              {businessOptions.map(b => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Compte</label>
              <select
                value={effectiveAccount}
                onChange={e => setFormAccount(e.target.value)}
                className={inputClass}
                disabled={!formBusiness || accountsForBusiness.length === 0}
              >
                {accountsForBusiness.length === 0 && <option value="">—</option>}
                {accountsForBusiness.map(a => (
                  <option key={a.id} value={a.id}>{a.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Catégorie</label>
              <select
                value={effectiveCategory}
                onChange={e => setFormCategory(e.target.value)}
                className={inputClass}
                disabled={categoriesForType.length === 0}
              >
                {categoriesForType.length === 0 && <option value="">—</option>}
                {categoriesForType.map(c => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Montant (FCFA)</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={formAmount}
                onChange={e => setFormAmount(e.target.value)}
                placeholder="0"
                className={inputClass}
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Description</label>
              <input
                type="text"
                value={formDescription}
                onChange={e => setFormDescription(e.target.value)}
                placeholder="Objet de l'écriture…"
                className={inputClass}
              />
            </div>
          </div>

          {createError && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {createError}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => setFormOpen(false)}
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
            >
              Annuler
            </button>
            <button
              onClick={handleSubmit}
              disabled={!canSubmit || creating}
              className="rounded-lg bg-navy-600 hover:bg-navy-700 px-4 py-2 text-sm font-medium text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {creating ? 'Enregistrement…' : 'Enregistrer'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Nouveau transfert */}
      <Modal open={transferOpen} onClose={() => !transferSubmitting && setTransferOpen(false)} title="Nouveau transfert entre caisses" width="md">
        <form onSubmit={handleTransferSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Compte source *</label>
              <select value={tFrom} onChange={e => setTFrom(e.target.value)} className="w-full border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white">
                {accountOptions.map(a => (
                  <option key={a.id} value={a.id}>{accountLabelFull(a.id)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Compte destination *</label>
              <select value={tTo} onChange={e => setTTo(e.target.value)} className="w-full border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white">
                {accountOptions.filter(a => a.id !== tFrom).map(a => (
                  <option key={a.id} value={a.id}>{accountLabelFull(a.id)}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Montant (FCFA) *</label>
              <input required type="number" min={1} step="0.01" value={tAmount} onChange={e => setTAmount(e.target.value)} placeholder="0" className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Date</label>
              <input type="datetime-local" value={tOccurredAt} onChange={e => setTOccurredAt(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500 block p-2">Référence</label>
            <input type="text" value={tReference} onChange={e => setTReference(e.target.value)} placeholder="Ex : virement Wave vers Caisse" className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
          </div>
          {transferError && (
            <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{transferError}</p>
          )}
          <div className="flex gap-2 justify-end pt-2">
            <button type="button" onClick={() => setTransferOpen(false)} disabled={transferSubmitting} className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50">Annuler</button>
            <button type="submit" disabled={transferSubmitting} className="px-4 py-2 text-sm bg-navy-800 text-white rounded-lg hover:bg-navy-700 disabled:opacity-50">{transferSubmitting ? 'Transfert…' : 'Transférer'}</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}