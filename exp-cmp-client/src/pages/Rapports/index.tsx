import { useState } from 'react';

const reportCategories = [
  {
    id: 'global',
    label: 'Vue globale',
    reports: [
      { id: 'r01', title: 'Résultat global', desc: 'Chiffre d\'affaires, dépenses, résultat net consolidé', icon: '📊' },
      { id: 'r02', title: 'Trésorerie', desc: 'Soldes par compte et par activité, flux de la période', icon: '💰' },
      { id: 'r03', title: 'Financements internes', desc: 'État des avances inter-activités', icon: '🔄' },
    ],
  },
  {
    id: 'activites',
    label: 'Par activité',
    reports: [
      { id: 'r04', title: 'Résultat Assurance', desc: 'CA, encaissements, créances, contrats actifs', icon: '🛡' },
      { id: 'r05', title: 'Résultat Poulets', desc: 'Lots, coûts, ventes, marges, stock', icon: '🐓' },
      { id: 'r06', title: 'Résultat VTC', desc: 'Versements, dépenses, rentabilité par véhicule', icon: '🚗' },
    ],
  },
  {
    id: 'detail',
    label: 'Détaillés',
    reports: [
      { id: 'r07', title: 'Créances & dettes', desc: 'Tous les montants à recevoir et à payer', icon: '◎' },
      { id: 'r08', title: 'Dépenses par catégorie', desc: 'Ventilation complète des sorties', icon: '📋' },
      { id: 'r09', title: 'Rentabilité véhicules', desc: 'Comparaison Ford Escape vs Toyota Corolla', icon: '🏎' },
      { id: 'r10', title: 'Rentabilité lots poulets', desc: 'Marge par lot, coût unitaire, évolution', icon: '📈' },
    ],
  },
];

const periods = [
  { id: 'today', label: "Aujourd'hui" },
  { id: '7d', label: '7 derniers jours' },
  { id: 'month', label: 'Ce mois' },
  { id: 'prev_month', label: 'Mois précédent' },
  { id: 'year', label: 'Année 2026' },
  { id: 'custom', label: 'Personnalisé' },
];

export default function Rapports() {
  const [selectedPeriod, setSelectedPeriod] = useState('month');
  const [generating, setGenerating] = useState<string | null>(null);

  const generate = (id: string) => {
    setGenerating(id);
    setTimeout(() => setGenerating(null), 1500);
  };

  return (
    <div className="p-6 max-w-screen-xl mx-auto space-y-6">

      {/* Period selector */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <div className="text-sm font-semibold text-slate-700 p-4">Période du rapport</div>
        <div className="flex flex-wrap gap-2">
          {periods.map(p => (
            <button
              key={p.id}
              onClick={() => setSelectedPeriod(p.id)}
              className={`px-4 py-2 rounded-lg text-sm font-medium border transition-all ${
                selectedPeriod === p.id
                  ? 'bg-navy-800 text-white border-navy-800'
                  : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
        {selectedPeriod === 'custom' && (
          <div className="flex p-4 items-center">
            <input type="date" defaultValue="2026-08-01" className="border border-slate-200 rounded p-2 text-sm text-slate-700 outline-none" />
            <span className="text-slate-400 text-sm">→</span>
            <input type="date" defaultValue="2026-08-23" className="border border-slate-200 rounded p-2 text-sm text-slate-700 outline-none" />
          </div>
        )}
      </div>

      {/* Report categories */}
      {reportCategories.map(cat => (
        <div key={cat.id}>
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-widest p-4">{cat.label}</div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 p-4">
            {cat.reports.map(report => (
              <div key={report.id} className="bg-white rounded-xl border border-slate-200 p-6 flex flex-col">
                <div className="flex items-start p-4 mb-4">
                  <span className="text-2xl">{report.icon}</span>
                  <div>
                    <div className="font-semibold text-slate-800">{report.title}</div>
                    <div className="text-xs text-slate-500 mt-1 leading-relaxed">{report.desc}</div>
                  </div>
                </div>

                <div className="mt-auto flex gap-2">
                  <button
                    onClick={() => generate(report.id + '-preview')}
                    className="flex-1 py-2 border border-slate-200 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-50 transition-colors"
                  >
                    {generating === report.id + '-preview' ? 'Génération…' : 'Aperçu'}
                  </button>
                  <button
                    onClick={() => generate(report.id + '-pdf')}
                    className="flex-1 py-2 border border-slate-200 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-50 transition-colors"
                  >
                    {generating === report.id + '-pdf' ? '⏳ PDF…' : '⬇ PDF'}
                  </button>
                  <button
                    onClick={() => generate(report.id + '-xls')}
                    className="flex-1 py-2 border border-slate-200 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-50 transition-colors"
                  >
                    {generating === report.id + '-xls' ? '⏳ Excel…' : '⬇ Excel'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      <div className="text-xs text-slate-400 text-center pt-2">
        Les exports PDF et Excel sont disponibles dans la version connectée à Supabase.
      </div>
    </div>
  );
}
