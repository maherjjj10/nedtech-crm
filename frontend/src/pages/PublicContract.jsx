import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Checkbox } from "../components/ui/checkbox";
import { Badge } from "../components/ui/badge";
import { CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api/v1`;

export default function PublicContract() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ signer_name: "", signer_email: "", consent: false });
  const [saving, setSaving] = useState(false);
  const [signed, setSigned] = useState(false);

  useEffect(() => {
    axios.get(`${API}/public/contracts/${token}`)
      .then(r => { setData(r.data); if (r.data.contract.status === "signed") setSigned(true); })
      .catch(e => setError(e?.response?.data?.detail || "Contract not found"));
  }, [token]);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.consent) { toast.error("Please confirm consent"); return; }
    setSaving(true);
    try {
      await axios.post(`${API}/public/contracts/${token}/sign`, form);
      setSigned(true);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed");
    } finally { setSaving(false); }
  };

  if (error) return <div className="min-h-screen flex items-center justify-center p-6"><Card className="p-8 max-w-md text-center border-border/70"><h1 className="text-xl font-bold">Contract unavailable</h1><p className="text-sm text-muted-foreground mt-2">{error}</p></Card></div>;
  if (!data) return <div className="min-h-screen flex items-center justify-center text-sm text-muted-foreground">Loading…</div>;
  const c = data.contract; const t = data.tenant;

  return (
    <div className="min-h-screen bg-background text-foreground py-10 px-4">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="n-overline">Contract from</div>
            <div className="text-2xl font-bold tracking-tight">{t.name}</div>
          </div>
          <Badge variant={c.status === "signed" ? "default" : "outline"}>{c.status}</Badge>
        </div>

        <Card className="p-8 border-border/70">
          <h1 className="text-3xl font-bold tracking-tight">{c.title}</h1>
          <p className="text-sm text-muted-foreground mt-1">For {c.client_name}</p>
          <div className="mt-6 whitespace-pre-wrap text-sm leading-relaxed">{c.body_markdown}</div>
          {c.signature && (
            <div className="mt-8 border-t border-border pt-4">
              <div className="n-overline mb-1">Signed by</div>
              <div className="font-serif italic text-2xl">{c.signature.signer_name}</div>
              <div className="text-xs text-muted-foreground">{new Date(c.signature.signed_at).toLocaleString()} · IP {c.signature.ip}</div>
            </div>
          )}
        </Card>

        {!signed && c.status !== "expired" && (
          <Card className="p-6 border-border/70">
            <div className="n-overline mb-4">Sign this contract</div>
            <form onSubmit={submit} className="space-y-3">
              <div className="space-y-1.5"><Label>Full legal name</Label><Input value={form.signer_name} onChange={(e)=>setForm({...form, signer_name:e.target.value})} required data-testid="contract-signer-input" /></div>
              <div className="space-y-1.5"><Label>Email (optional)</Label><Input type="email" value={form.signer_email} onChange={(e)=>setForm({...form, signer_email:e.target.value})} /></div>
              <label className="flex items-center gap-2 text-sm">
                <Checkbox checked={form.consent} onCheckedChange={(v)=>setForm({...form, consent: !!v})} data-testid="contract-consent" />
                I agree that typing my name and clicking Sign constitutes my legal signature.
              </label>
              <Button type="submit" disabled={saving} className="w-full" data-testid="contract-sign-btn">
                <CheckCircle2 className="h-4 w-4 mr-1" />{saving ? "Signing…" : "Sign contract"}
              </Button>
            </form>
          </Card>
        )}
        {signed && (
          <Card className="p-6 border-border/70 bg-accent">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-6 w-6" />
              <div>
                <div className="font-semibold">Signed — thank you.</div>
                <div className="text-xs text-muted-foreground">A copy has been recorded and shared with {t.name}.</div>
              </div>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
