import { useState } from 'react';
import { formatCFA } from '@/utils/format';
import {
  fetchVtcAffectations, fetchVtcChauffeurs, fetchVtcResumeFinancier,
  fetchVtcStatutPaiement, fetchVtcVehiculeStats, fetchVtcVehicules, fetchVtcVersements,
} from '@/services';
import { useApiQuery } from '@/hooks/useApiQuery';
import type {
  ChauffeurOut, ChauffeurStatus, ResumeFinancierOut, StatistiquesVehiculeOut,
  StatutPaiementOut, VehiculeOut, VehiculeStatus, VersementOut,
} from '@/types/api';
import Badge from '@/components/ui/Badge';
import Modal from '@/components/ui/Modal';

const vehiculeStatusLabel: Record<VehiculeStatus, { label: string; variant: 'success' | 'warning' | 'neutral' }> = {
  active: { label: 'Actif', variant: 'success' },
  out_of_service: { label: 'Hors service', variant: 'warning' },
  sold: { label: 'Vendu', variant: 'neutral' },
};

const chauffeurStatusLabel: Record<ChauffeurStatus, { label: string; variant: 'success' | 'neutral' }> = {
  active: { label: 'Actif', variant: 'success' },
  inactive: { label: 'Inactif', variant: 'neutral' },
};

const typeDepenseLabel: Record<string, string> = {
  fuel: 'Carburant', maintenance: 'Entretien', repair: 'Réparation', tires: 'Pneus',
  insurance: 'Assurance', registration: 'Immatriculation', misc: 'Divers',
};

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <div className="text-xs font-medium text-slate-500 uppercase tracking-wide p-2">{label}</div>
      <div className={`font-financial text-xl font-semibold ${color}`}>{formatCFA(value)}</div>
    </div>
  );
}

