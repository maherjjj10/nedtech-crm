import { useEffect, useMemo, useState, useCallback } from "react";
import PageHeader from "../components/layout/PageHeader";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Badge } from "../components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "../components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { api } from "../lib/apiClient";
import { toast } from "sonner";
import {
  Plus, Trash2, Send, Download, Copy, FileText, Search,
  History, X, Eye, ShieldCheck, FileSignature, Layers, MessageSquare,
} from "lucide-react";
import { formatDate, formatCurrency } from "../lib/format";
import { RichEditor, CONTRACT_VARIABLES } from "../components/ui/rich-editor";

const EMPTY_C = {
  title: "", client_id: "", template_id: "", body_html: "",
  contract_amount: "", currency: "USD",
  start_date: "", end_date: "", expires_at: "", invoice_number: "",
};
const EMPTY_T = { name: "", category: "", body_html: "" };
const STATUS_VARIANT = {
  draft: "outline", pending_review: "outline", sent: "secondary",
  viewed: "secondary", signed: "default", completed: "default",
  expired: "outline", cancelled: "outline",
};
const STATUS_LABEL = {
  draft: "Draft", pending_review: "Pending Review", sent: "Sent",
  viewed: "Viewed", signed: "Signed", completed: "Completed",
  expired: "Expired", cancelled: "Cancelled",
};

function VariableChips({ onInsert }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {CONTRACT_VARIABLES.map((v) => (
        <button type="button" key={v.key}
          onClick={() => onInsert(`{{${v.key}}}`)}
          className="text-xs px-2 py-1 rounded-md border border-border/60 hover:bg-accent transition-colors"
          data-testid={`var-${v.key}`}
          title={`Insert {{${v.key}}}`}>
          {v.label}
        </button>
      ))}
    </div>
  );
}

