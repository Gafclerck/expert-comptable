import type {
  AccountBalance, Transaction, Creance, InternalFunding,
  InsuranceContract, InsuranceClient, PoultryLot,
  Vehicle, Driver, Alert, CashFlowPoint, Document,
  Person, PersonalAdvance, AuditLog,
} from '../types';

// ─── UTILS ────────────────────────────────────────────────────────────────────

export const formatCFA = (n: number): string =>
  new Intl.NumberFormat('fr-FR').format(Math.round(n)) + ' F CFA';

export const formatCFACompact = (n: number): string => {
  if (Math.abs(n) >= 1_000_000) return (n / 1_000_000).toFixed(1).replace('.', ',') + ' M';
  if (Math.abs(n) >= 1_000) return (n / 1_000).toFixed(0) + ' k';
  return String(n);
};

// ─── ACCOUNTS ─────────────────────────────────────────────────────────────────

export const accounts: AccountBalance[] = [
  {
    id: 'caisse',
    type: 'caisse',
    label: 'Caisse / Espèces',
    total: 1_847_500,
    byActivity: { assurance: 820_000, poulets: 487_500, vtc: 540_000 },
  },
  {
    id: 'wave',
    type: 'wave',
    label: 'Wave',
    total: 623_000,
    byActivity: { assurance: 280_000, poulets: 143_000, vtc: 200_000 },
  },
  {
    id: 'orange_money',
    type: 'orange_money',
    label: 'Orange Money',
    total: 415_000,
    byActivity: { assurance: 215_000, poulets: 100_000, vtc: 100_000 },
  },
  {
    id: 'banque',
    type: 'banque',
    label: 'Banque (SGBS)',
    total: 2_150_000,
    byActivity: { assurance: 900_000, poulets: 750_000, vtc: 500_000 },
  },
];

export const totalBalance = accounts.reduce((s, a) => s + a.total, 0); // 5 035 500

// ─── PERIOD KPIs (ce mois) ────────────────────────────────────────────────────

export const periodKpis = {
  income: 3_420_000,
  expenses: 2_185_000,
  result: 1_235_000,
  receivables: 485_000,
  payables: 120_000,
  internalFunding: 300_000,
};

export const activityKpis = {
  assurance: {
    revenue: 1_450_000,
    expenses: 890_000,
    result: 560_000,
    receivables: 185_000,
    activeContracts: 24,
  },
  poulets: {
    revenue: 1_350_000,
    expenses: 1_085_000,
    result: 265_000,
    receivables: 200_000,
    stock: 45,
    activeLots: 2,
  },
  vtc: {
    revenue: 620_000,
    expenses: 210_000,
    result: 410_000,
    pendingPayments: 100_000,
    activeVehicles: 2,
  },
};

// ─── CASH FLOW ────────────────────────────────────────────────────────────────

export const cashFlowData: CashFlowPoint[] = [
  { date: '01/08', total: 3_820_000, assurance: 1_650_000, poulets: 1_200_000, vtc: 970_000 },
  { date: '04/08', total: 4_250_000, assurance: 1_720_000, poulets: 1_480_000, vtc: 1_050_000 },
  { date: '07/08', total: 3_940_000, assurance: 1_580_000, poulets: 1_330_000, vtc: 1_030_000 },
  { date: '10/08', total: 4_680_000, assurance: 1_900_000, poulets: 1_620_000, vtc: 1_160_000 },
  { date: '13/08', total: 4_350_000, assurance: 1_820_000, poulets: 1_410_000, vtc: 1_120_000 },
  { date: '16/08', total: 4_890_000, assurance: 2_050_000, poulets: 1_580_000, vtc: 1_260_000 },
  { date: '19/08', total: 4_620_000, assurance: 1_960_000, poulets: 1_490_000, vtc: 1_170_000 },
  { date: '22/08', total: 5_035_500, assurance: 2_215_000, poulets: 1_480_500, vtc: 1_340_000 },
];

// ─── TRANSACTIONS ─────────────────────────────────────────────────────────────

