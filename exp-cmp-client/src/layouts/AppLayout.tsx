// ─────────────────────────────────────────────────────────────
// AppLayout — coquille applicative authentifiée
// Sidebar + Header (période via contexte local) + <Outlet/>.
// L'état UI du shell (collapse, menu mobile) vit ici, comme
// dans layouts/AppLayout du monolithe frontend de référence.
// ─────────────────────────────────────────────────────────────

import { useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import Sidebar from '@/components/layout/Sidebar';
import Header from '@/components/layout/Header';
import Icon from '@/components/ui/Icon';
import { PeriodProvider } from './period';

export default function AppLayout() {
  const { profile } = useAuth();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const isAssistant = pathname.startsWith('/assistant');

  return (
    <PeriodProvider>
      <div className="flex h-full overflow-hidden" style={{ background: 'var(--color-background-primary)' }}>
        {mobileMenuOpen && (
          <div className="fixed inset-0 bg-navy-950/60 z-40 lg:hidden" onClick={() => setMobileMenuOpen(false)} />
        )}

        <div className={`fixed lg:relative z-50 lg:z-auto h-full transition-transform duration-200 ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}>
          <Sidebar
            collapsed={sidebarCollapsed}
            onToggleCollapse={() => setSidebarCollapsed(c => !c)}
            userName={profile?.full_name ?? 'Utilisateur'}
            userRole={profile?.role ?? 'root'}
          />
        </div>

        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <div className="lg:hidden flex h-14 items-center gap-3 px-4 bg-[var(--color-surface-primary)] border-b border-[var(--color-border)]">
            <button onClick={() => setMobileMenuOpen(true)} className="icon-button grid h-8 w-8 place-items-center" aria-label="Ouvrir la navigation"><Icon name="menu" size={18} /></button>
            <span className="text-white text-sm font-semibold">Expert Comptable</span>
          </div>

          <Header />

          <main className="ledger-main flex-1 overflow-y-auto">
            <Outlet />
          </main>
        </div>

        {/* Accès permanent à l'Assistant IA — visible depuis toutes les pages */}
        <button
          onClick={() => navigate('/assistant')}
          title="Ouvrir l'Assistant IA"
          className={`fixed bottom-6 right-6 z-30 flex items-center gap-2 rounded-full bg-gradient-to-r from-[var(--color-primary)] to-navy-700 px-5 py-3 text-sm font-semibold text-white shadow-[0_8px_30px_rgba(0,0,0,0.35)] transition-all hover:-translate-y-0.5 hover:shadow-[0_10px_40px_var(--color-primary-glow)] ${
            isAssistant ? 'pointer-events-none scale-0 opacity-0' : ''
          }`}
        >
          <Icon name="sparkles" size={18} />
          Assistant IA
        </button>
      </div>
    </PeriodProvider>
  );
}
