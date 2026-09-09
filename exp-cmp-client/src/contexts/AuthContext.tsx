// ─────────────────────────────────────────────────────────────
// AuthContext — état de session (JWT FastAPI)
// S'appuie sur `services/auth` (login/me) et `lib/tokenStore`.
// Ne connaît pas HTTP : la transport gère le refresh.
// ─────────────────────────────────────────────────────────────

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { login as apiLogin, getMe, logout as apiLogout, tokenStore } from '@/services/auth';
import type { MeOut } from '@/types/api';
import { ApiError } from '@/lib/api';

export interface Profile {
  full_name: string;
  role: 'root' | 'utilisateur';
}

interface AuthContextValue {
  user: MeOut | null;
  profile: Profile | null;
  loading: boolean;
  isRoot: boolean;
  signIn: (email: string, password: string) => Promise<{ error: string | null }>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function toProfile(user: MeOut): Profile {
  return {
    full_name: user.full_name ?? user.email,
    role: user.roles.includes('root') ? 'root' : 'utilisateur',
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MeOut | null>(null);
  const [loading, setLoading] = useState(true);

  const applyUser = (u: MeOut | null) => {
    setUser(u);
  };

  useEffect(() => {
    let cancelled = false;
    if (!tokenStore.hasTokens()) {
      setLoading(false);
      return;
    }
    getMe()
      .then((me) => { if (!cancelled) applyUser(me); })
      .catch(() => { if (!cancelled) tokenStore.clear(); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const signIn = async (email: string, password: string): Promise<{ error: string | null }> => {
    try {
      const { me } = await apiLogin(email, password);
      applyUser(me);
      return { error: null };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erreur de connexion';
      return { error: message };
    }
  };

  const signOut = async () => {
    await apiLogout();
    applyUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        profile: user ? toProfile(user) : null,
        loading,
        isRoot: Boolean(user?.roles.includes('root')),
        signIn,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

export { ApiError };