export const transactions: Transaction[] = [
  { id: 't001', date: '2026-08-23', activity: 'assurance', type: 'entree', category: 'Prime d\'assurance', description: 'Prime Mamadou Diallo – AA-456-BK', amount: 20_000, account: 'wave', reference: 'ASS-2026-0241', user: 'Ibrahima Sow', clientId: 'c001' },
  { id: 't002', date: '2026-08-23', activity: 'vtc', type: 'entree', category: 'Versement chauffeur', description: 'Versement journalier Moussa Koné – Ford Escape', amount: 18_000, account: 'caisse', reference: 'VTC-2026-0187', user: 'Ibrahima Sow', vehicleId: 'v001', driverId: 'd001' },
  { id: 't003', date: '2026-08-22', activity: 'vtc', type: 'sortie', category: 'Carburant', description: 'Essence Ford Escape', amount: 15_000, account: 'caisse', reference: 'VTC-2026-0186', user: 'Ibrahima Sow', vehicleId: 'v001' },
  { id: 't004', date: '2026-08-22', activity: 'poulets', type: 'sortie', category: 'Transport', description: 'Transport lot 007 – marché de Thiaroye', amount: 20_000, account: 'caisse', reference: 'PKT-2026-0044', user: 'Fatou Mbaye', lotId: 'lot007' },
  { id: 't005', date: '2026-08-21', activity: 'poulets', type: 'entree', category: 'Vente poulets', description: 'Vente 25 poulets lot 006 – Ousmane Ba', amount: 137_500, account: 'caisse', reference: 'PKT-2026-0043', user: 'Fatou Mbaye', lotId: 'lot006' },
  { id: 't006', date: '2026-08-21', activity: 'assurance', type: 'entree', category: 'Prime d\'assurance', description: 'Prime Aminata Sarr – DK-118-AA', amount: 45_000, account: 'orange_money', reference: 'ASS-2026-0240', user: 'Ibrahima Sow', clientId: 'c002' },
  { id: 't007', date: '2026-08-20', activity: 'assurance', type: 'sortie', category: 'Prêt familial', description: 'Papa emprunte sur caisse Assurance', amount: 50_000, account: 'caisse', reference: 'ASS-2026-0239', user: 'Root Admin' },
  { id: 't008', date: '2026-08-20', activity: 'vtc', type: 'entree', category: 'Versement chauffeur', description: 'Versement Aliou Diagne – Toyota Corolla', amount: 15_000, account: 'caisse', reference: 'VTC-2026-0185', user: 'Ibrahima Sow', vehicleId: 'v002', driverId: 'd002' },
  { id: 't009', date: '2026-08-19', activity: 'poulets', type: 'sortie', category: 'Abattage', description: 'Abattage lot 007 – 100 poulets', amount: 10_000, account: 'caisse', reference: 'PKT-2026-0042', user: 'Fatou Mbaye', lotId: 'lot007' },
  { id: 't010', date: '2026-08-19', activity: 'poulets', type: 'sortie', category: 'Déplumage', description: 'Déplumage lot 007', amount: 5_000, account: 'caisse', reference: 'PKT-2026-0041', user: 'Fatou Mbaye', lotId: 'lot007' },
  { id: 't011', date: '2026-08-18', activity: 'assurance', type: 'entree', category: 'Prime d\'assurance', description: 'Paiement partiel Cheikh Ndiaye – renouvellement', amount: 30_000, account: 'wave', reference: 'ASS-2026-0238', user: 'Ibrahima Sow', clientId: 'c003' },
  { id: 't012', date: '2026-08-18', activity: 'vtc', type: 'sortie', category: 'Entretien', description: 'Vidange + filtre Toyota Corolla', amount: 35_000, account: 'caisse', reference: 'VTC-2026-0184', user: 'Ibrahima Sow', vehicleId: 'v002' },
  { id: 't013', date: '2026-08-17', activity: 'poulets', type: 'sortie', category: 'Achat poulets', description: 'Achat 100 poulets lot 007 – fournisseur Mbour', amount: 250_000, account: 'caisse', reference: 'PKT-2026-0040', user: 'Fatou Mbaye', lotId: 'lot007' },
  { id: 't014', date: '2026-08-17', activity: 'assurance', type: 'sortie', category: 'Financement interne', description: 'Avance Assurance → Poulets lot 007', amount: 300_000, account: 'banque', reference: 'FIN-2026-0007', user: 'Root Admin' },
  { id: 't015', date: '2026-08-16', activity: 'assurance', type: 'entree', category: 'Prime d\'assurance', description: 'Nouveau contrat Rokhaya Gueye – moto TG-882', amount: 18_000, account: 'wave', reference: 'ASS-2026-0237', user: 'Ibrahima Sow', clientId: 'c004' },
  { id: 't016', date: '2026-08-15', activity: 'vtc', type: 'sortie', category: 'Carburant', description: 'Essence Toyota Corolla', amount: 12_000, account: 'caisse', reference: 'VTC-2026-0183', user: 'Ibrahima Sow', vehicleId: 'v002' },
  { id: 't017', date: '2026-08-14', activity: 'poulets', type: 'entree', category: 'Vente poulets', description: 'Vente 40 poulets lot 006 – marché Castors', amount: 220_000, account: 'caisse', reference: 'PKT-2026-0039', user: 'Fatou Mbaye', lotId: 'lot006' },
  { id: 't018', date: '2026-08-13', activity: 'assurance', type: 'entree', category: 'Prime d\'assurance', description: 'Renouvellement Mouhamadou Thiam', amount: 65_000, account: 'banque', reference: 'ASS-2026-0236', user: 'Ibrahima Sow', clientId: 'c005' },
  { id: 't019', date: '2026-08-12', activity: 'vtc', type: 'sortie', category: 'Réparation', description: 'Réparation freins Ford Escape', amount: 45_000, account: 'caisse', reference: 'VTC-2026-0182', user: 'Ibrahima Sow', vehicleId: 'v001' },
  { id: 't020', date: '2026-08-10', activity: 'poulets', type: 'entree', category: 'Remboursement financement', description: 'Remboursement partiel Poulets → Assurance', amount: 200_000, account: 'caisse', reference: 'FIN-2026-0007', user: 'Fatou Mbaye', lotId: 'lot006' },
];

