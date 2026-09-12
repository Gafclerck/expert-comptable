import { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import Icon from '@/components/ui/Icon';
import type { PageId } from '@/components/layout/Sidebar';
import { usePeriod, type Period } from '@/layouts/period';

const periods: { id: Period; label: string }[] = [{ id: 'today', label: "Aujourd'hui" }, { id: '7d', label: '7 jours' }, { id: 'month', label: 'Ce mois' }, { id: 'prev_month', label: 'Mois précédent' }, { id: 'year', label: 'Année' }];
const pageTitles: Record<PageId, string> = { dashboard: 'Vue globale', assurance: 'Assurance', poulets: 'Poulets', vtc: 'VTC', transactions: 'Transactions', creances: 'Créances & dettes', financements: 'Financements internes', comptes: 'Comptes & caisses', avances: 'Avances à justifier', personnes: 'Personnes', rappels: 'Rappels & alertes', assistant: 'Assistant IA', rapports: 'Rapports', documents: 'Documents', utilisateurs: 'Utilisateurs', audit: "Journal d'audit", parametres: 'Paramètres' };

export default function Header() {
  const [searchOpen, setSearchOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { pathname } = useLocation();
  const { period, setPeriod } = usePeriod();
  const currentPage = (pathname.slice(1) in pageTitles ? pathname.slice(1) : 'dashboard') as PageId;
  useEffect(() => { if (searchOpen) inputRef.current?.focus(); }, [searchOpen]);

  return <header className="ledger-topbar relative z-20 flex h-[72px] shrink-0 items-center gap-4 border-b border-[var(--color-border)] px-6">
    <div><h1 className="text-base font-semibold text-white">{pageTitles[currentPage]}</h1><p className="mt-0.5 hidden text-[11px] text-[var(--color-text-muted)] xl:block">{new Date().toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })}</p></div>
    <div className="hidden xl:flex rounded-full border border-[var(--color-border)] bg-[var(--color-surface-elevated)] p-1">
      {periods.map(item => <button key={item.id} onClick={() => setPeriod(item.id)} className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${period === item.id ? 'bg-[var(--color-primary)] text-white shadow-[0_0_14px_var(--color-primary-glow)]' : 'text-[var(--color-text-secondary)] hover:text-white'}`}>{item.label}</button>)}
    </div>
    <div className="flex-1" />
    {searchOpen ? <div className="flex h-9 items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-surface-elevated)] px-3"><Icon name="search" size={16} className="text-[var(--color-text-muted)]" /><input ref={inputRef} onBlur={() => setSearchOpen(false)} onKeyDown={event => event.key === 'Escape' && setSearchOpen(false)} placeholder="Rechercher…" className="w-36 bg-transparent text-xs text-white outline-none placeholder:text-[var(--color-text-muted)] sm:w-52" /></div> : <button onClick={() => setSearchOpen(true)} className="icon-button grid h-9 w-9 place-items-center" title="Recherche"><Icon name="search" size={17} /></button>}
  </header>;
}
