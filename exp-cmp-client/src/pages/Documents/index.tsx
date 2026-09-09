import { useState, useRef } from 'react';
import { fetchDocuments, uploadDocument, getDocumentUrl } from '@/services/mock';
import { useApiQuery } from '@/hooks/useApiQuery';
import { useAuth } from '@/contexts/AuthContext';
import type { Document } from '@/types';

const typeIcons: Record<string, string> = { pdf: '📄', image: '🖼', xls: '📊', other: '📎' };
const typeLabels: Record<string, string> = { pdf: 'PDF', image: 'Image', xls: 'Excel', other: 'Fichier' };

const formatSize = (bytes: number) => {
  if (bytes > 1_000_000) return (bytes / 1_000_000).toFixed(1) + ' Mo';
  return (bytes / 1_000).toFixed(0) + ' ko';
};

export default function Documents() {
  const { profile } = useAuth();
  const [filter, setFilter] = useState<'all' | string>('all');
  const [search, setSearch] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadActivity, setUploadActivity] = useState<string>('general');
  const [uploadMsg, setUploadMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: rawDocs, loading, refetch } = useApiQuery(fetchDocuments, []);

  const useDB = rawDocs !== null && !loading && rawDocs.length > 0;
  const allDocs: Document[] = loading ? [] : (rawDocs ?? []);

  const filtered = allDocs.filter(d => {
    if (filter !== 'all' && d.activity !== filter) return false;
    if (search && !d.name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadMsg(null);
    try {
      await uploadDocument();
      setUploadMsg({ ok: true, text: `✓ "${file.name}" importé avec succès` });
      refetch();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erreur lors de l\'import';
      setUploadMsg({ ok: false, text: msg });
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDownload = async (doc: Document) => {
    if (!doc.url) return;
    try {
      const publicUrl = await getDocumentUrl(doc.url);
      window.open(publicUrl, '_blank');
    } catch {
      // rien à ouvrir (document indisponible)
    }
  };

  return (
    <div className="p-6 max-w-screen-xl mx-auto space-y-6">

      {!useDB && !loading && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800">
          Le module documents n&apos;est pas encore livré côté backend&nbsp;: les fichiers affichés sont des
          données de démonstration, l&apos;upload réel sera actif une fois l&apos;endpoint déployé.
        </div>
      )}

      {/* Filters + upload activity selector */}
      <div className="flex p-4 flex-wrap items-center">
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Rechercher un document…"
          className="border border-slate-200 rounded p-2 text-sm text-slate-700 placeholder-slate-400 outline-none focus:border-navy-400 flex-1 min-w-[200px]"
        />
        {(['all', 'assurance', 'poulets', 'vtc'] as const).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`p-2 rounded-full text-xs font-medium border transition-all ${
              filter === f ? 'bg-navy-800 text-white border-navy-800' : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
            }`}
          >
            {f === 'all' ? 'Tous' : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {/* Upload zone */}
      <div
        onClick={() => fileInputRef.current?.click()}
        className="border-2 border-dashed border-slate-200 rounded-xl p-8 text-center hover:border-navy-300 hover:bg-slate-50 transition-all cursor-pointer"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,.xls,.xlsx"
          onChange={handleFileSelect}
          className="hidden"
        />
        {uploading ? (
          <>
            <div className="w-6 h-6 border-2 border-navy-200 border-t-navy-600 rounded-full animate-spin mx-auto mb-2" />
            <div className="text-sm font-medium text-navy-600">Upload en cours…</div>
          </>
        ) : (
          <>
            <div className="text-3xl mb-2">📎</div>
            <div className="text-sm font-medium text-slate-600 mb-1">Déposer un justificatif</div>
            <div className="text-xs text-slate-400 p-4">PDF, image, reçu, facture · Max 10 Mo</div>
            <div className="flex items-center justify-center gap-2">
              <span className="text-xs text-slate-500">Activité :</span>
              <select
                value={uploadActivity}
                onChange={e => { e.stopPropagation(); setUploadActivity(e.target.value); }}
                onClick={e => e.stopPropagation()}
                className="text-xs border border-slate-200 rounded px-2 py-1 bg-white outline-none"
              >
                <option value="general">Général</option>
                <option value="assurance">Assurance</option>
                <option value="poulets">Poulets</option>
                <option value="vtc">VTC</option>
              </select>
            </div>
          </>
        )}
      </div>

      {uploadMsg && (
        <div className={`text-sm rounded-lg p-4 ${uploadMsg.ok ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
          {uploadMsg.text}
        </div>
      )}

      {/* Documents grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 p-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="bg-white rounded-xl border border-slate-200 p-4 animate-pulse">
              <div className="flex items-start p-4">
                <div className="w-10 h-12 bg-slate-100 rounded" />
                <div className="flex-1 space-y-2">
                  <div className="h-3 bg-slate-100 rounded w-3/4" />
                  <div className="h-2 bg-slate-100 rounded w-1/2" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 p-4">
          {filtered.map(doc => (
            <div key={doc.id} className="bg-white rounded-xl border border-slate-200 p-4 hover:border-slate-300 hover:shadow-sm transition-all">
              <div className="flex items-start p-4">
                <div className="w-10 h-12 bg-slate-100 rounded flex items-center justify-center text-xl shrink-0">
                  {typeIcons[doc.type] ?? typeIcons.other}
                </div>
                <div className="flex-1 overflow-hidden">
                  <div className="text-sm font-medium text-slate-800 truncate">{doc.name}</div>
                  <div className="text-xs text-slate-500 mt-1">{doc.date} · {formatSize(doc.size)}</div>
                  <div className="flex items-center gap-2 p-2">
                    {doc.activity && (
                      <span className={`text-xs font-medium border rounded p-2 mt-1 ${
                        doc.activity === 'assurance' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                        doc.activity === 'poulets' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                        'bg-navy-50 text-navy-700 border-navy-200'
                      }`}>
                        {doc.activity.charAt(0).toUpperCase() + doc.activity.slice(1)}
                      </span>
                    )}
                    <span className="text-xs bg-slate-100 text-slate-500 rounded p-2 mt-1">{typeLabels[doc.type] ?? 'Fichier'}</span>
                    {useDB && <span className="text-xs bg-emerald-50 text-emerald-600 rounded p-2 mt-1">Live</span>}
                  </div>
                </div>
              </div>
              <div className="flex gap-2 border-t border-slate-100 p-4">
                <button
                  onClick={() => handleDownload(doc)}
                  className="flex-1 text-xs text-slate-500 hover:text-navy-600 py-1 rounded hover:bg-slate-50 transition-colors"
                >
                  Télécharger
                </button>
                <button className="flex-1 text-xs text-slate-500 hover:text-red-600 py-1 rounded hover:bg-slate-50 transition-colors">
                  Supprimer
                </button>
              </div>
            </div>
          ))}

          {filtered.length === 0 && (
            <div className="col-span-3 text-center py-12 text-slate-400 text-sm">
              Aucun document trouvé
            </div>
          )}
        </div>
      )}
    </div>
  );
}