// ─── CRÉANCES ─────────────────────────────────────────────────────────────────

export const creances: Creance[] = [
  {
    id: 'cr001',
    person: 'Mamadou Diallo',
    phone: '+221 77 541 23 10',
    sourceActivity: 'assurance',
    initialAmount: 25_000,
    payments: [{ id: 'p001', date: '2026-08-23', amount: 20_000, note: 'Paiement Wave', account: 'wave' }],
    dueDate: '2026-08-29',
    promiseDate: '2026-08-29',
    category: 'client_assurance',
    status: 'partial',
    description: 'Prime assurance AA-456-BK – reste 5 000 F',
  },
  {
    id: 'cr002',
    person: 'Cheikh Ndiaye',
    phone: '+221 78 234 56 78',
    sourceActivity: 'assurance',
    initialAmount: 75_000,
    payments: [{ id: 'p002', date: '2026-08-18', amount: 30_000, account: 'wave' }],
    dueDate: '2026-08-30',
    category: 'client_assurance',
    status: 'partial',
    description: 'Renouvellement contrat – véhicule DK-994-CC',
  },
  {
    id: 'cr003',
    person: 'Papa (famille)',
    phone: '',
    sourceActivity: 'assurance',
    initialAmount: 50_000,
    payments: [],
    dueDate: '2026-09-05',
    category: 'pret_familial',
    status: 'pending',
    description: 'Prêt personnel depuis caisse Assurance',
  },
  {
    id: 'cr004',
    person: 'Ousmane Ba',
    phone: '+221 76 987 65 43',
    sourceActivity: 'poulets',
    initialAmount: 82_500,
    payments: [{ id: 'p003', date: '2026-08-21', amount: 55_000, account: 'caisse' }],
    dueDate: '2026-08-25',
    category: 'client_poulets',
    status: 'partial',
    description: 'Achat 15 poulets lot 006 – solde dû',
  },
  {
    id: 'cr005',
    person: 'Ndèye Fall',
    phone: '+221 70 123 45 67',
    sourceActivity: 'assurance',
    initialAmount: 35_000,
    payments: [],
    dueDate: '2026-08-15',
    category: 'client_assurance',
    status: 'overdue',
    description: 'Prime assurance DK-782-AB – en retard de 8 jours',
  },
  {
    id: 'cr006',
    person: 'Ibou Diop (fournisseur)',
    phone: '+221 77 665 54 43',
    sourceActivity: 'poulets',
    initialAmount: 120_000,
    payments: [],
    dueDate: '2026-09-01',
    category: 'fournisseur',
    status: 'pending',
    description: 'Facture alimentation lot 007 – à régler',
  },
];

// ─── FINANCEMENTS INTERNES ────────────────────────────────────────────────────

export const internalFundings: InternalFunding[] = [
  {
    id: 'fin001',
    lenderActivity: 'assurance',
    borrowerActivity: 'poulets',
    initialAmount: 300_000,
    repaid: 200_000,
    date: '2026-08-17',
    purpose: 'Financement lot 007 – achat + frais',
    relatedLotId: 'lot007',
    status: 'partial',
  },
  {
    id: 'fin002',
    lenderActivity: 'vtc',
    borrowerActivity: 'assurance',
    initialAmount: 150_000,
    repaid: 150_000,
    date: '2026-07-10',
    purpose: 'Fonds de roulement temporaire Assurance',
    status: 'completed',
  },
  {
    id: 'fin003',
    lenderActivity: 'assurance',
    borrowerActivity: 'poulets',
    initialAmount: 180_000,
    repaid: 180_000,
    date: '2026-06-05',
    purpose: 'Financement lot 005',
    relatedLotId: 'lot005',
    status: 'completed',
  },
];

// ─── ASSURANCE ────────────────────────────────────────────────────────────────

