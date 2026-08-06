import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "./apiClient";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [tenant, setTenant] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchMe = useCallback(async () => {
    const token = localStorage.getItem("ned_token");
    if (!token) { setLoading(false); return; }
    try {
      const { data } = await api.get("/auth/me");
      setUser(data.user);
      setTenant(data.tenant);
    } catch {
      localStorage.removeItem("ned_token");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchMe(); }, [fetchMe]);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    localStorage.setItem("ned_token", data.access_token);
    setUser(data.user); setTenant(data.tenant);
  };

  const register = async (payload) => {
    const { data } = await api.post("/auth/register", payload);
    localStorage.setItem("ned_token", data.access_token);
    setUser(data.user); setTenant(data.tenant);
  };

  const logout = () => {
    localStorage.removeItem("ned_token");
    setUser(null); setTenant(null);
    window.location.href = "/auth/login";
  };

  return (
    <AuthCtx.Provider value={{ user, tenant, loading, login, register, logout, refresh: fetchMe, setTenant }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);
