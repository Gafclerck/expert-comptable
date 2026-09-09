interface BadgeProps {
  variant: 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'partial';
  children: React.ReactNode;
  size?: 'sm' | 'xs';
}

const styles = {
  success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  warning: 'bg-amber-50 text-amber-700 border-amber-200',
  danger: 'bg-red-50 text-red-700 border-red-200',
  info: 'bg-navy-100 text-navy-700 border-navy-200',
  neutral: 'bg-slate-100 text-slate-600 border-slate-200',
  partial: 'bg-amber-50 text-amber-700 border-amber-200',
};

export default function Badge({ variant, children, size = 'sm' }: BadgeProps) {
  return (
    <span className={`inline-flex items-center border rounded-full font-medium ${
      size === 'xs' ? 'text-xs p-2 mt-1' : 'text-xs px-2 mt-1'
    } ${styles[variant]}`}>
      {children}
    </span>
  );
}
