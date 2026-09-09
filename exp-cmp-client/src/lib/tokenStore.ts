// ─────────────────────────────────────────────────────────────
// TokenStore — persistance des jetons JWT (transport-level)
// Ne connaît ni HTTP ni le domaine : seule source de vérité
// des jetons access/refresh pour le client API.
// ─────────────────────────────────────────────────────────────

const ACCESS_KEY = 'ec.access_token';
const REFRESH_KEY = 'ec.refresh_token';

interface TokenPair {
  access_token: string;
  refresh_token: string;
}

export const tokenStore = {
  getAccessToken(): string | null {
    return window.localStorage.getItem(ACCESS_KEY);
  },

  getRefreshToken(): string | null {
    return window.localStorage.getItem(REFRESH_KEY);
  },

  hasTokens(): boolean {
    return Boolean(this.getAccessToken());
  },

  setTokens(tokens: TokenPair): void {
    window.localStorage.setItem(ACCESS_KEY, tokens.access_token);
    window.localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  },

  clear(): void {
    window.localStorage.removeItem(ACCESS_KEY);
    window.localStorage.removeItem(REFRESH_KEY);
  },
};