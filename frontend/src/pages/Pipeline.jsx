import { useEffect, useState } from "react";
import PageHeader from "../components/layout/PageHeader";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card } from "../components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "../components/ui/dialog";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { api } from "../lib/apiClient";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { formatCurrency } from "../lib/format";
import { useAuth } from "../lib/authContext";

const STAGE_LABEL = { lead: "Lead", qualified: "Qualified", proposal: "Proposal", negotiation: "Negotiation", won: "Won", lost: "Lost" };
const EMPTY = { title: "", client_name: "", value: 0, currency: "USD", stage: "lead", probability: 20, notes: "" };

export default function Pipeline() {
  const { tenant } = useAuth();
  const [stages, setStages] = useState([]);
  const [deals, setDeals] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);

  const load = async () => {
    const [s, d] = await Promise.all([api.get("/pipeline/stages"), api.get("/pipeline/deals")]);
    setStages(s.data); setDeals(d.data);
  };
  useEffect(() => { load(); }, []);

  const create = async (e) => {
    e.preventDefault();
    try {
      await api.post("/pipeline/deals", { ...form, value: Number(form.value), probability: Number(form.probability) });
      toast.success("Deal added"); setOpen(false); setForm(EMPTY); load();
    } catch (err) { toast.error(err?.response?.data?.detail || "Failed"); }
  };

  const move = async (deal, stage) => {
    await api.patch(`/pipeline/deals/${deal.id}`, { stage });
    load();
  };

  const remove = async (id) => {
    await api.delete(`/pipeline/deals/${id}`);
    load();
  };

  const byStage = (s) => deals.filter((d) => d.stage === s);
  const stageTotal = (s) => byStage(s).reduce((sum, d) => sum + (d.value || 0), 0);

  return (
    <>
      <PageHeader
        title="Sales pipeline"
        description="Drag ideas from lead to won. Drop what's not working."
        right={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button data-testid="new-deal-btn"><Plus className="h-4 w-4 mr-1" />New deal</Button>
            </DialogTrigger>
            <DialogContent data-testid="deal-dialog">
              <DialogHeader><DialogTitle>New deal</DialogTitle></DialogHeader>
              <form onSubmit={create} className="space-y-3">
                <div className="space-y-1.5"><Label>Title</Label><Input value={form.title} onChange={(e)=>setForm({...form, title:e.target.value})} required data-testid="deal-title-input" /></div>
                <div className="space-y-1.5"><Label>Client name</Label><Input value={form.client_name} onChange={(e)=>setForm({...form, client_name:e.target.value})} /></div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5"><Label>Value</Label><Input type="number" value={form.value} onChange={(e)=>setForm({...form, value:e.target.value})} data-testid="deal-value-input" /></div>
                  <div className="space-y-1.5"><Label>Stage</Label>
                    <Select value={form.stage} onValueChange={(v)=>setForm({...form, stage:v})}>
                      <SelectTrigger data-testid="deal-stage-select"><SelectValue /></SelectTrigger>
                      <SelectContent>{stages.map(s => <SelectItem key={s} value={s}>{STAGE_LABEL[s]}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                </div>
                <DialogFooter><Button type="submit" data-testid="deal-save-btn">Create deal</Button></DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        }
      />

      <div className="p-8">
        <div className="grid grid-flow-col auto-cols-[280px] gap-4 overflow-x-auto n-scroll pb-4" data-testid="pipeline-board">
          {stages.map((s) => (
            <div key={s} className="flex flex-col rounded-lg border border-border bg-card min-h-[70vh]" data-testid={`stage-column-${s}`}>
              <div className="px-4 py-3 border-b border-border flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold">{STAGE_LABEL[s]}</div>
                  <div className="text-xs text-muted-foreground">{byStage(s).length} · {formatCurrency(stageTotal(s), tenant?.currency)}</div>
                </div>
              </div>
              <div className="flex-1 p-3 space-y-2 n-scroll overflow-y-auto">
                {byStage(s).map((d) => (
                  <Card key={d.id} className="p-3 n-card-hover border-border/60" data-testid={`deal-card-${d.id}`}>
                    <div className="flex items-start justify-between gap-2">
                      <div className="font-medium text-sm">{d.title}</div>
                      <Button variant="ghost" size="icon" className="h-6 w-6" onClick={()=>remove(d.id)}><Trash2 className="h-3 w-3" /></Button>
                    </div>
                    <div className="text-xs text-muted-foreground">{d.client_name || "—"}</div>
                    <div className="mt-2 flex items-center justify-between text-xs">
                      <span className="font-semibold text-foreground">{formatCurrency(d.value, d.currency)}</span>
                      <Select value={d.stage} onValueChange={(v)=>move(d, v)}>
                        <SelectTrigger className="h-7 w-[110px] text-xs"><SelectValue /></SelectTrigger>
                        <SelectContent>{stages.map(x => <SelectItem key={x} value={x}>{STAGE_LABEL[x]}</SelectItem>)}</SelectContent>
                      </Select>
                    </div>
                  </Card>
                ))}
                {byStage(s).length === 0 && <div className="text-xs text-muted-foreground text-center py-6">No deals</div>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
