import { useEffect, useState } from "react";
import PageHeader from "../components/layout/PageHeader";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { api } from "../lib/apiClient";
import { toast } from "sonner";
import { Check, ExternalLink, Sparkles } from "lucide-react";
import { useAuth } from "../lib/authContext";
import { useLanguage } from "../i18n";

export default function Billing() {
  const { tenant } = useAuth();
  const { t } = useLanguage();

  const [plans, setPlans] = useState([]);
  const [status, setStatus] = useState(null);
  const [onboardUrl, setOnboardUrl] = useState("");
  const [loading, setLoading] = useState(null);

  const load = async () => {
    const [p, s] = await Promise.all([
      api.get("/billing/plans"),
      api.get("/billing/status"),
    ]);

    setPlans(p.data.plans || []);
    setOnboardUrl(p.data.onboarding_url || "");
    setStatus(s.data);
  };

  useEffect(() => {
    load();
  }, []);

  const checkout = async (lookup_key) => {
    setLoading(lookup_key);

    try {
      const { data } = await api.post("/billing/checkout", {
        lookup_key,
        origin_url: window.location.origin,
      });

      window.location.href = data.checkout_url;
    } catch (err) {
      toast.error(
        err?.response?.data?.detail ||
          t("checkoutFailed")
      );

      setLoading(null);
    }
  };

  const currentPlan = status?.plan;

  return (
    <>
      <PageHeader
        title={t("billingPlans")}
        description={t("billingDescription")}
      />

      <div className="p-8 space-y-6">

        {status?.status === "active" && (
          <Card className="p-4 border-border/70 bg-accent">

            <div className="flex items-center gap-3">

              <div className="h-8 w-8 rounded-full bg-foreground text-background flex items-center justify-center">
                <Check className="h-4 w-4" />
              </div>

              <div>
                <div className="text-sm font-medium">
                  {t("youAreOnThe")}{" "}
                  <span className="capitalize">
                    {(currentPlan || "").replace(
                      "_monthly",
                      ""
                    )}
                  </span>{" "}
                  {t("plan")}
                </div>

                <div className="text-xs text-muted-foreground">
                  {t("status")}: {status.status}
                </div>
              </div>

            </div>
          </Card>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

          {plans.map((p) => {
            const isCurrent =
              currentPlan === p.lookup_key;

            return (
              <Card
                key={p.lookup_key}
                className="p-6 border-border/70 flex flex-col n-card-hover"
                data-testid={`plan-${p.lookup_key}`}
              >

                <div className="flex items-center justify-between">

                  <h3 className="text-xl font-bold">
                    {p.name}
                  </h3>

                  {p.name === "Pro" && (
                    <Badge>
                      {t("popular")}
                    </Badge>
                  )}

                </div>

                <div className="mt-2 text-3xl font-black">
                  $
                  {p.amount ??
                    p.price_display?.replace(
                      /[^0-9]/g,
                      ""
                    ) ??
                    0}

                  <span className="text-sm font-medium text-muted-foreground">
                    {t("perMonth")}
                  </span>
                </div>

                <ul className="mt-4 space-y-2 text-sm flex-1">

                  {p.features.map((f, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2"
                    >
                      <Check className="h-4 w-4 mt-0.5 text-foreground" />
                      {f}
                    </li>
                  ))}

                </ul>

                <Button
                  className="mt-6"
                  variant={
                    isCurrent
                      ? "outline"
                      : "default"
                  }
                  disabled={
                    isCurrent ||
                    loading === p.lookup_key
                  }
                  onClick={() =>
                    checkout(p.lookup_key)
                  }
                  data-testid={`checkout-${p.lookup_key}`}
                >
                  {isCurrent
                    ? t("currentPlan")
                    : loading === p.lookup_key
                    ? t("redirecting")
                    : t("choosePlan")}
                </Button>

              </Card>
            );
          })}

        </div>

        {onboardUrl && (
          <Card className="p-6 border-border/70">

            <div className="flex items-start gap-3">

              <Sparkles className="h-5 w-5 mt-0.5" />

              <div className="flex-1">

                <div className="font-semibold">
                  {t("stripeSandboxTitle")}
                </div>

                <p className="text-sm text-muted-foreground mt-1">
                  {t("stripeSandboxDescription")}{" "}
                  <code className="bg-muted px-1.5 py-0.5 rounded text-xs">
                    4242 4242 4242 4242
                  </code>{" "}
                  {t("stripeSandboxInstructions")}
                </p>

                <Button
                  asChild
                  variant="outline"
                  size="sm"
                  className="mt-3"
                >
                  <a
                    href={onboardUrl}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <ExternalLink className="h-4 w-4 mr-1" />
                    {t("claimStripeAccount")}
                  </a>
                </Button>

              </div>

            </div>
          </Card>
        )}

      </div>
    </>
  );
}