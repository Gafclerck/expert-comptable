import { formatCFA } from '@/utils/format';

interface KpiCardProps {
  label: string;
  value: number;
  sign?: 'positive' | 'negative' | 'neutral' | 'auto';
  sub?: string;
  onClick?: () => void;
  size?: 'default' | 'large';
  mono?: boolean;
}

export default function KpiCard({ label, value, sign = 'neutral', sub, onClick, size = 'default', mono = true }: KpiCardProps) {
  const effectiveSign = sign === 'auto' ? (value >= 0 ? 'positive' : 'negative') : sign;
  const valueColor =
    effectiveSign === 'positive' ? 'text-emerald-600' :
    effectiveSign === 'negative' ? 'text-red-600' :
    'text-slate-900';

  return (
    <div
      onClick={onClick}
      className={`ledger-card ledger-card--glow ${
        size === 'large' ? 'p-6' : 'p-4'
      } ${onClick ? 'cursor-pointer hover:border-[var(--color-primary)] transition-all duration-150 group' : ''}`}
    >
      <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">{label}</div>
      <div className={`${mono ? 'font-financial' : ''} font-semibold leading-none ${
        size === 'large' ? 'text-2xl' : 'text-xl'
      } ${valueColor}`}>
        {effectiveSign === 'positive' && value > 0 ? '+' : ''}
        {formatCFA(value)}
      </div>
      {sub && <div className="text-xs text-slate-400 p-2">{sub}</div>}
      {onClick && (
        <div className="text-xs text-slate-400 mt-2 group-hover:text-[var(--color-primary)] transition-colors">
          Voir le détail →
        </div>
      )}
    </div>
  );
}
