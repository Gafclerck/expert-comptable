// ─────────────────────────────────────────────────────────────
// Service Dashboard — agrégats de la vue globale
// Compose les services ledger + identity (business registry)
// pour produire les modèles de vue du tableau de bord :
// soldes par compte et KPIs par activité sur une période.
// ─────────────────────────────────────────────────────────────

import type { ActivityId, AccountType } from '../types';
import { fetchAccounts, fetchAccountBalance, fetchTransactions } from './ledger';
import { getCachedBusinesses, resolveBusinessId } from './identity';

export interface AccountRow {
  id: string;
  type: AccountType;
  label: string;
  balance: number;
}

export interface ActivityKpis {
  revenue: number;
  expenses: number;
  result: number;
}

export interface PeriodKpisByActivity {
  period: ActivityKpis;
  assurance: ActivityKpis;
  poulets: ActivityKpis;
  vtc: ActivityKpis;
}

export async function fetchAccountsForDashboard(): Promise<AccountRow[]> {
  const accounts = await fetchAccounts();
  const rows = await Promise.all(
    accounts.map(async (account) => {
      const balance = await fetchAccountBalance(account.id).catch(() => null);
      return {
        id: account.id,
        type: account.type,
        label: account.name,
        balance: balance?.balance ?? account.opening_balance,
      } as AccountRow;
    })
  );
  return rows;
}

const ACTIVITY_CODES: ActivityId[] = ['assurance', 'poulets', 'vtc'];

async function activityKpis(code: ActivityId, startDate: string, endDate: string): Promise<ActivityKpis> {
  const businessId = await resolveBusinessId(code);
  if (!businessId) return { revenue: 0, expenses: 0, result: 0 };

  const transactions = await fetchTransactions({ businessId, limit: 500 });
  const start = new Date(`${startDate}T00:00:00`);
  const end = new Date(`${endDate}T23:59:59.999`);

  const inPeriod = transactions.filter((tx) => {
    const at = new Date(tx.occurred_at);
    return at >= start && at <= end;
  });

  const revenue = inPeriod
    .filter((tx) => tx.type === 'revenue')
    .reduce((sum, tx) => sum + Number(tx.amount), 0);
  const expenses = inPeriod
    .filter((tx) => tx.type === 'expense')
    .reduce((sum, tx) => sum + Number(tx.amount), 0);

  return { revenue, expenses, result: revenue - expenses };
}

export async function fetchMonthlyActivityKpis(startDate: string, endDate: string): Promise<PeriodKpisByActivity> {
  const [assurance, poulets, vtc] = await Promise.all(
    ACTIVITY_CODES.map((code) => activityKpis(code, startDate, endDate))
  );

  const total = (key: 'revenue' | 'expenses') => assurance[key] + poulets[key] + vtc[key];
  const period = {
    revenue: total('revenue'),
    expenses: total('expenses'),
    result: total('revenue') - total('expenses'),
  };

  return { period, assurance, poulets, vtc };
}

// Élargit le registre des activités disponibles (pour les menus).
export async function fetchAvailableActivities(): Promise<ActivityId[]> {
  const businesses = getCachedBusinesses();
  return ACTIVITY_CODES.filter((code) => businesses.some((b) => b.code === code));
}