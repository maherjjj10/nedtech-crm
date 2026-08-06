import { useEffect, useState } from "react";
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
import { Plus, Trash2, Send, Download, Copy, FileText } from "lucide-react";
import { formatDate } from "../lib/format";

const EMPTY_C = { title: "", client_name: "", template_id: "", body_markdown: "", expires_at: "" };
const EMPTY_T = { name: "", body_markdown: "" };
const STATUS_VARIANT = { draft: "outline", sent: "secondary", signed: "default", expired: "outline" };

export default function Contracts() {
  const [contracts, setContracts] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [openC, setOpenC] = useState(false);
  const [openT, setOpenT] = useState(false);
  const [formC, setFormC] = useState(EMPTY_C);
  const [formT, setFormT] = useState(EMPTY_T);

  const load = async () => {
    const [c, t] = await Promise.all([api.get("/contracts"), api.get("/contracts/templates")]);
    setContracts(c.data); setTemplates(t.data);
  };
  useEffect(() => { load(); }, []);

  const saveContract = async (e) => {
    e.preventDefault();
    try {
      const payload = { ...formC };
      if (payload.template_id === "") delete payload.template_id;
      if (!payload.expires_at) delete payload.expires_at;
      await api.post("/contracts", payload);
      toast.success("Contract created"); setOpenC(false); setFormC(EMPTY_C); load();
    } catch (err) { toast.error(err?.response?.data?.detail || "Failed"); }
  };

  const saveTemplate = async (e) => {
    e.preventDefault();
    try {
      await api.post("/contracts/templates", formT);
      toast.success("Template saved"); setOpenT(false); setFormT(EMPTY_T); load();
    } catch { toast.error("Failed"); }
  };

  const send = async (id) => {
    const { data } = await api.post(`/contracts/${id}/send`);
    navigator.clipboard.writeText(data.public_url);
    toast.success("Link copied — send it to your client");
    load();
  };

  const downloadPdf = async (id, title) => {
    const res = await api.get(`/contracts/${id}/pdf`, { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
    const a = document.createElement("a"); a.href = url; a.download = `${title || "contract"}.pdf`; a.click();
    window.URL.revokeObjectURL(url);
  };

  const remove = async (id) => { if (window.confirm("Delete contract?")) { await api.delete(`/contracts/${id}`); load(); } };
  const removeT = async (id) => { await api.delete(`/contracts/templates/${id}`); load(); };

  const applyTemplate = (tid) => {
    const t = templates.find(x => x.id === tid);
    if (t) setFormC(f => ({ ...f, template_id: tid, body_markdown: t.body_markdown }));
    else setFormC(f => ({ ...f, template_id: "" }));
  };

  return (
    <>
      <PageHeader
        title="Contracts"
        description="Draft, send, and e-sign contracts. Templates keep your team consistent."
        right={
          <div className="flex gap-2">
            <Dialog open={openT} onOpenChange={setOpenT}>
              <DialogTrigger asChild><Button variant="outline" size="sm" data-testid="new-template-btn"><FileText className="h-4 w-4 mr-1" />Templates</Button></DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader><DialogTitle>Contract templates</DialogTitle></DialogHeader>
                <div className="space-y-2 max-h-64 overflow-y-auto n-scroll pr-2">
                  {templates.length === 0 && <div className="text-sm text-muted-foreground py-4 text-center">No templates yet.</div>}
                  {templates.map(t => (
                    <div key={t.id} className="flex items-center justify-between border border-border/60 rounded-md px-3 py-2 text-sm">
                      <div className="font-medium">{t.name}</div>
                      <Button variant="ghost" size="icon" onClick={()=>removeT(t.id)}><Trash2 className="h-4 w-4" /></Button>
                    </div>
                  ))}
                </div>
                <form onSubmit={saveTemplate} className="space-y-3 border-t border-border pt-4">
                  <div className="space-y-1.5"><Label>Template name</Label><Input value={formT.name} onChange={(e)=>setFormT({...formT, name:e.target.value})} required data-testid="template-name-input" /></div>
                  <div className="space-y-1.5"><Label>Body</Label><Textarea rows={8} value={formT.body_markdown} onChange={(e)=>setFormT({...formT, body_markdown:e.target.value})} required data-testid="template-body-input" /></div>
                  <DialogFooter><Button type="submit" data-testid="template-save-btn">Save template</Button></DialogFooter>
                </form>
              </DialogContent>
            </Dialog>

            <Dialog open={openC} onOpenChange={setOpenC}>
              <DialogTrigger asChild><Button data-testid="new-contract-btn"><Plus className="h-4 w-4 mr-1" />New contract</Button></DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader><DialogTitle>New contract</DialogTitle></DialogHeader>
                <form onSubmit={saveContract} className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5 col-span-2"><Label>Title</Label><Input value={formC.title} onChange={(e)=>setFormC({...formC, title:e.target.value})} required data-testid="contract-title-input" /></div>
                    <div className="space-y-1.5"><Label>Client name</Label><Input value={formC.client_name} onChange={(e)=>setFormC({...formC, client_name:e.target.value})} data-testid="contract-client-input" /></div>
                    <div className="space-y-1.5"><Label>Expires (optional)</Label><Input type="date" value={formC.expires_at} onChange={(e)=>setFormC({...formC, expires_at:e.target.value})} /></div>
                    <div className="space-y-1.5 col-span-2"><Label>Start from template (optional)</Label>
                      <Select value={formC.template_id || "none"} onValueChange={(v)=>applyTemplate(v === "none" ? "" : v)}>
                        <SelectTrigger data-testid="contract-template-select"><SelectValue placeholder="Start blank" /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">Start blank</SelectItem>
                          {templates.map(t => <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1.5 col-span-2"><Label>Contract body</Label><Textarea rows={10} value={formC.body_markdown} onChange={(e)=>setFormC({...formC, body_markdown:e.target.value})} required data-testid="contract-body-input" /></div>
                  </div>
                  <DialogFooter><Button type="submit" data-testid="contract-save-btn">Create</Button></DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        }
      />

      <div className="p-8">
        <Tabs defaultValue="all">
          <TabsList data-testid="contracts-tabs">
            <TabsTrigger value="all">All ({contracts.length})</TabsTrigger>
            <TabsTrigger value="signed">Signed ({contracts.filter(c=>c.status==="signed").length})</TabsTrigger>
            <TabsTrigger value="pending">Pending ({contracts.filter(c=>c.status==="sent").length})</TabsTrigger>
          </TabsList>
          {["all","signed","pending"].map(tab => (
            <TabsContent key={tab} value={tab} className="mt-6">
              <Card className="border-border/70">
                {contracts.filter(c => tab==="all" || (tab==="signed" && c.status==="signed") || (tab==="pending" && c.status==="sent")).length === 0 && (
                  <div className="p-8 text-center text-sm text-muted-foreground">No contracts here yet.</div>
                )}
                {contracts.filter(c => tab==="all" || (tab==="signed" && c.status==="signed") || (tab==="pending" && c.status==="sent")).map((c) => (
                  <div key={c.id} className="flex items-center justify-between px-6 py-4 border-b border-border/60 last:border-0 text-sm" data-testid={`contract-row-${c.id}`}>
                    <div>
                      <div className="font-medium">{c.title}</div>
                      <div className="text-xs text-muted-foreground">{c.client_name || "—"} · created {formatDate(c.created_at)}{c.expires_at && ` · expires ${c.expires_at}`}</div>
                      {c.signature && <div className="text-xs mt-1">Signed by <b>{c.signature.signer_name}</b></div>}
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={STATUS_VARIANT[c.status] || "outline"}>{c.status}</Badge>
                      {c.status !== "signed" && c.status !== "expired" && (
                        <Button variant="outline" size="sm" onClick={()=>send(c.id)} data-testid={`send-contract-${c.id}`}><Send className="h-3 w-3 mr-1" />Send</Button>
                      )}
                      <Button variant="ghost" size="icon" onClick={()=>downloadPdf(c.id, c.title)} data-testid={`pdf-contract-${c.id}`}><Download className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" onClick={()=>remove(c.id)}><Trash2 className="h-4 w-4" /></Button>
                    </div>
                  </div>
                ))}
              </Card>
            </TabsContent>
          ))}
        </Tabs>
      </div>
    </>
  );
}
