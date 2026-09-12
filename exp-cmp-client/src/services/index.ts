// ─────────────────────────────────────────────────────────────
// Façade publique des services — VRAI backend uniquement
// Les pages parlant au backend n'importent QUE depuis ce module.
// Les données simulées (B2..B4 non livrés) sont importées en
// direct depuis @/services/mock par les pages concernées : la
// frontière réel/simulé est ainsi visible à la lecture.
// ─────────────────────────────────────────────────────────────

export * from './auth';
export * from './identity';
export * from './ledger';
export * from './dashboard';
export * from './insurance';
export * from './poultry';
export * from './vtc';
export * from './audit';
export * from './assistant';