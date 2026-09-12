import { useState, useMemo, useEffect } from 'react';
import type { FormEvent } from 'react';
import { formatCFA } from '@/utils/format';
import {
  fetchInsuranceClients, fetchClientContracts, fetchContractPayments,
  createInsuranceClient, createInsuranceContract, createInsurancePayment,
  fetchAccounts, fetchCategories,
} from '@/services';
import { resolveBusinessId } from '@/services/identity';
import { useApiQuery } from '@/hooks/useApiQuery';
import type {
  AccountOut, CategoryOut,
  InsuranceClientOut, InsuranceContractOut, InsurancePaymentOut, InsuranceContractStatus,
} from '@/types/api';
import Badge from '@/components/ui/Badge';
import Modal from '@/components/ui/Modal';

const statusLabel: Record<InsuranceContractStatus, string> = {
  active: 'Actif',
  expired: 'Expiré',
  cancelled: 'Annulé',
};

const statusVariant: Record<InsuranceContractStatus, 'success' | 'danger' | 'neutral'> = {
  active: 'success',
  expired: 'danger',
  cancelled: 'neutral',
};

type ContractTab = 'contrats' | 'clients';

export default function Assurance() {
  const { data: rawClients, loading, refetch: refetchClients } = useApiQuery<InsuranceClientOut[]>(fetchInsuranceClients, []);
  const clients = rawClients ?? [];

  // Comptes + catégories pour le formulaire paiement
  const [assuranceAccounts, setAssuranceAccounts] = useState<AccountOut[]>([]);
  const { data: categoriesData } = useApiQuery<CategoryOut[]>(fetchCategories, []);
  const categories = categoriesData ?? [];

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const bizId = await resolveBusinessId('assurance');
        if (!active || !bizId) return;
        const accts = await fetchAccounts(bizId);
        if (active) setAssuranceAccounts(accts);
      } catch { /* retry on form open */ }
    })();
    return () => { active = false; };
  }, []);

  const { data: rawContracts, refetch: refetchContracts } = useApiQuery<InsuranceContractOut[]>(
    async () => {
      const lists = await Promise.all(clients.map(c => fetchClientContracts(c.id)));
      return lists.flat();
    },
    [clients]
  );
  const contracts = rawContracts ?? [];

  // ── Form Nouveau client ──────────────────────────────────────
  const [clientFormOpen, setClientFormOpen] = useState(false);
  const [cFullName, setCFullName] = useState('');
  const [cPhone, setCPhone] = useState('');
  const [cNumber, setCNumber] = useState('');
  const [clientSubmitting, setClientSubmitting] = useState(false);
  const [clientError, setClientError] = useState<string | null>(null);

  function openClientForm() {
    setCFullName(''); setCPhone(''); setCNumber(''); setClientError(null); setClientFormOpen(true);
  }

  async function handleClientSubmit(e: FormEvent) {
    e.preventDefault();
    if (!cFullName.trim()) { setClientError('Le nom est requis.'); return; }
    setClientSubmitting(true); setClientError(null);
    try {
      await createInsuranceClient({ full_name: cFullName.trim(), phone: cPhone.trim() || null, client_number: cNumber.trim() || null });
      setClientFormOpen(false); refetchClients();
    } catch (err) { setClientError(err instanceof Error ? err.message : 'Erreur.'); setClientSubmitting(false); }
  }

  // ── Form Nouveau contrat ─────────────────────────────────────
  const [contractFormOpen, setContractFormOpen] = useState(false);
  const [ctClientId, setCtClientId] = useState('');
  const [ctMatricule, setCtMatricule] = useState('');
  const [ctType, setCtType] = useState('');
  const [ctPremium, setCtPremium] = useState('');
  const [ctStart, setCtStart] = useState('');
  const [ctEnd, setCtEnd] = useState('');
  const [contractSubmitting, setContractSubmitting] = useState(false);
  const [contractError, setContractError] = useState<string | null>(null);

  function openContractForm() {
    setCtClientId(clients[0]?.id ?? ''); setCtMatricule(''); setCtType('');
    setCtPremium(''); setCtStart(new Date().toISOString().slice(0, 10)); setCtEnd('');
    setContractError(null); setContractFormOpen(true);
  }

  async function handleContractSubmit(e: FormEvent) {
    e.preventDefault();
    const premium = Number(ctPremium);
    if (!ctClientId || !ctMatricule.trim() || !ctType.trim() || !Number.isFinite(premium) || premium <= 0 || !ctStart) {
      setContractError('Remplissez client, matricule, type, prime (> 0) et date de début.'); return;
    }
    setContractSubmitting(true); setContractError(null);
    try {
      await createInsuranceContract(ctClientId, {
        matricule: ctMatricule.trim(), contract_type: ctType.trim(), premium,
        start_date: ctStart, end_date: ctEnd || null,
      });
      setContractFormOpen(false); refetchContracts();
    } catch (err) { setContractError(err instanceof Error ? err.message : 'Erreur.'); setContractSubmitting(false); }
  }

  // ── Form Nouveau paiement ────────────────────────────────────
  const [paymentFormOpen, setPaymentFormOpen] = useState(false);
  const [pContractId, setPContractId] = useState('');
  const [pAmount, setPAmount] = useState('');
  const [pPaidAt, setPPaidAt] = useState(new Date().toISOString().slice(0, 10));
  const [pAccountId, setPAccountId] = useState('');
  const [pCategoryId, setPCategoryId] = useState('');
  const [paymentSubmitting, setPaymentSubmitting] = useState(false);
  const [paymentError, setPaymentError] = useState<string | null>(null);

  const creditCategories = categories.filter(c => c.type === 'credit');
  const activeContracts = contracts.filter(c => c.status === 'active');

  function openPaymentForm() {
    setPContractId(selectedContract?.id ?? activeContracts[0]?.id ?? '');
    setPAmount(''); setPPaidAt(new Date().toISOString().slice(0, 10));
    setPAccountId(assuranceAccounts[0]?.id ?? '');
    setPCategoryId(creditCategories[0]?.id ?? '');
    setPaymentError(null); setPaymentFormOpen(true);
  }

  async function handlePaymentSubmit(e: FormEvent) {
    e.preventDefault();
    const amount = Number(pAmount);
    if (!pContractId || !Number.isFinite(amount) || amount <= 0 || !pAccountId || !pCategoryId) {
      setPaymentError('Remplissez montant (> 0), contrat, caisse et catégorie.'); return;
    }
    setPaymentSubmitting(true); setPaymentError(null);
    try {
      await createInsurancePayment(pContractId, { amount, paid_at: pPaidAt || null, account_id: pAccountId, category_id: pCategoryId });
      setPaymentFormOpen(false); refetchContracts();
    } catch (err) { setPaymentError(err instanceof Error ? err.message : 'Erreur.'); setPaymentSubmitting(false); }
  }

  // ── Vue ──────────────────────────────────────────────────────
  const [selectedContract, setSelectedContract] = useState<InsuranceContractOut | null>(null);
  const [selectedClient, setSelectedClient] = useState<InsuranceClientOut | null>(null);
  const [tab, setTab] = useState<ContractTab>('contrats');
  const [filter, setFilter] = useState<'all' | InsuranceContractStatus>('all');

  const { data: payments } = useApiQuery<InsurancePaymentOut[]>(
    () => selectedContract ? fetchContractPayments(selectedContract.id) : Promise.resolve([]),
    [selectedContract?.id]
  );

  const filtered = contracts.filter(c => filter === 'all' || c.status === filter);

  const kpis = useMemo(() => {
    const totalPremium = contracts.reduce((s, c) => s + Number(c.premium), 0);
    const totalRemaining = contracts.reduce((s, c) => s + Number(c.remaining_amount), 0);
    return {
      premium: totalPremium,
      collected: totalPremium - totalRemaining,
      receivables: totalRemaining,
      activeCots: contracts.filter(c => c.status === 'active').length,
    };
  }, [contracts]);

  if (loading) return <div className="p-6 text-center text-slate-400 text-sm">Chargement…</div>;

  return (
    <div className="p-6 max-w-screen-xl mx-auto space-y-6">

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Primes émises", value: kpis.premium, color: 'text-emerald-600', isCount: false },
          { label: 'Encaissé', value: kpis.collected, color: 'text-emerald-600', isCount: false },
          { label: 'Créances clients', value: kpis.receivables, color: 'text-amber-600', isCount: false },
          { label: 'Contrats actifs', value: kpis.activeCots, color: 'text-navy-700', isCount: true },
        ].map(k => (
          <div key={k.label} className="bg-white rounded-lg border border-slate-200 p-4">
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wide p-2">{k.label}</div>
            <div className={`font-financial text-xl font-semibold ${k.color}`}>
              {k.isCount ? k.value : formatCFA(Number(k.value))}
            </div>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 flex-wrap">
        <button onClick={openClientForm} className="p-4 py-1 rounded-full text-xs font-medium bg-navy-800 text-white border border-navy-800 hover:bg-navy-700 transition-all">+ Nouveau client</button>
        <button onClick={openContractForm} className="p-4 py-1 rounded-full text-xs font-medium bg-emerald-600 text-white border border-emerald-600 hover:bg-emerald-500 transition-all">+ Nouveau contrat</button>
        <button onClick={openPaymentForm} className="p-4 py-1 rounded-full text-xs font-medium bg-amber-600 text-white border border-amber-600 hover:bg-amber-500 transition-all">+ Nouveau paiement</button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-slate-200">
        {(['contrats', 'clients'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize transition-colors border-b-2 -mb-px ${
              tab === t
                ? 'border-navy-600 text-navy-700'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {t === 'contrats' ? `Contrats (${contracts.length})` : `Clients (${clients.length})`}
          </button>
        ))}
      </div>

      {tab === 'contrats' && (
        <>
          <div className="flex items-center gap-2 flex-wrap">
            {(['all', 'active', 'expired', 'cancelled'] as const).map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`p-4 py-1 rounded-full text-xs font-medium border transition-all ${
                  filter === f
                    ? 'bg-navy-800 text-white border-navy-800'
                    : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
                }`}
              >
                {f === 'all' ? 'Tous' : statusLabel[f as InsuranceContractStatus]}
              </button>
            ))}
          </div>

          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50">
                  <th className="text-left p-4 text-xs font-semibold text-slate-500 uppercase tracking-wide">Client</th>
                  <th className="text-left p-4 text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">Matricule</th>
                  <th className="text-left p-4 text-xs font-semibold text-slate-500 uppercase tracking-wide hidden lg:table-cell">Type</th>
                  <th className="text-right p-4 text-xs font-semibold text-slate-500 uppercase tracking-wide">Prime</th>
                  <th className="text-right p-4 text-xs font-semibold text-slate-500 uppercase tracking-wide">Reste</th>
                  <th className="text-left p-4 text-xs font-semibold text-slate-500 uppercase tracking-wide hidden xl:table-cell">Début → Fin</th>
                  <th className="text-left p-4 text-xs font-semibold text-slate-500 uppercase tracking-wide">Statut</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(contract => {
                  const c = clients.find(cl => cl.id === contract.client_id);
                  return (
                    <tr
                      key={contract.id}
                      className="border-b border-slate-50 hover:bg-slate-50 cursor-pointer transition-colors"
                      onClick={() => setSelectedContract(contract)}
                    >
                      <td className="p-4 font-medium text-slate-800">{c?.full_name ?? '—'}</td>
                      <td className="p-4 text-slate-600 font-mono text-xs hidden md:table-cell">{contract.matricule}</td>
                      <td className="p-4 text-slate-600 text-xs hidden lg:table-cell">{contract.contract_type}</td>
                      <td className="p-4 text-right font-financial font-medium text-slate-800">{formatCFA(Number(contract.premium))}</td>
                      <td className={`p-4 text-right font-financial font-medium ${Number(contract.remaining_amount) > 0 ? 'text-amber-600' : 'text-slate-400'}`}>
                        {formatCFA(Number(contract.remaining_amount))}
                      </td>
                      <td className="p-4 text-slate-500 text-xs hidden xl:table-cell">
                        {contract.start_date} → {contract.end_date ?? '—'}
                      </td>
                      <td className="p-4">
                        <Badge variant={statusVariant[contract.status]}>{statusLabel[contract.status]}</Badge>
                      </td>
                    </tr>
                  );
                })}
                {filtered.length === 0 && (
                  <tr><td colSpan={7} className="p-12 text-center text-slate-400 text-sm">Aucun contrat</td></tr>
                )}
              </tbody>
            </table>
            </div>
          </div>
        </>
      )}

      {tab === 'clients' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {clients.map(c => {
            const clientCots = contracts.filter(ct => ct.client_id === c.id);
            const totalPremium = clientCots.reduce((s, ct) => s + Number(ct.premium), 0);
            const totalRemaining = clientCots.reduce((s, ct) => s + Number(ct.remaining_amount), 0);
            return (
              <button
                key={c.id}
                onClick={() => setSelectedClient(c)}
                className="text-left bg-white rounded-xl border border-slate-200 p-6 hover:border-navy-300 hover:shadow-sm transition-all"
              >
                <div className="flex items-start justify-between p-4">
                  <div>
                    <div className="font-semibold text-slate-800">{c.full_name}</div>
                    <div className="text-xs text-slate-500 mt-1">{c.phone ?? '—'}</div>
                  </div>
                  <span className="text-xs bg-slate-100 text-slate-600 rounded px-2 mt-1">
                    {clientCots.length} contrat{clientCots.length > 1 ? 's' : ''}
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="font-mono text-xs bg-slate-100 text-slate-500 rounded p-2 mt-1">{c.client_number}</span>
                </div>
                <div className="flex justify-between border-t border-slate-100 p-4">
                  <div>
                    <div className="text-xs text-slate-400">Total primes</div>
                    <div className="font-financial text-xs font-medium text-slate-700">{formatCFA(totalPremium)}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-slate-400">Reste à payer</div>
                    <div className={`font-financial text-xs font-medium ${totalRemaining > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>
                      {formatCFA(totalRemaining)}
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
          {clients.length === 0 && (
            <div className="col-span-full text-center py-12 text-slate-400 text-sm">Aucun client</div>
          )}
        </div>
      )}

      {/* Contract detail modal */}
      <Modal
        open={!!selectedContract}
        onClose={() => setSelectedContract(null)}
        title="Détail du contrat"
        width="lg"
      >
        {selectedContract && (() => {
          const c = clients.find(cl => cl.id === selectedContract.client_id);
          const paid = Number(selectedContract.premium) - Number(selectedContract.remaining_amount);
          const reste = Number(selectedContract.remaining_amount);
          const contractPayments = payments ?? [];
          return (
            <div className="p-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-slate-500 mt-1">Client</div>
                  <div className="font-semibold text-slate-800">{c?.full_name ?? '—'}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mt-1">Matricule</div>
                  <div className="font-mono font-medium text-slate-800">{selectedContract.matricule}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mt-1">Type</div>
                  <div className="text-slate-700">{selectedContract.contract_type}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mt-1">Statut</div>
                  <Badge variant={statusVariant[selectedContract.status]}>{statusLabel[selectedContract.status]}</Badge>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mt-1">Début</div>
                  <div className="text-slate-700">{selectedContract.start_date}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mt-1">Fin</div>
                  <div className="text-slate-700">{selectedContract.end_date ?? '—'}</div>
                </div>
              </div>

              <div className="bg-slate-50 rounded-lg p-4">
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Prime totale</div>
                    <div className="font-financial text-lg font-bold text-slate-800">{formatCFA(Number(selectedContract.premium))}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Payé</div>
                    <div className="font-financial text-lg font-bold text-emerald-600">{formatCFA(paid)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Reste</div>
                    <div className={`font-financial text-lg font-bold ${reste > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>
                      {formatCFA(reste)}
                    </div>
                  </div>
                </div>
                <div className="p-4">
                  <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-emerald-500 rounded-full transition-all"
                      style={{ width: `${Math.min(100, (paid / Number(selectedContract.premium)) * 100)}%` }}
                    />
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    {Math.round((paid / Number(selectedContract.premium)) * 100)}% payé
                  </div>
                </div>
              </div>

              <div>
                <div className="text-sm font-semibold text-slate-700 p-4">Historique des paiements</div>
                {contractPayments.length === 0 ? (
                  <div className="text-sm text-slate-400 text-center py-4">Aucun paiement enregistré</div>
                ) : (
                  <div className="space-y-2">
                    {contractPayments.map(p => (
                      <div key={p.id} className="flex justify-between items-center py-2 border-b border-slate-100">
                        <div className="text-sm text-slate-700">{new Date(p.paid_at).toLocaleString('fr-FR')}</div>
                        <div className="font-financial font-semibold text-emerald-600">{formatCFA(Number(p.amount))}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })()}
      </Modal>

      {/* Client detail modal */}
      <Modal
        open={!!selectedClient}
        onClose={() => setSelectedClient(null)}
        title={selectedClient?.full_name ?? ''}
        width="md"
      >
        {selectedClient && (() => {
          const clientCots = contracts.filter(ct => ct.client_id === selectedClient.id);
          return (
            <div className="p-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-slate-500 mt-1">Téléphone</div>
                  <div className="text-slate-700">{selectedClient.phone ?? '—'}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mt-1">N° client</div>
                  <div className="text-slate-700 font-mono">{selectedClient.client_number}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mt-1">Statut</div>
                  <span className={`text-xs font-semibold uppercase tracking-wide rounded-full px-2 mt-1 ${
                    selectedClient.status === 'active' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'
                  }`}>
                    {selectedClient.status}
                  </span>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mt-1">Contrats</div>
                  <div className="text-slate-700">{clientCots.length}</div>
                </div>
              </div>

              <div className="space-y-2">
                {clientCots.map(ct => (
                  <div key={ct.id} className="border border-slate-200 rounded-lg p-4 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge variant={statusVariant[ct.status]}>{statusLabel[ct.status]}</Badge>
                      <span className="text-sm text-slate-700">{ct.matricule}</span>
                    </div>
                    <div className="text-right">
                      <div className="font-financial text-sm font-bold text-slate-800">{formatCFA(Number(ct.premium))}</div>
                      <div className="text-xs text-slate-500">Reste : {formatCFA(Number(ct.remaining_amount))}</div>
                    </div>
                  </div>
                ))}
                {clientCots.length === 0 && (
                  <div className="text-sm text-slate-400 text-center py-4">Aucun contrat</div>
                )}
              </div>
            </div>
          );
        })()}
      </Modal>

      {/* Form Nouveau client */}
      <Modal open={clientFormOpen} onClose={() => !clientSubmitting && setClientFormOpen(false)} title="Nouveau client assurance" width="md">
        <form onSubmit={handleClientSubmit} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-slate-500 block p-2">Nom complet *</label>
            <input required value={cFullName} onChange={e => setCFullName(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Téléphone</label>
              <input value={cPhone} onChange={e => setCPhone(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">N° client</label>
              <input value={cNumber} onChange={e => setCNumber(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
          </div>
          {clientError && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{clientError}</p>}
          <div className="flex gap-2 justify-end pt-2">
            <button type="button" onClick={() => setClientFormOpen(false)} disabled={clientSubmitting} className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50">Annuler</button>
            <button type="submit" disabled={clientSubmitting} className="px-4 py-2 text-sm bg-navy-800 text-white rounded-lg hover:bg-navy-700 disabled:opacity-50">{clientSubmitting ? 'Création…' : 'Créer'}</button>
          </div>
        </form>
      </Modal>

      {/* Form Nouveau contrat */}
      <Modal open={contractFormOpen} onClose={() => !contractSubmitting && setContractFormOpen(false)} title="Nouveau contrat assurance" width="md">
        <form onSubmit={handleContractSubmit} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-slate-500 block p-2">Client *</label>
            <select value={ctClientId} onChange={e => setCtClientId(e.target.value)} className="w-full border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white">
              {clients.map(c => <option key={c.id} value={c.id}>{c.full_name}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Matricule *</label>
              <input required value={ctMatricule} onChange={e => setCtMatricule(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Type de contrat *</label>
              <input required value={ctType} onChange={e => setCtType(e.target.value)} placeholder="RC Auto, Tous risques…" className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Prime (FCFA) *</label>
              <input required type="number" min={1} value={ctPremium} onChange={e => setCtPremium(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Début *</label>
              <input required type="date" value={ctStart} onChange={e => setCtStart(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Fin</label>
              <input type="date" value={ctEnd} onChange={e => setCtEnd(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
          </div>
          {contractError && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{contractError}</p>}
          <div className="flex gap-2 justify-end pt-2">
            <button type="button" onClick={() => setContractFormOpen(false)} disabled={contractSubmitting} className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50">Annuler</button>
            <button type="submit" disabled={contractSubmitting} className="px-4 py-2 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-500 disabled:opacity-50">{contractSubmitting ? 'Création…' : 'Créer'}</button>
          </div>
        </form>
      </Modal>

      {/* Form Nouveau paiement */}
      <Modal open={paymentFormOpen} onClose={() => !paymentSubmitting && setPaymentFormOpen(false)} title="Enregistrer un paiement" width="md">
        <form onSubmit={handlePaymentSubmit} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-slate-500 block p-2">Contrat *</label>
            <select value={pContractId} onChange={e => setPContractId(e.target.value)} className="w-full border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white">
              {activeContracts.map(ct => {
                const cl = clients.find(c => c.id === ct.client_id);
                return <option key={ct.id} value={ct.id}>{cl?.full_name ?? '—'} — {ct.matricule}</option>;
              })}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Montant (FCFA) *</label>
              <input required type="number" min={1} value={pAmount} onChange={e => setPAmount(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Date</label>
              <input type="date" value={pPaidAt} onChange={e => setPPaidAt(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Caisse *</label>
              <select value={pAccountId} onChange={e => setPAccountId(e.target.value)} className="w-full border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white">
                {assuranceAccounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Catégorie *</label>
              <select value={pCategoryId} onChange={e => setPCategoryId(e.target.value)} className="w-full border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white">
                {creditCategories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
          </div>
          {paymentError && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{paymentError}</p>}
          <div className="flex gap-2 justify-end pt-2">
            <button type="button" onClick={() => setPaymentFormOpen(false)} disabled={paymentSubmitting} className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50">Annuler</button>
            <button type="submit" disabled={paymentSubmitting} className="px-4 py-2 text-sm bg-amber-600 text-white rounded-lg hover:bg-amber-500 disabled:opacity-50">{paymentSubmitting ? 'Enregistrement…' : 'Enregistrer'}</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}