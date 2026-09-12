import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { formatCFA } from '@/utils/format';
import {
  fetchAccounts, fetchCategories,
  fetchVtcAffectations, fetchVtcChauffeurs, fetchVtcResumeFinancier,
  fetchVtcStatutPaiement, fetchVtcVehiculeStats, fetchVtcVehicules, fetchVtcVersements,
  createVtcChauffeur, updateVtcChauffeurStatus,
  createVtcDepense, createVtcIndisponibilite, createVtcVersement,
  createVtcAffectation, endVtcAffectation,
  createVtcVehicule, updateVtcVehicule, updateVtcVehiculeStatus,
  type ChauffeurCreatePayload, type DepenseCreatePayload, type DepenseExpenseType,
  type VehiculeCreatePayload, type VehiculeUpdatePayload,
} from '@/services';
import { resolveBusinessId } from '@/services/identity';
import { useApiQuery } from '@/hooks/useApiQuery';
import type {
  AccountOut, AffectationOut, CategoryOut, ChauffeurOut, ChauffeurStatus,
  ResumeFinancierOut, StatistiquesVehiculeOut, VehiculeOut, VehiculeStatus, VersementOut,
} from '@/types/api';
import Badge from '@/components/ui/Badge';
import Modal from '@/components/ui/Modal';

const today = new Date().toISOString().slice(0, 10);

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

const depenseTypes: DepenseExpenseType[] = ['fuel', 'maintenance', 'repair', 'tires', 'insurance', 'registration', 'misc'];

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <div className="text-xs font-medium text-slate-500 uppercase tracking-wide p-2">{label}</div>
      <div className={`font-financial text-xl font-semibold ${color}`}>{formatCFA(value)}</div>
    </div>
  );
}

