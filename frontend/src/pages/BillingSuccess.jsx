import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { api } from "../lib/apiClient";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";

export default function BillingSuccess() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const [status, setStatus] = useState("polling");
  const sessionId = params.get("session_id");

  useEffect(() => {
    if (!sessionId) { setStatus("error"); return; }
    let tries = 0;
    const tick = async () => {
      tries++;
      try {
        const { data } = await api.get(`/billing/status/${sessionId}`);
        if (data.payment_status === "paid") setStatus("paid");
        else if (["failed", "expired"].includes(data.payment_status)) setStatus("failed");
        else if (tries < 15) setTimeout(tick, 2000);
        else setStatus("timeout");
      } catch { if (tries < 15) setTimeout(tick, 2000); else setStatus("error"); }
    };
    tick();
  }, [sessionId]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-6">
      <Card className="p-10 border-border/70 max-w-md w-full text-center">
        {status === "polling" && <><Loader2 className="h-10 w-10 mx-auto animate-spin text-muted-foreground" /><h2 className="text-xl font-bold mt-4">Finalising your subscription…</h2><p className="text-sm text-muted-foreground mt-2">Just a moment.</p></>}
        {status === "paid" && <><CheckCircle2 className="h-12 w-12 mx-auto text-foreground" /><h2 className="text-2xl font-bold mt-4">You&apos;re all set!</h2><p className="text-sm text-muted-foreground mt-2">Your plan is active. Welcome aboard.</p><Button className="mt-6" onClick={()=>nav("/")}>Go to dashboard</Button></>}
        {status === "failed" && <><XCircle className="h-12 w-12 mx-auto" /><h2 className="text-2xl font-bold mt-4">Payment didn&apos;t go through</h2><Button className="mt-6" variant="outline" onClick={()=>nav("/billing")}>Try again</Button></>}
        {(status === "timeout" || status === "error") && <><h2 className="text-2xl font-bold">We&apos;re still working on it</h2><p className="text-sm text-muted-foreground mt-2">Refresh in a minute — your plan will show up.</p><Button className="mt-6" onClick={()=>nav("/billing")}>Back to billing</Button></>}
      </Card>
    </div>
  );
}
