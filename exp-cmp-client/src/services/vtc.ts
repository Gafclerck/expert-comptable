// ─────────────────────────────────────────────────────────────
// Service VTC — véhicules, chauffeurs, affectations, versements,
// dépenses et indicateurs du module backend `vtc`.
// Chaque fonction correspond à un endpoint du module.
// ─────────────────────────────────────────────────────────────

import { api } from '../lib/api';
import type {
  AffectationOut, AffectationStatus, ChauffeurOut, ChauffeurStatus,
  DepenseOut, ResumeFinancierOut, StatutPaiementOut,
  StatistiquesVehiculeOut, VehiculeOut, VehiculeStatus, VersementOut,
} from '../types/api';

// ─── Payloads ─────────────────────────────────────────────────

export interface ChauffeurCreatePayload {
  full_name: string;
  phone?: string | null;
  license_number?: string | null;
}

export interface ChauffeurUpdateStatusPayload {
  status: ChauffeurStatus;
}

export interface VehiculeCreatePayload {
  make: string;
  model: string;
  year?: number | null;
  registration: string;
  acquisition_cost?: number;
}

export interface VehiculeUpdatePayload {
  make?: string;
  model?: string;
  year?: number | null;
  registration?: string;
  acquisition_cost?: number;
}

export interface VehiculeUpdateStatusPayload {
  status: VehiculeStatus;
}

export interface AffectationCreatePayload {
  driver_id: string;
  vehicle_id: string;
  start_date: string;
  end_date?: string | null;
  expected_amount: number;
  terms?: string | null;
}

export interface AffectationEndPayload {
  end_date?: string | null;
}

export interface VersementCreatePayload {
  driver_id: string;
  vehicle_id: string;
  amount: number;
  account_id: string;
  category_id: string;
  occurred_at?: string | null;
}

export type DepenseExpenseType =
  | 'fuel' | 'maintenance' | 'repair' | 'tires'
  | 'insurance' | 'registration' | 'misc';

export interface DepenseCreatePayload {
  vehicle_id: string;
  expense_type: DepenseExpenseType;
  amount: number;
  quantity?: number | null;
  unit?: string | null;
  description?: string | null;
  account_id: string;
  category_id: string;
  occurred_at?: string | null;
}

export interface IndisponibiliteCreatePayload {
  vehicle_id: string;
  start_date: string;
  end_date?: string | null;
  reason?: string | null;
}

export interface IndisponibiliteEndPayload {
  end_date?: string | null;
}

// ─── Chauffeurs ───────────────────────────────────────────────

export async function fetchVtcChauffeurs(status?: ChauffeurStatus): Promise<ChauffeurOut[]> {
  const query = status ? `?status=${status}` : '';
  const data = await api.get<ChauffeurOut[]>(`/vtc/chauffeurs${query}`);
  return data ?? [];
}

// ─── Véhicules ────────────────────────────────────────────────

export async function fetchVtcVehicules(status?: VehiculeStatus): Promise<VehiculeOut[]> {
  const query = status ? `?status=${status}` : '';
  const data = await api.get<VehiculeOut[]>(`/vtc/vehicules${query}`);
  return data ?? [];
}

export async function fetchVtcVehiculeStats(vehicleId: string): Promise<StatistiquesVehiculeOut> {
  return api.get<StatistiquesVehiculeOut>(`/vtc/vehicules/${vehicleId}/stats`);
}

// ─── Affectations ─────────────────────────────────────────────

export interface AffectationFilters {
  driverId?: string;
  vehicleId?: string;
  status?: AffectationStatus;
}

export async function fetchVtcAffectations(filters: AffectationFilters = {}): Promise<AffectationOut[]> {
  const params = new URLSearchParams();
  if (filters.driverId) params.set('driver_id', filters.driverId);
  if (filters.vehicleId) params.set('vehicle_id', filters.vehicleId);
  if (filters.status) params.set('status', filters.status);
  const query = params.toString();
  const data = await api.get<AffectationOut[]>(`/vtc/affectations${query ? `?${query}` : ''}`);
  return data ?? [];
}

