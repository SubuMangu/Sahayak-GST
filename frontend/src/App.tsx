import { Navigate, Route, Routes } from "react-router-dom";

import Layout from "./components/Layout";
import { useAuth } from "./store/auth";

import Billing from "./pages/Billing";
import Dashboard from "./pages/Dashboard";
import InvoiceReview from "./pages/InvoiceReview";
import Invoices from "./pages/Invoices";
import Login from "./pages/Login";
import Notifications from "./pages/Notifications";
import Onboarding from "./pages/Onboarding";
import Reconciliation from "./pages/Reconciliation";
import Returns from "./pages/Returns";
import Settings from "./pages/Settings";

function RequireAuth({ children }: { children: JSX.Element }) {
  const token = useAuth((s) => s.accessToken);
  return token ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/onboarding" element={<RequireAuth><Onboarding /></RequireAuth>} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/invoices" element={<Invoices />} />
        <Route path="/invoices/:id" element={<InvoiceReview />} />
        <Route path="/returns" element={<Returns />} />
        <Route path="/reconciliation" element={<Reconciliation />} />
        <Route path="/billing" element={<Billing />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/notifications" element={<Notifications />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
