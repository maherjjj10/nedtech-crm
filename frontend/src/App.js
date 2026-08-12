import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import "./App.css";

import {
  AuthProvider,
  useAuth,
} from "./lib/authContext";

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


/*
 * Basic authentication guard.
 */
function Guard({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-sm text-muted-foreground">
        Loading…
      </div>
    );
  }

  if (!user) {
    return (
      <Navigate
        to="/auth/login"
        replace
      />
    );
  }

  return children;
}


/*
 * Permission guard.
 *
 * Example:
 *
 * <PermissionGuard module="finance">
 *   <Finance />
 * </PermissionGuard>
 *
 * If the employee doesn't have permission,
 * he is redirected to Dashboard.
 */
function PermissionGuard({
  module,
  children,
}) {
  const {
    user,
    loading,
    can,
  } = useAuth();


  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-sm text-muted-foreground">
        Loading…
      </div>
    );
  }


  if (!user) {
    return (
      <Navigate
        to="/auth/login"
        replace
      />
    );
  }


  if (!can(module)) {
    return (
      <Navigate
        to="/"
        replace
      />
    );
  }


  return children;
}


/*
 * Platform administrator guard.
 */
function PlatformGuard({ children }) {
  const {
    user,
    loading,
  } = useAuth();


  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-sm text-muted-foreground">
        Loading…
      </div>
    );
  }


  if (!user) {
    return (
      <Navigate
        to="/auth/login"
        replace
      />
    );
  }


  const isPlatformAdmin =
    user.platform_role === "platform_owner" ||
    user.platform_role === "super_admin";


  if (!isPlatformAdmin) {
    return (
      <Navigate
        to="/"
        replace
      />
    );
  }


  return children;
}


function App() {
  return (
    <ThemeProvider>

      <AuthProvider>

        <BrowserRouter>

          <Routes>

            {/* =========================================
                PUBLIC / AUTH
            ========================================= */}

            <Route
              path="/auth/login"
              element={<Login />}
            />

            <Route
              path="/auth/register"
              element={<Register />}
            />

            <Route
              path="/auth/callback"
              element={<AuthCallback />}
            />

            <Route
              path="/auth/forgot-password"
              element={<ForgotPassword />}
            />

            <Route
              path="/auth/reset-password/:token"
              element={<ResetPassword />}
            />

            <Route
              path="/invite/:token"
              element={<InviteAccept />}
            />

            <Route
              path="/billing/success"
              element={<BillingSuccess />}
            />

            <Route
              path="/billing/cancel"
              element={<Navigate to="/billing" replace />}
            />

            <Route
              path="/public/quote/:token"
              element={<PublicQuote />}
            />

            <Route
              path="/public/contract/:token"
              element={<PublicContract />}
            />


            {/* =========================================
                PROTECTED APPLICATION
            ========================================= */}

            <Route
              element={
                <Guard>
                  <AppShell />
                </Guard>
              }
            >

              {/* Dashboard */}
              <Route
                path="/"
                element={
                  <PermissionGuard module="dashboard">
                    <Dashboard />
                  </PermissionGuard>
                }
              />


              {/* CRM */}
              <Route
                path="/clients"
                element={
                  <PermissionGuard module="crm">
                    <Clients />
                  </PermissionGuard>
                }
              />

              <Route
                path="/clients/:id"
                element={
                  <PermissionGuard module="crm">
                    <ClientDetail />
                  </PermissionGuard>
                }
              />


              {/* Sales */}
              <Route
                path="/pipeline"
                element={
                  <PermissionGuard module="sales">
                    <Pipeline />
                  </PermissionGuard>
                }
              />


              {/* Tasks */}
              <Route
                path="/tasks"
                element={
                  <PermissionGuard module="tasks">
                    <Tasks />
                  </PermissionGuard>
                }
              />


              {/* Finance */}
              <Route
                path="/finance"
                element={
                  <PermissionGuard module="finance">
                    <Finance />
                  </PermissionGuard>
                }
              />


              {/* Contracts */}
              <Route
                path="/contracts"
                element={
                  <PermissionGuard module="contracts">
                    <Contracts />
                  </PermissionGuard>
                }
              />


              {/* Products */}
              <Route
                path="/products"
                element={
                  <PermissionGuard module="products">
                    <Products />
                  </PermissionGuard>
                }
              />


              {/* Employees / HR */}
              <Route
                path="/employees"
                element={
                  <PermissionGuard module="hr">
                    <Employees />
                  </PermissionGuard>
                }
              />


              {/* AI */}
              <Route
                path="/ai"
                element={
                  <PermissionGuard module="ai">
                    <AIAssistant />
                  </PermissionGuard>
                }
              />


              {/* Billing */}
              <Route
                path="/billing"
                element={
                  <PermissionGuard module="billing">
                    <Billing />
                  </PermissionGuard>
                }
              />


              {/* Profile */}
              <Route
                path="/profile"
                element={
                  <PermissionGuard module="profile">
                    <Profile />
                  </PermissionGuard>
                }
              />


              {/* Settings */}
              <Route
                path="/settings"
                element={
                  <PermissionGuard module="settings">
                    <Settings />
                  </PermissionGuard>
                }
              />


              {/* Platform Admin */}
              <Route
                path="/platform"
                element={
                  <PlatformGuard>
                    <Platform />
                  </PlatformGuard>
                }
              />

            </Route>


            {/* =========================================
                FALLBACK
            ========================================= */}

            <Route
              path="*"
              element={
                <Navigate
                  to="/"
                  replace
                />
              }
            />

          </Routes>

        </BrowserRouter>

      </AuthProvider>

    </ThemeProvider>
  );
}


export default App;