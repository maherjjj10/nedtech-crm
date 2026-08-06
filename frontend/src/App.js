import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./App.css";
import { AuthProvider, useAuth } from "./lib/authContext";
import { ThemeProvider } from "./lib/themeContext";
import AppShell from "./components/layout/AppShell";
import Login from "./pages/auth/Login";
import Register from "./pages/auth/Register";
import AuthCallback from "./pages/auth/Callback";
import ForgotPassword from "./pages/auth/ForgotPassword";
import ResetPassword from "./pages/auth/ResetPassword";
import InviteAccept from "./pages/InviteAccept";
import Dashboard from "./pages/Dashboard";
import Clients from "./pages/Clients";
import ClientDetail from "./pages/ClientDetail";
import Pipeline from "./pages/Pipeline";
import Tasks from "./pages/Tasks";
import Finance from "./pages/Finance";
import Products from "./pages/Products";
import Employees from "./pages/Employees";
import AIAssistant from "./pages/AIAssistant";
import Settings from "./pages/Settings";
import Billing from "./pages/Billing";
import BillingSuccess from "./pages/BillingSuccess";
import Platform from "./pages/Platform";
import Profile from "./pages/Profile";
import Contracts from "./pages/Contracts";
import PublicQuote from "./pages/PublicQuote";
import PublicContract from "./pages/PublicContract";

function Guard({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen flex items-center justify-center text-sm text-muted-foreground">Loading…</div>;
  if (!user) return <Navigate to="/auth/login" replace />;
  return children;
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/auth/login" element={<Login />} />
            <Route path="/auth/register" element={<Register />} />
            <Route path="/auth/callback" element={<AuthCallback />} />
            <Route path="/auth/forgot-password" element={<ForgotPassword />} />
            <Route path="/auth/reset-password/:token" element={<ResetPassword />} />
            <Route path="/invite/:token" element={<InviteAccept />} />
            <Route path="/billing/success" element={<BillingSuccess />} />
            <Route path="/billing/cancel" element={<Navigate to="/billing" replace />} />
            <Route path="/public/quote/:token" element={<PublicQuote />} />
            <Route path="/public/contract/:token" element={<PublicContract />} />

            <Route element={<Guard><AppShell /></Guard>}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/clients" element={<Clients />} />
              <Route path="/clients/:id" element={<ClientDetail />} />
              <Route path="/pipeline" element={<Pipeline />} />
              <Route path="/tasks" element={<Tasks />} />
              <Route path="/finance" element={<Finance />} />
              <Route path="/contracts" element={<Contracts />} />
              <Route path="/products" element={<Products />} />
              <Route path="/employees" element={<Employees />} />
              <Route path="/ai" element={<AIAssistant />} />
              <Route path="/billing" element={<Billing />} />
              <Route path="/platform" element={<Platform />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/settings" element={<Settings />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
