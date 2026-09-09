// ─────────────────────────────────────────────────────────────
// AppRouter — arbre des routes de l'application
// Heberger-ish du prototype frontend : BrowserRouter + AuthProvider
// ici, App.tsx ne fait que l'instancier. PublicRoute gère /login,
// ProtectedRoute protège le layout (AppLayout) + les pages.
// ─────────────────────────────────────────────────────────────

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from '@/contexts/AuthContext';
import PublicRoute from './PublicRoute';
import ProtectedRoute from './ProtectedRoute';
import AppLayout from '@/layouts/AppLayout';

import Login from '@/pages/Login';
import Dashboard from '@/pages/Dashboard';
import Assurance from '@/pages/Assurance';
import Poulets from '@/pages/Poulets';
import VTC from '@/pages/VTC';
import Transactions from '@/pages/Transactions';
import Creances from '@/pages/Creances';
import Financements from '@/pages/Financements';
import Comptes from '@/pages/Comptes';
import Avances from '@/pages/Avances';
import Personnes from '@/pages/Personnes';
import Rappels from '@/pages/Rappels';
import Assistant from '@/pages/Assistant';
import Rapports from '@/pages/Rapports';
import Documents from '@/pages/Documents';
import Utilisateurs from '@/pages/Utilisateurs';
import Audit from '@/pages/Audit';
import Parametres from '@/pages/Parametres';

export default function AppRouter() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />

          <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/assurance" element={<Assurance />} />
            <Route path="/poulets" element={<Poulets />} />
            <Route path="/vtc" element={<VTC />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="/creances" element={<Creances />} />
            <Route path="/financements" element={<Financements />} />
            <Route path="/comptes" element={<Comptes />} />
            <Route path="/avances" element={<Avances />} />
            <Route path="/personnes" element={<Personnes />} />
            <Route path="/rappels" element={<Rappels />} />
            <Route path="/assistant" element={<Assistant />} />
            <Route path="/rapports" element={<Rapports />} />
            <Route path="/documents" element={<Documents />} />
            <Route path="/utilisateurs" element={<Utilisateurs />} />
            <Route path="/audit" element={<Audit />} />
            <Route path="/parametres" element={<Parametres />} />
          </Route>

          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}