export default function VTC() {
  const { data: resume, loading: loadingResume, refetch: refetchResume } = useApiQuery<ResumeFinancierOut>(() => fetchVtcResumeFinancier(), []);
  const { data: rawVehicles, loading: loadingVehicles, refetch: refetchVehicles } = useApiQuery<VehiculeOut[]>(() => fetchVtcVehicules(), []);
  const { data: rawDrivers, loading: loadingDrivers, refetch: refetchDrivers } = useApiQuery<ChauffeurOut[]>(() => fetchVtcChauffeurs(), []);
  const { data: rawAffectations, loading: loadingAffectations, refetch: refetchAffectations } = useApiQuery(() => fetchVtcAffectations({ status: 'active' }), []);

  // Comptes VTC + catégories pour dépenses / versements.
  const [vtcAccounts, setVtcAccounts] = useState<AccountOut[]>([]);
  const { data: categoriesData } = useApiQuery<CategoryOut[]>(fetchCategories, []);
  const categories = categoriesData ?? [];
  const debitCategories = categories.filter(c => c.type === 'debit');
  const creditCategories = categories.filter(c => c.type === 'credit');

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const bizId = await resolveBusinessId('vtc');
        if (!active || !bizId) return;
        const accts = await fetchAccounts(bizId);
        if (active) setVtcAccounts(accts);
      } catch { /* retry on form open */ }
    })();
    return () => { active = false; };
  }, []);

  function reloadAll() { refetchResume(); refetchVehicles(); refetchDrivers(); refetchAffectations(); }

  // ── Sélection + détails ──────────────────────────────────────
  const [selectedVehicle, setSelectedVehicle] = useState<VehiculeOut | null>(null);
  const [vehicleStats, setVehicleStats] = useState<StatistiquesVehiculeOut | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);

  const [selectedDriver, setSelectedDriver] = useState<ChauffeurOut | null>(null);
  const [driverPaiement, setDriverPaiement] = useState<{ total_expected: number; total_paid: number; total_remaining: number } | null>(null);
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
    refreshVehicleStats(vehicle);
  }

  function refreshVehicleStats(vehicle: VehiculeOut) {
    setVehicleStats(null);
    setStatsLoading(true);
    fetchVtcVehiculeStats(vehicle.id)
      .then(setVehicleStats)
      .catch(() => setVehicleStats(null))
      .finally(() => setStatsLoading(false));
  }

  function openDriver(driver: ChauffeurOut) {
    setSelectedDriver(driver);
    refreshDriverData(driver);
  }

  function refreshDriverData(driver: ChauffeurOut) {
    setDriverPaiement(null);
    setDriverVersements([]);
    setDriverLoading(true);
    Promise.all([
      fetchVtcStatutPaiement(driver.id).then(p => ({ total_expected: p.total_expected, total_paid: p.total_paid, total_remaining: p.total_remaining })).catch(() => null),
      fetchVtcVersements({ driverId: driver.id }).catch(() => []),
    ]).then(([paiement, versements]) => {
      setDriverPaiement(paiement);
      setDriverVersements(versements);
    }).finally(() => setDriverLoading(false));
  }

  // ── Form Nouveau véhicule ────────────────────────────────────
  const [vehFormOpen, setVehFormOpen] = useState(false);
  const [vehMake, setVehMake] = useState('');
  const [vehModel, setVehModel] = useState('');
  const [vehYear, setVehYear] = useState('');
  const [vehReg, setVehReg] = useState('');
  const [vehCost, setVehCost] = useState('');
  const [vehSubmitting, setVehSubmitting] = useState(false);
  const [vehError, setVehError] = useState<string | null>(null);

  function openVehicleForm() {
    setVehMake(''); setVehModel(''); setVehYear(''); setVehReg(''); setVehCost('');
    setVehError(null); setVehFormOpen(true);
  }

  async function handleVehicleCreate(e: FormEvent) {
    e.preventDefault();
    if (!vehMake.trim() || !vehModel.trim() || !vehReg.trim()) { setVehError('Marque, modèle et immatriculation sont requis.'); return; }
    const cost = vehCost === '' ? 0 : Number(vehCost);
    if (!Number.isFinite(cost) || cost < 0) { setVehError('Coût d\'acquisition invalide.'); return; }
    setVehSubmitting(true); setVehError(null);
    try {
      const payload: VehiculeCreatePayload = {
        make: vehMake.trim(), model: vehModel.trim(), registration: vehReg.trim(),
        acquisition_cost: cost,
      };
      if (vehYear.trim() && Number.isInteger(Number(vehYear))) payload.year = Number(vehYear);
      await createVtcVehicule(payload);
      setVehFormOpen(false); reloadAll();
    } catch (err) { setVehError(err instanceof Error ? err.message : 'Erreur.'); setVehSubmitting(false); }
  }

  // ── Form Modifier véhicule ───────────────────────────────────
  const [vehEditOpen, setVehEditOpen] = useState(false);
  const [vedMake, setVedMake] = useState('');
  const [vedModel, setVedModel] = useState('');
  const [vedYear, setVedYear] = useState('');
  const [vedReg, setVedReg] = useState('');
  const [vedCost, setVedCost] = useState('');
  const [vedSubmitting, setVedSubmitting] = useState(false);
  const [vedError, setVedError] = useState<string | null>(null);

  function openVehicleEdit() {
    if (!selectedVehicle) return;
    setVedMake(selectedVehicle.make); setVedModel(selectedVehicle.model);
    setVedYear(selectedVehicle.year == null ? '' : String(selectedVehicle.year));
    setVedReg(selectedVehicle.registration); setVedCost(String(selectedVehicle.acquisition_cost));
    setVedError(null); setVehEditOpen(true);
  }

  async function handleVehicleEdit(e: FormEvent) {
    e.preventDefault();
    if (!selectedVehicle) return;
    const payload: VehiculeUpdatePayload = {};
    if (vedMake.trim() !== selectedVehicle.make) payload.make = vedMake.trim();
    if (vedModel.trim() !== selectedVehicle.model) payload.model = vedModel.trim();
    if (vedReg.trim() !== selectedVehicle.registration) payload.registration = vedReg.trim();
    const year = vedYear.trim() === '' ? null : Number(vedYear);
    if (year !== selectedVehicle.year && (year === null || Number.isInteger(year))) payload.year = year;
    const cost = vedCost === '' ? null : Number(vedCost);
    if (cost !== null && Number.isFinite(cost) && cost !== selectedVehicle.acquisition_cost) payload.acquisition_cost = cost;
    if (Object.keys(payload).length === 0) { setVehEditOpen(false); return; }
    setVedSubmitting(true); setVedError(null);
    try {
      await updateVtcVehicule(selectedVehicle.id, payload);
      setVehEditOpen(false); reloadAll();
      const v = selectedVehicle;
      setSelectedVehicle({ ...v, ...payload } as VehiculeOut);
    } catch (err) { setVedError(err instanceof Error ? err.message : 'Erreur.'); setVedSubmitting(false); }
  }

  // ── Form Statut véhicule ─────────────────────────────────────
  const [vehStatusOpen, setVehStatusOpen] = useState(false);
  const [vehStatus, setVehStatus] = useState<VehiculeStatus>('active');
  const [vehStatusSubmitting, setVehStatusSubmitting] = useState(false);
  const [vehStatusError, setVehStatusError] = useState<string | null>(null);

  function openVehicleStatus() {
    if (!selectedVehicle) return;
    setVehStatus(selectedVehicle.status); setVehStatusError(null); setVehStatusOpen(true);
  }

  async function handleVehicleStatus(e: FormEvent) {
    e.preventDefault();
    if (!selectedVehicle || vehStatus === selectedVehicle.status) { setVehStatusOpen(false); return; }
    setVehStatusSubmitting(true); setVehStatusError(null);
    try {
      await updateVtcVehiculeStatus(selectedVehicle.id, { status: vehStatus });
      setVehStatusOpen(false); reloadAll();
      setSelectedVehicle({ ...selectedVehicle, status: vehStatus });
    } catch (err) { setVehStatusError(err instanceof Error ? err.message : 'Erreur.'); setVehStatusSubmitting(false); }
  }

  // ── Form Nouveau chauffeur ───────────────────────────────────
  const [chfFormOpen, setChfFormOpen] = useState(false);
  const [chfName, setChfName] = useState('');
  const [chfPhone, setChfPhone] = useState('');
  const [chfLicense, setChfLicense] = useState('');
  const [chfSubmitting, setChfSubmitting] = useState(false);
  const [chfError, setChfError] = useState<string | null>(null);

  function openChauffeurForm() {
    setChfName(''); setChfPhone(''); setChfLicense(''); setChfError(null); setChfFormOpen(true);
  }

  async function handleChauffeurCreate(e: FormEvent) {
    e.preventDefault();
    if (!chfName.trim()) { setChfError('Le nom est requis.'); return; }
    setChfSubmitting(true); setChfError(null);
    try {
      const payload: ChauffeurCreatePayload = { full_name: chfName.trim() };
      if (chfPhone.trim()) payload.phone = chfPhone.trim();
      if (chfLicense.trim()) payload.license_number = chfLicense.trim();
      await createVtcChauffeur(payload);
      setChfFormOpen(false); reloadAll();
    } catch (err) { setChfError(err instanceof Error ? err.message : 'Erreur.'); setChfSubmitting(false); }
  }

  // ── Form Statut chauffeur ────────────────────────────────────
  const [chfStatusOpen, setChfStatusOpen] = useState(false);
  const [chfStatus, setChfStatus] = useState<ChauffeurStatus>('active');
  const [chfStatusSubmitting, setChfStatusSubmitting] = useState(false);
  const [chfStatusError, setChfStatusError] = useState<string | null>(null);

  function openChauffeurStatus() {
    if (!selectedDriver) return;
    setChfStatus(selectedDriver.status); setChfStatusError(null); setChfStatusOpen(true);
  }

  async function handleChauffeurStatus(e: FormEvent) {
    e.preventDefault();
    if (!selectedDriver || chfStatus === selectedDriver.status) { setChfStatusOpen(false); return; }
    setChfStatusSubmitting(true); setChfStatusError(null);
    try {
      await updateVtcChauffeurStatus(selectedDriver.id, { status: chfStatus });
      setChfStatusOpen(false); reloadAll();
      setSelectedDriver({ ...selectedDriver, status: chfStatus });
    } catch (err) { setChfStatusError(err instanceof Error ? err.message : 'Erreur.'); setChfStatusSubmitting(false); }
  }

  // ── Form Affectation ─────────────────────────────────────────
  const [affFormOpen, setAffFormOpen] = useState(false);
  const [affDriverId, setAffDriverId] = useState('');
  const [affVehicleId, setAffVehicleId] = useState('');
  const [affStart, setAffStart] = useState(today);
  const [affExpected, setAffExpected] = useState('');
  const [affTerms, setAffTerms] = useState('');
  const [affSubmitting, setAffSubmitting] = useState(false);
  const [affError, setAffError] = useState<string | null>(null);

  const activeDrivers = drivers.filter(d => d.status === 'active');
  const activeVehicles = vehicles.filter(v => v.status === 'active');

  function openAffectationForm() {
    setAffDriverId(selectedDriver?.id ?? activeDrivers[0]?.id ?? '');
    setAffVehicleId(activeVehicles[0]?.id ?? '');
    setAffStart(today); setAffExpected(''); setAffTerms('');
    setAffError(null); setAffFormOpen(true);
  }

  async function handleAffectationCreate(e: FormEvent) {
    e.preventDefault();
    const expected = Number(affExpected);
    if (!affDriverId || !affVehicleId || !Number.isFinite(expected) || expected <= 0 || !affStart) {
      setAffError('Chauffeur, véhicule, date et montant attendu (> 0) sont requis.'); return;
    }
    setAffSubmitting(true); setAffError(null);
    try {
      await createVtcAffectation({
        driver_id: affDriverId, vehicle_id: affVehicleId, start_date: affStart,
        expected_amount: expected, terms: affTerms.trim() || null,
      });
      setAffFormOpen(false); reloadAll();
    } catch (err) { setAffError(err instanceof Error ? err.message : 'Erreur.'); setAffSubmitting(false); }
  }

  // ── Form Dépense ─────────────────────────────────────────────
  const [depFormOpen, setDepFormOpen] = useState(false);
  const [depType, setDepType] = useState<DepenseExpenseType>('fuel');
  const [depAmount, setDepAmount] = useState('');
  const [depQuantity, setDepQuantity] = useState('');
  const [depUnit, setDepUnit] = useState('');
  const [depDesc, setDepDesc] = useState('');
  const [depAccountId, setDepAccountId] = useState('');
  const [depCategoryId, setDepCategoryId] = useState('');
  const [depSubmitting, setDepSubmitting] = useState(false);
  const [depError, setDepError] = useState<string | null>(null);

  function openDepenseForm() {
    if (!selectedVehicle) return;
    setDepType('fuel'); setDepAmount(''); setDepQuantity(''); setDepUnit(''); setDepDesc('');
    setDepAccountId(vtcAccounts[0]?.id ?? '');
    setDepCategoryId(debitCategories[0]?.id ?? '');
    setDepError(null); setDepFormOpen(true);
  }

  async function handleDepenseCreate(e: FormEvent) {
    e.preventDefault();
    if (!selectedVehicle) return;
    const amount = Number(depAmount);
    if (!Number.isFinite(amount) || amount <= 0 || !depAccountId || !depCategoryId) {
      setDepError('Montant (> 0), caisse et catégorie sont requis.'); return;
    }
    setDepSubmitting(true); setDepError(null);
    try {
      const payload: DepenseCreatePayload = {
        vehicle_id: selectedVehicle.id, expense_type: depType, amount,
        account_id: depAccountId, category_id: depCategoryId,
      };
      if (depQuantity.trim() !== '' && Number.isFinite(Number(depQuantity))) payload.quantity = Number(depQuantity);
      if (depUnit.trim()) payload.unit = depUnit.trim();
      if (depDesc.trim()) payload.description = depDesc.trim();
      await createVtcDepense(payload);
      setDepFormOpen(false); reloadAll(); refreshVehicleStats(selectedVehicle);
    } catch (err) { setDepError(err instanceof Error ? err.message : 'Erreur.'); setDepSubmitting(false); }
  }

  // ── Form Versement ───────────────────────────────────────────
  const [verFormOpen, setVerFormOpen] = useState(false);
  const [verVehicleId, setVerVehicleId] = useState('');
  const [verAmount, setVerAmount] = useState('');
  const [verAccountId, setVerAccountId] = useState('');
  const [verCategoryId, setVerCategoryId] = useState('');
  const [verSubmitting, setVerSubmitting] = useState(false);
  const [verError, setVerError] = useState<string | null>(null);

  function openVersementForm() {
    if (!selectedDriver) return;
    setVerVehicleId(activeVehicles[0]?.id ?? '');
    setVerAmount('');
    setVerAccountId(vtcAccounts[0]?.id ?? '');
    setVerCategoryId(creditCategories[0]?.id ?? '');
    setVerError(null); setVerFormOpen(true);
  }

  async function handleVersementCreate(e: FormEvent) {
    e.preventDefault();
    if (!selectedDriver) return;
    const amount = Number(verAmount);
    if (!Number.isFinite(amount) || amount <= 0 || !verVehicleId || !verAccountId || !verCategoryId) {
      setVerError('Montant (> 0), véhicule, caisse et catégorie sont requis.'); return;
    }
    setVerSubmitting(true); setVerError(null);
    try {
      await createVtcVersement({
        driver_id: selectedDriver.id, vehicle_id: verVehicleId, amount,
        account_id: verAccountId, category_id: verCategoryId,
      });
      setVerFormOpen(false); reloadAll(); refreshDriverData(selectedDriver);
    } catch (err) { setVerError(err instanceof Error ? err.message : 'Erreur.'); setVerSubmitting(false); }
  }

  // ── Form Indisponibilité ─────────────────────────────────────
  const [indFormOpen, setIndFormOpen] = useState(false);
  const [indStart, setIndStart] = useState(today);
  const [indEnd, setIndEnd] = useState('');
  const [indReason, setIndReason] = useState('');
  const [indSubmitting, setIndSubmitting] = useState(false);
  const [indError, setIndError] = useState<string | null>(null);

  function openIndispoForm() {
    if (!selectedVehicle) return;
    setIndStart(today); setIndEnd(''); setIndReason(''); setIndError(null); setIndFormOpen(true);
  }

  async function handleIndispoCreate(e: FormEvent) {
    e.preventDefault();
    if (!selectedVehicle || !indStart) { setIndError('Date de début requise.'); return; }
    setIndSubmitting(true); setIndError(null);
    try {
      await createVtcIndisponibilite({
        vehicle_id: selectedVehicle.id, start_date: indStart,
        end_date: indEnd || null, reason: indReason.trim() || null,
      });
      setIndFormOpen(false); reloadAll();
    } catch (err) { setIndError(err instanceof Error ? err.message : 'Erreur.'); setIndSubmitting(false); }
  }

  // ── Form Clôture affectation ─────────────────────────────────
  const [endAffOpen, setEndAffOpen] = useState(false);
  const [endAffTarget, setEndAffTarget] = useState<AffectationOut | null>(null);
  const [endAffDate, setEndAffDate] = useState(today);
  const [endAffSubmitting, setEndAffSubmitting] = useState(false);
  const [endAffError, setEndAffError] = useState<string | null>(null);

  function openEndAffectation(aff: AffectationOut) {
    setEndAffTarget(aff); setEndAffDate(today); setEndAffError(null); setEndAffOpen(true);
  }

  async function handleEndAffectation(e: FormEvent) {
    e.preventDefault();
    if (!endAffTarget) return;
    setEndAffSubmitting(true); setEndAffError(null);
    try {
      await endVtcAffectation(endAffTarget.id, { end_date: endAffDate || null });
      setEndAffOpen(false); setEndAffTarget(null); reloadAll();
    } catch (err) { setEndAffError(err instanceof Error ? err.message : 'Erreur.'); setEndAffSubmitting(false); }
  }

  if (loadingResume || loadingVehicles || loadingDrivers || loadingAffectations) {
    return <div className="p-6 text-center text-slate-400 text-sm">Chargement…</div>;
  }

  return (
    <div className="p-6 max-w-screen-xl mx-auto space-y-6">

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Revenus (versements)" value={totals.versements} color="text-emerald-600" />
        <StatCard label="Dépenses" value={totals.depenses} color="text-red-600" />
        <StatCard label="Résultat net" value={totals.net} color={totals.net >= 0 ? 'text-emerald-600' : 'text-red-600'} />
        <StatCard label="Versements attendus" value={pendingPayments} color="text-amber-600" />
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 flex-wrap">
        <button onClick={openVehicleForm} className="p-4 py-1 rounded-full text-xs font-medium bg-navy-800 text-white border border-navy-800 hover:bg-navy-700 transition-all">+ Nouveau véhicule</button>
        <button onClick={openChauffeurForm} className="p-4 py-1 rounded-full text-xs font-medium bg-emerald-600 text-white border border-emerald-600 hover:bg-emerald-500 transition-all">+ Nouveau chauffeur</button>
        <button onClick={openAffectationForm} className="p-4 py-1 rounded-full text-xs font-medium bg-amber-600 text-white border border-amber-600 hover:bg-amber-500 transition-all">+ Affecter un chauffeur</button>
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

                <div className="grid grid-cols-3 gap-4">
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

                <div className="grid grid-cols-2 gap-4 border-t border-slate-100">
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

            <div className="flex flex-wrap gap-2">
              <button onClick={openVehicleEdit} className="px-3 py-1.5 rounded-lg text-xs font-medium bg-navy-800 text-white hover:bg-navy-700 transition-colors">Modifier</button>
              <button onClick={openVehicleStatus} className="px-3 py-1.5 rounded-lg text-xs font-medium bg-white text-slate-700 border border-slate-200 hover:border-slate-300 transition-colors">Changer le statut</button>
              <button onClick={openDepenseForm} className="px-3 py-1.5 rounded-lg text-xs font-medium bg-white text-slate-700 border border-slate-200 hover:border-slate-300 transition-colors">+ Dépense</button>
              <button onClick={openIndispoForm} className="px-3 py-1.5 rounded-lg text-xs font-medium bg-white text-slate-700 border border-slate-200 hover:border-slate-300 transition-colors">Indisponibilité</button>
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
        {selectedDriver && (() => {
          const activeAssignment = affectations.find(a => a.driver_id === selectedDriver.id);
          return (
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div><div className="text-xs text-slate-500 mt-1">Téléphone</div><div className="text-slate-700">{selectedDriver.phone ?? '—'}</div></div>
                <div><div className="text-xs text-slate-500 mt-1">Permis</div><div className="text-slate-700">{selectedDriver.license_number ?? '—'}</div></div>
              </div>

              <div className="flex flex-wrap gap-2">
                <button onClick={openChauffeurStatus} className="px-3 py-1.5 rounded-lg text-xs font-medium bg-white text-slate-700 border border-slate-200 hover:border-slate-300 transition-colors">Changer le statut</button>
                <button onClick={openVersementForm} className="px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-600 text-white hover:bg-emerald-500 transition-colors">+ Versement</button>
              </div>

              {activeAssignment && (
                <div className="bg-slate-50 rounded-lg p-4 flex items-center justify-between">
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Affectation active — {activeAssignment.vehicle_registration ?? '—'}</div>
                    <div className="font-financial text-sm font-semibold text-slate-800">
                      Attendu {formatCFA(activeAssignment.expected_amount)} · Reste {formatCFA(activeAssignment.remaining_amount)}
                    </div>
                  </div>
                  <button onClick={() => openEndAffectation(activeAssignment)} className="px-3 py-1.5 rounded-lg text-xs font-medium bg-white text-slate-700 border border-slate-200 hover:border-slate-300 transition-colors">Clôturer</button>
                </div>
              )}

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
          );
        })()}
      </Modal>

      {/* Form Nouveau véhicule */}
      <Modal open={vehFormOpen} onClose={() => !vehSubmitting && setVehFormOpen(false)} title="Nouveau véhicule" width="md">
        <form onSubmit={handleVehicleCreate} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Marque *</label>
              <input required value={vehMake} onChange={e => setVehMake(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Modèle *</label>
              <input required value={vehModel} onChange={e => setVehModel(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Immatriculation *</label>
              <input required value={vehReg} onChange={e => setVehReg(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Année</label>
              <input type="number" value={vehYear} onChange={e => setVehYear(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500 block p-2">Coût d&apos;acquisition (FCFA)</label>
            <input type="number" min={0} value={vehCost} onChange={e => setVehCost(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
          </div>
          {vehError && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{vehError}</p>}
          <div className="flex gap-2 justify-end pt-2">
            <button type="button" onClick={() => setVehFormOpen(false)} disabled={vehSubmitting} className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50">Annuler</button>
            <button type="submit" disabled={vehSubmitting} className="px-4 py-2 text-sm bg-navy-800 text-white rounded-lg hover:bg-navy-700 disabled:opacity-50">{vehSubmitting ? 'Création…' : 'Créer'}</button>
          </div>
        </form>
      </Modal>

      {/* Form Modifier véhicule */}
      <Modal open={vehEditOpen} onClose={() => !vedSubmitting && setVehEditOpen(false)} title="Modifier le véhicule" width="md">
        <form onSubmit={handleVehicleEdit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Marque</label>
              <input value={vedMake} onChange={e => setVedMake(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Modèle</label>
              <input value={vedModel} onChange={e => setVedModel(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Immatriculation</label>
              <input value={vedReg} onChange={e => setVedReg(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Année</label>
              <input type="number" value={vedYear} onChange={e => setVedYear(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500 block p-2">Coût d&apos;acquisition (FCFA)</label>
            <input type="number" min={0} value={vedCost} onChange={e => setVedCost(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
          </div>
          {vedError && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{vedError}</p>}
          <div className="flex gap-2 justify-end pt-2">
            <button type="button" onClick={() => setVehEditOpen(false)} disabled={vedSubmitting} className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50">Annuler</button>
            <button type="submit" disabled={vedSubmitting} className="px-4 py-2 text-sm bg-navy-800 text-white rounded-lg hover:bg-navy-700 disabled:opacity-50">{vedSubmitting ? 'Enregistrement…' : 'Enregistrer'}</button>
          </div>
        </form>
      </Modal>

      {/* Form Statut véhicule */}
      <Modal open={vehStatusOpen} onClose={() => !vehStatusSubmitting && setVehStatusOpen(false)} title="Changer le statut du véhicule" width="sm">
        <form onSubmit={handleVehicleStatus} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-slate-500 block p-2">Statut</label>
            <select value={vehStatus} onChange={e => setVehStatus(e.target.value as VehiculeStatus)} className="w-full border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white">
              <option value="active">Actif</option>
              <option value="out_of_service">Hors service</option>
              <option value="sold">Vendu</option>
            </select>
          </div>
          {vehStatusError && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{vehStatusError}</p>}
          <div className="flex gap-2 justify-end pt-2">
            <button type="button" onClick={() => setVehStatusOpen(false)} disabled={vehStatusSubmitting} className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50">Annuler</button>
            <button type="submit" disabled={vehStatusSubmitting} className="px-4 py-2 text-sm bg-navy-800 text-white rounded-lg hover:bg-navy-700 disabled:opacity-50">{vehStatusSubmitting ? 'Enregistrement…' : 'Enregistrer'}</button>
          </div>
        </form>
      </Modal>

      {/* Form Nouveau chauffeur */}
      <Modal open={chfFormOpen} onClose={() => !chfSubmitting && setChfFormOpen(false)} title="Nouveau chauffeur" width="md">
        <form onSubmit={handleChauffeurCreate} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-slate-500 block p-2">Nom complet *</label>
            <input required value={chfName} onChange={e => setChfName(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Téléphone</label>
              <input value={chfPhone} onChange={e => setChfPhone(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">N° de permis</label>
              <input value={chfLicense} onChange={e => setChfLicense(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
          </div>
          {chfError && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{chfError}</p>}
          <div className="flex gap-2 justify-end pt-2">
            <button type="button" onClick={() => setChfFormOpen(false)} disabled={chfSubmitting} className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50">Annuler</button>
            <button type="submit" disabled={chfSubmitting} className="px-4 py-2 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-500 disabled:opacity-50">{chfSubmitting ? 'Création…' : 'Créer'}</button>
          </div>
        </form>
      </Modal>

      {/* Form Statut chauffeur */}
      <Modal open={chfStatusOpen} onClose={() => !chfStatusSubmitting && setChfStatusOpen(false)} title="Changer le statut du chauffeur" width="sm">
        <form onSubmit={handleChauffeurStatus} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-slate-500 block p-2">Statut</label>
            <select value={chfStatus} onChange={e => setChfStatus(e.target.value as ChauffeurStatus)} className="w-full border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white">
              <option value="active">Actif</option>
              <option value="inactive">Inactif</option>
            </select>
          </div>
          {chfStatusError && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{chfStatusError}</p>}
          <div className="flex gap-2 justify-end pt-2">
            <button type="button" onClick={() => setChfStatusOpen(false)} disabled={chfStatusSubmitting} className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50">Annuler</button>
            <button type="submit" disabled={chfStatusSubmitting} className="px-4 py-2 text-sm bg-navy-800 text-white rounded-lg hover:bg-navy-700 disabled:opacity-50">{chfStatusSubmitting ? 'Enregistrement…' : 'Enregistrer'}</button>
          </div>
        </form>
      </Modal>

      {/* Form Affectation */}
      <Modal open={affFormOpen} onClose={() => !affSubmitting && setAffFormOpen(false)} title="Affecter un chauffeur" width="md">
        <form onSubmit={handleAffectationCreate} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Chauffeur *</label>
              <select value={affDriverId} onChange={e => setAffDriverId(e.target.value)} className="w-full border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white">
                {activeDrivers.map(d => <option key={d.id} value={d.id}>{d.full_name}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Véhicule *</label>
              <select value={affVehicleId} onChange={e => setAffVehicleId(e.target.value)} className="w-full border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white">
                {activeVehicles.map(v => <option key={v.id} value={v.id}>{v.make} {v.model} — {v.registration}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Début *</label>
              <input required type="date" value={affStart} onChange={e => setAffStart(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Montant attendu (FCFA) *</label>
              <input required type="number" min={1} value={affExpected} onChange={e => setAffExpected(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500 block p-2">Conditions</label>
            <input value={affTerms} onChange={e => setAffTerms(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
          </div>
          {affError && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{affError}</p>}
          <div className="flex gap-2 justify-end pt-2">
            <button type="button" onClick={() => setAffFormOpen(false)} disabled={affSubmitting} className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50">Annuler</button>
            <button type="submit" disabled={affSubmitting} className="px-4 py-2 text-sm bg-amber-600 text-white rounded-lg hover:bg-amber-500 disabled:opacity-50">{affSubmitting ? 'Enregistrement…' : 'Affecter'}</button>
          </div>
        </form>
      </Modal>

      {/* Form Dépense */}
      <Modal open={depFormOpen} onClose={() => !depSubmitting && setDepFormOpen(false)} title="Enregistrer une dépense" width="md">
        <form onSubmit={handleDepenseCreate} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Type *</label>
              <select value={depType} onChange={e => setDepType(e.target.value as DepenseExpenseType)} className="w-full border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white">
                {depenseTypes.map(t => <option key={t} value={t}>{typeDepenseLabel[t]}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Montant (FCFA) *</label>
              <input required type="number" min={1} value={depAmount} onChange={e => setDepAmount(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Quantité</label>
              <input type="number" min={0} step="0.01" value={depQuantity} onChange={e => setDepQuantity(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Unité</label>
              <input value={depUnit} onChange={e => setDepUnit(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Description</label>
              <input value={depDesc} onChange={e => setDepDesc(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Caisse *</label>
              <select value={depAccountId} onChange={e => setDepAccountId(e.target.value)} className="w-full border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white">
                {vtcAccounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Catégorie *</label>
              <select value={depCategoryId} onChange={e => setDepCategoryId(e.target.value)} className="w-full border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white">
                {debitCategories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
          </div>
          {depError && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{depError}</p>}
          <div className="flex gap-2 justify-end pt-2">
            <button type="button" onClick={() => setDepFormOpen(false)} disabled={depSubmitting} className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50">Annuler</button>
            <button type="submit" disabled={depSubmitting} className="px-4 py-2 text-sm bg-navy-800 text-white rounded-lg hover:bg-navy-700 disabled:opacity-50">{depSubmitting ? 'Enregistrement…' : 'Enregistrer'}</button>
          </div>
        </form>
      </Modal>

      {/* Form Versement */}
      <Modal open={verFormOpen} onClose={() => !verSubmitting && setVerFormOpen(false)} title="Enregistrer un versement" width="md">
        <form onSubmit={handleVersementCreate} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Véhicule *</label>
              <select value={verVehicleId} onChange={e => setVerVehicleId(e.target.value)} className="w-full border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white">
                {activeVehicles.map(v => <option key={v.id} value={v.id}>{v.make} {v.model} — {v.registration}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Montant (FCFA) *</label>
              <input required type="number" min={1} value={verAmount} onChange={e => setVerAmount(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Caisse *</label>
              <select value={verAccountId} onChange={e => setVerAccountId(e.target.value)} className="w-full border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white">
                {vtcAccounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Catégorie *</label>
              <select value={verCategoryId} onChange={e => setVerCategoryId(e.target.value)} className="w-full border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white">
                {creditCategories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
          </div>
          {verError && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{verError}</p>}
          <div className="flex gap-2 justify-end pt-2">
            <button type="button" onClick={() => setVerFormOpen(false)} disabled={verSubmitting} className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50">Annuler</button>
            <button type="submit" disabled={verSubmitting} className="px-4 py-2 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-500 disabled:opacity-50">{verSubmitting ? 'Enregistrement…' : 'Enregistrer'}</button>
          </div>
        </form>
      </Modal>

      {/* Form Indisponibilité */}
      <Modal open={indFormOpen} onClose={() => !indSubmitting && setIndFormOpen(false)} title="Déclarer une indisponibilité" width="md">
        <form onSubmit={handleIndispoCreate} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Début *</label>
              <input required type="date" value={indStart} onChange={e => setIndStart(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Fin</label>
              <input type="date" value={indEnd} onChange={e => setIndEnd(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500 block p-2">Raison</label>
            <input value={indReason} onChange={e => setIndReason(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
          </div>
          {indError && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{indError}</p>}
          <div className="flex gap-2 justify-end pt-2">
            <button type="button" onClick={() => setIndFormOpen(false)} disabled={indSubmitting} className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50">Annuler</button>
            <button type="submit" disabled={indSubmitting} className="px-4 py-2 text-sm bg-navy-800 text-white rounded-lg hover:bg-navy-700 disabled:opacity-50">{indSubmitting ? 'Enregistrement…' : 'Enregistrer'}</button>
          </div>
        </form>
      </Modal>

      {/* Form Clôture affectation */}
      <Modal open={endAffOpen} onClose={() => !endAffSubmitting && setEndAffOpen(false)} title="Clôturer l'affectation" width="sm">
        <form onSubmit={handleEndAffectation} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-slate-500 block p-2">Date de fin</label>
            <input type="date" value={endAffDate} onChange={e => setEndAffDate(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
          </div>
          {endAffError && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{endAffError}</p>}
          <div className="flex gap-2 justify-end pt-2">
            <button type="button" onClick={() => setEndAffOpen(false)} disabled={endAffSubmitting} className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50">Annuler</button>
            <button type="submit" disabled={endAffSubmitting} className="px-4 py-2 text-sm bg-amber-600 text-white rounded-lg hover:bg-amber-500 disabled:opacity-50">{endAffSubmitting ? 'Clôture…' : 'Clôturer'}</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}