export const insuranceClients: InsuranceClient[] = [
  {
    id: 'c001',
    name: 'Mamadou Diallo',
    phone: '+221 77 541 23 10',
    vehicles: [
      {
        id: 'iv001',
        clientId: 'c001',
        plateNumber: 'AA-456-BK',
        brand: 'Toyota',
        model: 'Corolla',
        contracts: [
          {
            id: 'ic001',
            vehicleId: 'iv001',
            clientId: 'c001',
            clientName: 'Mamadou Diallo',
            plateNumber: 'AA-456-BK',
            vehicle: 'Toyota Corolla',
            premium: 25_000,
            payments: [{ id: 'p_ic001', date: '2026-08-23', amount: 20_000, account: 'wave' }],
            startDate: '2026-08-23',
            endDate: '2027-08-22',
            status: 'partial',
            promiseDate: '2026-08-29',
          },
        ],
      },
    ],
  },
  {
    id: 'c002',
    name: 'Aminata Sarr',
    phone: '+221 77 234 56 78',
    vehicles: [
      {
        id: 'iv002',
        clientId: 'c002',
        plateNumber: 'DK-118-AA',
        brand: 'Renault',
        model: 'Symbol',
        contracts: [
          {
            id: 'ic002',
            vehicleId: 'iv002',
            clientId: 'c002',
            clientName: 'Aminata Sarr',
            plateNumber: 'DK-118-AA',
            vehicle: 'Renault Symbol',
            premium: 45_000,
            payments: [{ id: 'p_ic002', date: '2026-08-21', amount: 45_000, account: 'orange_money' }],
            startDate: '2026-08-21',
            endDate: '2027-08-20',
            status: 'active',
          },
        ],
      },
    ],
  },
  {
    id: 'c003',
    name: 'Cheikh Ndiaye',
    phone: '+221 78 234 56 78',
    vehicles: [
      {
        id: 'iv003',
        clientId: 'c003',
        plateNumber: 'DK-994-CC',
        brand: 'Peugeot',
        model: '206',
        contracts: [
          {
            id: 'ic003',
            vehicleId: 'iv003',
            clientId: 'c003',
            clientName: 'Cheikh Ndiaye',
            plateNumber: 'DK-994-CC',
            vehicle: 'Peugeot 206',
            premium: 75_000,
            payments: [{ id: 'p_ic003', date: '2026-08-18', amount: 30_000, account: 'wave' }],
            startDate: '2026-08-18',
            endDate: '2027-08-17',
            status: 'partial',
          },
        ],
      },
    ],
  },
  {
    id: 'c004',
    name: 'Rokhaya Guèye',
    phone: '+221 76 112 33 44',
    vehicles: [
      {
        id: 'iv004',
        clientId: 'c004',
        plateNumber: 'TG-882-AA',
        brand: 'Honda',
        model: 'Wave 125',
        contracts: [
          {
            id: 'ic004',
            vehicleId: 'iv004',
            clientId: 'c004',
            clientName: 'Rokhaya Guèye',
            plateNumber: 'TG-882-AA',
            vehicle: 'Honda Wave 125',
            premium: 18_000,
            payments: [{ id: 'p_ic004', date: '2026-08-16', amount: 18_000, account: 'wave' }],
            startDate: '2026-08-16',
            endDate: '2027-08-15',
            status: 'active',
          },
        ],
      },
    ],
  },
  {
    id: 'c005',
    name: 'Mouhamadou Thiam',
    phone: '+221 77 889 00 11',
    vehicles: [
      {
        id: 'iv005',
        clientId: 'c005',
        plateNumber: 'DK-221-BC',
        brand: 'Toyota',
        model: 'Hilux',
        contracts: [
          {
            id: 'ic005',
            vehicleId: 'iv005',
            clientId: 'c005',
            clientName: 'Mouhamadou Thiam',
            plateNumber: 'DK-221-BC',
            vehicle: 'Toyota Hilux',
            premium: 65_000,
            payments: [{ id: 'p_ic005', date: '2026-08-13', amount: 65_000, account: 'banque' }],
            startDate: '2026-08-13',
            endDate: '2027-08-12',
            status: 'active',
          },
        ],
      },
    ],
  },
  {
    id: 'c006',
    name: 'Ndèye Fall',
    phone: '+221 70 123 45 67',
    vehicles: [
      {
        id: 'iv006',
        clientId: 'c006',
        plateNumber: 'DK-782-AB',
        brand: 'Nissan',
        model: 'Note',
        contracts: [
          {
            id: 'ic006',
            vehicleId: 'iv006',
            clientId: 'c006',
            clientName: 'Ndèye Fall',
            plateNumber: 'DK-782-AB',
            vehicle: 'Nissan Note',
            premium: 35_000,
            payments: [],
            startDate: '2026-08-01',
            endDate: '2027-07-31',
            status: 'pending',
          },
        ],
      },
    ],
  },
];

export const allContracts: InsuranceContract[] = insuranceClients.flatMap(c =>
  c.vehicles.flatMap(v => v.contracts)
);

// ─── POULETS ──────────────────────────────────────────────────────────────────