function ContractForm({ initial, clients, templates, onSave, onCancel }) {
  const [form, setForm] = useState(initial);

  const clientOptions = useMemo(() => clients.map(c => ({
    id: c.id, label: c.name + (c.company ? ` — ${c.company}` : ""),
  })), [clients]);

  const applyTemplate = (tid) => {
    const t = templates.find(x => x.id === tid);
    setForm(f => ({ ...f, template_id: tid === "none" ? "" : tid, body_html: t ? t.body_html : f.body_html, title: f.title || (t ? t.name : f.title) }));
  };

  const insertVariable = useCallback((token) => {
    setForm(f => ({ ...f, body_html: (f.body_html || "") + `<p>${token}</p>` }));
  }, []);

  const submit = (e) => {
    e.preventDefault();
    const payload = { ...form };
    if (!payload.client_id) delete payload.client_id;
    if (!payload.template_id) delete payload.template_id;
    if (!payload.contract_amount) delete payload.contract_amount;
    else payload.contract_amount = Number(payload.contract_amount);
    ["start_date", "end_date", "expires_at", "invoice_number"].forEach(k => { if (!payload[k]) delete payload[k]; });
    onSave(payload);
  };

  const grouped = useMemo(() => {
    const g = {};
    templates.forEach(t => {
      const cat = t.category || "Other";
      g[cat] = g[cat] || [];
      g[cat].push(t);
    });
    return g;
  }, [templates]);

  return (
    <form onSubmit={submit} className="space-y-4" data-testid="contract-form">
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5 col-span-2">
          <Label>Title</Label>
          <Input value={form.title} onChange={(e)=>setForm({...form, title:e.target.value})} required data-testid="contract-title-input" />
        </div>

        <div className="space-y-1.5">
          <Label>Client (auto-fills company/email/VAT)</Label>
          <Select value={form.client_id || "none"} onValueChange={(v)=>setForm({...form, client_id: v==="none" ? "" : v})}>
            <SelectTrigger data-testid="contract-client-select"><SelectValue placeholder="Pick a client…" /></SelectTrigger>
            <SelectContent className="max-h-72">
              <SelectItem value="none">— No client —</SelectItem>
              {clientOptions.map(o => <SelectItem key={o.id} value={o.id} data-testid={`client-option-${o.id}`}>{o.label}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label>Template</Label>
          <Select value={form.template_id || "none"} onValueChange={applyTemplate}>
            <SelectTrigger data-testid="contract-template-select"><SelectValue placeholder="Start blank" /></SelectTrigger>
            <SelectContent className="max-h-80">
              <SelectItem value="none">Start blank</SelectItem>
              {Object.entries(grouped).map(([cat, tpls]) => (
                <div key={cat}>
                  <div className="px-2 py-1 text-[10px] uppercase tracking-widest text-muted-foreground">{cat}</div>
                  {tpls.map(t => <SelectItem key={t.id} value={t.id} data-testid={`template-option-${t.id}`}>{t.name}</SelectItem>)}
                </div>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label>Contract amount</Label>
          <Input type="number" step="0.01" value={form.contract_amount} onChange={(e)=>setForm({...form, contract_amount:e.target.value})} data-testid="contract-amount-input" />
        </div>
        <div className="space-y-1.5">
          <Label>Currency</Label>
          <Input value={form.currency} onChange={(e)=>setForm({...form, currency:e.target.value})} />
        </div>
        <div className="space-y-1.5">
          <Label>Start date</Label>
          <Input type="date" value={form.start_date} onChange={(e)=>setForm({...form, start_date:e.target.value})} />
        </div>
        <div className="space-y-1.5">
          <Label>End date</Label>
          <Input type="date" value={form.end_date} onChange={(e)=>setForm({...form, end_date:e.target.value})} />
        </div>
        <div className="space-y-1.5">
          <Label>Expires (signing deadline)</Label>
          <Input type="date" value={form.expires_at} onChange={(e)=>setForm({...form, expires_at:e.target.value})} />
        </div>
        <div className="space-y-1.5">
          <Label>Linked invoice #</Label>
          <Input value={form.invoice_number} onChange={(e)=>setForm({...form, invoice_number:e.target.value})} />
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label>Contract body</Label>
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground">Rich editor</div>
        </div>
        <RichEditor value={form.body_html} onChange={(html)=>setForm({...form, body_html: html})} placeholder="Draft your contract or start from a template above…" />
      </div>

      <div className="space-y-1.5">
        <Label className="text-xs uppercase tracking-widest text-muted-foreground">Insert a variable</Label>
        <VariableChips onInsert={insertVariable} />
      </div>

      <DialogFooter>
        {onCancel && <Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button>}
        <Button type="submit" data-testid="contract-save-btn">Save contract</Button>
      </DialogFooter>
    </form>
  );
}

function TemplateManager({ templates, onCreate, onDelete }) {
  const [form, setForm] = useState(EMPTY_T);
  const sys = templates.filter(t => t.is_system);
  const custom = templates.filter(t => !t.is_system);

  return (
    <div className="space-y-4">
      <div>
        <div className="n-overline mb-2">System templates</div>
        <div className="grid grid-cols-2 gap-2">
          {sys.map(t => (
            <div key={t.id} className="border border-border/60 rounded-md px-3 py-2 text-sm flex items-center justify-between" data-testid={`sys-tpl-${t.id}`}>
              <div>
                <div className="font-medium">{t.name}</div>
                <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{t.category}</div>
              </div>
              <Badge variant="outline" className="text-[10px]">System</Badge>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="n-overline mb-2">Your templates</div>
        {custom.length === 0 && <div className="text-sm text-muted-foreground py-2">No custom templates yet.</div>}
        <div className="space-y-1.5">
          {custom.map(t => (
            <div key={t.id} className="border border-border/60 rounded-md px-3 py-2 text-sm flex items-center justify-between">
              <div><span className="font-medium">{t.name}</span> <span className="text-xs text-muted-foreground ml-2">{t.category || ""}</span></div>
              <Button variant="ghost" size="icon" onClick={()=>onDelete(t.id)}><Trash2 className="h-4 w-4" /></Button>
            </div>
          ))}
        </div>
      </div>

      <form onSubmit={(e)=>{ e.preventDefault(); onCreate(form); setForm(EMPTY_T); }} className="space-y-3 border-t border-border pt-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5 col-span-2"><Label>Template name</Label><Input value={form.name} onChange={(e)=>setForm({...form, name:e.target.value})} required data-testid="template-name-input" /></div>
          <div className="space-y-1.5 col-span-2"><Label>Category</Label><Input value={form.category} onChange={(e)=>setForm({...form, category:e.target.value})} placeholder="e.g. Legal, Design" /></div>
        </div>
        <div className="space-y-2">
          <Label>Body (rich text)</Label>
          <RichEditor value={form.body_html} onChange={(html)=>setForm({...form, body_html: html})} placeholder="Design your template. Use {{variable}} tokens…" />
        </div>
        <DialogFooter><Button type="submit" data-testid="template-save-btn">Save template</Button></DialogFooter>
      </form>
    </div>
  );
}

function DashboardStats({ stats, tenantCurrency }) {
  const items = [
    { label: "Active", value: stats.active_count, icon: FileText },
    { label: "Signed", value: stats.signed_count, icon: ShieldCheck },
    { label: "Pending Sign", value: stats.pending_signature_count, icon: FileSignature },
    { label: "Expiring Soon", value: stats.expiring_count, icon: History },
    { label: "Contract Value", value: formatCurrency(stats.total_value, tenantCurrency), icon: Layers },
    { label: "Signed Revenue", value: formatCurrency(stats.revenue, tenantCurrency), icon: ShieldCheck },
  ];
  return (
    <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
      {items.map(({ label, value, icon: Icon }) => (
        <Card key={label} className="p-4 border-border/70">
          <div className="flex items-center justify-between text-muted-foreground text-xs uppercase tracking-widest"><span>{label}</span><Icon className="h-3.5 w-3.5" /></div>
          <div className="text-xl font-bold mt-1">{value ?? 0}</div>
        </Card>
      ))}
    </div>
  );
}

export default function Contracts() {
  const [contracts, setContracts] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [clients, setClients] = useState([]);
  const [stats, setStats] = useState({});
  const [openC, setOpenC] = useState(false);
  const [openT, setOpenT] = useState(false);
  const [openHistory, setOpenHistory] = useState(null); // contract id
  const [versions, setVersions] = useState([]);
  const [q, setQ] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const load = async () => {
    const [c, t, cl, s] = await Promise.all([
      api.get("/contracts"),
      api.get("/contracts/templates"),
      api.get("/clients"),
      api.get("/contracts/dashboard"),
    ]);
    setContracts(c.data); setTemplates(t.data); setClients(cl.data); setStats(s.data);
  };
  useEffect(() => { load(); }, []);

  const saveContract = async (payload) => {
    try {
      await api.post("/contracts", payload);
      toast.success("Contract created");
      setOpenC(false);
      load();
    } catch (err) { toast.error(err?.response?.data?.detail || "Failed"); }
  };

  const saveTemplate = async (payload) => {
    try {
      if (!payload.name || !payload.body_html) { toast.error("Name and body are required"); return; }
      await api.post("/contracts/templates", payload);
      toast.success("Template saved");
      load();
    } catch { toast.error("Failed"); }
  };

  const send = async (id) => {
    try {
      const { data } = await api.post(`/contracts/${id}/send`);
      const url = data.public_url && data.public_url.startsWith("http")
        ? data.public_url
        : `${window.location.origin}/public/contract/${data.share_token}`;
      await navigator.clipboard.writeText(url);
      toast.success("Link copied — send it to your client");
      load();
    } catch (err) { toast.error(err?.response?.data?.detail || "Failed"); }
  };

  const remind = async (id) => {
    try {
      await api.post(`/contracts/${id}/reminder`);
      toast.success("Reminder logged (email delivery in Phase 2)");
    } catch (err) { toast.error(err?.response?.data?.detail || "Failed"); }
  };

  const cancel = async (id) => {
    if (!window.confirm("Cancel this contract?")) return;
    try { await api.post(`/contracts/${id}/cancel`); load(); }
    catch (err) { toast.error(err?.response?.data?.detail || "Failed"); }
  };

  const downloadPdf = async (id, title) => {
    const res = await api.get(`/contracts/${id}/pdf`, { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
    const a = document.createElement("a"); a.href = url; a.download = `${title || "contract"}.pdf`; a.click();
    window.URL.revokeObjectURL(url);
  };

  const remove = async (id) => { if (window.confirm("Delete contract?")) { await api.delete(`/contracts/${id}`); load(); } };
  const removeT = async (id) => { await api.delete(`/contracts/templates/${id}`); load(); };

  const openVersionHistory = async (id) => {
    const { data } = await api.get(`/contracts/${id}/versions`);
    setVersions(data);
    setOpenHistory(id);
  };

  const restoreVersion = async (vid) => {
    if (!window.confirm("Restore this version? Current content will be replaced.")) return;
    try {
      await api.post(`/contracts/${openHistory}/versions/${vid}/restore`);
      toast.success("Version restored");
      setOpenHistory(null);
      load();
    } catch (err) { toast.error(err?.response?.data?.detail || "Failed"); }
  };

  const filtered = useMemo(() => {
    let list = contracts;
    if (statusFilter !== "all") list = list.filter(c => c.status === statusFilter);
    if (q) {
      const needle = q.toLowerCase();
      list = list.filter(c =>
        c.title.toLowerCase().includes(needle)
        || (c.client_snapshot?.client_name || "").toLowerCase().includes(needle)
        || (c.client_snapshot?.company || "").toLowerCase().includes(needle)
        || (c.verification_id || "").toLowerCase().includes(needle)
      );
    }
    return list;
  }, [contracts, q, statusFilter]);

  return (
    <>
      <PageHeader
        title="Contracts"
        description="Draft, send, and e-sign contracts. Templates and dynamic variables keep everything consistent."
        right={
          <div className="flex gap-2">
            <Dialog open={openT} onOpenChange={setOpenT}>
              <DialogTrigger asChild><Button variant="outline" size="sm" data-testid="new-template-btn"><FileText className="h-4 w-4 mr-1" />Templates</Button></DialogTrigger>
              <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
                <DialogHeader><DialogTitle>Contract templates</DialogTitle></DialogHeader>
                <TemplateManager templates={templates} onCreate={saveTemplate} onDelete={removeT} />
              </DialogContent>
            </Dialog>

            <Dialog open={openC} onOpenChange={setOpenC}>
              <DialogTrigger asChild><Button data-testid="new-contract-btn"><Plus className="h-4 w-4 mr-1" />New contract</Button></DialogTrigger>
              <DialogContent className="max-w-4xl max-h-[92vh] overflow-y-auto">
                <DialogHeader><DialogTitle>New contract</DialogTitle></DialogHeader>
                <ContractForm
                  initial={EMPTY_C}
                  clients={clients}
                  templates={templates}
                  onSave={saveContract}
                  onCancel={()=>setOpenC(false)}
                />
              </DialogContent>
            </Dialog>
          </div>
        }
      />

      <div className="p-8 space-y-6">
        <DashboardStats stats={stats} tenantCurrency={contracts[0]?.currency} />

        <div className="flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <Search className="h-4 w-4 absolute left-3 top-3 text-muted-foreground" />
            <Input placeholder="Search title, client, verification ID…" value={q} onChange={(e)=>setQ(e.target.value)} className="pl-9" data-testid="contracts-search" />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-48" data-testid="contracts-status-filter"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              {Object.entries(STATUS_LABEL).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>

        <Tabs defaultValue="all">
          <TabsList data-testid="contracts-tabs">
            <TabsTrigger value="all" data-testid="tab-all">All ({filtered.length})</TabsTrigger>
            <TabsTrigger value="active" data-testid="tab-active">Active</TabsTrigger>
            <TabsTrigger value="signed" data-testid="tab-signed">Signed</TabsTrigger>
            <TabsTrigger value="pending" data-testid="tab-pending">Pending</TabsTrigger>
          </TabsList>
          {[["all", () => true],
            ["active", c => ["draft","sent","viewed","pending_review"].includes(c.status)],
            ["signed", c => ["signed","completed"].includes(c.status)],
            ["pending", c => ["sent","viewed","pending_review"].includes(c.status)]].map(([tab, fn]) => (
            <TabsContent key={tab} value={tab} className="mt-6">
              <Card className="border-border/70">
                {filtered.filter(fn).length === 0 && (
                  <div className="p-8 text-center text-sm text-muted-foreground">No contracts here yet.</div>
                )}
                {filtered.filter(fn).map((c) => (
                  <div key={c.id} className="flex items-center justify-between px-6 py-4 border-b border-border/60 last:border-0 text-sm flex-wrap gap-3" data-testid={`contract-row-${c.id}`}>
                    <div className="min-w-0 flex-1">
                      <div className="font-medium flex items-center gap-2">
                        <span>{c.title}</span>
                        {c.verification_id && <span className="text-[10px] px-1.5 py-0.5 border border-border/60 rounded text-muted-foreground">{c.verification_id}</span>}
                      </div>
                      <div className="text-xs text-muted-foreground truncate">
                        {c.client_snapshot?.company || c.client_snapshot?.client_name || "—"} · created {formatDate(c.created_at)}
                        {c.contract_amount ? ` · ${formatCurrency(c.contract_amount, c.currency)}` : ""}
                        {c.expires_at && ` · expires ${c.expires_at}`}
                      </div>
                      {c.signature && <div className="text-xs mt-1">Signed by <b>{c.signature.signer_name}</b> on {formatDate(c.signed_at || c.signature.signed_at)}</div>}
                    </div>
                    <div className="flex items-center gap-1">
                      <Badge variant={STATUS_VARIANT[c.status] || "outline"}>{STATUS_LABEL[c.status] || c.status}</Badge>
                      {["draft","sent","viewed","pending_review"].includes(c.status) && (
                        <Button variant="outline" size="sm" onClick={()=>send(c.id)} data-testid={`send-contract-${c.id}`}><Send className="h-3 w-3 mr-1" />Send</Button>
                      )}
                      {["sent","viewed"].includes(c.status) && (
                        <Button variant="ghost" size="sm" onClick={()=>remind(c.id)} title="Send reminder" data-testid={`remind-${c.id}`}><FileSignature className="h-3.5 w-3.5" /></Button>
                      )}
                      {c.share_token && (
                        <Button variant="ghost" size="icon" title="Copy public link" onClick={async()=>{ const url=`${window.location.origin}/public/contract/${c.share_token}`; await navigator.clipboard.writeText(url); toast.success("Link copied"); }} data-testid={`copy-link-${c.id}`}><Copy className="h-4 w-4" /></Button>
                      )}
                      <Button variant="ghost" size="icon" onClick={()=>downloadPdf(c.id, c.title)} data-testid={`pdf-contract-${c.id}`}><Download className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" title="Version history" onClick={()=>openVersionHistory(c.id)} data-testid={`history-${c.id}`}><History className="h-4 w-4" /></Button>
                      {!["signed","completed"].includes(c.status) && (
                        <Button variant="ghost" size="icon" title="Cancel" onClick={()=>cancel(c.id)} data-testid={`cancel-${c.id}`}><X className="h-4 w-4" /></Button>
                      )}
                      <Button variant="ghost" size="icon" onClick={()=>remove(c.id)} data-testid={`delete-${c.id}`}><Trash2 className="h-4 w-4" /></Button>
                    </div>
                  </div>
                ))}
              </Card>
            </TabsContent>
          ))}
        </Tabs>
      </div>

      <Dialog open={!!openHistory} onOpenChange={(v)=>{ if(!v) setOpenHistory(null); }}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader><DialogTitle>Version history</DialogTitle></DialogHeader>
          {versions.length === 0 && <div className="text-sm text-muted-foreground">No versions yet.</div>}
          <div className="space-y-2">
            {versions.map((v, idx) => (
              <div key={v.id} className="border border-border/60 rounded-md p-3 text-sm" data-testid={`version-${v.id}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">v{versions.length - idx} · {v.note || "edit"}</div>
                    <div className="text-xs text-muted-foreground">{formatDate(v.created_at)} · {v.actor}</div>
                  </div>
                  <Button size="sm" variant="outline" onClick={()=>restoreVersion(v.id)} data-testid={`restore-${v.id}`}>Restore</Button>
                </div>
                <div className="mt-2 text-xs text-muted-foreground truncate">{v.snapshot?.title} — {v.snapshot?.status}</div>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
