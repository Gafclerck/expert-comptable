// ─────────────────────────────────────────────────────────────
// Types API — contrat des schémas backend (FastAPI)
// Ne contient AUCUN type de vue : miroir des Pydantic schemas.
// ─────────────────────────────────────────────────────────────

export type UserStatus = 'active' | 'inactive';
export type PersonStatus = 'active' | 'inactive';
export type BusinessStatus = 'active' | 'inactive';
export type BusinessAccountRole = 'owner' | 'driver' | 'customer' | 'supplier';

export type AccountType = 'cash' | 'bank' | 'mobile_money' | 'other';
export type CategoryType = 'credit' | 'debit';
export type TransactionType = 'revenue' | 'expense';
export type TransactionStatus = 'pending' | 'confirmed' | 'posted';
export type LineDirection = 'debit' | 'credit';
export type TransferStatus = 'pending' | 'posted';

export type InsuranceClientStatus = 'active' | 'inactive';
export type InsuranceContractStatus = 'active' | 'expired' | 'cancelled';

export type AuditAction =
  | 'CREATE' | 'UPDATE' | 'CONFIRM' | 'REJECT' | 'DISPUTE'
  | 'RESOLVE' | 'REPAY' | 'RETURN' | 'TRANSFER' | 'CORRECT';

// ─── Identity ─────────────────────────────────────────────────

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface MeOut {
  id: string;
  email: string;
  full_name: string | null;
  roles: string[];
}

export interface UserOut {
  id: string;
  email: string;
  status: UserStatus;
  person_id: string | null;
  person_full_name: string | null;
  roles: string[];
  created_at: string;
  last_login_at: string | null;
}

export interface RoleOut {
  id: string;
  code: string;
  name: string;
}

export interface PersonOut {
  id: string;
  full_name: string;
  phone: string | null;
  status: PersonStatus;
  created_at: string;
}

export interface BusinessOut {
  id: string;
  code: string;
  name: string;
  status: BusinessStatus;
}

export interface BusinessAccountOut {
  id: string;
  business_id: string;
  person_id: string;
  role: BusinessAccountRole;
  person_full_name: string | null;
}

// ─── Ledger ───────────────────────────────────────────────────

export interface AccountOut {
  id: string;
  business_id: string;
  name: string;
  type: AccountType;
  currency: string;
  opening_balance: number;
  active: boolean;
  created_at: string;
}

export interface AccountBalanceOut {
  account_id: string;
  name: string;
  currency: string;
  opening_balance: number;
  inflows: number;
  outflows: number;
  balance: number;
}

export interface CategoryOut {
  id: string;
  code: string;
  name: string;
  type: CategoryType;
}

export interface TransactionLineIn {
  category_id: string;
  amount: number;
  direction: LineDirection;
  description?: string | null;
}

export interface TransactionAllocationIn {
  business_id: string;
  amount: number;
}

export interface TransactionLineOut {
  id: string;
  category_id: string;
  amount: number;
  direction: LineDirection;
  description: string | null;
}

export interface TransactionAllocationOut {
  id: string;
  business_id: string;
  amount: number;
  percentage: number;
}

export interface TransactionOut {
  id: string;
  business_id: string;
  account_id: string;
  type: TransactionType;
  amount: number;
  description: string | null;
  occurred_at: string;
  status: TransactionStatus;
  created_by: string | null;
  immutable: boolean;
  created_at: string;
  lines: TransactionLineOut[];
  allocations: TransactionAllocationOut[];
}

export interface TransactionCreate {
  business_id: string;
  account_id: string;
  type: TransactionType;
  amount: number;
  description?: string | null;
  occurred_at?: string | null;
  lines: TransactionLineIn[];
  allocations?: TransactionAllocationIn[];
}

export interface TransferOut {
  id: string;
  source_account_id: string;
  destination_account_id: string;
  amount: number;
  occurred_at: string;
  status: TransferStatus;
  reference: string | null;
  created_by: string | null;
  created_at: string;
}

export interface TransferCreate {
  source_account_id: string;
  destination_account_id: string;
  amount: number;
  occurred_at?: string | null;
  reference?: string | null;
}

// ─── Insurance ────────────────────────────────────────────────

export interface InsuranceClientOut {
  id: string;
  person_id: string;
  client_number: string;
  full_name: string;
  phone: string | null;
  status: InsuranceClientStatus;
  created_at: string;
}

export interface InsuranceContractOut {
  id: string;
  client_id: string;
  matricule: string;
  contract_type: string;
  premium: number;
  start_date: string;
  end_date: string | null;
  status: InsuranceContractStatus;
  remaining_amount: number;
  created_at: string;
}

export interface InsurancePaymentOut {
  id: string;
  contract_id: string;
  amount: number;
  paid_at: string;
  transaction_id: string;
  created_at: string;
}

// ─── Poultry (poulailler) ─────────────────────────────────────

export interface PoultryLotOut {
  id: string;
  initial_quantity: number;
  remaining_quantity: number;
  unit_purchase_price: number;
  created_at: string;
}

export interface PoultryPurchaseOut {
  id: string;
  lot_id: string;
  quantity: number;
  unit_price: number;
  note: string | null;
  transaction_id: string;
  created_at: string;
}

export interface PoultrySaleOut {
  id: string;
  quantity: number;
  unit_price: number;
  transaction_id: string;
  created_at: string;
}

export interface PoultryStockOut {
  total_quantity: number;
}

export interface PoultryPurchaseCreate {
  quantity: number;
  unit_price: number;
  note?: string | null;
  account_id: string;
  category_id: string;
  occurred_at?: string | null;
}

export interface PoultrySaleCreate {
  quantity: number;
  unit_price: number;
  account_id: string;
  category_id: string;
  occurred_at?: string | null;
}

// ─── Audit ────────────────────────────────────────────────────

export interface AuditLogOut {
  id: string;
  actor_id: string | null;
  action: AuditAction;
  entity_type: string;
  entity_id: string | null;
  old_values: Record<string, unknown> | null;
  new_values: Record<string, unknown> | null;
  reason: string | null;
  created_at: string;
}

// ─── Assistant (v2) ───────────────────────────────────────────

export interface ToolMeta {
  operation: string;
  label: string;
  example: string;
  business: string | null;
  is_critical: boolean;
}

export interface AssistantReply {
  text: string;
  session_id: string;
  executed_tools: string[];
  clarification: boolean;
  missing_field: string | null;
  options: string[];
  confirmation_required: boolean;
  pending_action: string | null;
}