import { NavLink } from 'react-router-dom';
import Icon, { type IconName } from '@/components/ui/Icon';

export type PageId = 'dashboard' | 'assurance' | 'poulets' | 'vtc' | 'transactions' | 'creances' | 'financements' | 'comptes' | 'avances' | 'personnes' | 'rappels' | 'assistant' | 'rapports' | 'documents' | 'utilisateurs' | 'audit' | 'parametres';
interface NavItem { id: PageId; label: string; icon: IconName; path: string; badge?: number; group: string; }

const navItems: NavItem[] = [
  { id: 'dashboard', label: 'Vue globale', icon: 'grid', path: '/dashboard', group: 'principal' },
  { id: 'assurance', label: 'Assurance', icon: 'shield', path: '/assurance', group: 'activites' },
  { id: 'poulets', label: 'Poulets', icon: 'package', path: '/poulets', group: 'activites' },
  { id: 'vtc', label: 'VTC', icon: 'car', path: '/vtc', group: 'activites' },
  { id: 'transactions', label: 'Transactions', icon: 'arrows', path: '/transactions', group: 'finances' },
  { id: 'comptes', label: 'Comptes & caisses', icon: 'wallet', path: '/comptes', group: 'finances' },
  { id: 'personnes', label: 'Personnes', icon: 'users', path: '/personnes', group: 'controle' },
  { id: 'utilisateurs', label: 'Utilisateurs', icon: 'user-plus', path: '/utilisateurs', group: 'admin' },
  { id: 'audit', label: 'Audit', icon: 'list', path: '/audit', group: 'admin' },
  { id: 'parametres', label: 'Paramètres', icon: 'settings', path: '/parametres', group: 'admin' },
];
const groups = [['principal', ''], ['activites', 'Activités'], ['finances', 'Finances'], ['controle', 'Contrôle'], ['admin', 'Administration']] as const;
interface SidebarProps { collapsed?: boolean; onToggleCollapse?: () => void; userName?: string; userRole?: string; }

function initials(name: string) { const parts = name.trim().split(/\s+/).filter(Boolean); return (parts[0]?.[0] ?? 'E') + (parts[1]?.[0] ?? 'C'); }

export default function Sidebar({ collapsed = false, onToggleCollapse, userName = 'Utilisateur', userRole = 'root' }: SidebarProps) {
  return <aside style={{ width: collapsed ? 72 : 252 }} className="ledger-sidebar flex flex-col h-full shrink-0 transition-[width] duration-200">
    <div className="flex h-[72px] items-center gap-3 px-5 border-b border-[var(--color-border)]">
      <div className="brand-mark">EC</div>
      {!collapsed && <div className="min-w-0"><p className="text-sm font-semibold leading-none text-white">Expert Comptable</p><p className="mt-1 text-[11px] text-[var(--color-text-muted)]">Gestion multi-activités</p></div>}
      <button onClick={onToggleCollapse} className="ml-auto hidden lg:grid icon-button h-7 w-7 place-items-center" title={collapsed ? 'Agrandir la navigation' : 'Réduire la navigation'}><Icon name={collapsed ? 'chevron-right' : 'chevron-left'} size={15} /></button>
    </div>
    <nav className="flex-1 overflow-y-auto px-3 py-4">
      {groups.map(([group, label]) => <div key={group} className="mb-5">
        {label && !collapsed && <p className="px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.13em] text-[var(--color-text-muted)]">{label}</p>}
        {navItems.filter(item => item.group === group).map(item => <NavLink key={item.id} to={item.path} title={collapsed ? item.label : undefined} className={({ isActive }) => `nav-item ${isActive ? 'nav-item--active' : ''}`}>
          <Icon name={item.icon} size={17} className="shrink-0" />
          {!collapsed && <span className="min-w-0 flex-1 truncate">{item.label}</span>}
          {item.badge ? <span className="nav-badge">{item.badge}</span> : null}
        </NavLink>)}
      </div>)}
    </nav>
    <div className="border-t border-[var(--color-border)] p-4"><div className="flex items-center gap-2.5"><div className="avatar-initials">{initials(userName)}</div>{!collapsed && <div className="min-w-0"><p className="truncate text-xs font-medium text-white">{userName}</p><p className="mt-0.5 truncate text-[11px] text-[var(--color-text-muted)]">{userRole === 'root' ? 'Administrateur' : 'Utilisateur'}</p></div>}</div></div>
  </aside>;
}
