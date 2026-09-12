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