export const poultryLots: PoultryLot[] = [
  {
    id: 'lot007',
    lotNumber: 'LOT-2026-007',
    purchaseDate: '2026-08-17',
    quantity: 100,
    unitPrice: 2_500,
    transport: 20_000,
    slaughter: 10_000,
    plucking: 5_000,
    feed: 15_000,
    other: 0,
    mortality: 2,
    sold: 0,
    revenue: 0,
    receivables: 0,
    fundingId: 'fin001',
    status: 'active',
    notes: 'Financé par Assurance. En cours de vente.',
  },
  {
    id: 'lot006',
    lotNumber: 'LOT-2026-006',
    purchaseDate: '2026-07-28',
    quantity: 120,
    unitPrice: 2_400,
    transport: 18_000,
    slaughter: 12_000,
    plucking: 6_000,
    feed: 20_000,
    other: 5_000,
    mortality: 3,
    sold: 65,
    revenue: 357_500,
    receivables: 82_500,
    status: 'active',
    notes: 'Partiellement vendu. Reste 52 poulets en stock.',
  },
  {
    id: 'lot005',
    lotNumber: 'LOT-2026-005',
    purchaseDate: '2026-06-15',
    quantity: 80,
    unitPrice: 2_600,
    transport: 15_000,
    slaughter: 8_000,
    plucking: 4_000,
    feed: 12_000,
    other: 0,
    mortality: 1,
    sold: 79,
    revenue: 434_500,
    receivables: 0,
    fundingId: 'fin003',
    status: 'closed',
    notes: 'Lot clôturé. Financement Assurance remboursé.',
  },
  {
    id: 'lot004',
    lotNumber: 'LOT-2026-004',
    purchaseDate: '2026-05-10',
    quantity: 100,
    unitPrice: 2_450,
    transport: 18_000,
    slaughter: 10_000,
    plucking: 5_000,
    feed: 18_000,
    other: 3_000,
    mortality: 4,
    sold: 96,
    revenue: 528_000,
    receivables: 0,
    status: 'closed',
  },
];

// ─── VTC ──────────────────────────────────────────────────────────────────────

export const vehicles: Vehicle[] = [
  {
    id: 'v001',
    name: 'Ford Escape #1',
    brand: 'Ford',
    model: 'Escape',
    plate: 'DK-4521-AB',
    year: 2019,
    acquisitionCost: 7_500_000,
    initialExpenses: 350_000,
    fuelCost: 185_000,
    maintenanceCost: 65_000,
    repairCost: 45_000,
    insuranceCost: 75_000,
    totalRevenue: 1_850_000,
    status: 'active',
    currentDriverId: 'd001',
  },
  {
    id: 'v002',
    name: 'Toyota Corolla #1',
    brand: 'Toyota',
    model: 'Corolla',
    plate: 'DK-7812-CD',
    year: 2018,
    acquisitionCost: 5_200_000,
    initialExpenses: 180_000,
    fuelCost: 142_000,
    maintenanceCost: 85_000,
    repairCost: 35_000,
    insuranceCost: 65_000,
    totalRevenue: 1_420_000,
    status: 'active',
    currentDriverId: 'd002',
  },
];

export const drivers: Driver[] = [
  {
    id: 'd001',
    name: 'Moussa Koné',
    phone: '+221 77 321 00 11',
    vehicleId: 'v001',
    dailyRate: 18_000,
    workedDays: {
      '2026-08-23': true,
      '2026-08-22': false,
      '2026-08-21': true,
      '2026-08-20': true,
      '2026-08-19': false,
      '2026-08-18': true,
      '2026-08-17': true,
    },
    payments: [
      { id: 'dp001', date: '2026-08-23', amount: 18_000, note: 'Versement journalier', account: 'caisse' },
      { id: 'dp002', date: '2026-08-21', amount: 18_000, account: 'caisse' },
      { id: 'dp003', date: '2026-08-20', amount: 18_000, account: 'caisse' },
      { id: 'dp004', date: '2026-08-18', amount: 18_000, account: 'caisse' },
    ],
    status: 'active',
  },
  {
    id: 'd002',
    name: 'Aliou Diagne',
    phone: '+221 76 456 78 90',
    vehicleId: 'v002',
    dailyRate: 15_000,
    workedDays: {
      '2026-08-23': false,
      '2026-08-22': true,
      '2026-08-21': true,
      '2026-08-20': true,
      '2026-08-19': true,
      '2026-08-18': false,
      '2026-08-17': true,
    },
    payments: [
      { id: 'dp005', date: '2026-08-22', amount: 15_000, account: 'caisse' },
      { id: 'dp006', date: '2026-08-21', amount: 15_000, account: 'caisse' },
      { id: 'dp007', date: '2026-08-20', amount: 15_000, account: 'caisse' },
      { id: 'dp008', date: '2026-08-19', amount: 15_000, account: 'caisse' },
    ],
    status: 'active',
  },
  {
    id: 'd003',
    name: 'Lamine Niang',
    phone: '+221 78 222 33 44',
    vehicleId: 'v001',
    dailyRate: 18_000,
    workedDays: {},
    payments: [],
    status: 'inactive',
  },
];

// ─── ALERTS ───────────────────────────────────────────────────────────────────

