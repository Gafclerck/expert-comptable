// ─────────────────────────────────────────────────────────────
// PublicRoute — pages accessibles hors session (login)
// Redirige vers /dashboard si un utilisateur est déjà connecté.
// ─────────────────────────────────────────────────────────────

import { Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

export default function PublicRoute({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  if (user) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}