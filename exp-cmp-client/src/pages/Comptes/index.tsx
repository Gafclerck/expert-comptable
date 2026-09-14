import { useState, useEffect } from 'react';
import type { FormEvent } from 'react';
import { formatCFA } from '@/utils/format';
import { createAccount, fetchAccountsForDashboard } from '@/services';
import type { AccountRow } from '@/services';
import { getCachedBusinesses } from '@/services/identity';
import type { AccountType } from '@/types/api';
import { useApiQuery } from '@/hooks/useApiQuery';
import { useAuth } from '@/contexts/AuthContext';
import Modal from '@/components/ui/Modal';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

const accountIcons: Record<string, string> = {
  caisse: '💵',
  wave: '📱',
  orange_money: '🟠',
  banque: '🏦',
};

const ACCOUNT_COLORS = ['var(--color-primary)', 'var(--color-success)', 'var(--color-warning)', 'var(--color-primary)'];

export default function Comptes() {
  const { data: accountsData, loading, refetch } = useApiQuery<AccountRow[]>(fetchAccountsForDashboard, []);
  const accounts = accountsData ?? [];
  const totalBalance = accounts.reduce((s, a) => s + a.balance, 0);

  const { isRoot } = useAuth();
  const businesses = getCachedBusinesses();

  // ── Form Nouveau compte (RequireRoot) ────────────────────────
  const [accountFormOpen, setAccountFormOpen] = useState(false);
  const [aBusiness, setABusiness] = useState('');
  const [aName, setAName] = useState('');
  const [aType, setAType] = useState<AccountType>('cash');
  const [aCurrency, setACurrency] = useState('FCFA');
  const [aOpening, setAOpening] = useState('');
  const [accountSubmitting, setAccountSubmitting] = useState(false);
  const [accountError, setAccountError] = useState<string | null>(null);

  const ACCOUNT_TYPE_OPTIONS: Array<{ id: AccountType; label: string }> = [
    { id: 'cash', label: 'Caisse' },
    { id: 'bank', label: 'Banque' },
    { id: 'mobile_money', label: 'Mobile Money' },
    { id: 'other', label: 'Autre' },
  ];

  function openAccountForm() {
    setABusiness(businesses[0]?.id ?? '');
    setAName(''); setAType('cash'); setACurrency('FCFA'); setAOpening('');
    setAccountError(null); setAccountFormOpen(true);
  }

  async function handleAccountSubmit(e: FormEvent) {
    e.preventDefault();
    const opening = Number(aOpening) || 0;
    if (!aBusiness || !aName.trim() || !Number.isFinite(opening) || opening < 0) {
      setAccountError("Remplissez le nom, l'activité et un solde initial valide.");
      return;
    }
    setAccountSubmitting(true); setAccountError(null);
    try {
      await createAccount({
        business_id: aBusiness,
        name: aName.trim(),
        type: aType,
        currency: aCurrency.trim() || 'FCFA',
        opening_balance: opening,
      });
      setAccountFormOpen(false); refetch();
    } catch (err) { setAccountError(err instanceof Error ? err.message : 'Erreur.'); setAccountSubmitting(false); }
  }

  const [activeAccount, setActiveAccount] = useState<string | null>(null);

  useEffect(() => {
    if (accountsData && accountsData.length > 0 && activeAccount === null) {
      setActiveAccount(accountsData[0].id);
    }
  }, [accountsData, activeAccount]);

  const account = accounts.find(a => a.id === activeAccount) ?? accounts[0] ?? null;

  const globalPieData = accounts.map(a => ({
    name: a.label,
    value: a.balance,
  }));

  return (
    <div className="p-6 max-w-screen-xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between px-4 pt-2 pb-2">
        <h1 className="text-xl font-semibold text-slate-800">Comptes</h1>
        {isRoot && (
          <button
            onClick={openAccountForm}
            className="bg-navy-600 hover:bg-navy-700 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
          >
            Nouveau compte
          </button>
        )}
      </div>

      {/* Total */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Trésorerie totale</div>
        {loading ? (
          <div className="h-10 w-48 bg-slate-100 rounded animate-pulse" />
        ) : (
          <div className="font-financial text-4xl font-bold text-slate-800 tracking-tight">{formatCFA(totalBalance)}</div>
        )}
        <div className="text-xs text-slate-400 mt-1">Tous comptes · toutes activités</div>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 p-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 bg-slate-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : accounts.length === 0 ? (
        <div className="text-center py-12 text-slate-400 text-sm">Aucun compte trouvé</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Account selector */}
          <div className="lg:col-span-2 space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 p-4">
              {accounts.map(acc => (
                <button
                  key={acc.id}
                  onClick={() => setActiveAccount(acc.id)}
                  className={`p-4 rounded-xl border text-left transition-all ${activeAccount === acc.id
                    ? 'border-navy-400 bg-navy-50 shadow-sm rounded-xl'
                    : 'border-slate-200 bg-white hover:border-slate-400'
                    }`}
                >
                  <div className="text-xl mb-2">{accountIcons[acc.type] ?? '💰'}</div>
                  <div className="text-xs text-slate-500 font-medium mb-1">{acc.label}</div>
                  <div className="font-financial text-base font-bold text-slate-900">{formatCFA(acc.balance)}</div>
                  <div className="text-xs text-slate-400 mt-1">
                    {totalBalance > 0 ? Math.round((acc.balance / totalBalance) * 100) : 0}% du total
                  </div>
                </button>
              ))}
            </div>

            {/* Simplified account detail — no byActivity breakdown */}
            {account && (
              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-xl">{accountIcons[account.type] ?? '💰'}</span>
                  <div>
                    <div className="font-semibold text-slate-800">{account.label}</div>
                    <div className="font-financial text-lg font-bold text-navy-800">{formatCFA(account.balance)}</div>
                  </div>
                </div>
                <div className="text-xs text-slate-400">
                  {totalBalance > 0
                    ? `${((account.balance / totalBalance) * 100).toFixed(1)}% de la trésorerie totale`
                    : 'Aucune donnée de ventilation par activité disponible'}
                </div>
              </div>
            )}

            {/* Simplified accounts table — totals only */}
            <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
              <div className="p-4 border-b border-slate-100">
                <div className="text-sm font-semibold text-slate-700">Soldes par compte</div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-100">
                      <th className="text-left py-2 px-4 text-xs font-semibold text-slate-500">Compte</th>
                      <th className="text-right py-2 px-4 text-xs font-semibold text-slate-500">Part</th>
                      <th className="text-right py-2 px-4 text-xs font-semibold text-slate-600">Solde</th>
                    </tr>
                  </thead>
                  <tbody>
                    {accounts.map(acc => (
                      <tr key={acc.id} className="border-b border-slate-50 hover:bg-slate-50">
                        <td className="p-4">
                          <div className="flex items-center gap-2">
                            <span>{accountIcons[acc.type] ?? '💰'}</span>
                            <span className="text-slate-700 font-medium">{acc.label}</span>
                          </div>
                        </td>
                        <td className="p-4 text-right text-xs text-slate-400">
                          {totalBalance > 0 ? Math.round((acc.balance / totalBalance) * 100) : 0}%
                        </td>
                        <td className="p-4 text-right font-financial text-sm font-semibold text-slate-900">{formatCFA(acc.balance)}</td>
                      </tr>
                    ))}
                    <tr className="bg-slate-50 font-semibold">
                      <td className="p-4 text-xs text-slate-600 font-bold uppercase">Total</td>
                      <td className="p-4 text-right text-xs text-slate-400">100%</td>
                      <td className="p-4 text-right font-financial text-base font-bold text-navy-800">{formatCFA(totalBalance)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Global distribution chart */}
          <div className="space-y-4">
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <div className="text-sm font-semibold text-slate-700 p-4">Répartition globale</div>
              {globalPieData.length > 0 ? (
                <>
                  <ResponsiveContainer width="100%" height={180}>
                    <PieChart>
                      <Pie data={globalPieData} cx="50%" cy="50%" innerRadius={50} outerRadius={75} paddingAngle={3} dataKey="value">
                        {globalPieData.map((_, i) => (
                          <Cell key={i} fill={ACCOUNT_COLORS[i % ACCOUNT_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip
                        formatter={(v: unknown) => [formatCFA((v as number) ?? 0), '']}
                        contentStyle={{ fontSize: 12, borderRadius: 8 }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="p-2 mt-2">
                    {accounts.map((acc, i) => (
                      <div key={acc.id} className="flex items-center gap-2 text-xs text-slate-600">
                        <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ backgroundColor: ACCOUNT_COLORS[i % ACCOUNT_COLORS.length] }} />
                        <span className="flex-1">{acc.label}</span>
                        <span className="font-financial">{totalBalance > 0 ? Math.round((acc.balance / totalBalance) * 100) : 0}%</span>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="text-center py-8 text-slate-400 text-xs">Aucune donnée</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Form Nouveau compte */}
      <Modal open={accountFormOpen} onClose={() => !accountSubmitting && setAccountFormOpen(false)} title="Nouveau compte" width="md">
        <form onSubmit={handleAccountSubmit} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-slate-500 block p-2">Activité *</label>
            <select value={aBusiness} onChange={e => setABusiness(e.target.value)} className="w-full border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white">
              {businesses.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500 block p-2">Nom du compte *</label>
            <input required value={aName} onChange={e => setAName(e.target.value)} placeholder="Caisse Principale, Compte Wave…" className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Type *</label>
              <select value={aType} onChange={e => setAType(e.target.value as AccountType)} className="w-full border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white">
                {ACCOUNT_TYPE_OPTIONS.map(o => <option key={o.id} value={o.id}>{o.label}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Devise</label>
              <input value={aCurrency} onChange={e => setACurrency(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500 block p-2">Solde initial (FCFA)</label>
            <input type="number" min={0} step="0.01" value={aOpening} onChange={e => setAOpening(e.target.value)} placeholder="0" className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
          </div>
          {accountError && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{accountError}</p>}
          <div className="flex gap-2 justify-end pt-2">
            <button type="button" onClick={() => setAccountFormOpen(false)} disabled={accountSubmitting} className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50">Annuler</button>
            <button type="submit" disabled={accountSubmitting} className="px-4 py-2 text-sm bg-navy-800 text-white rounded-lg hover:bg-navy-700 disabled:opacity-50">{accountSubmitting ? 'Création…' : 'Créer'}</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