export default function VTC() {
  const { data: resume, loading: loadingResume } = useApiQuery<ResumeFinancierOut>(() => fetchVtcResumeFinancier(), []);
  const { data: rawVehicles, loading: loadingVehicles } = useApiQuery<VehiculeOut[]>(() => fetchVtcVehicules(), []);
  const { data: rawDrivers, loading: loadingDrivers } = useApiQuery<ChauffeurOut[]>(() => fetchVtcChauffeurs(), []);
  const { data: rawAffectations, loading: loadingAffectations } = useApiQuery(() => fetchVtcAffectations({ status: 'active' }), []);

  const [selectedVehicle, setSelectedVehicle] = useState<VehiculeOut | null>(null);
  const [vehicleStats, setVehicleStats] = useState<StatistiquesVehiculeOut | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);

  const [selectedDriver, setSelectedDriver] = useState<ChauffeurOut | null>(null);
  const [driverPaiement, setDriverPaiement] = useState<StatutPaiementOut | null>(null);
  const [driverVersements, setDriverVersements] = useState<VersementOut[]>([]);
  const [driverLoading, setDriverLoading] = useState(false);

  const [tab, setTab] = useState<'vehicules' | 'chauffeurs'>('vehicules');

  const vehicles = rawVehicles ?? [];
  const drivers = rawDrivers ?? [];
  const affectations = rawAffectations ?? [];

  const totals = resume?.totals ?? { versements: 0, depenses: 0, net: 0 };
  const pendingPayments = affectations.reduce((s, a) => s + a.remaining_amount, 0);

  const perVehicle = new Map((resume?.per_vehicle ?? []).map(v => [v.vehicle_id, v]));

  function openVehicle(vehicle: VehiculeOut) {
    setSelectedVehicle(vehicle);
    setVehicleStats(null);
    setStatsLoading(true);
    fetchVtcVehiculeStats(vehicle.id)
      .then(setVehicleStats)
      .catch(() => setVehicleStats(null))
      .finally(() => setStatsLoading(false));
  }

  function openDriver(driver: ChauffeurOut) {
    setSelectedDriver(driver);
    setDriverPaiement(null);
    setDriverVersements([]);
    setDriverLoading(true);
    Promise.all([
      fetchVtcStatutPaiement(driver.id).catch(() => null),
      fetchVtcVersements({ driverId: driver.id }).catch(() => []),
    ]).then(([paiement, versements]) => {
      setDriverPaiement(paiement);
      setDriverVersements(versements);
    }).finally(() => setDriverLoading(false));
  }

  if (loadingResume || loadingVehicles || loadingDrivers || loadingAffectations) {
    return <div className="p-6 text-center text-slate-400 text-sm">Chargement…</div>;
  }

  return (
    <div className="p-6 max-w-screen-xl mx-auto space-y-6">

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 p-4">
        <StatCard label="Revenus (versements)" value={totals.versements} color="text-emerald-600" />
        <StatCard label="Dépenses" value={totals.depenses} color="text-red-600" />
        <StatCard label="Résultat net" value={totals.net} color={totals.net >= 0 ? 'text-emerald-600' : 'text-red-600'} />
        <StatCard label="Versements attendus" value={pendingPayments} color="text-amber-600" />
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-slate-200">
        {(['vehicules', 'chauffeurs'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize transition-colors border-b-2 -mb-px ${
              tab === t
                ? 'border-navy-600 text-navy-700'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {t === 'vehicules' ? `Véhicules (${vehicles.length})` : `Chauffeurs (${drivers.length})`}
          </button>
        ))}
      </div>

      {tab === 'vehicules' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {vehicles.length === 0 && (
            <div className="text-sm text-slate-400 text-center py-8 md:col-span-2">Aucun véhicule enregistré.</div>
          )}
          {vehicles.map(v => {
            const stats = perVehicle.get(v.id);
            const revenus = stats?.versements ?? 0;
            const depenses = stats?.depenses ?? 0;
            const result = stats?.net ?? 0;
            const status = vehiculeStatusLabel[v.status];
            return (
              <button
                key={v.id}
                onClick={() => openVehicle(v)}
                className="text-left bg-white rounded-xl border border-slate-200 p-6 hover:border-navy-300 hover:shadow-sm transition-all group"
              >
                <div className="flex items-start justify-between p-4">
                  <div>
                    <div className="font-semibold text-slate-800 text-base">{v.make} {v.model}</div>
                    <div className="font-mono text-xs text-slate-500 mt-1">{v.registration}{v.year ? ` · ${v.year}` : ''}</div>
                  </div>
                  <Badge variant={status.variant}>{status.label}</Badge>
                </div>

                <div className="grid grid-cols-3 p-4">
                  <div>
                    <div className="text-xs text-slate-400 mt-1">Revenus</div>
                    <div className="font-financial text-sm font-semibold text-emerald-600">{formatCFA(revenus)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-400 mt-1">Dépenses</div>
                    <div className="font-financial text-sm font-semibold text-red-600">{formatCFA(depenses)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-400 mt-1">Résultat</div>
                    <div className={`font-financial text-sm font-semibold ${result >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                      {result >= 0 ? '+' : ''}{formatCFA(result)}
                    </div>
                  </div>
                </div>

                <div className="text-xs text-slate-500 p-4 group-hover:text-slate-700 transition-colors">Voir la fiche →</div>
              </button>
            );
          })}
        </div>
      )}

      {tab === 'chauffeurs' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {drivers.length === 0 && (
              <div className="text-sm text-slate-400 text-center py-8 md:col-span-2 lg:col-span-3">Aucun chauffeur enregistré.</div>
            )}
            {drivers.map(driver => {
              const activeAssignment = affectations.find(a => a.driver_id === driver.id);
              const status = chauffeurStatusLabel[driver.status];
              return (
                <button
                  key={driver.id}
                  onClick={() => openDriver(driver)}
                  className="text-left bg-white rounded-xl border border-slate-200 p-6 hover:border-navy-300 hover:shadow-sm transition-all group"
                >
                  <div className="flex items-start justify-between p-4">
                    <div>
                      <div className="font-semibold text-slate-800">{driver.full_name}</div>
                      <div className="text-xs text-slate-500 mt-1">{driver.phone ?? 'Téléphone non renseigné'}</div>
                    </div>
                    <Badge variant={status.variant}>{status.label}</Badge>
                  </div>

                  {activeAssignment && (
                    <div className="text-xs text-slate-600 p-4">
                      Véhicule : <strong>{activeAssignment.vehicle_registration ?? '—'}</strong>
                    </div>
                  )}

                  <div className="grid grid-cols-2 p-4 border-t border-slate-100">
                    <div>
                      <div className="text-xs text-slate-400">Attendu</div>
                      <div className="font-financial text-sm font-semibold text-slate-800">{formatCFA(activeAssignment?.expected_amount ?? 0)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-400">En attente</div>
                      <div className={`font-financial text-sm font-semibold ${(activeAssignment?.remaining_amount ?? 0) > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>
                        {formatCFA(activeAssignment?.remaining_amount ?? 0)}
                      </div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Vehicle detail modal */}
      <Modal
        open={!!selectedVehicle}
        onClose={() => setSelectedVehicle(null)}
        title={selectedVehicle ? `${selectedVehicle.make} ${selectedVehicle.model}` : ''}
        width="lg"
      >
        {selectedVehicle && (
          <div className="p-6 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div><div className="text-xs text-slate-500 mt-1">Immatriculation</div><div className="font-mono font-semibold text-slate-800">{selectedVehicle.registration}</div></div>
              <div><div className="text-xs text-slate-500 mt-1">Année</div><div className="text-slate-700">{selectedVehicle.year ?? '—'}</div></div>
              <div><div className="text-xs text-slate-500 mt-1">Prix d&apos;acquisition</div><div className="font-financial font-semibold text-slate-800">{formatCFA(selectedVehicle.acquisition_cost)}</div></div>
              <div><div className="text-xs text-slate-500 mt-1">Statut</div><div className="text-slate-700">{vehiculeStatusLabel[selectedVehicle.status].label}</div></div>
            </div>

            {statsLoading ? (
              <div className="text-sm text-slate-400 text-center py-4">Chargement du bilan…</div>
            ) : vehicleStats ? (
              <>
                <div>
                  <div className="text-sm font-semibold text-slate-700 p-4">Bilan financier cumulé</div>
                  <div className="grid grid-cols-3 gap-4 bg-slate-50 rounded-lg p-4 text-center">
                    <div>
                      <div className="text-xs text-slate-500 mb-1">Revenus totaux</div>
                      <div className="font-financial text-lg font-bold text-emerald-600">{formatCFA(vehicleStats.versements)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-500 mb-1">Dépenses cumulées</div>
                      <div className="font-financial text-lg font-bold text-red-600">{formatCFA(vehicleStats.depenses)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-500 mb-1">Résultat net</div>
                      <div className={`font-financial text-lg font-bold ${vehicleStats.rentabilite >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                        {vehicleStats.rentabilite >= 0 ? '+' : ''}{formatCFA(vehicleStats.rentabilite)}
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <div className="text-sm font-semibold text-slate-700 p-4">Détail des dépenses</div>
                  {Object.keys(vehicleStats.depenses_par_type).length === 0 ? (
                    <div className="text-sm text-slate-400 text-center py-4">Aucune dépense enregistrée.</div>
                  ) : (
                    <div className="space-y-2">
                      {Object.entries(vehicleStats.depenses_par_type).map(([type, amount]) => (
                        <div key={type} className="flex justify-between text-sm border-b border-slate-100 py-2">
                          <span className="text-slate-600">{typeDepenseLabel[type] ?? type}</span>
                          <span className="font-financial font-medium text-slate-800">{formatCFA(amount)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="text-sm text-slate-400 text-center py-4">Bilan indisponible.</div>
            )}
          </div>
        )}
      </Modal>

      {/* Driver detail modal */}
      <Modal
        open={!!selectedDriver}
        onClose={() => setSelectedDriver(null)}
        title={selectedDriver?.full_name ?? ''}
        width="md"
      >
        {selectedDriver && (
          <div className="p-6 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div><div className="text-xs text-slate-500 mt-1">Téléphone</div><div className="text-slate-700">{selectedDriver.phone ?? '—'}</div></div>
              <div><div className="text-xs text-slate-500 mt-1">Permis</div><div className="text-slate-700">{selectedDriver.license_number ?? '—'}</div></div>
            </div>

            {driverLoading ? (
              <div className="text-sm text-slate-400 text-center py-4">Chargement…</div>
            ) : (
              <>
                <div className="grid grid-cols-3 gap-4 text-center bg-slate-50 rounded-lg p-4">
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Attendu</div>
                    <div className="font-financial text-lg font-bold text-slate-800">{formatCFA(driverPaiement?.total_expected ?? 0)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Total versé</div>
                    <div className="font-financial text-lg font-bold text-emerald-600">{formatCFA(driverPaiement?.total_paid ?? 0)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 mb-1">En attente</div>
                    <div className={`font-financial text-lg font-bold ${(driverPaiement?.total_remaining ?? 0) > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>
                      {formatCFA(driverPaiement?.total_remaining ?? 0)}
                    </div>
                  </div>
                </div>

                <div>
                  <div className="text-sm font-semibold text-slate-700 p-4">Versements récents</div>
                  {driverVersements.length === 0 ? (
                    <div className="text-sm text-slate-400 text-center py-4">Aucun versement</div>
                  ) : (
                    <div className="space-y-2">
                      {driverVersements.slice(0, 5).map(v => (
                        <div key={v.id} className="flex justify-between items-center py-2 border-b border-slate-100">
                          <div className="text-sm text-slate-700">{new Date(v.paid_at).toLocaleDateString('fr-FR')}</div>
                          <div className="font-financial font-semibold text-emerald-600">{formatCFA(v.amount)}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
