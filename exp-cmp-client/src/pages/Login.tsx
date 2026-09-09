import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';

/* ─────────────────────────────────────────────
   Botanical illustration — clean bezier paths
   ───────────────────────────────────────────── */
function BotanicalPanel() {
  return (
    <div className="absolute inset-0 overflow-hidden" style={{ background: 'var(--color-primary)' }}>
      <svg className="absolute inset-0 w-full h-full" viewBox="0 0 400 640" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
        <path d="M0 640 C80 580 180 560 280 540 C340 530 380 520 400 510 L400 640Z" fill="var(--color-divider)" />
        <path d="M0 640 C100 610 200 595 300 575 C360 562 390 555 400 548 L400 640Z" fill="var(--color-border)" />
        <path d="M0 640 C120 628 230 618 320 605 C370 598 395 592 400 588 L400 640Z" fill="var(--color-border)" />
        <path d="M0 640 C150 636 260 632 350 624 C385 620 398 617 400 615 L400 640Z" fill="var(--color-border)" />
        <path d="M0 640 C180 639 300 638 380 635 L400 634 L400 640Z" fill="var(--color-border)" />
        <path d="M400 0 C380 60 390 140 375 220 C365 290 350 340 360 400 L400 400Z" fill="var(--color-divider)" />
        <path d="M400 0 C390 80 395 160 385 240 C378 300 370 350 378 400 L400 400Z" fill="var(--color-border)" />
      </svg>

      <svg className="absolute" style={{ bottom: -20, left: -30, width: 220, height: 380 }} viewBox="0 0 220 380" xmlns="http://www.w3.org/2000/svg">
        <path d="M110 380 C108 300 105 220 100 140 C98 100 95 60 90 10" stroke="var(--color-secondary)" strokeWidth="4" fill="none" strokeLinecap="round" />
        <path d="M108 340 C90 320 60 305 30 310 C55 300 85 315 108 340Z" fill="var(--color-primary)" />
        <path d="M106 300 C85 278 50 260 15 265 C45 255 82 272 106 300Z" fill="var(--color-secondary)" />
        <path d="M104 258 C82 234 45 215 10 218 C40 207 80 228 104 258Z" fill="var(--color-primary)" />
        <path d="M102 218 C80 192 42 172 8 173 C38 162 78 184 102 218Z" fill="var(--color-secondary)" />
        <path d="M100 178 C78 150 42 130 10 130 C38 118 77 140 100 178Z" fill="var(--color-primary)" />
        <path d="M99 140 C77 112 42 90 12 88 C38 76 76 100 99 140Z" fill="var(--color-secondary)" />
        <path d="M97 100 C76 72 44 50 18 46 C42 34 76 58 97 100Z" fill="var(--color-primary)" />
        <path d="M110 340 C128 318 158 302 188 306 C163 297 133 314 110 340Z" fill="var(--color-primary)" />
        <path d="M108 298 C128 274 160 257 190 260 C165 250 133 268 108 298Z" fill="var(--color-secondary)" />
        <path d="M106 256 C126 230 158 212 186 213 C162 203 131 222 106 256Z" fill="var(--color-primary)" />
        <path d="M104 215 C124 187 155 168 182 168 C158 158 128 178 104 215Z" fill="var(--color-secondary)" />
        <path d="M102 175 C122 146 152 126 178 125 C155 114 125 136 102 175Z" fill="var(--color-primary)" />
        <path d="M100 136 C119 106 149 86 174 83 C152 72 122 95 100 136Z" fill="var(--color-secondary)" />
        <path d="M98 96 C116 66 144 46 168 42 C147 31 118 55 98 96Z" fill="var(--color-primary)" />
      </svg>

      <svg className="absolute" style={{ top: -40, right: -40, width: 260, height: 280 }} viewBox="0 0 260 280" xmlns="http://www.w3.org/2000/svg">
        {([
          { d: "M200 260 C180 220 140 160 80 100 C110 150 155 210 200 260Z", fill: "var(--color-surface-primary)" },
          { d: "M200 260 C195 215 175 150 130 80 C150 140 180 210 200 260Z", fill: "var(--color-primary)" },
          { d: "M200 260 C205 215 200 148 170 75 C178 138 200 210 200 260Z", fill: "var(--color-surface-primary)" },
          { d: "M200 260 C215 215 225 148 215 72 C208 138 215 210 200 260Z", fill: "var(--color-primary)" },
          { d: "M200 260 C225 218 248 155 255 78 C238 145 228 212 200 260Z", fill: "var(--color-surface-primary)" },
          { d: "M200 260 C232 224 268 168 285 95 C260 155 242 218 200 260Z", fill: "var(--color-primary)" },
        ] as { d: string; fill: string }[]).map((leaf, i) => (
          <path key={i} d={leaf.d} fill={leaf.fill} opacity="0.9" />
        ))}
        <path d="M200 260 C195 230 185 190 170 150" stroke="var(--color-background-primary)" strokeWidth="3" fill="none" strokeLinecap="round" />
      </svg>

      <svg className="absolute" style={{ bottom: 60, left: 80, width: 120, height: 200 }} viewBox="0 0 120 200" xmlns="http://www.w3.org/2000/svg">
        <path d="M20 200 C22 160 30 120 15 60" stroke="var(--color-secondary)" strokeWidth="3" fill="none" strokeLinecap="round" />
        <path d="M40 200 C38 155 42 110 55 50" stroke="var(--color-secondary)" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        <path d="M60 200 C58 170 55 130 40 80" stroke="var(--color-primary)" strokeWidth="2" fill="none" strokeLinecap="round" />
        <path d="M80 200 C80 165 85 125 100 65" stroke="var(--color-secondary)" strokeWidth="2" fill="none" strokeLinecap="round" />
        <path d="M100 200 C98 172 95 140 85 95" stroke="var(--color-secondary)" strokeWidth="1.5" fill="none" strokeLinecap="round" />
      </svg>

      <svg className="absolute" style={{ top: 220, right: 10, width: 100, height: 130 }} viewBox="0 0 100 130" xmlns="http://www.w3.org/2000/svg">
        <path d="M50 125 C48 100 40 70 20 40 C10 25 5 10 8 0 C30 20 55 55 60 90 C62 75 58 50 48 20 C55 10 68 5 75 0 C72 25 65 55 60 90 C60 105 56 118 50 125Z" fill="var(--color-surface-primary)" opacity="0.8" />
      </svg>

      <div className="absolute top-6 left-6">
        <div className="font-display font-bold text-white/70 text-sm tracking-[0.15em]">EXPERT COMPTABLE</div>
        <div className="font-display text-white/40 text-xs tracking-widest mt-1">GESTION MULTI-ACTIVITÉS</div>
      </div>

      <div className="absolute bottom-8 left-0 right-0 px-6 text-center">
        <p className="font-display text-[var(--color-primary)] text-xs font-medium opacity-60">Assurance · Poulets · VTC</p>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   Login page — session JWT FastAPI
   ───────────────────────────────────────────── */
export default function Login() {
  const { signIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPwd, setShowPwd] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const { error } = await signIn(email, password);
    if (error) setError(error);
    setLoading(false);
  };

  const inputClass = "ledger-input w-full font-display outline-none transition-all";

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden"
      style={{ background: 'var(--color-background-primary)' }}
    >
      <div className="absolute top-0 left-0 w-80 h-80 rounded-full bg-[var(--color-primary)]/10 blur-3xl -translate-x-1/2 -translate-y-1/2" />
      <div className="absolute bottom-0 right-0 w-96 h-96 rounded-full bg-[var(--color-primary)]/10 blur-3xl translate-x-1/3 translate-y-1/3" />

      <div className="ledger-card relative w-full flex overflow-hidden" style={{ maxWidth: 840, minHeight: 500 }}>

        <div className="flex-1 bg-[var(--color-surface-glass)] flex flex-col justify-center p-12" style={{ minWidth: 340 }}>

          <div className="flex items-center p-2 mb-8">
            <div className="w-8 h-8 rounded-lg bg-[var(--color-primary)] flex items-center justify-center">
              <span className="text-white text-xs font-bold font-mono">EC</span>
            </div>
            <span className="font-display font-semibold text-slate-800 text-base tracking-tight">Expert Comptable</span>
          </div>

          <h1 className="font-display text-3xl font-semibold text-slate-800 mb-1">Se connecter</h1>
          <p className="font-display text-sm text-slate-500 mb-7">Accédez à votre tableau de bord.</p>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="font-display text-xs font-semibold text-slate-500 block p-2 ml-1">Email</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} required autoComplete="email" placeholder="vous@exemple.com" className={inputClass} />
            </div>
            <div>
              <label className="font-display text-xs font-semibold text-slate-500 block p-2 ml-1">Mot de passe</label>
              <div className="relative">
                <input type={showPwd ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} required autoComplete="current-password" placeholder="••••••••" className={`${inputClass} pr-12`} />
                <button type="button" onClick={() => setShowPwd(v => !v)} className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                    {showPwd
                      ? <><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></>
                      : <><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></>
                    }
                  </svg>
                </button>
              </div>
            </div>

            {error && <p className="font-display text-sm text-red-600 bg-red-50 rounded-2xl px-4 p-2">{error}</p>}

            <button type="submit" disabled={loading} className="ledger-button w-full font-display">
              {loading ? 'Connexion…' : 'Se connecter'}
            </button>
          </form>
        </div>

        <div className="hidden md:block relative" style={{ width: 300, flexShrink: 0 }}>
          <BotanicalPanel />
        </div>
      </div>
    </div>
  );
}
