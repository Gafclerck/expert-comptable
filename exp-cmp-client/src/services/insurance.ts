// ─────────────────────────────────────────────────────────────
// Service Insurance — clients, contrats, paiements assurance
// Chaque fonction correspond à un endpoint du module backend
// `insurance`. Le paiement d'un contrat crée automatiquement
// une transaction ledger côté backend (transaction_id retourné).
// ─────────────────────────────────────────────────────────────

import { api } from '../lib/api';
import type { InsuranceClientOut, InsuranceContractOut, InsurancePaymentOut } from '../types/api';

// ─── Clients ──────────────────────────────────────────────────

export async function fetchInsuranceClients(): Promise<InsuranceClientOut[]> {
  const data = await api.get<InsuranceClientOut[]>('/insurance/clients?skip=0&limit=200');
  return data ?? [];
}

export interface InsuranceClientCreatePayload {
  full_name: string;
  phone?: string | null;
  client_number?: string | null;
}

export async function createInsuranceClient(payload: InsuranceClientCreatePayload): Promise<InsuranceClientOut> {
  return api.post<InsuranceClientOut>('/insurance/clients', payload);
}

export async function fetchInsuranceClient(clientId: string): Promise<InsuranceClientOut> {
  return api.get<InsuranceClientOut>(`/insurance/clients/${clientId}`);
}

// ─── Contrats ─────────────────────────────────────────────────

export interface InsuranceContractCreatePayload {
  matricule: string;
  contract_type: string;
  premium: number;
  start_date: string;
  end_date?: string | null;
}

export async function fetchClientContracts(clientId: string): Promise<InsuranceContractOut[]> {
  const data = await api.get<InsuranceContractOut[]>(`/insurance/clients/${clientId}/contracts?skip=0&limit=100`);
  return data ?? [];
}

export async function createInsuranceContract(clientId: string, payload: InsuranceContractCreatePayload): Promise<InsuranceContractOut> {
  return api.post<InsuranceContractOut>(`/insurance/clients/${clientId}/contracts`, payload);
}

export async function fetchInsuranceContract(contractId: string): Promise<InsuranceContractOut> {
  return api.get<InsuranceContractOut>(`/insurance/contracts/${contractId}`);
}

// ─── Paiements ────────────────────────────────────────────────

export interface InsurancePaymentCreatePayload {
  amount: number;
  paid_at?: string | null;
  account_id: string;
  category_id: string;
}

export async function fetchContractPayments(contractId: string): Promise<InsurancePaymentOut[]> {
  const data = await api.get<InsurancePaymentOut[]>(`/insurance/contracts/${contractId}/payments?skip=0&limit=100`);
  return data ?? [];
}

export async function createInsurancePayment(contractId: string, payload: InsurancePaymentCreatePayload): Promise<InsurancePaymentOut> {
  return api.post<InsurancePaymentOut>(`/insurance/contracts/${contractId}/payments`, payload);
}