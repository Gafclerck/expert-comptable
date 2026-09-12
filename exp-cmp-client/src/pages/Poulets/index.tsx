import { useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { formatCFA } from '@/utils/format';
import {
  createPoultryPurchase,
  createPoultrySale,
  fetchAccounts,
} from '@/services';
import { fetchCategories } from '@/services/ledger';
import { resolveBusinessId } from '@/services/identity';
import { useApiQuery } from '@/hooks/useApiQuery';
import { usePoultryData } from '@/hooks/usePoultry';
import type { AccountOut, CategoryOut, PoultryLotOut, PoultryPurchaseOut } from '@/types/api';
import Badge from '@/components/ui/Badge';
import Modal from '@/components/ui/Modal';

type Filter = 'all' | 'active' | 'closed';
type FormMode = 'achat' | 'vente';

export default function Poulets() {
  const { lots, purchases, sales, stock, loading, error, refetch } = usePoultryData();

  // Comptes de l'activité poulets + catégories pour les formulaires d'achat/vente.
  const [pouletsAccounts, setPouletsAccounts] = useState<AccountOut[]>([]);
  const { data: categoriesData } = useApiQuery<CategoryOut[]>(fetchCategories, []);
  const categories = categoriesData ?? [];

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const businessId = await resolveBusinessId('poulets');
        if (!active || !businessId) return;
        const accounts = await fetchAccounts(businessId);
        if (active) setPouletsAccounts(accounts);
      } catch {
        // Laisser le formulaire se réessayer à l'ouverture.
      }
    })();
    return () => { active = false; };
  }, []);

  const purchaseByLotId = useMemo(() => {
    const map = new Map<string, PoultryPurchaseOut>();
    purchases.forEach((p) => map.set(p.lot_id, p));
    return map;
  }, [purchases]);

  const kpis = useMemo(() => {
    const revenue = sales.reduce((s, v) => s + v.quantity * Number(v.unit_price), 0);
    const expenses = purchases.reduce((s, a) => s + a.quantity * Number(a.unit_price), 0);
    return { revenue, expenses, result: revenue - expenses, stock };
  }, [sales, purchases, stock]);

  const [selectedLot, setSelectedLot] = useState<PoultryLotOut | null>(null);
  const [filter, setFilter] = useState<Filter>('all');

  // Formulaire achat/vente.
  const [formOpen, setFormOpen] = useState(false);
  const [formMode, setFormMode] = useState<FormMode>('achat');
  const [quantity, setQuantity] = useState('');
  const [unitPrice, setUnitPrice] = useState('');
  const [note, setNote] = useState('');
  const [accountId, setAccountId] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  function openForm(mode: FormMode) {
    const ctype = mode === 'achat' ? 'debit' : 'credit';
    const candidates = categories.filter((c) => c.type === ctype);
    setFormMode(mode);
    setQuantity('');
    setUnitPrice('');
    setNote('');
    setAccountId(pouletsAccounts[0]?.id ?? '');
    setCategoryId(candidates[0]?.id ?? '');
    setSubmitError(null);
    setFormOpen(true);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const qty = Number(quantity);
    const price = Number(unitPrice);
    if (!Number.isInteger(qty) || qty <= 0 || !Number.isFinite(price) || price <= 0) {
      setSubmitError('Vérifiez la quantité (nombre entier > 0) et le prix unitaire (> 0).');
      return;
    }
    if (!accountId || !categoryId) {
      setSubmitError('Caisse ou catégorie manquante.');
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    try {
      if (formMode === 'achat') {
        await createPoultryPurchase({
          quantity: qty,
          unit_price: price,
          note: note.trim() || null,
          account_id: accountId,
          category_id: categoryId,
        });
      } else {
        await createPoultrySale({
          quantity: qty,
          unit_price: price,
          account_id: accountId,
          category_id: categoryId,
        });
      }
      setFormOpen(false);
      refetch();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Enregistrement impossible.');
      setSubmitting(false);
    }
  }

  const filtered = lots.filter((l) => {
    if (filter === 'active') return l.remaining_quantity > 0;
    if (filter === 'closed') return l.remaining_quantity === 0;
    return true;
  });

  if (loading) {
    return <div className="p-6 text-center text-slate-400 text-sm">Chargement…</div>;
  }

  return (
    <div className="p-6 max-w-screen-xl mx-auto space-y-6">

      {/* Banner d'erreur éventuelle de l'API */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-4">{error}</div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Chiffre d'affaires", value: kpis.revenue, color: 'text-emerald-600' },
          { label: 'Dépenses (achats)', value: kpis.expenses, color: 'text-red-600' },
          { label: 'Résultat net', value: kpis.result, color: kpis.result >= 0 ? 'text-emerald-600' : 'text-red-600' },
          { label: 'Stock actuel', value: kpis.stock, color: 'text-slate-800', unit: 'poulets' },
        ].map((k) => (
          <div key={k.label} className="bg-white rounded-lg border border-slate-200 p-4">
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wide p-2">{k.label}</div>
            <div className={`font-financial text-xl font-semibold ${k.color}`}>
              {"unit" in k ? `${k.value} ${k.unit}` : formatCFA(k.value as number)}
            </div>
          </div>
        ))}
      </div>

      {/* Actions + filtre */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => openForm('achat')}
          className="p-4 py-1 rounded-full text-xs font-medium bg-navy-800 text-white border border-navy-800 hover:bg-navy-700 transition-all"
        >
          + Enregistrer un achat
        </button>
        <button
          onClick={() => openForm('vente')}
          className="p-4 py-1 rounded-full text-xs font-medium bg-emerald-600 text-white border border-emerald-600 hover:bg-emerald-500 transition-all"
        >
          + Enregistrer une vente
        </button>

        <div className="flex items-center gap-2 ml-auto">
          {(['all', 'active', 'closed'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`p-4 py-1 rounded-full text-xs font-medium border transition-all ${
                filter === f
                  ? 'bg-navy-800 text-white border-navy-800'
                  : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
              }`}
            >
              {f === 'all' ? 'Tous les lots' : f === 'active' ? 'En cours' : 'Clôturés'}
            </button>
          ))}
        </div>
      </div>

      {/* Lots grid */}
      {filtered.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-400 text-sm">
          Aucun lot. Enregistrez un premier achat de poulets.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {filtered.map((lot, i) => {
            const purchase = purchaseByLotId.get(lot.id);
            const cost = lot.initial_quantity * Number(lot.unit_purchase_price);
            const sold = lot.initial_quantity - lot.remaining_quantity;
            return (
              <button
                key={lot.id}
                onClick={() => setSelectedLot(lot)}
                className="text-left bg-white rounded-xl border border-slate-200 p-6 hover:border-amber-300 hover:shadow-sm transition-all group"
              >
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="font-mono text-sm font-bold text-navy-800">Lot #{i + 1}</div>
                    <div className="text-xs text-slate-500 mt-1">
                      {new Date(lot.created_at).toLocaleDateString('fr-FR')} · {lot.initial_quantity} poulets achetés
                    </div>
                  </div>
                  <Badge variant={lot.remaining_quantity > 0 ? 'warning' : 'neutral'}>
                    {lot.remaining_quantity > 0 ? 'En cours' : 'Clôturé'}
                  </Badge>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <div className="text-xs text-slate-400 mt-1">Coût total</div>
                    <div className="font-financial text-sm font-semibold text-slate-800">{formatCFA(cost)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-400 mt-1">Vendus</div>
                    <div className={`font-financial text-sm font-semibold ${sold > 0 ? 'text-emerald-600' : 'text-slate-400'}`}>
                      {sold} / {lot.initial_quantity}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-400 mt-1">Restant</div>
                    <div className={`font-financial text-sm font-semibold ${lot.remaining_quantity > 0 ? 'text-amber-600' : 'text-slate-400'}`}>
                      {lot.remaining_quantity} poulet{lot.remaining_quantity > 1 ? 's' : ''}
                    </div>
                  </div>
                </div>

                {purchase?.note && (
                  <div className="text-xs text-slate-500 bg-slate-50 rounded p-2 border border-slate-100">{purchase.note}</div>
                )}

                <div className="text-xs text-slate-500 p-4 group-hover:text-slate-700 transition-colors">Voir le détail →</div>
              </button>
            );
          })}
        </div>
      )}

      {/* Lot detail modal */}
      <Modal
        open={!!selectedLot}
        onClose={() => setSelectedLot(null)}
        title="Détail du lot"
        width="md"
      >
        {selectedLot && (() => {
          const lot = selectedLot;
          const purchase = purchaseByLotId.get(lot.id);
          const cost = lot.initial_quantity * Number(lot.unit_purchase_price);
          const sold = lot.initial_quantity - lot.remaining_quantity;
          return (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-slate-500 mt-1">Date d'achat</div>
                  <div className="text-slate-800">{new Date(lot.created_at).toLocaleString('fr-FR')}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mt-1">Référence</div>
                  <div className="font-mono text-xs text-slate-700">{lot.id.slice(0, 8)}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mt-1">Quantité achetée</div>
                  <div className="text-slate-800">{lot.initial_quantity} poulets</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mt-1">Prix unitaire</div>
                  <div className="font-financial text-slate-800">{formatCFA(Number(lot.unit_purchase_price))}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mt-1">Coût total</div>
                  <div className="font-financial font-semibold text-slate-800">{formatCFA(cost)}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mt-1">Statut</div>
                  <Badge variant={lot.remaining_quantity > 0 ? 'warning' : 'neutral'}>
                    {lot.remaining_quantity > 0 ? 'En cours' : 'Clôturé'}
                  </Badge>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mt-1">Vendus</div>
                  <div className="font-financial text-emerald-600">{sold} poulets</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mt-1">Restant en stock</div>
                  <div className="font-financial text-slate-800">{lot.remaining_quantity} poulets</div>
                </div>
              </div>

              {purchase && (
                <div className="bg-slate-50 rounded-lg p-4 text-xs text-slate-600 space-y-1">
                  <div>Achat <span className="font-mono">{purchase.id.slice(0, 8)}</span> · transaction <span className="font-mono">{purchase.transaction_id.slice(0, 8)}</span></div>
                  {purchase.note && <div>Note : {purchase.note}</div>}
                </div>
              )}
            </div>
          );
        })()}
      </Modal>

      {/* Achat / vente form modal */}
      <Modal
        open={formOpen}
        onClose={() => !submitting && setFormOpen(false)}
        title={formMode === 'achat' ? 'Enregistrer un achat de poulets' : 'Enregistrer une vente de poulets'}
        width="md"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Quantité</label>
              <input
                type="number"
                min={1}
                step={1}
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                placeholder="24"
                className="w-full border border-slate-200 rounded p-2 text-sm text-slate-700 placeholder-slate-400 outline-none focus:border-navy-400"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Prix unitaire (FCFA)</label>
              <input
                type="number"
                min={0}
                step={1}
                value={unitPrice}
                onChange={(e) => setUnitPrice(e.target.value)}
                placeholder="2500"
                className="w-full border border-slate-200 rounded p-2 text-sm text-slate-700 placeholder-slate-400 outline-none focus:border-navy-400"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Caisse</label>
              <select
                value={accountId}
                onChange={(e) => setAccountId(e.target.value)}
                className="w-full border border-slate-200 rounded p-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white"
              >
                {pouletsAccounts.map((a) => (
                  <option key={a.id} value={a.id}>{a.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Catégorie</label>
              <select
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
                className="w-full border border-slate-200 rounded p-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white"
              >
                {categories
                  .filter((c) => c.type === (formMode === 'achat' ? 'debit' : 'credit'))
                  .map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
              </select>
            </div>
            {formMode === 'achat' && (
              <div className="col-span-2">
                <label className="block text-xs font-medium text-slate-500 mb-1">Note (optionnel)</label>
                <input
                  type="text"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Provenance, fournisseur…"
                  className="w-full border border-slate-200 rounded p-2 text-sm text-slate-700 placeholder-slate-400 outline-none focus:border-navy-400"
                />
              </div>
            )}
          </div>

          {submitError && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">{submitError}</div>
          )}

          <div className="flex items-center gap-2 pt-2">
            <button
              type="submit"
              disabled={submitting}
              className={`p-4 py-1 rounded-full text-xs font-medium text-white transition-all ${
                formMode === 'achat' ? 'bg-navy-800 border border-navy-800 hover:bg-navy-700' : 'bg-emerald-600 border border-emerald-600 hover:bg-emerald-500'
              } disabled:opacity-50`}
            >
              {submitting ? 'Enregistrement…' : 'Enregistrer'}
            </button>
            <button
              type="button"
              onClick={() => setFormOpen(false)}
              disabled={submitting}
              className="p-4 py-1 rounded-full text-xs font-medium bg-white text-slate-600 border border-slate-200 hover:border-slate-300 disabled:opacity-50"
            >
              Annuler
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}