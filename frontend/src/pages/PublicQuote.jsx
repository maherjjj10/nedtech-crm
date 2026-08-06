import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";
import { CheckCircle2, XCircle } from "lucide-react";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api/v1`;

function money(v, cur = "USD") {
  try { return new Intl.NumberFormat("en-US", { style: "currency", currency: cur }).format(Number(v || 0)); }
  catch { return `${cur} ${Number(v||0).toFixed(2)}`; }
}

export default function PublicQuote() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [decision, setDecision] = useState(null);
  const [form, setForm] = useState({ signer_name: "", comment: "" });
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    axios.get(`${API}/public/quotes/${token}`)
      .then(r => setData(r.data))
      .catch(e => setError(e?.response?.data?.detail || "Quote not found"));
  }, [token]);

  const submit = async (dec) => {
    if (!form.signer_name.trim()) { toast.error("Please enter your name"); return; }
    setSaving(true);
    try {
      await axios.post(`${API}/public/quotes/${token}/decision`, { decision: dec, signer_name: form.signer_name.trim(), comment: form.comment || null });
      setDone(dec);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed");
    } finally { setSaving(false); }
  };

  if (error) return <div className="min-h-screen flex items-center justify-center p-6"><Card className="p-8 max-w-md text-center border-border/70"><h1 className="text-xl font-bold">Quote unavailable</h1><p className="text-sm text-muted-foreground mt-2">{error}</p></Card></div>;
  if (!data) return <div className="min-h-screen flex items-center justify-center text-sm text-muted-foreground">Loading…</div>;
  const q = data.quote; const t = data.tenant;

  if (done || ["accepted","rejected","converted"].includes(q.status)) {
    const final = done || q.status;
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-6">
        <Card className="p-10 max-w-md text-center border-border/70">
          {final === "accepted" || final === "converted" ? <CheckCircle2 className="h-12 w-12 mx-auto text-foreground" /> : <XCircle className="h-12 w-12 mx-auto text-muted-foreground" />}
          <h1 className="text-2xl font-bold mt-4">Quote {final}</h1>
          <p className="text-sm text-muted-foreground mt-2">
            {final === "accepted" || final === "converted" ? `Thank you — ${t.name} will be in touch shortly.` : "You've declined this quote."}
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground py-10 px-4">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="n-overline">Proposal from</div>
            <div className="text-2xl font-bold tracking-tight">{t.name}</div>
            {t.website && <a href={t.website} target="_blank" rel="noreferrer" className="text-xs underline text-muted-foreground">{t.website}</a>}
          </div>
          <Badge variant="outline">{q.number || "QUOTE"}</Badge>
        </div>

        <Card className="p-8 border-border/70">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Quotation</h1>
              <p className="text-sm text-muted-foreground mt-1">For {q.client_name || "you"}</p>
            </div>
            <div className="text-right">
              <div className="n-overline">Total</div>
              <div className="text-3xl font-black">{money(q.totals.total, q.currency)}</div>
            </div>
          </div>

          <div className="mt-6 border-t border-border pt-4">
            <table className="w-full text-sm">
              <thead><tr className="n-overline text-left border-b border-border/60"><th className="pb-2">Description</th><th className="pb-2 text-right">Qty</th><th className="pb-2 text-right">Unit</th><th className="pb-2 text-right">Total</th></tr></thead>
              <tbody>
                {(q.items || []).map((it, i) => (
                  <tr key={i} className="border-b border-border/40">
                    <td className="py-2">{it.description}</td>
                    <td className="py-2 text-right">{it.quantity}</td>
                    <td className="py-2 text-right">{money(it.unit_price, q.currency)}</td>
                    <td className="py-2 text-right">{money(it.quantity * it.unit_price * (1 + (it.tax_rate||0)/100), q.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="mt-4 text-right space-y-0.5 text-sm">
              <div>Subtotal: <span className="font-medium">{money(q.totals.subtotal, q.currency)}</span></div>
              <div>Tax: <span className="font-medium">{money(q.totals.tax, q.currency)}</span></div>
              <div className="text-lg font-bold mt-1">Total: {money(q.totals.total, q.currency)}</div>
            </div>
          </div>

          {q.notes && <div className="mt-4 text-sm text-muted-foreground border-t border-border pt-4"><b className="text-foreground">Notes:</b> {q.notes}</div>}
        </Card>

        <Card className="p-6 border-border/70">
          <div className="n-overline mb-4">Your response</div>
          <div className="space-y-3">
            <div className="space-y-1.5"><Label>Your full name</Label><Input value={form.signer_name} onChange={(e)=>setForm({...form, signer_name:e.target.value})} data-testid="quote-signer-input" /></div>
            <div className="space-y-1.5"><Label>Comment (optional)</Label><Textarea rows={3} value={form.comment} onChange={(e)=>setForm({...form, comment:e.target.value})} data-testid="quote-comment-input" /></div>
            <div className="flex gap-3 pt-2">
              <Button onClick={()=>submit("accepted")} disabled={saving} className="flex-1" data-testid="quote-accept-btn"><CheckCircle2 className="h-4 w-4 mr-1" />Accept quote</Button>
              <Button variant="outline" onClick={()=>submit("rejected")} disabled={saving} className="flex-1" data-testid="quote-reject-btn"><XCircle className="h-4 w-4 mr-1" />Reject</Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
