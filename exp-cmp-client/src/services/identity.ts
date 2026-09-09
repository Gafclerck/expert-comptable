// ─────────────────────────────────────────────────────────────
// Service Identity — utilisateurs, personnes, activités (business)
// Chaque fonction correspond à un endpoint du module backend
// `identity`. Le registre d'activités (cache) permet de résoudre
// les codes métier du front (assurance/poulets/vtc) vers les UUID.
// ─────────────────────────────────────────────────────────────

import { api } from '../lib/api';
import type {
  BusinessAccountOut, BusinessAccountRole,
  BusinessOut, PersonOut, RoleOut, UserOut,
} from '../types/api';

// Cache module-level du registre d'activités.
let businessesCache: BusinessOut[] | null = null;

// ─── Roles ────────────────────────────────────────────────────

export async function fetchRoles(): Promise<RoleOut[]> {
  const data = await api.get<RoleOut[]>('/identity/roles');
  return data ?? [];
}

// ─── Utilisateurs ─────────────────────────────────────────────

export interface UserCreatePayload {
  email: string;
  password: string;
  full_name: string;
  phone?: string | null;
  is_root?: boolean;
}

export interface UserUpdatePayload {
  email?: string;
  password?: string;
  status?: 'active' | 'inactive';
  is_root?: boolean;
}

export async function fetchUsers(): Promise<UserOut[]> {
  const data = await api.get<UserOut[]>('/identity/users?skip=0&limit=200');
  return data ?? [];
}

export async function createUser(payload: UserCreatePayload): Promise<UserOut> {
  return api.post<UserOut>('/identity/users', payload);
}

export async function updateUser(userId: string, payload: UserUpdatePayload): Promise<UserOut> {
  return api.patch<UserOut>(`/identity/users/${userId}`, payload);
}

export async function deactivateUser(userId: string): Promise<UserOut> {
  return api.delete<UserOut>(`/identity/users/${userId}`);
}

// ─── Personnes ────────────────────────────────────────────────

export interface PersonCreatePayload {
  full_name: string;
  phone?: string | null;
}

export interface PersonUpdatePayload {
  full_name?: string;
  phone?: string | null;
  status?: 'active' | 'inactive';
}

export async function fetchPersons(): Promise<PersonOut[]> {
  const data = await api.get<PersonOut[]>('/identity/persons?skip=0&limit=500');
  return data ?? [];
}

export async function createPerson(payload: PersonCreatePayload): Promise<PersonOut> {
  return api.post<PersonOut>('/identity/persons', payload);
}

export async function updatePerson(personId: string, payload: PersonUpdatePayload): Promise<PersonOut> {
  return api.patch<PersonOut>(`/identity/persons/${personId}`, payload);
}

// ─── Activités (Businesses) ───────────────────────────────────

export async function fetchBusinesses(force = false): Promise<BusinessOut[]> {
  if (!force && businessesCache) return businessesCache;
  const data = await api.get<BusinessOut[]>('/identity/businesses?skip=0&limit=100');
  businessesCache = data ?? [];
  return businessesCache;
}

export function getCachedBusinesses(): BusinessOut[] {
  return businessesCache ?? [];
}

export function getCachedBusinessId(code: string): string | null {
  return businessesCache?.find((b) => b.code === code)?.id ?? null;
}

export function getCachedBusinessCode(id: string): string | null {
  return businessesCache?.find((b) => b.id === id)?.code ?? null;
}

export async function resolveBusinessId(code: string): Promise<string | null> {
  if (businessesCache) return getCachedBusinessId(code);
  await fetchBusinesses();
  return getCachedBusinessId(code);
}

export async function createBusiness(payload: { code: string; name: string }): Promise<BusinessOut> {
  const business = await api.post<BusinessOut>('/identity/businesses', payload);
  businessesCache = null; // invalider le cache
  return business;
}

// ─── Rattachements activité ↔ personne (Business Accounts) ───

export interface BusinessAccountCreatePayload {
  person_id: string;
  role: BusinessAccountRole;
}

export async function fetchBusinessAccounts(businessId: string): Promise<BusinessAccountOut[]> {
  const data = await api.get<BusinessAccountOut[]>(`/identity/businesses/${businessId}/accounts`);
  return data ?? [];
}

export async function addBusinessAccount(businessId: string, payload: BusinessAccountCreatePayload): Promise<BusinessAccountOut> {
  return api.post<BusinessAccountOut>(`/identity/businesses/${businessId}/accounts`, payload);
}