// ─────────────────────────────────────────────────────────────
// Contexte local de période — état UI du filtre de temps
// Partagé entre le Header (sélecteur) et les pages du layout.
// Portée locale au sous-arbre <AppLayout/> : aucune fuite vers
// les routes / le reste de l'app.
// ─────────────────────────────────────────────────────────────

import { createContext, useContext, useState, type ReactNode } from 'react';

export type Period = 'today' | '7d' | 'month' | 'prev_month' | 'year' | 'custom';

interface PeriodContextValue {
  period: Period;
  setPeriod: (p: Period) => void;
}

const PeriodContext = createContext<PeriodContextValue | null>(null);

export function PeriodProvider({ children }: { children: ReactNode }) {
  const [period, setPeriod] = useState<Period>('month');
  return (
    <PeriodContext.Provider value={{ period, setPeriod }}>
      {children}
    </PeriodContext.Provider>
  );
}

export function usePeriod(): PeriodContextValue {
  const ctx = useContext(PeriodContext);
  if (!ctx) throw new Error('usePeriod must be used within PeriodProvider');
  return ctx;
}