// ─────────────────────────────────────────────────────────────
// Service Ledger — comptes, catégories, transactions, transferts
// Chaque fonction correspond à un endpoint du module backend
// `ledger`. Les fonctions de liste prennent un `businessId`
// optionnel afin de respecter le périmètre d'un utilisateur.
// ─────────────────────────────────────────────────────────────

import { api } from '../lib/api';
import type {
  AccountBalanceOut, AccountOut, AccountType,
  CategoryOut, TransactionCreate, TransactionOut, TransferCreate, TransferOut,
} from '../types/api';

// ─── Comptes ──────────────────────────────────────────────────

export async function fetchAccounts(businessId?: string): Promise<AccountOut[]> {
  const query = businessId ? `?business_id=${businessId}&skip=0&limit=200` : '?skip=0&limit=200';
  const data = await api.get<AccountOut[]>(`/ledger/accounts${query}`);
  return data ?? [];
}

export interface AccountCreatePayload {
  business_id: string;
  name: string;
  type?: AccountType;
  currency?: string;
  opening_balance?: number;
}

export async function createAccount(payload: AccountCreatePayload): Promise<AccountOut> {
  return api.post<AccountOut>('/ledger/accounts', payload);
}

export async function fetchAccountBalance(accountId: string): Promise<AccountBalanceOut> {
  return api.get<AccountBalanceOut>(`/ledger/accounts/${accountId}/balance`);
}

// ─── Catégories ───────────────────────────────────────────────

export async function fetchCategories(): Promise<CategoryOut[]> {
  const data = await api.get<CategoryOut[]>('/ledger/categories');
  return data ?? [];
}

export async function createCategory(payload: { code: string; name: string; type: 'credit' | 'debit' }): Promise<CategoryOut> {
  return api.post<CategoryOut>('/ledger/categories', payload);
}

// ─── Transactions ─────────────────────────────────────────────

export interface TransactionFilters {
  businessId?: string;
  accountId?: string;
  skip?: number;
  limit?: number;
}

// Le backend plafonne chaque page a `limit <= 200` : on page en interne
// pour satisfaire le `limit` demande, quel que soit son ordre de grandeur.
const TRANSACTION_PAGE_SIZE = 200;

async function fetchTransactionsPage(
  filters: TransactionFilters,
  skip: number,
  limit: number
): Promise<TransactionOut[]> {
  const params = new URLSearchParams();
  if (filters.businessId) params.set('business_id', filters.businessId);
  if (filters.accountId) params.set('account_id', filters.accountId);
  params.set('skip', String(skip));
  params.set('limit', String(limit));
  const data = await api.get<TransactionOut[]>(`/ledger/transactions?${params.toString()}`);
  return data ?? [];
}

export async function fetchTransactions(filters: TransactionFilters = {}): Promise<TransactionOut[]> {
  const requested = filters.limit ?? 200;
  const collected: TransactionOut[] = [];
  let skip = filters.skip ?? 0;
  // Boucle bornee (25 pages max) pour eviter les boucles infinies.
  for (let page = 0; page < 25 && collected.length < requested; page++) {
    const rows = await fetchTransactionsPage(filters, skip, TRANSACTION_PAGE_SIZE);
    collected.push(...rows);
    skip += rows.length;
    if (rows.length < TRANSACTION_PAGE_SIZE) break;
  }
  return collected.slice(0, requested);
}

export async function createTransaction(payload: TransactionCreate): Promise<TransactionOut> {
  return api.post<TransactionOut>('/ledger/transactions', payload);
}

export async function fetchTransaction(transactionId: string): Promise<TransactionOut> {
  return api.get<TransactionOut>(`/ledger/transactions/${transactionId}`);
}

// ─── Transferts ───────────────────────────────────────────────

export async function fetchTransfers(): Promise<TransferOut[]> {
  const data = await api.get<TransferOut[]>('/ledger/transfers?skip=0&limit=200');
  return data ?? [];
}

export async function createTransfer(payload: TransferCreate): Promise<TransferOut> {
  return api.post<TransferOut>('/ledger/transfers', payload);
}