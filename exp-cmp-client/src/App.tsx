// ─────────────────────────────────────────────────────────────
// App — point d'entrée racine
// Réduit à l'instanciation de l'AppRouter : le routage vit dans
// routes/AppRouter.tsx (comme le prototype frontend).
// ─────────────────────────────────────────────────────────────

import AppRouter from './routes/AppRouter';

export default function App() {
  return <AppRouter />;
}