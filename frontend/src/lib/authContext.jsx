import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "./apiClient";

const AuthCtx = createContext(null);

const PLATFORM_ROLES = ["platform_owner", "super_admin"];

const DEFAULT_PERMISSIONS = {
  dashboard: true,
  crm: true,
  sales: true,
  tasks: true,
  finance: false,
  products: false,
  hr: false,
  ai: false,
  calendar: true,
  contracts: true,
  billing: false,
  profile: true,
  settings: false,
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [tenant, setTenant] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchMe = useCallback(async () => {
    const token = localStorage.getItem("ned_token");

    if (!token) {
      setLoading(false);
      return;
    }

    try {
      const { data } = await api.get("/auth/me");

      setUser(data.user);
      setTenant(data.tenant);
    } catch {
      localStorage.removeItem("ned_token");
      localStorage.removeItem("ned_token_original");
      setUser(null);
      setTenant(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMe();
  }, [fetchMe]);

  const login = async (email, password) => {
    localStorage.removeItem("ned_token_original");

    const { data } = await api.post("/auth/login", {
      email,
      password,
    });

    localStorage.setItem("ned_token", data.access_token);

    setUser(data.user);
    setTenant(data.tenant);

    return data;
  };

  const register = async (payload) => {
    localStorage.removeItem("ned_token_original");

    const { data } = await api.post("/auth/register", payload);

    localStorage.setItem("ned_token", data.access_token);

    setUser(data.user);
    setTenant(data.tenant);

    return data;
  };

  const logout = () => {
    localStorage.removeItem("ned_token");
    localStorage.removeItem("ned_token_original");

    setUser(null);
    setTenant(null);

    window.location.href = "/auth/login";
  };

  /*
   * Platform owners and super admins have unrestricted access.
   */
  const isPlatformAdmin =
    user?.platform_role === "platform_owner" ||
    user?.platform_role === "super_admin";

  /*
   * Check frontend access.
   *
   * Access requires:
   * 1. User permission
   * 2. Tenant module enabled
   *
   * Platform admins bypass both checks.
   */
  const can = useCallback(
    (module) => {
      if (!user) return false;

      if (
        user.platform_role === "platform_owner" ||
        user.platform_role === "super_admin"
      ) {
        return true;
      }

      if (!module) return true;

      const permissions = {
        ...DEFAULT_PERMISSIONS,
        ...(user.permissions || {}),
      };

      const permissionAllowed = permissions[module] === true;

      /*
       * Some modules are not stored as tenant modules
       * (profile, dashboard, billing, etc.).
       * In that case the user permission is enough.
       */
      const tenantModules = tenant?.modules || {};

      const tenantModuleExists = Object.prototype.hasOwnProperty.call(
        tenantModules,
        module
      );

      const tenantModuleAllowed = tenantModuleExists
        ? tenantModules[module] !== false
        : true;

      return permissionAllowed && tenantModuleAllowed;
    },
    [user, tenant]
  );

  return (
    <AuthCtx.Provider
      value={{
        user,
        tenant,
        loading,
        login,
        register,
        logout,
        refresh: fetchMe,
        setTenant,
        can,
        isPlatformAdmin,
      }}
    >
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);