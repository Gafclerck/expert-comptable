// ─────────────────────────────────────────────────────────────
// Hook useTransactions — liste + création d'écritures (ledger)
// Compose le service ledger (fetchTransactions / createTransaction)
// et expose un état unifié (+ refetch, + création avec retour
// d'erreur). Aucune logique API ici : tout passe par les services.
// ─────────────────────────────────────────────────────────────

import { useCallback, useState } from 'react';
import { useApiQuery } from './useApiQuery';
import { createTransaction, fetchTransactions } from '@/services/ledger';
import type { TransactionCreate, TransactionOut } from '@/types/api';

export function useTransactions(businessId?: string) {
  const { data, loading, error, refetch } = useApiQuery<TransactionOut[]>(
    () => fetchTransactions({ businessId, limit: 1000 }),
    [businessId]
  );
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const create = useCallback(
    async (payload: TransactionCreate): Promise<TransactionOut> => {
      setCreating(true);
      setCreateError(null);
      try {
        const txn = await createTransaction(payload);
        setCreating(false);
        refetch();
        return txn;
      } catch (err) {
        setCreating(false);
        setCreateError(err instanceof Error ? err.message : 'Erreur lors de l\u2019enregistrement');
        throw err;
      }
    },
    [refetch]
  );

  return {
    transactions: data ?? [],
    loading,
    error,
    refetch,
    create,
    creating,
    createError,
    resetCreateError: () => setCreateError(null),
  };
}