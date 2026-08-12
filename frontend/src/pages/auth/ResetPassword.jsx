import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import axios from "axios";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { toast } from "sonner";
import { useLanguage } from "../../i18n";

const API = `${process.env.REACT_APP_BACKEND_URL}/api/v1`;

export default function ResetPassword() {
  const { token } = useParams();
  const nav = useNavigate();
  const { t } = useLanguage();

  const [form, setForm] = useState({
    new_password: "",
    confirm: "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(e) {
    e.preventDefault();
    setError("");

    if (form.new_password !== form.confirm) {
      setError(t("passwordsDoNotMatch"));
      return;
    }

    if (form.new_password.length < 8) {
      setError(t("passwordMinLength"));
      return;
    }

    setLoading(true);

    try {
      await axios.post(`${API}/auth/reset-password`, {
        token,
        new_password: form.new_password,
      });

      toast.success(t("passwordResetSuccess"));
      nav("/auth/login");
    } catch (err) {
      setError(
        err?.response?.data?.detail ||
          t("resetFailed")
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen grid md:grid-cols-2">

      {/* Left */}
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
            {t("setNewPassword")}
          </p>

          <h2 className="text-4xl lg:text-5xl font-black leading-[1.05] tracking-tight">
            {t("oneLastStep")}
          </h2>

        </div>

        <p className="text-xs opacity-60">
          © {new Date().getFullYear()} NED Tech Media
        </p>

      </div>

      {/* Right */}
      <div className="flex items-center justify-center p-8">

        <form
          onSubmit={onSubmit}
          className="w-full max-w-sm space-y-6"
          data-testid="reset-form"
        >

          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              {t("resetPassword")}
            </h1>

            <p className="text-sm text-muted-foreground mt-1">
              {t("resetPasswordDescription")}
            </p>
          </div>

          <div className="space-y-4">

            <div className="space-y-2">
              <Label htmlFor="new-password">
                {t("newPassword")}
              </Label>

              <Input
                id="new-password"
                type="password"
                value={form.new_password}
                onChange={(e) =>
                  setForm({
                    ...form,
                    new_password: e.target.value,
                  })
                }
                required
                minLength={8}
                data-testid="reset-new-pw-input"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirm-password">
                {t("confirmNewPassword")}
              </Label>

              <Input
                id="confirm-password"
                type="password"
                value={form.confirm}
                onChange={(e) =>
                  setForm({
                    ...form,
                    confirm: e.target.value,
                  })
                }
                required
                minLength={8}
                data-testid="reset-confirm-pw-input"
              />
            </div>

          </div>

          <Button
            type="submit"
            className="w-full"
            disabled={loading}
            data-testid="reset-submit-btn"
          >
            {loading
              ? t("resetting")
              : t("resetPassword")}
          </Button>

          {error && (
            <div
              className="rounded-md border border-destructive/40 bg-destructive/10 text-destructive text-sm p-3"
              data-testid="reset-error"
            >
              {error}
            </div>
          )}

          <div className="text-sm text-center text-muted-foreground">
            <Link
              to="/auth/login"
              className="underline text-foreground"
            >
              {t("backToSignIn")}
            </Link>
          </div>

        </form>
      </div>
    </div>
  );
}