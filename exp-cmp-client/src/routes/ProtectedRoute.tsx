// ─────────────────────────────────────────────────────────────
// ProtectedRoute — garde d'authentification
// Affiche un écran de chargement pendant la session, redirige
// vers /login si non connecté, sinon rend le layout enfant.
// ─────────────────────────────────────────────────────────────

import { Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

function LoadingScreen() {
  return (
    <div className="h-full flex items-center justify-center" style={{ background: 'var(--color-background-primary)' }}>
      <div className="text-center">
        <div className="w-10 h-10 rounded-xl bg-[var(--color-primary)] flex items-center justify-center text-white text-sm font-bold font-mono mx-auto">EC</div>
        <div className="text-sm text-slate-500">Chargement…</div>
      </div>
    </div>
  );
}

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}