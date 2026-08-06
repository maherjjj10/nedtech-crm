import { useEffect, useState } from "react";
import PageHeader from "../components/layout/PageHeader";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { api } from "../lib/apiClient";
import { toast } from "sonner";
import { Check, ExternalLink, Sparkles } from "lucide-react";
import { useAuth } from "../lib/authContext";

export default function Billing() {
  const { tenant } = useAuth();
  const [plans, setPlans] = useState([]);
  const [status, setStatus] = useState(null);
  const [onboardUrl, setOnboardUrl] = useState("");
  const [loading, setLoading] = useState(null);

  const load = async () => {
    const [p, s] = await Promise.all([api.get("/billing/plans"), api.get("/billing/status")]);
    setPlans(p.data.plans || []);
    setOnboardUrl(p.data.onboarding_url || "");
    setStatus(s.data);
  };
  useEffect(() => { load(); }, []);

  const checkout = async (lookup_key) => {
    setLoading(lookup_key);
    try {
      const { data } = await api.post("/billing/checkout", {
        lookup_key, origin_url: window.location.origin,
      });
      window.location.href = data.checkout_url;
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Checkout failed");
      setLoading(null);
    }
  };

  const currentPlan = status?.plan;

  return (
    <>
      <PageHeader
        title="Billing & plans"
        description="Turn features on with a plan that matches your stage."
      />

      <div className="p-8 space-y-6">
        {status?.status === "active" && (
          <Card className="p-4 border-border/70 bg-accent">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-full bg-foreground text-background flex items-center justify-center"><Check className="h-4 w-4" /></div>
              <div>
                <div className="text-sm font-medium">You&apos;re on the <span className="capitalize">{(currentPlan || "").replace('_monthly','')}</span> plan</div>
                <div className="text-xs text-muted-foreground">Status: {status.status}</div>
              </div>
            </div>
          </Card>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {plans.map((p) => {
            const isCurrent = currentPlan === p.lookup_key;
            return (
              <Card key={p.lookup_key} className="p-6 border-border/70 flex flex-col n-card-hover" data-testid={`plan-${p.lookup_key}`}>
                <div className="flex items-center justify-between">
                  <h3 className="text-xl font-bold">{p.name}</h3>
                  {p.name === "Pro" && <Badge>Popular</Badge>}
                </div>
                <div className="mt-2 text-3xl font-black">
                  ${p.amount ?? p.price_display?.replace(/[^0-9]/g, "") ?? 0}
                  <span className="text-sm font-medium text-muted-foreground">/mo</span>
                </div>
                <ul className="mt-4 space-y-2 text-sm flex-1">
                  {p.features.map((f, i) => (
                    <li key={i} className="flex items-start gap-2"><Check className="h-4 w-4 mt-0.5 text-foreground" />{f}</li>
                  ))}
                </ul>
                <Button
                  className="mt-6"
                  variant={isCurrent ? "outline" : "default"}
                  disabled={isCurrent || loading === p.lookup_key}
                  onClick={() => checkout(p.lookup_key)}
                  data-testid={`checkout-${p.lookup_key}`}
                >
                  {isCurrent ? "Current plan" : loading === p.lookup_key ? "Redirecting…" : "Choose plan"}
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
                <div className="font-semibold">You&apos;re running on a test Stripe sandbox</div>
                <p className="text-sm text-muted-foreground mt-1">
                  Use test card <code className="bg-muted px-1.5 py-0.5 rounded text-xs">4242 4242 4242 4242</code> with any future date and any CVC.
                  Click below to claim your real Stripe account and go live — the platform auto-swaps the keys.
                </p>
                <Button asChild variant="outline" size="sm" className="mt-3">
                  <a href={onboardUrl} target="_blank" rel="noreferrer">
                    <ExternalLink className="h-4 w-4 mr-1" />Claim your Stripe account
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