export const alerts: Alert[] = [
  {
    id: 'al001',
    level: 'urgent',
    title: 'Créance en retard – Ndèye Fall',
    description: 'Prime assurance DK-782-AB de 35 000 F CFA due depuis le 15/08. Retard de 8 jours.',
    date: '2026-08-23',
    activity: 'assurance',
    actionLabel: 'Voir la créance',
    actionPage: 'creances',
    resolved: false,
  },
  {
    id: 'al002',
    level: 'today',
    title: 'Versement attendu – Moussa Koné',
    description: 'Moussa Koné (Ford Escape) a travaillé aujourd\'hui. Versement de 18 000 F CFA attendu.',
    date: '2026-08-23',
    activity: 'vtc',
    actionLabel: 'Voir le chauffeur',
    actionPage: 'vtc',
    resolved: false,
  },
  {
    id: 'al003',
    level: 'today',
    title: 'Promesse de paiement – Mamadou Diallo',
    description: 'Mamadou Diallo avait promis de payer le solde de 5 000 F CFA (AA-456-BK) avant vendredi.',
    date: '2026-08-29',
    activity: 'assurance',
    actionLabel: 'Voir le contrat',
    actionPage: 'assurance',
    resolved: false,
  },
  {
    id: 'al004',
    level: 'upcoming',
    title: 'Financement non remboursé – Poulets doit 100 000 F à Assurance',
    description: 'Il reste 100 000 F CFA à rembourser sur le financement FIN-2026-0007 (lot 007).',
    date: '2026-08-30',
    activity: 'poulets',
    actionLabel: 'Voir le financement',
    actionPage: 'financements',
    resolved: false,
  },
  {
    id: 'al005',
    level: 'upcoming',
    title: '185 000 F CFA de créances à échéance cette semaine',
    description: 'Cheikh Ndiaye (45 000 F) et Ousmane Ba (27 500 F) arrivent à échéance avant le 30/08.',
    date: '2026-08-28',
    activity: 'assurance',
    resolved: false,
  },
  {
    id: 'al006',
    level: 'upcoming',
    title: 'Contrat Assurance – échéance dans 30 jours',
    description: 'Le contrat DK-118-AA (Aminata Sarr) expire le 20/08/2027. Anticiper le renouvellement.',
    date: '2026-08-23',
    activity: 'assurance',
    resolved: false,
  },
  {
    id: 'al007',
    level: 'resolved',
    title: 'Remboursement lot 006 – Assurance remboursé',
    description: 'Poulets a remboursé 200 000 F CFA à Assurance sur le financement FIN-2026-0007.',
    date: '2026-08-20',
    activity: 'poulets',
    actionLabel: 'Voir le financement',
    actionPage: 'financements',
    resolved: true,
  },
];

// ─── DOCUMENTS ────────────────────────────────────────────────────────────────

export const documents: Document[] = [
  { id: 'doc001', name: 'Contrat assurance AA-456-BK.pdf', type: 'pdf', size: 245_000, date: '2026-08-23', activity: 'assurance', relatedId: 'ic001', relatedType: 'contract', user: 'Ibrahima Sow' },
  { id: 'doc002', name: 'Facture achat lot 007.jpg', type: 'image', size: 1_240_000, date: '2026-08-17', activity: 'poulets', relatedId: 'lot007', relatedType: 'lot', user: 'Fatou Mbaye' },
  { id: 'doc003', name: 'Reçu carburant Ford Escape 22-08.jpg', type: 'image', size: 890_000, date: '2026-08-22', activity: 'vtc', relatedId: 'v001', relatedType: 'vehicle', user: 'Ibrahima Sow' },
  { id: 'doc004', name: 'Contrat assurance DK-118-AA.pdf', type: 'pdf', size: 312_000, date: '2026-08-21', activity: 'assurance', relatedId: 'ic002', relatedType: 'contract', user: 'Ibrahima Sow' },
  { id: 'doc005', name: 'Facture entretien Corolla.pdf', type: 'pdf', size: 180_000, date: '2026-08-18', activity: 'vtc', relatedId: 'v002', relatedType: 'vehicle', user: 'Ibrahima Sow' },
  { id: 'doc006', name: 'Bordereau vente lot 006.pdf', type: 'pdf', size: 155_000, date: '2026-08-14', activity: 'poulets', relatedId: 'lot006', relatedType: 'lot', user: 'Fatou Mbaye' },
];

// ─── PERSONNES ────────────────────────────────────────────────────────────────

