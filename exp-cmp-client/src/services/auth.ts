// ─────────────────────────────────────────────────────────────
// Service Auth — session utilisateur (login, refresh, me, mdp)
// La rotation des jetons (refresh auto sur 401) est gérée par
// la couche de transport (`lib/api.ts`) ; ce service ne fait que
// décrire les endpoints du module backend `identity`.
// ─────────────────────────────────────────────────────────────

import { api } from '../lib/api';
import { tokenStore } from '../lib/tokenStore';
import { fetchBusinesses } from './identity';
import type { LoginResponse, MeOut } from '../types/api';

export { tokenStore };

export interface LoginResult {
  me: MeOut;
  tokens: LoginResponse;
}

export async function login(email: string, password: string): Promise<LoginResult> {
  const tokens = await api.postForm<LoginResponse>('/auth/login', {
    username: email,
    password,
  });
  tokenStore.setTokens(tokens);
  const me = await api.get<MeOut>('/auth/me');
  await primeBusinessRegistry();
  return { me, tokens };
}

export async function getMe(): Promise<MeOut> {
  const me = await api.get<MeOut>('/auth/me');
  await primeBusinessRegistry();
  return me;
}

export async function changePassword(ancienMotDePasse: string, nouveauMotDePasse: string): Promise<void> {
  await api.post<{ detail: string }>('/auth/change-password', {
    ancien_mot_de_passe: ancienMotDePasse,
    nouveau_mot_de_passe: nouveauMotDePasse,
  });
}

export async function logout(): Promise<void> {
  tokenStore.clear();
}

// Précharge le registre des activités (cache identity) dès que
// la session est connue, pour un usage immédiat dans les pages.
async function primeBusinessRegistry(): Promise<void> {
  await fetchBusinesses();
}