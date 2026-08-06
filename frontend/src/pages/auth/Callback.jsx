import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../../lib/authContext";

export default function AuthCallback() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const { refresh } = useAuth();

  useEffect(() => {
    const token = params.get("token");
    if (token) {
      localStorage.setItem("ned_token", token);
      refresh().then(() => nav("/"));
    } else {
      nav("/auth/login");
    }
  // eslint-disable-next-line
  }, []);

  return <div className="min-h-screen flex items-center justify-center text-sm text-muted-foreground">Signing you in…</div>;
}