export const people: Person[] = [
  { id: 'p001', name: 'Ibrahima Sow', phone: '+221 77 100 00 01', role: 'root', userId: 'u001', totalAdvanced: 450_000, totalRepaid: 300_000, totalHeld: 0, pendingCount: 0, confirmedCount: 5, disputedCount: 0 },
  { id: 'p002', name: 'Fatou Mbaye', phone: '+221 77 100 00 02', role: 'member', userId: 'u002', totalAdvanced: 185_000, totalRepaid: 60_000, totalHeld: 40_000, pendingCount: 1, confirmedCount: 3, disputedCount: 1 },
  { id: 'p003', name: 'Amadou Sow', phone: '+221 77 100 00 03', role: 'member', userId: 'u003', totalAdvanced: 100_000, totalRepaid: 0, totalHeld: 100_000, pendingCount: 1, confirmedCount: 1, disputedCount: 0 },
  { id: 'p004', name: 'Papa (famille)', phone: '', role: 'other', totalAdvanced: 50_000, totalRepaid: 0, totalHeld: 0, pendingCount: 0, confirmedCount: 1, disputedCount: 0 },
  { id: 'p005', name: 'Moussa Koné', phone: '+221 77 321 00 11', role: 'driver', totalAdvanced: 0, totalRepaid: 0, totalHeld: 20_000, pendingCount: 0, confirmedCount: 0, disputedCount: 0 },
  { id: 'p006', name: 'Ibou Diop', phone: '+221 77 665 54 43', role: 'supplier', totalAdvanced: 0, totalRepaid: 0, totalHeld: 0, pendingCount: 0, confirmedCount: 0, disputedCount: 0 },
];

// ─── AVANCES PERSONNELLES ─────────────────────────────────────────────────────

export const personalAdvances: PersonalAdvance[] = [
  {
    id: 'adv001',
    reference: 'ADV-2026-001',
    date: '2026-08-15',
    funderId: 'p001',
    funderName: 'Ibrahima Sow',
    holderId: 'p003',
    holderName: 'Amadou Sow',
    activity: 'vtc',
    amount: 100_000,
    purpose: 'Achat pièces Ford Escape (batterie + freins)',
    vehicleRef: 'Ford Escape – DK-4521-AB',
    status: 'confirmed',
    confirmationMethod: 'recipient_confirmation',
    confirmedBy: 'Amadou Sow',
    confirmedAt: '2026-08-15',
    evidenceStatus: 'verified',
    movements: [
      { id: 'm001', date: '2026-08-16', type: 'expense', amount: 40_000, description: 'Batterie Ford Escape', evidenceStatus: 'verified' },
      { id: 'm002', date: '2026-08-18', type: 'expense', amount: 20_000, description: 'Mécanicien – main d\'œuvre freins', evidenceStatus: 'provided' },
    ],
  },
  {
    id: 'adv002',
    reference: 'ADV-2026-002',
    date: '2026-08-18',
    funderId: 'p002',
    funderName: 'Fatou Mbaye',
    holderId: 'p002',
    holderName: 'Fatou Mbaye',
    activity: 'poulets',
    amount: 85_000,
    purpose: 'Alimentation lot 007 + frais abattage',
    status: 'confirmed',
    confirmationMethod: 'root_override',
    confirmedBy: 'Root Admin',
    confirmedAt: '2026-08-18',
    evidenceStatus: 'to_check',
    movements: [
      { id: 'm003', date: '2026-08-18', type: 'expense', amount: 35_000, description: 'Alimentation lot 007', evidenceStatus: 'provided' },
      { id: 'm004', date: '2026-08-19', type: 'expense', amount: 10_000, description: 'Abattage 40 poulets', evidenceStatus: 'none' },
    ],
  },
  {
    id: 'adv003',
    reference: 'ADV-2026-003',
    date: '2026-08-22',
    funderId: 'p001',
    funderName: 'Ibrahima Sow',
    holderId: 'p005',
    holderName: 'Moussa Koné',
    activity: 'vtc',
    amount: 20_000,
    purpose: 'Carburant + péage semaine 34',
    vehicleRef: 'Ford Escape – DK-4521-AB',
    status: 'pending_confirmation',
    evidenceStatus: 'none',
    movements: [],
  },
  {
    id: 'adv004',
    reference: 'ADV-2026-004',
    date: '2026-08-20',
    funderId: 'p002',
    funderName: 'Fatou Mbaye',
    holderId: 'p003',
    holderName: 'Amadou Sow',
    activity: 'vtc',
    amount: 100_000,
    purpose: 'Réparation Toyota Corolla – boîte de vitesse',
    vehicleRef: 'Toyota Corolla – DK-7812-CD',
    status: 'disputed',
    declaredAmount: 70_000,
    disputeNote: 'Amadou Sow déclare n\'avoir reçu que 70 000 F. Écart de 30 000 F à clarifier.',
    evidenceStatus: 'none',
    movements: [],
  },
];

// ─── AUDIT LOGS ───────────────────────────────────────────────────────────────

