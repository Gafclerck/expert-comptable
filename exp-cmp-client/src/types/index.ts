// ─────────────────────────────────────────────────────────────
// Types d'application (vues + domaines)
// API  → types backend (miroir des schémas) : voir ./api
// MOCK → types des modules non encore livrés par le backend
// ─────────────────────────────────────────────────────────────

export type {
  UserStatus, PersonStatus, BusinessStatus, BusinessAccountRole,
  AccountType, CategoryType, TransactionType, TransactionStatus,
  LineDirection, TransferStatus,
  InsuranceClientStatus, InsuranceContractStatus, AuditAction,
  LoginResponse, MeOut, UserOut, RoleOut, PersonOut, BusinessOut, BusinessAccountOut,
  AccountOut, AccountBalanceOut, CategoryOut, TransactionOut, TransactionCreate,
  TransactionLineIn, TransactionLineOut, TransactionAllocationIn, TransactionAllocationOut,
  TransferOut, TransferCreate,
  InsuranceClientOut, InsuranceContractOut, InsurancePaymentOut,
  AuditLogOut, ToolMeta, AssistantReply,
} from './api';

export type ActivityId = 'assurance' | 'poulets' | 'vtc';

export interface Activity {
  id: ActivityId;
  label: string;
  icon: string;
}

// ─── MOCK · Comptes / Soldes ───────────────────────────────────

export interface AccountBalance {
  id: string;
  type: string;
  label: string;
  total: number;
  byActivity: Record<ActivityId, number>;
}

// ─── MOCK · Transactions (affichage historique demo) ─────────

export interface Transaction {
  id: string;
  date: string;
  activity: ActivityId;
  type: 'entree' | 'sortie';
  category: string;
  description: string;
  amount: number;
  account: string;
  reference?: string;
  user: string;
  clientId?: string;
  vehicleId?: string;
  driverId?: string;
  lotId?: string;
}

// ─── MOCK · Personnes ─────────────────────────────────────────

export type PersonRole = 'root' | 'member' | 'driver' | 'supplier' | 'other';

export interface Person {
  id: string;
  name: string;
  phone: string;
  role: PersonRole;
  userId?: string;
  totalAdvanced: number;
  totalRepaid: number;
  totalHeld: number;
  pendingCount: number;
  confirmedCount: number;
  disputedCount: number;
}

// ─── MOCK · Assurance (hors backend) ──────────────────────────

export interface InsuranceContract {
  id: string;
  vehicleId: string;
  clientId: string;
  clientName: string;
  plateNumber: string;
  vehicle: string;
  premium: number;
  payments: Payment[];
  startDate: string;
  endDate: string;
  status: string;
  promiseDate?: string;
}

export interface InsuranceVehicle {
  id: string;
  clientId: string;
  plateNumber: string;
  brand: string;
  model: string;
  contracts: InsuranceContract[];
}

export interface InsuranceClient {
  id: string;
  name: string;
  phone: string;
  vehicles: InsuranceVehicle[];
}

// ─── MOCK · Journal d'audit (historique demo) ─────────────────

export interface AuditLog {
  id: string;
  date: string;
  time: string;
  userId: string;
  userName: string;
  action: string;
  entity: string;
  entityId: string;
  oldValue?: string;
  newValue?: string;
  method?: string;
  note?: string;
}

// ─── MOCK · Créances & Dettes ─────────────────────────────────

export interface Payment {
  id: string;
  date: string;
  amount: number;
  note?: string;
  account: string;
}

export interface Creance {
  id: string;
  person: string;
  phone?: string;
  sourceActivity: ActivityId;
  initialAmount: number;
  payments: Payment[];
  dueDate: string;
  promiseDate?: string;
  category: 'client_assurance' | 'client_poulets' | 'pret_familial' | 'fournisseur' | 'avance' | 'autre';
  status: 'pending' | 'partial' | 'overdue' | 'paid';
  description?: string;
}

// ─── MOCK · Financements internes ─────────────────────────────

export interface InternalFunding {
  id: string;
  lenderActivity: ActivityId;
  borrowerActivity: ActivityId;
  initialAmount: number;
  repaid: number;
  date: string;
  purpose: string;
  relatedLotId?: string;
  status: 'active' | 'partial' | 'completed';
}

// ─── MOCK · Poulets ───────────────────────────────────────────

export interface PoultryLot {
  id: string;
  lotNumber: string;
  purchaseDate: string;
  quantity: number;
  unitPrice: number;
  transport: number;
  slaughter: number;
  plucking: number;
  feed: number;
  other: number;
  mortality: number;
  sold: number;
  revenue: number;
  receivables: number;
  fundingId?: string;
  status: 'active' | 'closed';
  notes?: string;
}

// ─── MOCK · VTC ───────────────────────────────────────────────

export interface Vehicle {
  id: string;
  name: string;
  brand: string;
  model: string;
  plate: string;
  year: number;
  acquisitionCost: number;
  initialExpenses: number;
  fuelCost: number;
  maintenanceCost: number;
  repairCost: number;
  insuranceCost: number;
  totalRevenue: number;
  status: 'active' | 'maintenance' | 'inactive';
  currentDriverId?: string;
}

export interface Driver {
  id: string;
  name: string;
  phone: string;
  vehicleId: string;
  dailyRate: number;
  workedDays: Record<string, boolean>;
  payments: Payment[];
  status: 'active' | 'inactive';
}

// ─── MOCK · Alertes / Rappels ─────────────────────────────────

export type AlertLevel = 'urgent' | 'today' | 'upcoming' | 'resolved';

export interface Alert {
  id: string;
  level: AlertLevel;
  title: string;
  description: string;
  date: string;
  activity?: ActivityId;
  actionLabel?: string;
  actionPage?: string;
  resolved: boolean;
}

// ─── MOCK · Documents ─────────────────────────────────────────

export interface Document {
  id: string;
  name: string;
  type: string;
  size: number;
  date: string;
  activity?: ActivityId;
  relatedId?: string;
  relatedType?: string;
  user: string;
  url?: string;
}

// ─── MOCK · Avances personnelles ──────────────────────────────

export type AdvanceStatus = 'pending_confirmation' | 'confirmed' | 'disputed' | 'closed';
export type EvidenceStatus = 'none' | 'provided' | 'to_check' | 'verified' | 'rejected';
export type ConfirmationMethod = 'recipient_confirmation' | 'root_override' | 'external_proof' | 'system_match';

export interface AdvanceMovement {
  id: string;
  date: string;
  type: 'expense' | 'return' | 'reimbursement';
  amount: number;
  description: string;
  evidenceStatus: EvidenceStatus;
}

export interface PersonalAdvance {
  id: string;
  reference: string;
  date: string;
  funderId: string;
  funderName: string;
  holderId: string;
  holderName: string;
  activity: ActivityId;
  amount: number;
  purpose: string;
  vehicleRef?: string;
  status: AdvanceStatus;
  confirmationMethod?: ConfirmationMethod;
  confirmedBy?: string;
  confirmedAt?: string;
  declaredAmount?: number;
  evidenceStatus: EvidenceStatus;
  movements: AdvanceMovement[];
  disputeNote?: string;
}

// ─── MOCK · Rapports ──────────────────────────────────────────

export interface CashFlowPoint {
  date: string;
  total: number;
  assurance: number;
  poulets: number;
  vtc: number;
}

export interface ReportTemplate {
  id: string;
  title: string;
  description: string;
  icon: string;
  category: string;
}