// ─── Versements & dépenses ────────────────────────────────────

export async function fetchVtcVersements(filters: { driverId?: string; vehicleId?: string } = {}): Promise<VersementOut[]> {
  const params = new URLSearchParams();
  if (filters.driverId) params.set('driver_id', filters.driverId);
  if (filters.vehicleId) params.set('vehicle_id', filters.vehicleId);
  const query = params.toString();
  const data = await api.get<VersementOut[]>(`/vtc/versements${query ? `?${query}` : ''}`);
  return data ?? [];
}

export async function fetchVtcDepenses(filters: { vehicleId?: string } = {}): Promise<DepenseOut[]> {
  const query = filters.vehicleId ? `?vehicle_id=${filters.vehicleId}` : '';
  const data = await api.get<DepenseOut[]>(`/vtc/depenses${query}`);
  return data ?? [];
}

// ─── Indicateurs ──────────────────────────────────────────────

export async function fetchVtcStatutPaiement(driverId: string): Promise<StatutPaiementOut> {
  return api.get<StatutPaiementOut>(`/vtc/paiements/${driverId}`);
}

export async function fetchVtcResumeFinancier(start?: string, end?: string): Promise<ResumeFinancierOut> {
  const params = new URLSearchParams();
  if (start) params.set('start', start);
  if (end) params.set('end', end);
  const query = params.toString();
  return api.get<ResumeFinancierOut>(`/vtc/resume-financier${query ? `?${query}` : ''}`);
}

// ─── Écritures — Chauffeurs ───────────────────────────────────

export async function createVtcChauffeur(payload: ChauffeurCreatePayload): Promise<ChauffeurOut> {
  return api.post<ChauffeurOut>('/vtc/chauffeurs', payload);
}

export async function updateVtcChauffeurStatus(chauffeurId: string, payload: ChauffeurUpdateStatusPayload): Promise<ChauffeurOut> {
  return api.patch<ChauffeurOut>(`/vtc/chauffeurs/${chauffeurId}/status`, payload);
}

// ─── Écritures — Véhicules ────────────────────────────────────

export async function createVtcVehicule(payload: VehiculeCreatePayload): Promise<VehiculeOut> {
  return api.post<VehiculeOut>('/vtc/vehicules', payload);
}

export async function updateVtcVehicule(vehiculeId: string, payload: VehiculeUpdatePayload): Promise<VehiculeOut> {
  return api.patch<VehiculeOut>(`/vtc/vehicules/${vehiculeId}`, payload);
}

export async function updateVtcVehiculeStatus(vehiculeId: string, payload: VehiculeUpdateStatusPayload): Promise<VehiculeOut> {
  return api.patch<VehiculeOut>(`/vtc/vehicules/${vehiculeId}/status`, payload);
}

// ─── Écritures — Affectations ─────────────────────────────────

export async function createVtcAffectation(payload: AffectationCreatePayload): Promise<AffectationOut> {
  return api.post<AffectationOut>('/vtc/affectations', payload);
}

export async function endVtcAffectation(affectationId: string, payload: AffectationEndPayload = {}): Promise<AffectationOut> {
  return api.patch<AffectationOut>(`/vtc/affectations/${affectationId}/end`, payload);
}

// ─── Écritures — Versements ───────────────────────────────────

export async function createVtcVersement(payload: VersementCreatePayload): Promise<VersementOut> {
  return api.post<VersementOut>('/vtc/versements', payload);
}

// ─── Écritures — Dépenses ─────────────────────────────────────

export async function createVtcDepense(payload: DepenseCreatePayload): Promise<DepenseOut> {
  return api.post<DepenseOut>('/vtc/depenses', payload);
}

// ─── Écritures — Indisponibilités ─────────────────────────────

export async function createVtcIndisponibilite(payload: IndisponibiliteCreatePayload): Promise<unknown> {
  return api.post('/vtc/indisponibilites', payload);
}

export async function closeVtcIndisponibilite(indispoId: string, payload: IndisponibiliteEndPayload = {}): Promise<unknown> {
  return api.patch(`/vtc/indisponibilites/${indispoId}/close`, payload);
}
