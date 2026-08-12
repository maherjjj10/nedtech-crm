import { useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { toast } from "sonner";
import { useLanguage } from "../../i18n";

const API = `${process.env.REACT_APP_BACKEND_URL}/api/v1`;

export default function ForgotPassword() {
  const { t } = useLanguage();

  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [devUrl, setDevUrl] = useState("");

  async function onSubmit(e) {
    e.preventDefault();
    setLoading(true);

    try {
      const { data } = await axios.post(
        `${API}/auth/forgot-password`,
        { email: email.trim() }
      );

      setSent(true);

      if (data.dev_reset_url) {
        setDevUrl(data.dev_reset_url);
      }
    } catch (err) {
      toast.error(
        err?.response?.data?.detail ||
          t("somethingWentWrong")
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
            {t("recoverAccess")}
          </p>

          <h2 className="text-4xl lg:text-5xl font-black leading-[1.05] tracking-tight">
            {t("lockedOutTitle")}
          </h2>

          <p className="text-base opacity-70 max-w-md">
            {t("recoverAccessDescription")}
          </p>

        </div>

        <p className="text-xs opacity-60">
          © {new Date().getFullYear()} NED Tech Media
        </p>

      </div>

      {/* Right */}
      <div className="flex items-center justify-center p-8">

        {!sent ? (

          <form
            onSubmit={onSubmit}
            className="w-full max-w-sm space-y-6"
            data-testid="forgot-form"
          >

            <div>
              <h1 className="text-3xl font-bold tracking-tight">
                {t("forgotPassword")}
              </h1>

              <p className="text-sm text-muted-foreground mt-1">
                {t("forgotPasswordDescription")}
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">
                {t("email")}
              </Label>

              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) =>
                  setEmail(e.target.value)
                }
                required
                data-testid="forgot-email-input"
              />
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={loading}
              data-testid="forgot-submit-btn"
            >
              {loading
                ? t("sending")
                : t("sendResetLink")}
            </Button>

            <div className="text-sm text-center text-muted-foreground">
              {t("rememberedPassword")}{" "}

              <Link
                to="/auth/login"
                className="underline text-foreground"
              >
                {t("signIn")}
              </Link>
            </div>

          </form>

        ) : (

          <div
            className="w-full max-w-sm space-y-4"
            data-testid="forgot-success"
          >

            <h1 className="text-3xl font-bold tracking-tight">
              {t("checkYourEmail")}
            </h1>

            <p className="text-sm text-muted-foreground">
              {t("resetEmailSentPrefix")}{" "}
              <b>{email}</b>{" "}
              {t("resetEmailSentSuffix")}
            </p>

            {devUrl && (
              <div className="rounded-md border border-border p-3 text-xs">

                <div className="n-overline mb-1">
                  {t("devModeEmailNotConfigured")}
                </div>

                <a
                  className="underline break-all"
                  href={devUrl}
                >
                  {devUrl}
                </a>

              </div>
            )}

            <Link
              to="/auth/login"
              className="underline text-sm"
            >
              {t("backToSignIn")}
            </Link>

          </div>

        )}

      </div>
    </div>
  );
}