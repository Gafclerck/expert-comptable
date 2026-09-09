import { useState } from 'react';
import { formatCFA } from '@/utils/format';
import { fetchVehicles, fetchDrivers } from '@/services/mock';
import { useApiQuery } from '@/hooks/useApiQuery';
import type { Vehicle, Driver } from '@/types';
import Badge from '@/components/ui/Badge';
import Modal from '@/components/ui/Modal';

const recentDays = Array.from({ length: 7 }, (_, i) => {
  const d = new Date();
  d.setDate(d.getDate() - (6 - i));
  return d.toISOString().slice(0, 10);
});
const frDayShort = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'];
const dayLabels: Record<string, string> = Object.fromEntries(
  recentDays.map(day => {
    const d = new Date(day + 'T12:00:00');
    return [day, `${frDayShort[d.getDay()]} ${d.getDate()}`];
  })
);

export default function VTC() {
  const { data: rawVehicles, loading: loadingVehicles } = useApiQuery(fetchVehicles, []);
  const { data: rawDrivers, loading: loadingDrivers } = useApiQuery(fetchDrivers, []);

  const vehicles: Vehicle[] = (rawVehicles ?? []).map((r: any) => ({
    id: r.id,
    name: r.name ?? '',
    brand: r.brand ?? '',
    model: r.model ?? '',
    plate: r.plate ?? '',
    year: r.year ?? '',
    status: (r.status ?? 'active') as Vehicle['status'],
    acquisitionCost: Number(r.acquisition_cost ?? 0),
    initialExpenses: Number(r.initial_expenses ?? 0),
    fuelCost: Number(r.fuel_cost ?? 0),
    maintenanceCost: Number(r.maintenance_cost ?? 0),
    repairCost: Number(r.repair_cost ?? 0),
    insuranceCost: Number(r.insurance_cost ?? 0),
    totalRevenue: Number(r.total_revenue ?? 0),
    currentDriverId: r.current_driver_id ?? null,
  }));

  const drivers: Driver[] = (rawDrivers ?? []).map((r: any) => {
    const workDaysArr: any[] = r.driver_work_days ?? [];
    const workedDays: Record<string, boolean> = Object.fromEntries(
      workDaysArr.map((wd: any) => [wd.date, Boolean(wd.worked)])
    );
    return {
      id: r.id,
      name: r.name ?? '',
      phone: r.phone ?? '',
      status: (r.status ?? 'active') as Driver['status'],
      dailyRate: Number(r.daily_rate ?? 0),
      vehicleId: r.vehicle_id ?? null,
      workedDays,
      payments: (r.payments ?? []).map((p: any) => ({
        id: p.id,
        date: p.date ?? '',
        amount: Number(p.amount ?? 0),
        note: p.note,
      })),
    };
  });

  const totalRevenue = vehicles.reduce((s, v) => s + v.totalRevenue, 0);
  const totalExpenses = vehicles.reduce((s, v) => s + v.fuelCost + v.maintenanceCost + v.repairCost + v.insuranceCost, 0);
  const pendingPayments = drivers.reduce((s, d) => {
    const worked = Object.values(d.workedDays).filter(Boolean).length;
    const paid = d.payments.reduce((sp, p) => sp + p.amount, 0);
    return s + Math.max(0, worked * d.dailyRate - paid);
  }, 0);
  const activityKpis = {
    vtc: {
      revenue: totalRevenue,
      expenses: totalExpenses,
      result: totalRevenue - totalExpenses,
      pendingPayments,
    },
  };

  const [selectedVehicle, setSelectedVehicle] = useState<Vehicle | null>(null);
  const [selectedDriver, setSelectedDriver] = useState<Driver | null>(null);
  const [tab, setTab] = useState<'vehicules' | 'chauffeurs'>('vehicules');

  if (loadingVehicles || loadingDrivers) return <div className="p-6 text-center text-slate-400 text-sm">Chargement…</div>;

  return (
    <div className="p-6 max-w-screen-xl mx-auto space-y-6">

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 p-4">
        {[
          { label: 'Revenus (versements)', value: activityKpis.vtc.revenue, color: 'text-emerald-600' },
          { label: 'Dépenses', value: activityKpis.vtc.expenses, color: 'text-red-600' },
          { label: 'Résultat net', value: activityKpis.vtc.result, color: 'text-emerald-600' },
          { label: 'Versements attendus', value: activityKpis.vtc.pendingPayments, color: 'text-amber-600' },
        ].map(k => (
          <div key={k.label} className="bg-white rounded-lg border border-slate-200 p-4">
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wide p-2">{k.label}</div>
            <div className={`font-financial text-xl font-semibold ${k.color}`}>{formatCFA(k.value)}</div>
          </div>
        ))}
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
          {vehicles.map(v => {
            const totalExpenses = v.fuelCost + v.maintenanceCost + v.repairCost + v.insuranceCost;
            const result = v.totalRevenue - totalExpenses;
            const driver = drivers.find(d => d.id === v.currentDriverId);
            return (
              <button
                key={v.id}
                onClick={() => setSelectedVehicle(v)}
                className="text-left bg-white rounded-xl border border-slate-200 p-6 hover:border-navy-300 hover:shadow-sm transition-all group"
              >
                <div className="flex items-start justify-between p-4">
                  <div>
                    <div className="font-semibold text-slate-800 text-base">{v.name}</div>
                    <div className="font-mono text-xs text-slate-500 mt-1">{v.plate} · {v.year}</div>
                  </div>
                  <Badge variant={v.status === 'active' ? 'success' : v.status === 'maintenance' ? 'warning' : 'neutral'}>
                    {v.status === 'active' ? 'Actif' : v.status === 'maintenance' ? 'Maintenance' : 'Inactif'}
                  </Badge>
                </div>

                {driver && (
                  <div className="text-xs text-slate-600 bg-slate-50 rounded p-4">
                    Chauffeur actuel : <strong>{driver.name}</strong> · {formatCFA(driver.dailyRate)}/jour
                  </div>
                )}

                <div className="grid grid-cols-3 p-4">
                  <div>
                    <div className="text-xs text-slate-400 mt-1">Revenus</div>
                    <div className="font-financial text-sm font-semibold text-emerald-600">{formatCFA(v.totalRevenue)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-400 mt-1">Dépenses</div>
                    <div className="font-financial text-sm font-semibold text-red-600">{formatCFA(totalExpenses)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-400 mt-1">Résultat</div>
                    <div className={`font-financial text-sm font-semibold ${result >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                      {result >= 0 ? '+' : ''}{formatCFA(result)}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-2 border-t border-slate-100 p-4">
                  {[
                    { label: 'Carburant', value: v.fuelCost },
                    { label: 'Entretien', value: v.maintenanceCost },
                    { label: 'Réparations', value: v.repairCost },
                    { label: 'Assurance', value: v.insuranceCost },
                  ].map(item => (
                    <div key={item.label}>
                      <div className="text-xs text-slate-400">{item.label}</div>
                      <div className="font-financial text-xs text-slate-600">{formatCFA(item.value)}</div>
                    </div>
                  ))}
                </div>

                <div className="text-xs text-slate-500 p-4 group-hover:text-slate-700 transition-colors">Voir la fiche →</div>
              </button>
            );
          })}
        </div>
      )}

      {tab === 'chauffeurs' && (
        <div className="space-y-4">
          {/* Versements du jour */}
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <div className="text-sm font-semibold text-amber-900 mb-2">Versements attendus aujourd&apos;hui</div>
            <div className="flex gap-4">
              {drivers.filter(d => d.status === 'active' && d.workedDays[recentDays[recentDays.length - 1]]).map(d => {
                const todayPaid = d.payments.some(p => p.date === recentDays[recentDays.length - 1]);
                return (
                  <div key={d.id} className={`flex items-center gap-2 rounded-lg px-4 py-2 ${todayPaid ? 'bg-emerald-100' : 'bg-white border border-amber-300'}`}>
                    <div className={`w-2 h-2 rounded-full ${todayPaid ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                    <span className="text-sm font-medium text-slate-800">{d.name}</span>
                    <span className="font-financial text-sm text-slate-700">{formatCFA(d.dailyRate)}</span>
                    <Badge variant={todayPaid ? 'success' : 'warning'}>{todayPaid ? 'Reçu' : 'Attendu'}</Badge>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Driver cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {drivers.map(driver => {
              const vehicle = vehicles.find(v => v.id === driver.vehicleId);
              const workedCount = Object.values(driver.workedDays).filter(Boolean).length;
              const totalPaid = driver.payments.reduce((s, p) => s + p.amount, 0);
              const expectedTotal = workedCount * driver.dailyRate;
              const pendingAmount = expectedTotal - totalPaid;

              return (
                <button
                  key={driver.id}
                  onClick={() => setSelectedDriver(driver)}
                  className="text-left bg-white rounded-xl border border-slate-200 p-6 hover:border-navy-300 hover:shadow-sm transition-all group"
                >
                  <div className="flex items-start justify-between p-4">
                    <div>
                      <div className="font-semibold text-slate-800">{driver.name}</div>
                      <div className="text-xs text-slate-500 mt-1">{driver.phone}</div>
                    </div>
                    <Badge variant={driver.status === 'active' ? 'success' : 'neutral'}>
                      {driver.status === 'active' ? 'Actif' : 'Inactif'}
                    </Badge>
                  </div>

                  {vehicle && (
                    <div className="text-xs text-slate-600 p-4">Véhicule : <strong>{vehicle.name}</strong></div>
                  )}

                  {/* 7-day grid */}
                  <div className="p-4">
                    <div className="text-xs text-slate-400 p-2">7 derniers jours</div>
                    <div className="flex gap-1">
                      {recentDays.map(day => {
                        const worked = driver.workedDays[day];
                        const paid = driver.payments.some(p => p.date === day);
                        return (
                          <div key={day} className="flex-1">
                            <div className={`h-6 rounded-sm text-xs flex items-center justify-center font-medium ${
                              !worked ? 'bg-slate-100 text-slate-400' :
                              paid ? 'bg-emerald-100 text-emerald-700' :
                              'bg-amber-100 text-amber-700'
                            }`}>
                              {worked ? (paid ? '✓' : '!') : '–'}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    <div className="flex gap-1 mt-1">
                      {recentDays.map(day => (
                        <div key={day} className="flex-1 text-xs text-slate-400 text-center">{dayLabels[day].split(' ')[0]}</div>
                      ))}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 p-4">
                    <div>
                      <div className="text-xs text-slate-400">Jours travaillés</div>
                      <div className="font-financial text-sm font-semibold text-slate-800">{workedCount} j</div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-400">En attente</div>
                      <div className={`font-financial text-sm font-semibold ${pendingAmount > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>
                        {formatCFA(pendingAmount)}
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
        title={selectedVehicle?.name ?? ''}
        width="lg"
      >
        {selectedVehicle && (() => {
          const v = selectedVehicle;
          const totalExpenses = v.fuelCost + v.maintenanceCost + v.repairCost + v.insuranceCost;
          const result = v.totalRevenue - totalExpenses;
          const driver = drivers.find(d => d.id === v.currentDriverId);

          return (
            <div className="p-6">
              <div className="grid grid-cols-2 gap-4">
                <div><div className="text-xs text-slate-500 mt-1">Immatriculation</div><div className="font-mono font-semibold text-slate-800">{v.plate}</div></div>
                <div><div className="text-xs text-slate-500 mt-1">Année</div><div className="text-slate-700">{v.year}</div></div>
                <div><div className="text-xs text-slate-500 mt-1">Prix d&apos;acquisition</div><div className="font-financial font-semibold text-slate-800">{formatCFA(v.acquisitionCost)}</div></div>
                <div><div className="text-xs text-slate-500 mt-1">Frais initiaux</div><div className="font-financial text-slate-700">{formatCFA(v.initialExpenses)}</div></div>
              </div>

              {driver && (
                <div className="bg-slate-50 rounded-lg p-4">
                  <div className="text-xs text-slate-500 mb-1">Chauffeur actuel</div>
                  <div className="font-medium text-slate-800">{driver.name} · {driver.phone}</div>
                  <div className="text-xs text-slate-500 mt-1">{formatCFA(driver.dailyRate)}/jour</div>
                </div>
              )}

              <div>
                <div className="text-sm font-semibold text-slate-700 p-4">Bilan financier cumulé</div>
                <div className="grid grid-cols-3 gap-4 bg-slate-50 rounded-lg p-4 text-center">
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Revenus totaux</div>
                    <div className="font-financial text-lg font-bold text-emerald-600">{formatCFA(v.totalRevenue)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Dépenses cumulées</div>
                    <div className="font-financial text-lg font-bold text-red-600">{formatCFA(totalExpenses)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Résultat net</div>
                    <div className={`font-financial text-lg font-bold ${result >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                      {result >= 0 ? '+' : ''}{formatCFA(result)}
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <div className="text-sm font-semibold text-slate-700 p-4">Détail des dépenses</div>
                <div className="space-y-2">
                  {[
                    { label: 'Carburant', value: v.fuelCost, pct: (v.fuelCost / totalExpenses) * 100, color: 'bg-red-400' },
                    { label: 'Entretien', value: v.maintenanceCost, pct: (v.maintenanceCost / totalExpenses) * 100, color: 'bg-orange-400' },
                    { label: 'Réparations', value: v.repairCost, pct: (v.repairCost / totalExpenses) * 100, color: 'bg-amber-400' },
                    { label: 'Assurance', value: v.insuranceCost, pct: (v.insuranceCost / totalExpenses) * 100, color: 'bg-yellow-400' },
                  ].map(item => (
                    <div key={item.label}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-slate-600">{item.label}</span>
                        <span className="font-financial font-medium text-slate-800">{formatCFA(item.value)}</span>
                      </div>
                      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div className={`h-full ${item.color} rounded-full`} style={{ width: `${item.pct}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })()}
      </Modal>

      {/* Driver detail modal */}
      <Modal
        open={!!selectedDriver}
        onClose={() => setSelectedDriver(null)}
        title={selectedDriver?.name ?? ''}
        width="md"
      >
        {selectedDriver && (() => {
          const d = selectedDriver;
          const vehicle = vehicles.find(v => v.id === d.vehicleId);
          const workedCount = Object.values(d.workedDays).filter(Boolean).length;
          const totalPaid = d.payments.reduce((s, p) => s + p.amount, 0);
          const expectedTotal = workedCount * d.dailyRate;

          return (
            <div className="p-6">
              <div className="grid grid-cols-2 gap-4">
                <div><div className="text-xs text-slate-500 mt-1">Téléphone</div><div className="text-slate-700">{d.phone}</div></div>
                <div><div className="text-xs text-slate-500 mt-1">Taux journalier</div><div className="font-financial font-semibold text-slate-800">{formatCFA(d.dailyRate)}</div></div>
              </div>
              {vehicle && (
                <div><div className="text-xs text-slate-500 mt-1">Véhicule</div><div className="text-slate-700">{vehicle.name} · {vehicle.plate}</div></div>
              )}

              <div className="bg-slate-50 rounded-lg p-4">
                <div className="text-xs font-semibold text-slate-600 p-4">7 derniers jours</div>
                <div className="grid grid-cols-7 gap-1">
                  {recentDays.map(day => {
                    const worked = d.workedDays[day];
                    const paid = d.payments.some(p => p.date === day);
                    return (
                      <div key={day} className="text-center">
                        <div className={`h-10 rounded flex items-center justify-center text-xs font-medium mb-1 ${
                          !worked ? 'bg-slate-100 text-slate-400' :
                          paid ? 'bg-emerald-100 text-emerald-700' :
                          'bg-amber-100 text-amber-700'
                        }`}>
                          {worked ? (paid ? '✓' : '!') : '—'}
                        </div>
                        <div className="text-xs text-slate-400 leading-tight">{dayLabels[day]}</div>
                      </div>
                    );
                  })}
                </div>
                <div className="flex p-4 text-xs text-slate-500">
                  <span className="flex items-center gap-1"><span className="w-2 h-2 bg-emerald-400 rounded-sm" /> Travaillé + versé</span>
                  <span className="flex items-center gap-1"><span className="w-2 h-2 bg-amber-400 rounded-sm" /> Travaillé, non versé</span>
                  <span className="flex items-center gap-1"><span className="w-2 h-2 bg-slate-100 rounded-sm" /> Non travaillé</span>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <div className="text-xs text-slate-500 mb-1">Jours travaillés</div>
                  <div className="font-financial text-xl font-bold text-slate-800">{workedCount}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mb-1">Total versé</div>
                  <div className="font-financial text-xl font-bold text-emerald-600">{formatCFA(totalPaid)}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mb-1">En attente</div>
                  <div className={`font-financial text-xl font-bold ${expectedTotal - totalPaid > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>
                    {formatCFA(expectedTotal - totalPaid)}
                  </div>
                </div>
              </div>

              <div>
                <div className="text-sm font-semibold text-slate-700 p-4">Versements récents</div>
                {d.payments.length === 0 ? (
                  <div className="text-sm text-slate-400 text-center py-4">Aucun versement</div>
                ) : (
                  <div className="space-y-2">
                    {d.payments.slice(0, 5).map(p => (
                      <div key={p.id} className="flex justify-between items-center py-2 border-b border-slate-100">
                        <div>
                          <div className="text-sm text-slate-700">{p.date}</div>
                          {p.note && <div className="text-xs text-slate-400">{p.note}</div>}
                        </div>
                        <div className="font-financial font-semibold text-emerald-600">{formatCFA(p.amount)}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })()}
      </Modal>
    </div>
  );
}
