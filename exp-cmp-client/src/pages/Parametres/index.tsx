import { useAuth } from '@/contexts/AuthContext';
import { fetchBusinesses } from '@/services';
import { useApiQuery } from '@/hooks/useApiQuery';
import type { BusinessOut } from '@/types/api';

export default function Parametres() {
  const { user, profile, isRoot, signOut } = useAuth();
  const { data: rawBusinesses } = useApiQuery<BusinessOut[]>(fetchBusinesses, []);
  const businesses = rawBusinesses ?? [];

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">

      {/* Organisation */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <div className="text-sm font-semibold text-slate-700">Organisation</div>
        <div className="space-y-4">
          <div>
            <label className="text-xs font-medium text-slate-500 block p-2">Nom de l&apos;organisation</label>
            <input defaultValue="Groupe Sow" className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none focus:border-navy-400" />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500 block p-2">Devise</label>
            <select className="border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 w-full outline-none bg-white">
              <option>FCFA (Franc CFA)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Activités */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
        <div className="text-sm font-semibold text-slate-700">Activités</div>
        <div className="space-y-2">
          {businesses.map(b => (
            <div key={b.id} className="flex items-center justify-between py-2 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <div className="text-sm text-slate-700 font-medium">{b.name}</div>
                <span className="font-mono text-xs text-slate-400 bg-slate-100 rounded p-2 mt-1">{b.code}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-emerald-600 bg-emerald-50 rounded px-2 mt-1">
                  {b.status === 'active' ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
          ))}
          {businesses.length === 0 && (
            <div className="text-sm text-slate-400 text-center py-4">Aucune activité trouvée</div>
          )}
        </div>
      </div>

      {/* Backend connection */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
        <div className="text-sm font-semibold text-slate-700">Connexion API</div>
        <div className="flex items-center bg-slate-50 rounded-lg p-4">
          <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
          <div className="flex-1">
            <div className="text-sm font-medium text-slate-800">Session JWT connectée</div>
            <div className="text-xs text-slate-500 mt-1">{user?.email}</div>
          </div>
          <span className={`text-xs font-medium px-2 mt-1 rounded-full ${
            isRoot ? 'bg-navy-100 text-navy-700' : 'bg-slate-100 text-slate-600'
          }`}>
            {isRoot ? 'Root admin' : (profile?.role ?? '—')}
          </span>
        </div>
        <div className="text-xs text-slate-500 bg-slate-50 border border-slate-200 rounded-lg p-4 leading-relaxed">
          L&apos;application utilise l&apos;API FastAPI du backend. Les modules encore en démo
          (VTC, Poulets, créances, financements, documents, avances) affichent des données de
          démonstration tant que leur endpoint n&apos;est pas livré.
        </div>
      </div>

      {/* Session */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <div className="text-sm font-semibold text-slate-700 p-4">Session</div>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm text-slate-800">{profile?.full_name ?? user?.email}</div>
            <div className="text-xs text-slate-400 mt-1">{user?.email}</div>
          </div>
          <button
            onClick={signOut}
            className="text-sm text-red-600 border border-red-200 rounded-lg px-4 py-2 hover:bg-red-50 transition-colors"
          >
            Se déconnecter
          </button>
        </div>
      </div>
    </div>
  );
}