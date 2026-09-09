import { useState } from 'react';
import { fetchUsers, createUser } from '@/services';
import { useApiQuery } from '@/hooks/useApiQuery';
import type { UserOut } from '@/types/api';
import Modal from '@/components/ui/Modal';

const roleColors: Record<string, string> = {
  root: 'bg-red-50 text-red-700 border-red-200',
};
const roleLabels: Record<string, string> = { root: 'Root Admin' };

const roles = [
  { id: 'root', label: 'Root Admin', desc: 'Accès total à toutes les données et fonctions', color: 'bg-red-100 text-red-700 border-red-200' },
];

export default function Utilisateurs() {
  const { data: rawUsers, loading, refetch } = useApiQuery<UserOut[]>(fetchUsers, []);
  const [showCreate, setShowCreate] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isRoot, setIsRoot] = useState(false);

  const users = rawUsers ?? [];

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFormError(null);
    try {
      await createUser({ email, password, full_name: name, is_root: isRoot });
      setShowCreate(false);
      setName(''); setEmail(''); setPassword(''); setIsRoot(false);
      refetch();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Erreur lors de la création');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-6 max-w-screen-xl mx-auto space-y-6">

      {/* Roles */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <div className="flex items-center gap-2 mb-2">
            <span className={`text-xs font-semibold border rounded-full p-2 mt-1 ${roles[0].color}`}>{roles[0].label}</span>
          </div>
          <p className="text-xs text-slate-500 leading-relaxed">{roles[0].desc}</p>
        </div>
      </div>

      {/* Users table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <div className="text-sm font-semibold text-slate-700">Utilisateurs ({users.length})</div>
          <button
            onClick={() => setShowCreate(true)}
            className="text-xs bg-navy-800 text-white rounded-lg p-2 hover:bg-navy-700 transition-colors"
          >
            + Créer un utilisateur
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-100">
              <th className="text-left p-6 text-xs font-semibold text-slate-500 uppercase tracking-wide">Nom</th>
              <th className="text-left p-6 text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">Email</th>
              <th className="text-left p-6 text-xs font-semibold text-slate-500 uppercase tracking-wide">Rôle(s)</th>
              <th className="text-left p-6 text-xs font-semibold text-slate-500 uppercase tracking-wide hidden lg:table-cell">Statut</th>
              <th className="text-left p-6 text-xs font-semibold text-slate-500 uppercase tracking-wide hidden lg:table-cell">Dernière connexion</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="p-12 text-center text-slate-400 text-sm">Chargement…</td></tr>
            ) : users.map(user => (
              <tr key={user.id} className="border-b border-slate-50 hover:bg-slate-50 transition-colors">
                <td className="p-6">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-full bg-navy-100 text-navy-700 flex items-center justify-center text-xs font-semibold">
                      {(user.person_full_name ?? user.email).split(/[@\s]+/).filter(Boolean).map(n => n[0]).join('').slice(0, 2).toUpperCase()}
                    </div>
                    <span className="font-medium text-slate-800">{user.person_full_name ?? user.email}</span>
                  </div>
                </td>
                <td className="p-6 text-slate-500 hidden md:table-cell">{user.email}</td>
                <td className="p-6">
                  <div className="flex gap-1">
                    {user.roles.length > 0 ? user.roles.map(r => (
                      <span key={r} className={`text-xs font-medium border rounded-full px-2 mt-1 ${roleColors[r] ?? 'bg-slate-100 text-slate-600 border-slate-200'}`}>
                        {roleLabels[r] ?? r}
                      </span>
                    )) : (
                      <span className="text-xs text-slate-500">—</span>
                    )}
                  </div>
                </td>
                <td className="p-6 hidden lg:table-cell">
                  <span className={`text-xs font-semibold uppercase tracking-wide rounded-full px-2 mt-1 ${
                    user.status === 'active' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'
                  }`}>
                    {user.status}
                  </span>
                </td>
                <td className="p-6 text-slate-400 text-xs hidden lg:table-cell">
                  {user.last_login_at ? new Date(user.last_login_at).toLocaleDateString('fr-FR') : 'Jamais'}
                </td>
              </tr>
            ))}
            {!loading && users.length === 0 && (
              <tr><td colSpan={5} className="p-12 text-center text-slate-400 text-sm">Aucun utilisateur</td></tr>
            )}
          </tbody>
          </table>
        </div>
      </div>

      {/* Create user modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Créer un utilisateur" width="md">
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-slate-500 block p-2">Nom complet</label>
            <input
              required
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500 block p-2">Email</label>
            <input
              required
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="email@exemple.com"
              className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500 block p-2">Mot de passe (min. 8 caractères)</label>
            <input
              required
              type="password"
              minLength={8}
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400"
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
            <input type="checkbox" checked={isRoot} onChange={e => setIsRoot(e.target.checked)} />
            Compte administrateur (root)
          </label>

          {formError && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{formError}</p>}

          <div className="flex gap-2 justify-end pt-2">
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 text-sm bg-navy-800 text-white rounded-lg hover:bg-navy-700 transition-colors disabled:opacity-50"
            >
              {submitting ? 'Création…' : 'Créer'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}