export const auditLogs: AuditLog[] = [
  { id: 'au001', date: '2026-08-23', time: '14:32', userId: 'u001', userName: 'Ibrahima Sow', action: 'Déclaration avance', entity: 'PersonalAdvance', entityId: 'ADV-2026-003', newValue: '20 000 F → Moussa Koné (VTC)', note: 'Carburant semaine 34' },
  { id: 'au002', date: '2026-08-22', time: '09:15', userId: 'u001', userName: 'Ibrahima Sow (ROOT)', action: 'Override confirmation', entity: 'PersonalAdvance', entityId: 'ADV-2026-002', newValue: 'Confirmé par ROOT', method: 'root_override', note: 'Confirmation après vérification directe avec Fatou' },
  { id: 'au003', date: '2026-08-21', time: '16:48', userId: 'u002', userName: 'Fatou Mbaye', action: 'Déclaration dépense', entity: 'AdvanceMovement', entityId: 'ADV-2026-002', newValue: '10 000 F – Abattage lot 007' },
  { id: 'au004', date: '2026-08-20', time: '11:05', userId: 'u002', userName: 'Fatou Mbaye', action: 'Déclaration avance', entity: 'PersonalAdvance', entityId: 'ADV-2026-004', newValue: '100 000 F → Amadou Sow (VTC)' },
  { id: 'au005', date: '2026-08-20', time: '13:22', userId: 'u003', userName: 'Amadou Sow', action: 'Litige déclaré', entity: 'PersonalAdvance', entityId: 'ADV-2026-004', oldValue: '100 000 F (déclaré)', newValue: '70 000 F (reçu)', note: 'Montant reçu différent de la déclaration' },
  { id: 'au006', date: '2026-08-18', time: '10:00', userId: 'u002', userName: 'Fatou Mbaye', action: 'Déclaration avance', entity: 'PersonalAdvance', entityId: 'ADV-2026-002', newValue: '85 000 F → Fatou Mbaye (Poulets)' },
  { id: 'au007', date: '2026-08-18', time: '10:45', userId: 'u002', userName: 'Fatou Mbaye', action: 'Déclaration dépense', entity: 'AdvanceMovement', entityId: 'ADV-2026-002', newValue: '35 000 F – Alimentation lot 007' },
  { id: 'au008', date: '2026-08-15', time: '08:30', userId: 'u001', userName: 'Ibrahima Sow', action: 'Déclaration avance', entity: 'PersonalAdvance', entityId: 'ADV-2026-001', newValue: '100 000 F → Amadou Sow (VTC)' },
  { id: 'au009', date: '2026-08-15', time: '09:10', userId: 'u003', userName: 'Amadou Sow', action: 'Confirmation réception', entity: 'PersonalAdvance', entityId: 'ADV-2026-001', method: 'recipient_confirmation', note: 'Confirmé – 100 000 F bien reçus' },
  { id: 'au010', date: '2026-08-16', time: '14:00', userId: 'u003', userName: 'Amadou Sow', action: 'Déclaration dépense', entity: 'AdvanceMovement', entityId: 'ADV-2026-001', newValue: '40 000 F – Batterie Ford Escape' },
  { id: 'au011', date: '2026-08-18', time: '16:30', userId: 'u003', userName: 'Amadou Sow', action: 'Déclaration dépense', entity: 'AdvanceMovement', entityId: 'ADV-2026-001', newValue: '20 000 F – Mécanicien freins' },
  { id: 'au012', date: '2026-08-17', time: '11:00', userId: 'u001', userName: 'Root Admin', action: 'Création transaction', entity: 'Transaction', entityId: 'FIN-2026-0007', newValue: 'Financement Assurance → Poulets 300 000 F' },
];

// ─── INTELLIGENCE INSIGHTS ────────────────────────────────────────────────────

export const insights = [
  {
    id: 'ins001',
    icon: '📈',
    text: 'Les dépenses VTC sont 18 % supérieures au mois précédent.',
    detail: 'Principalement dues aux réparations freins Ford Escape (45 000 F) et carburant en hausse.',
    type: 'warning',
    activity: 'vtc' as const,
  },
  {
    id: 'ins002',
    icon: '⛽',
    text: 'La Ford Escape représente la plus grande dépense carburant cette semaine.',
    detail: '15 000 F CFA vs 12 000 F CFA pour la Corolla sur 7 jours.',
    type: 'info',
    activity: 'vtc' as const,
  },
  {
    id: 'ins003',
    icon: '🕐',
    text: '185 000 F CFA de créances arrivent à échéance dans les 7 prochains jours.',
    detail: 'Cheikh Ndiaye (45 000 F) + Ousmane Ba (27 500 F) + autres.',
    type: 'warning',
    activity: 'assurance' as const,
  },
  {
    id: 'ins004',
    icon: '🐓',
    text: 'Le lot 007 a une marge estimée inférieure à la moyenne des 3 derniers lots.',
    detail: 'Coût moyen par poulet : 3 100 F vs moyenne historique de 2 850 F.',
    type: 'info',
    activity: 'poulets' as const,
  },
  {
    id: 'ins005',
    icon: '🔄',
    text: 'Poulets doit encore 100 000 F CFA à Assurance (FIN-2026-0007).',
    detail: 'Remboursement de 200 000 F reçu le 20/08. Solde restant à régler après ventes lot 007.',
    type: 'info',
    activity: 'poulets' as const,
  },
];
