import { useState, useMemo } from 'react';
import { formatCFA } from '@/utils/format';
import {
  fetchInsuranceClients, fetchClientContracts, fetchContractPayments,
} from '@/services';
import { useApiQuery } from '@/hooks/useApiQuery';
import type {
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
  const { data: rawClients, loading } = useApiQuery<InsuranceClientOut[]>(fetchInsuranceClients, []);
  const clients = rawClients ?? [];

  const { data: rawContracts } = useApiQuery<InsuranceContractOut[]>(
    async () => {
      const lists = await Promise.all(clients.map(c => fetchClientContracts(c.id)));
      return lists.flat();
    },
    [clients]
  );
  const contracts = rawContracts ?? [];

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
      <div className="grid grid-cols-2 md:grid-cols-4 p-4">
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
    </div>
  );
}