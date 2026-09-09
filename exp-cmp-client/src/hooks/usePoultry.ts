// ─────────────────────────────────────────────────────────────
// Hook usePoultryData — agrégat des données poulailler backend
// Compose les 4 appels du service poultry (lots, achats, ventes,
// stock) et expose un résultat unifié + refetch global. Aucune
// logique API ici : tout passe par `@/services/poultry`.
// ─────────────────────────────────────────────────────────────

import { useApiQuery } from './useApiQuery';
import {
  fetchPoultryLots,
  fetchPoultryPurchases,
  fetchPoultrySales,
  fetchPoultryStock,
} from '@/services/poultry';
import type {
  PoultryLotOut,
  PoultryPurchaseOut,
  PoultrySaleOut,
} from '@/types/api';

export interface PoultryData {
  lots: PoultryLotOut[];
  purchases: PoultryPurchaseOut[];
  sales: PoultrySaleOut[];
  stock: number;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function usePoultryData(): PoultryData {
  const lots = useApiQuery<PoultryLotOut[]>(fetchPoultryLots, []);
  const purchases = useApiQuery<PoultryPurchaseOut[]>(fetchPoultryPurchases, []);
  const sales = useApiQuery<PoultrySaleOut[]>(fetchPoultrySales, []);
  const stock = useApiQuery<{ total_quantity: number }>(fetchPoultryStock, []);

  const loading = lots.loading || purchases.loading || sales.loading || stock.loading;
  const error = lots.error ?? purchases.error ?? sales.error ?? stock.error;
  const refetch = () => {
    lots.refetch();
    purchases.refetch();
    sales.refetch();
    stock.refetch();
  };

  return {
    lots: lots.data ?? [],
    purchases: purchases.data ?? [],
    sales: sales.data ?? [],
    stock: stock.data?.total_quantity ?? 0,
    loading,
    error,
    refetch,
  };
}