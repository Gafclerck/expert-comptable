// ─────────────────────────────────────────────────────────────
// Client API — couche de transport (fetch + JWT)
// Responsabilités :
//   - construction des URLs à partir du point de montage `/api`
//   - injection du jeton Bearer
//   - refresh du jeton avec single-flight sur erreur 401
//   - normalisation des erreurs FastAPI ({ detail })
// Ne contient AUCUNE logique métier : les services définissent
// les appels de domaine par-dessus cette couche.
// ─────────────────────────────────────────────────────────────

import { tokenStore } from './tokenStore';

const API_BASE = (import.meta.env.VITE_API_URL ?? '/api').replace(/\/+$/, '');

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

function buildUrl(path: string): string {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE}${cleanPath}`;
}

function extractMessage(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && 'detail' in detail) {
    return extractMessage((detail as { detail: unknown }).detail);
  }
  if (Array.isArray(detail)) {
    return detail.map((d) => d?.msg ?? JSON.stringify(d)).join(' · ');
  }
  return 'Erreur inconnue';
}

let refreshPromise: Promise<boolean> | null = null;

async function tryRefreshTokens(): Promise<boolean> {
  const refreshToken = tokenStore.getRefreshToken();
  if (!refreshToken) return false;
  try {
    const res = await fetch(buildUrl('/auth/refresh'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) {
      tokenStore.clear();
      return false;
    }
    const data = await res.json();
    tokenStore.setTokens(data);
    return true;
  } catch {
    tokenStore.clear();
    return false;
  }
}

async function rawFetch(path: string, options: RequestInit): Promise<Response> {
  const url = buildUrl(path);

  const headers = new Headers(options.headers);
  const hasBody = options.body != null;
  if (hasBody && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const accessToken = tokenStore.getAccessToken();
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);

  let res = await fetch(url, { ...options, headers });

  if (res.status === 401 && tokenStore.hasTokens()) {
    // Single-flight : un seul refresh concurrent, les autres attendent.
    refreshPromise ??= tryRefreshTokens().finally(() => { refreshPromise = null; });
    const refreshed = await refreshPromise;
    if (refreshed) {
      const retryHeaders = new Headers(headers);
      retryHeaders.set('Authorization', `Bearer ${tokenStore.getAccessToken()}`);
      res = await fetch(url, { ...options, headers: retryHeaders });
    }
  }

  return res;
}

async function toPayload<T>(res: Response): Promise<T> {
  const contentType = res.headers.get('content-type') ?? '';
  if (!res.ok) {
    const detailRaw = contentType.includes('application/json')
      ? await res.json().catch(() => null)
      : await res.text().catch(() => '');
    throw new ApiError(res.status, detailRaw, extractMessage(detailRaw));
  }
  if (res.status === 204) return undefined as T;
  if (!contentType.includes('application/json')) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  baseUrl: API_BASE,

  get<T>(path: string, init?: RequestInit): Promise<T> {
    return rawFetch(path, { ...init, method: 'GET' }).then(toPayload<T>);
  },

  post<T>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
    return rawFetch(path, {
      ...init,
      method: 'POST',
      body: body === undefined ? undefined : JSON.stringify(body),
    }).then(toPayload<T>);
  },

  patch<T>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
    return rawFetch(path, {
      ...init,
      method: 'PATCH',
      body: body === undefined ? undefined : JSON.stringify(body),
    }).then(toPayload<T>);
  },

  delete<T>(path: string, init?: RequestInit): Promise<T> {
    return rawFetch(path, { ...init, method: 'DELETE' }).then(toPayload<T>);
  },

  postForm<T>(path: string, data: Record<string, string>, init?: RequestInit): Promise<T> {
    const body = new URLSearchParams(data);
    return rawFetch(path, {
      ...init,
      method: 'POST',
      body,
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }).then(toPayload<T>);
  },
};