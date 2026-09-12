import { useState } from 'react';
import { fetchUsers, createUser, updateUser, deactivateUser } from '@/services';
import { useApiQuery } from '@/hooks/useApiQuery';
import { useAuth } from '@/contexts/AuthContext';
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
  const { user: me } = useAuth();
  const { data: rawUsers, loading, refetch } = useApiQuery<UserOut[]>(fetchUsers, []);
  const [showCreate, setShowCreate] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isRoot, setIsRoot] = useState(false);

  // ── Modification ─────────────────────────────────────────────
  const [editTarget, setEditTarget] = useState<UserOut | null>(null);
  const [editEmail, setEditEmail] = useState('');
  const [editPassword, setEditPassword] = useState('');
  const [editStatus, setEditStatus] = useState<'active' | 'inactive'>('active');
  const [editRoot, setEditRoot] = useState(false);
  const [editSubmitting, setEditSubmitting] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  // ── Désactivation ───────────────────────────────────────────
  const [deactivateTarget, setDeactivateTarget] = useState<UserOut | null>(null);
  const [deactivating, setDeactivating] = useState(false);

  const [menuUserId, setMenuUserId] = useState<string | null>(null);

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

  function openEdit(target: UserOut) {
    setEditTarget(target);
    setEditEmail(target.email);
    setEditPassword('');
    setEditStatus(target.status);
    setEditRoot(target.roles.includes('root'));
    setEditError(null);
    setMenuUserId(null);
  }

  async function handleEditSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!editTarget) return;
    setEditSubmitting(true); setEditError(null);
    try {
      const payload: { email?: string; password?: string; status?: 'active' | 'inactive'; is_root?: boolean } = {};
      if (editEmail !== editTarget.email) payload.email = editEmail;
      if (editPassword) payload.password = editPassword;
      if (editStatus !== editTarget.status) payload.status = editStatus;
      if (editRoot !== editTarget.roles.includes('root')) payload.is_root = editRoot;
      await updateUser(editTarget.id, payload);
      setEditTarget(null); refetch();
    } catch (err) {
      setEditError(err instanceof Error ? err.message : 'Erreur lors de la modification');
    } finally {
      setEditSubmitting(false);
    }
  }

  async function handleDeactivate() {
    if (!deactivateTarget) return;
    setDeactivating(true);
    try {
      await deactivateUser(deactivateTarget.id);
      setDeactivateTarget(null); setMenuUserId(null); refetch();
    } catch (err) {
      setDeactivateTarget(null);
      setFormError(err instanceof Error ? err.message : 'Erreur lors de la désactivation');
    } finally {
      setDeactivating(false);
    }
  }

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
              <th className="text-right p-6 text-xs font-semibold text-slate-500 uppercase tracking-wide">Actions</th>
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
                <td className="p-6 text-right relative">
                  <button
                    onClick={() => setMenuUserId(menuUserId === user.id ? null : user.id)}
                    className="text-slate-500 hover:text-slate-800 px-2 text-lg leading-none"
                    title="Actions"
                  >⋯</button>
                  {menuUserId === user.id && (
                    <>
                      <button className="fixed inset-0 z-40 cursor-default" aria-label="Fermer" onClick={() => setMenuUserId(null)} />
                      <div className="absolute right-4 top-12 z-50 bg-white rounded-lg border border-slate-200 shadow-lg w-44 overflow-hidden">
                        <button onClick={() => openEdit(user)} className="w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-50">Modifier</button>
                        {user.status === 'active' && user.id !== me?.id && (
                          <button onClick={() => { setDeactivateTarget(user); setMenuUserId(null); }} className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50">Désactiver</button>
                        )}
                      </div>
                    </>
                  )}
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

      {/* Edit user modal */}
      <Modal open={!!editTarget} onClose={() => setEditTarget(null)} title="Modifier l'utilisateur" width="md">
        {editTarget && (
          <form onSubmit={handleEditSubmit} className="space-y-4">
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Email</label>
              <input type="email" value={editEmail} onChange={e => setEditEmail(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 block p-2">Nouveau mot de passe (laisser vide pour conserver)</label>
              <input type="password" minLength={8} value={editPassword} onChange={e => setEditPassword(e.target.value)} className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-slate-500 block p-2">Statut</label>
                <select value={editStatus} onChange={e => setEditStatus(e.target.value as 'active' | 'inactive')} className="w-full border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-700 outline-none focus:border-navy-400 bg-white">
                  <option value="active">Actif</option>
                  <option value="inactive">Inactif</option>
                </select>
              </div>
              <div />
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
              <input type="checkbox" checked={editRoot} onChange={e => setEditRoot(e.target.checked)} />
              Compte administrateur (root)
            </label>

            {editError && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{editError}</p>}

            <div className="flex gap-2 justify-end pt-2">
              <button type="button" onClick={() => setEditTarget(null)} disabled={editSubmitting} className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors disabled:opacity-50">Annuler</button>
              <button type="submit" disabled={editSubmitting} className="px-4 py-2 text-sm bg-navy-800 text-white rounded-lg hover:bg-navy-700 transition-colors disabled:opacity-50">{editSubmitting ? 'Enregistrement…' : 'Enregistrer'}</button>
            </div>
          </form>
        )}
      </Modal>

      {/* Deactivate confirm modal */}
      <Modal open={!!deactivateTarget} onClose={() => setDeactivateTarget(null)} title="Désactiver l'utilisateur" width="sm">
        {deactivateTarget && (
          <div className="space-y-4">
            <p className="text-sm text-slate-700">Désactiver l'utilisateur <strong>{deactivateTarget.person_full_name ?? deactivateTarget.email}</strong> ? Il ne pourra plus se connecter.</p>
            <div className="flex gap-2 justify-end">
              <button type="button" onClick={() => setDeactivateTarget(null)} disabled={deactivating} className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50">Annuler</button>
              <button type="button" onClick={handleDeactivate} disabled={deactivating} className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-500 disabled:opacity-50">{deactivating ? 'Désactivation…' : 'Désactiver'}</button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}