export const formatCFA = (n: number): string =>
  new Intl.NumberFormat('fr-FR').format(Math.round(n)) + ' F CFA';

export const formatCFACompact = (n: number): string => {
  if (Math.abs(n) >= 1_000_000) return (n / 1_000_000).toFixed(1).replace('.', ',') + ' M';
  if (Math.abs(n) >= 1_000) return (n / 1_000).toFixed(0) + ' k';
  return String(n);
};
