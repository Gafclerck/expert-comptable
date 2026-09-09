// ─────────────────────────────────────────────────────────────
// Services MOCK — modules métier NON encore livrés par le backend
// (P0 : creances, financements, poulets, vtc, alertes, documents,
// avances personnelles). Retourne les données de `data/mock.ts`
// avec un délai simulé — UI immédiatement fonctionnelle.
//
// ⚠ À remplacer par des endpoints backend dès que les modules
// correspondants (B2..B4, P3) existeront.
// ─────────────────────────────────────────────────────────────

import * as mock from '../data/mock';
import type {
  Alert, Creance, Document, Driver, InternalFunding,
  Person, PersonalAdvance, PoultryLot, Vehicle,
} from '../types';

const delay = 250;

function simulate<T>(data: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(data), delay));
}

// ─── Créances & Dettes ────────────────────────────────────────

export async function fetchCreances(): Promise<Creance[]> {
  return simulate(mock.creances);
}

// ─── Financements internes ────────────────────────────────────

export async function fetchInternalFundings(): Promise<InternalFunding[]> {
  return simulate(mock.internalFundings);
}

// ─── Poulets (lots) ───────────────────────────────────────────

export async function fetchPoultryLots(): Promise<PoultryLot[]> {
  return simulate(mock.poultryLots);
}

// ─── VTC (véhicules & chauffeurs) ─────────────────────────────

export async function fetchVehicles(): Promise<Vehicle[]> {
  return simulate(mock.vehicles);
}

export async function fetchDrivers(): Promise<Driver[]> {
  return simulate(mock.drivers);
}

// ─── Alertes / Rappels ────────────────────────────────────────

export async function fetchAlerts(): Promise<Alert[]> {
  return simulate(mock.alerts);
}

export function subscribeToAlerts(_callback: () => void): { unsubscribe: () => void } {
  return { unsubscribe: () => {} };
}

export async function resolveAlert(id: string): Promise<void> {
  return simulate(undefined).then(() => {
    mock.alerts.forEach(a => { if (a.id === id) a.resolved = true; });
  });
}

// ─── Documents ────────────────────────────────────────────────

export async function fetchDocuments(): Promise<Document[]> {
  return simulate(mock.documents);
}

export async function uploadDocument(): Promise<void> {
  return simulate(undefined);
}

export async function getDocumentUrl(_storagePath: string): Promise<string> {
  return Promise.resolve('');
}

// ─── Avances personnelles ─────────────────────────────────────

export async function fetchPersonalAdvances(): Promise<PersonalAdvance[]> {
  return simulate(mock.personalAdvances);
}

// ─── Personnes (vue contrôle : avances, retenues) ────────────
// Utilise les données mock tant que le module "avances
// personnelles" (P4) n'est pas livré — le backend identity
// ne fournit que l'identité, pas les agrégats de contrôle.

export async function fetchPeople(): Promise<Person[]> {
  return simulate(mock.people);
}