import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { useAuth } from "../../lib/authContext";
import { toast } from "sonner";
import { useLanguage } from "../../i18n";

export default function Login() {
  const nav = useNavigate();
  const { login } = useAuth();
  const { t } = useLanguage();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    try {
      localStorage.removeItem("ned_token");
      localStorage.removeItem("ned_token_original");
    } catch {
      // ignore
    }
  }, []);

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(email.trim(), password);
      toast.success(t("welcomeBack"));
      nav("/");
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        (err?.response
          ? `${t("loginFailed")} (${err.response.status})`
          : t("cannotReachServer"));

      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen grid md:grid-cols-2">

      <div className="hidden md:flex flex-col justify-between bg-foreground text-background p-12">

        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-md bg-background text-foreground flex items-center justify-center font-black">
            N
          </div>

          <div className="text-lg font-semibold tracking-tight">
            NED Tech CRM
          </div>
        </div>

        <div className="space-y-6">

          <p className="text-xs uppercase tracking-[0.3em] opacity-70">
            {t("enterpriseBusinessOs")}
          </p>

          <h2 className="text-4xl lg:text-5xl font-black leading-[1.05] tracking-tight">
            {t("loginHeroTitle")}
          </h2>

          <p className="text-base opacity-70 max-w-md">
            {t("loginHeroDescription")}
          </p>

        </div>

        <p className="text-xs opacity-60">
          © {new Date().getFullYear()} NED Tech Media
        </p>

      </div>

      <div className="flex items-center justify-center p-8">

        <form
          onSubmit={onSubmit}
          className="w-full max-w-sm space-y-6"
          data-testid="login-form"
        >

          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              {t("signIn")}
            </h1>

            <p className="text-sm text-muted-foreground mt-1">
              {t("signInDescription")}
            </p>
          </div>

          <div className="space-y-4">

            <div className="space-y-2">
              <Label htmlFor="email">
                {t("email")}
              </Label>

              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                data-testid="login-email-input"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">
                {t("password")}
              </Label>

              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                data-testid="login-password-input"
              />
            </div>

          </div>

          <Button
            type="submit"
            className="w-full"
            disabled={loading}
            data-testid="login-submit-btn"
          >
            {loading
              ? t("signingIn")
              : t("signIn")}
          </Button>

          {error && (
            <div
              className="rounded-md border border-destructive/40 bg-destructive/10 text-destructive text-sm p-3"
              data-testid="login-error"
            >
              {error}
            </div>
          )}

          <div className="text-sm text-center text-muted-foreground">
            <Link
              to="/auth/forgot-password"
              className="underline text-foreground"
              data-testid="link-forgot"
            >
              {t("forgotPassword")}
            </Link>
          </div>

          <div className="text-sm text-center text-muted-foreground">
            {t("dontHaveAccount")}{" "}

            <Link
              to="/auth/register"
              className="underline text-foreground"
              data-testid="link-register"
            >
              {t("createWorkspace")}
            </Link>
          </div>

        </form>
      </div>
    </div>
  );
}