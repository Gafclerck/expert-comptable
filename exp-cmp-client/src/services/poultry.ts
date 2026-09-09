// ─────────────────────────────────────────────────────────────
// Service Poultry — lots, achats, ventes, stock du poulailler
// Chaque fonction correspond à un endpoint du module backend
// `poultry` (B2). Un achat crée un lot et débite la caisse ; une
// vente prélève en FIFO et crédite la caisse (transaction_id).
// ─────────────────────────────────────────────────────────────

import { api } from '../lib/api';
import type {
  PoultryLotOut,
  PoultryPurchaseCreate,
  PoultryPurchaseOut,
  PoultrySaleCreate,
  PoultrySaleOut,
  PoultryStockOut,
} from '../types/api';

// ─── Lots ─────────────────────────────────────────────────────

export async function fetchPoultryLots(): Promise<PoultryLotOut[]> {
  const data = await api.get<PoultryLotOut[]>('/poultry/lots?skip=0&limit=200');
  return data ?? [];
}

// ─── Achats (approvisionnements) ─────────────────────────────

export async function fetchPoultryPurchases(): Promise<PoultryPurchaseOut[]> {
  const data = await api.get<PoultryPurchaseOut[]>('/poultry/purchases?skip=0&limit=200');
  return data ?? [];
}

export async function createPoultryPurchase(payload: PoultryPurchaseCreate): Promise<PoultryPurchaseOut> {
  return api.post<PoultryPurchaseOut>('/poultry/purchases', payload);
}

// ─── Ventes ───────────────────────────────────────────────────

export async function fetchPoultrySales(): Promise<PoultrySaleOut[]> {
  const data = await api.get<PoultrySaleOut[]>('/poultry/sales?skip=0&limit=200');
  return data ?? [];
}

export async function createPoultrySale(payload: PoultrySaleCreate): Promise<PoultrySaleOut> {
  return api.post<PoultrySaleOut>('/poultry/sales', payload);
}

// ─── Stock ────────────────────────────────────────────────────

export async function fetchPoultryStock(): Promise<PoultryStockOut> {
  return api.get<PoultryStockOut>('/poultry/stock');
}