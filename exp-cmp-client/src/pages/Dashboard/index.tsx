import { useNavigate } from 'react-router-dom';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, type TooltipValueType } from 'recharts';
import Icon, { type IconName } from '@/components/ui/Icon';
import { formatCFA, formatCFACompact } from '@/utils/format';
import { fetchAccountsForDashboard, fetchMonthlyActivityKpis } from '@/services';
import { fetchPersonalAdvances } from '@/services/mock';
import type { AccountRow } from '@/services';
import type { PersonalAdvance } from '@/types';
import { useApiQuery } from '@/hooks/useApiQuery';

const accountIcons: Record<string, IconName> = { cash: 'wallet', mobile_money: 'repeat', bank: 'wallet', other: 'circle' };

function Metric({ label, value, trend, icon, tone, onClick }: { label: string; value: number; trend: string; icon: IconName; tone: 'purple' | 'green' | 'yellow' | 'blue'; onClick?: () => void }) {
  const tones = { purple: 'bg-[var(--color-primary)]/15 text-[var(--color-primary)]', green: 'bg-[var(--color-success)]/15 text-[var(--color-success)]', yellow: 'bg-[var(--color-warning)]/15 text-[var(--color-warning)]', blue: 'bg-[var(--color-secondary)]/15 text-[var(--color-secondary)]' };
  return <button onClick={onClick} className="ledger-card group min-h-[154px] p-5 text-left transition-transform duration-150 hover:-translate-y-0.5">
    <div className="flex items-start justify-between"><span className={`grid h-9 w-9 place-items-center rounded-full ${tones[tone]}`}><Icon name={icon} size={17} /></span><span className="text-[11px] text-[var(--color-text-muted)]">Ce mois</span></div>
    <p className="mt-4 text-xs font-medium text-[var(--color-text-secondary)]">{label}</p>
    <p className="font-financial mt-1 text-xl font-semibold tracking-tight text-white">{formatCFA(value)}</p>
    <p className={`mt-2 text-[11px] ${tone === 'yellow' ? 'text-[var(--color-warning)]' : tone === 'green' ? 'text-[var(--color-success)]' : 'text-[var(--color-text-muted)]'}`}>{trend}</p>
  </button>;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { data: accountsData, loading: accountsLoading } = useApiQuery<AccountRow[]>(fetchAccountsForDashboard, []);
  const { data: kpisData, loading: kpisLoading } = useApiQuery(() => fetchMonthlyActivityKpis('2026-08-01', '2026-08-31'), []);
  const { data: advancesData, loading: advancesLoading } = useApiQuery<PersonalAdvance[]>(fetchPersonalAdvances, []);
  const accounts = accountsData ?? [];
  const advances = advancesData ?? [];
  const totalBalance = accounts.reduce((sum, account) => sum + account.balance, 0);
  const period = kpisData?.period ?? { revenue: 0, expenses: 0, result: 0 };
  const activityRows = [
    { label: 'Assurance', value: kpisData?.assurance ?? { revenue: 0, expenses: 0, result: 0 }, path: '/assurance', icon: 'shield' as IconName },
    { label: 'Poulets', value: kpisData?.poulets ?? { revenue: 0, expenses: 0, result: 0 }, path: '/poulets', icon: 'package' as IconName },
    { label: 'VTC', value: kpisData?.vtc ?? { revenue: 0, expenses: 0, result: 0 }, path: '/vtc', icon: 'car' as IconName },
  ];
  const chartData = activityRows.map(row => ({ name: row.label, recettes: row.value.revenue, depenses: row.value.expenses }));
  const outstanding = advances.filter(advance => advance.status === 'pending_confirmation' || advance.status === 'disputed');

  if (accountsLoading || kpisLoading || advancesLoading) return <div className="grid min-h-64 place-items-center"><div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--color-primary)] border-t-transparent" /></div>;

  return <div className="dashboard-page space-y-6">
    <section className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div><p className="section-eyebrow">Synthèse financière</p><h2 className="mt-1 text-2xl font-semibold tracking-tight text-white">Vue d'ensemble</h2><p className="mt-1 text-sm text-[var(--color-text-secondary)]">Votre situation consolidée pour août 2026.</p></div>
      <button onClick={() => navigate('/transactions')} className="ledger-button inline-flex items-center justify-center gap-2"><Icon name="arrows" size={16} />Voir les transactions</button>
    </section>

    <section className="ledger-card ledger-card--glow relative overflow-hidden p-6 sm:p-7">
      <div className="absolute -right-20 -top-28 h-64 w-64 rounded-full bg-[var(--color-primary)]/10 blur-3xl" />
      <div className="relative flex flex-col gap-5 md:flex-row md:items-end md:justify-between"><div><p className="text-xs font-medium text-[var(--color-text-secondary)]">Trésorerie disponible</p><p className="font-financial mt-2 text-3xl font-semibold tracking-tight text-white sm:text-4xl">{formatCFA(totalBalance)}</p><p className={`mt-3 inline-flex items-center gap-1.5 text-xs font-medium ${period.result >= 0 ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]'}`}><Icon name="arrow-up-right" size={14} />{period.result >= 0 ? '+' : ''}{formatCFACompact(period.result)} de résultat ce mois</p></div><div className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm sm:flex sm:gap-8"><div><p className="text-[11px] text-[var(--color-text-muted)]">Activités</p><p className="mt-1 font-semibold text-white">3 actives</p></div><div><p className="text-[11px] text-[var(--color-text-muted)]">Comptes</p><p className="mt-1 font-semibold text-white">{accounts.length} connectés</p></div></div></div>
    </section>

    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Metric label="Recettes" value={period.revenue} trend="Encaissements de la période" icon="arrow-up-right" tone="green" onClick={() => navigate('/transactions')} />
      <Metric label="Dépenses" value={period.expenses} trend="Décaissements de la période" icon="arrows" tone="yellow" onClick={() => navigate('/transactions')} />
      <Metric label="Résultat net" value={period.result} trend={period.result >= 0 ? 'Performance positive' : 'À surveiller'} icon="chart" tone="purple" onClick={() => navigate('/rapports')} />
      <Metric label="À justifier" value={outstanding.length} trend={`${outstanding.length} opération(s) à traiter`} icon="clock" tone="blue" onClick={() => navigate('/avances')} />
    </section>

    <section className="grid gap-5 xl:grid-cols-5">
      <div className="ledger-card xl:col-span-3 p-5 sm:p-6"><div className="flex items-start justify-between"><div><h3 className="text-base font-semibold text-white">Flux par activité</h3><p className="mt-1 text-xs text-[var(--color-text-muted)]">Recettes et dépenses du mois</p></div><button onClick={() => navigate('/rapports')} className="icon-button grid h-8 w-8 place-items-center" title="Ouvrir les rapports"><Icon name="arrow-up-right" size={15} /></button></div><div className="mt-5 h-[250px]"><ResponsiveContainer width="100%" height="100%"><BarChart data={chartData} barGap={6} margin={{ top: 5, right: 0, left: -18, bottom: 0 }}><CartesianGrid vertical={false} stroke="var(--color-divider)" strokeDasharray="3 4" /><XAxis dataKey="name" tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} /><YAxis tickFormatter={formatCFACompact} tick={{ fill: 'var(--color-text-muted)', fontSize: 10 }} axisLine={false} tickLine={false} /><Tooltip formatter={(value: TooltipValueType | undefined) => formatCFA(Number(value ?? 0))} contentStyle={{ background: '#1C1C22', border: '1px solid rgba(255,255,255,.08)', borderRadius: 12, color: '#FFFFFF', fontSize: 12 }} /><Bar dataKey="recettes" name="Recettes" fill="var(--color-primary)" radius={[6, 6, 0, 0]} /><Bar dataKey="depenses" name="Dépenses" fill="var(--color-warning)" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div></div>
      <div className="ledger-card xl:col-span-2 p-5 sm:p-6"><div className="flex items-center justify-between"><div><h3 className="text-base font-semibold text-white">Comptes</h3><p className="mt-1 text-xs text-[var(--color-text-muted)]">Soldes disponibles</p></div><button onClick={() => navigate('/comptes')} className="text-xs font-medium text-[var(--color-secondary)]">Voir tout</button></div><div className="mt-5 space-y-2">{accounts.slice(0, 4).map(account => <button key={account.id} onClick={() => navigate('/comptes')} className="flex w-full items-center gap-3 rounded-xl p-3 text-left transition-colors hover:bg-white/[.045]"><span className="grid h-8 w-8 place-items-center rounded-full bg-white/[.06] text-[var(--color-secondary)]"><Icon name={accountIcons[account.type] ?? 'wallet'} size={15} /></span><span className="min-w-0 flex-1"><span className="block truncate text-xs font-medium text-white">{account.label}</span><span className="mt-0.5 block text-[11px] text-[var(--color-text-muted)]">Solde disponible</span></span><span className="font-financial text-xs font-semibold text-white">{formatCFA(account.balance)}</span></button>)}{accounts.length === 0 && <p className="py-8 text-center text-sm text-[var(--color-text-muted)]">Aucun compte disponible.</p>}</div></div>
    </section>

    <section className="ledger-card overflow-hidden"><div className="flex items-center justify-between px-5 py-4 sm:px-6"><div><h3 className="text-base font-semibold text-white">Performance des activités</h3><p className="mt-1 text-xs text-[var(--color-text-muted)]">Contribution au résultat de la période</p></div><button onClick={() => navigate('/rapports')} className="hidden text-xs font-medium text-[var(--color-secondary)] sm:block">Analyser</button></div><div className="border-t border-[var(--color-divider)]">{activityRows.map(row => <button key={row.label} onClick={() => navigate(row.path)} className="flex w-full items-center gap-4 border-b border-[var(--color-divider)] px-5 py-4 text-left last:border-b-0 hover:bg-white/[.035] sm:px-6"><span className="grid h-9 w-9 place-items-center rounded-full bg-[var(--color-primary)]/12 text-[var(--color-primary)]"><Icon name={row.icon} size={16} /></span><span className="min-w-0 flex-1"><span className="block text-sm font-medium text-white">{row.label}</span><span className="mt-1 block text-[11px] text-[var(--color-text-muted)]">Recettes {formatCFA(row.value.revenue)} · Dépenses {formatCFA(row.value.expenses)}</span></span><span className={`font-financial text-sm font-semibold ${row.value.result >= 0 ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]'}`}>{row.value.result >= 0 ? '+' : ''}{formatCFA(row.value.result)}</span><Icon name="chevron-right" size={16} className="text-[var(--color-text-muted)]" /></button>)}</div></section>
  </div>;
}
