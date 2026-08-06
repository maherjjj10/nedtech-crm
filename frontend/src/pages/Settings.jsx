import { useEffect, useState } from "react";
import PageHeader from "../components/layout/PageHeader";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card } from "../components/ui/card";
import { Label } from "../components/ui/label";
import { Switch } from "../components/ui/switch";
import { Badge } from "../components/ui/badge";
import { api } from "../lib/apiClient";
import { toast } from "sonner";
import { useAuth } from "../lib/authContext";
import { Calendar as CalendarIcon, Check, Link as LinkIcon } from "lucide-react";

const MODULE_LABELS = {
  crm: "CRM & clients", sales: "Sales pipeline", tasks: "Tasks & projects",
  finance: "Finance", products: "Products & services", hr: "Employees",
  files: "File manager", calendar: "Calendar", reports: "Reports",
  ai: "AI assistant", inventory: "Inventory (future)", pos: "POS (future)",
  orders: "Restaurant orders (future)", marketing: "Marketing automation (future)",
  website: "Website builder (future)", portal: "Customer portal (future)",
  accounting: "Accounting (future)", payroll: "HR & payroll (future)",
};

export default function Settings() {
  const { tenant, refresh } = useAuth();
  const [form, setForm] = useState({ name: "", currency: "USD", vat_rate: 0, locale: "en", address: "", phone: "", website: "" });
  const [modules, setModules] = useState({});
  const [calendar, setCalendar] = useState(null);

  useEffect(() => {
    if (tenant) {
      setForm({
        name: tenant.name || "", currency: tenant.currency || "USD",
        vat_rate: tenant.vat_rate || 0, locale: tenant.locale || "en",
        address: tenant.address || "", phone: tenant.phone || "", website: tenant.website || "",
      });
      setModules(tenant.modules || {});
    }
    api.get("/calendar/status").then(r => setCalendar(r.data)).catch(()=>{});
  }, [tenant]);

  const connectCalendar = async () => {
    try {
      const { data } = await api.get("/calendar/connect");
      window.location.href = data.authorize_url;
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Add GOOGLE_CLIENT_ID/SECRET first");
    }
  };

  const save = async (e) => {
    e.preventDefault();
    try {
      await api.patch("/tenants/me", { ...form, vat_rate: Number(form.vat_rate) });
      toast.success("Settings saved"); refresh();
    } catch { toast.error("Failed"); }
  };

  const toggle = async (mod, enabled) => {
    setModules((m) => ({ ...m, [mod]: enabled }));
    try {
      await api.post("/tenants/me/modules", { module: mod, enabled });
      toast.success(`${MODULE_LABELS[mod]} ${enabled ? "enabled" : "disabled"}`);
      refresh();
    } catch { toast.error("Failed"); }
  };

  return (
    <>
      <PageHeader title="Settings" description="Company info, currency, and which modules are turned on." />
      <div className="p-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6 border-border/70">
          <h3 className="text-lg font-semibold mb-4">Company</h3>
          <form onSubmit={save} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5 col-span-2"><Label>Company name</Label><Input value={form.name} onChange={(e)=>setForm({...form, name:e.target.value})} data-testid="tenant-name-input" /></div>
              <div className="space-y-1.5"><Label>Currency</Label><Input value={form.currency} onChange={(e)=>setForm({...form, currency:e.target.value})} /></div>
              <div className="space-y-1.5"><Label>VAT / Tax %</Label><Input type="number" value={form.vat_rate} onChange={(e)=>setForm({...form, vat_rate:e.target.value})} /></div>
              <div className="space-y-1.5"><Label>Website</Label><Input value={form.website} onChange={(e)=>setForm({...form, website:e.target.value})} /></div>
              <div className="space-y-1.5"><Label>Phone</Label><Input value={form.phone} onChange={(e)=>setForm({...form, phone:e.target.value})} /></div>
              <div className="space-y-1.5 col-span-2"><Label>Address</Label><Input value={form.address} onChange={(e)=>setForm({...form, address:e.target.value})} /></div>
            </div>
            <Button type="submit" data-testid="save-settings-btn">Save changes</Button>
          </form>
        </Card>

        <Card className="p-6 border-border/70 lg:col-span-2">
          <div className="flex items-center gap-2 mb-1">
            <CalendarIcon className="h-4 w-4" />
            <h3 className="text-lg font-semibold">Google Calendar sync</h3>
            {calendar?.connected && <Badge className="ml-1"><Check className="h-3 w-3 mr-1" />Connected</Badge>}
          </div>
          <p className="text-xs text-muted-foreground mb-4">
            {calendar?.configured
              ? "Push task due dates as events into your Google Calendar. One-click connect below."
              : "Ready to activate — paste GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend/.env, then click connect."}
          </p>
          <Button onClick={connectCalendar} disabled={!calendar?.configured} data-testid="connect-calendar-btn">
            <LinkIcon className="h-4 w-4 mr-1" />
            {calendar?.connected ? "Reconnect Google Calendar" : "Connect Google Calendar"}
          </Button>
        </Card>

        <Card className="p-6 border-border/70">
          <h3 className="text-lg font-semibold mb-1">Modules</h3>
          <p className="text-xs text-muted-foreground mb-4">Enable only what you need. Future modules ship as we build them.</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {Object.entries(MODULE_LABELS).map(([code, label]) => (
              <div key={code} className="flex items-center justify-between px-3 py-2 rounded-md border border-border/60">
                <span className="text-sm">{label}</span>
                <Switch checked={!!modules[code]} onCheckedChange={(v)=>toggle(code, v)} data-testid={`module-toggle-${code}`} />
              </div>
            ))}
          </div>
        </Card>
      </div>
    </>
  );
}
