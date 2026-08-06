import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import PageHeader from "../components/layout/PageHeader";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "../components/ui/dialog";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { api } from "../lib/apiClient";
import { Plus, Search, Trash2, Pencil } from "lucide-react";
import { toast } from "sonner";
import { formatDate } from "../lib/format";

const EMPTY = { name: "", email: "", phone: "", company: "", website: "", tags: [], status: "active", notes: "" };

export default function Clients() {
  const [clients, setClients] = useState([]);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);

  const load = async () => {
    const { data } = await api.get("/clients", { params: q ? { q } : {} });
    setClients(data);
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const openNew = () => { setEditing(null); setForm(EMPTY); setOpen(true); };
  const openEdit = (c) => { setEditing(c); setForm({ ...EMPTY, ...c, tags: c.tags || [] }); setOpen(true); };

  const save = async (e) => {
    e.preventDefault();
    try {
      const payload = { ...form, tags: Array.isArray(form.tags) ? form.tags : String(form.tags || "").split(",").map(s=>s.trim()).filter(Boolean) };
      if (editing) await api.patch(`/clients/${editing.id}`, payload);
      else await api.post("/clients", payload);
      toast.success(editing ? "Client updated" : "Client created");
      setOpen(false); load();
    } catch (err) { toast.error(err?.response?.data?.detail || "Save failed"); }
  };

  const remove = async (id) => {
    if (!window.confirm("Delete this client?")) return;
    await api.delete(`/clients/${id}`);
    toast.success("Deleted"); load();
  };

  return (
    <>
      <PageHeader
        title="Clients"
        description="Everyone your business talks to — contacts, tags, notes."
        right={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button onClick={openNew} data-testid="new-client-btn"><Plus className="h-4 w-4 mr-1" />New client</Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg" data-testid="client-dialog">
              <DialogHeader>
                <DialogTitle>{editing ? "Edit client" : "New client"}</DialogTitle>
              </DialogHeader>
              <form onSubmit={save} className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div className="col-span-2 space-y-1.5"><Label>Name</Label><Input value={form.name} onChange={(e)=>setForm({...form, name:e.target.value})} required data-testid="client-name-input" /></div>
                  <div className="space-y-1.5"><Label>Email</Label><Input type="email" value={form.email || ""} onChange={(e)=>setForm({...form, email:e.target.value})} /></div>
                  <div className="space-y-1.5"><Label>Phone</Label><Input value={form.phone || ""} onChange={(e)=>setForm({...form, phone:e.target.value})} /></div>
                  <div className="space-y-1.5"><Label>Company</Label><Input value={form.company || ""} onChange={(e)=>setForm({...form, company:e.target.value})} /></div>
                  <div className="space-y-1.5"><Label>Website</Label><Input value={form.website || ""} onChange={(e)=>setForm({...form, website:e.target.value})} /></div>
                  <div className="col-span-2 space-y-1.5"><Label>Tags (comma separated)</Label><Input value={Array.isArray(form.tags) ? form.tags.join(", ") : form.tags} onChange={(e)=>setForm({...form, tags:e.target.value})} /></div>
                  <div className="col-span-2 space-y-1.5"><Label>Notes</Label><Textarea value={form.notes || ""} onChange={(e)=>setForm({...form, notes:e.target.value})} /></div>
                </div>
                <DialogFooter><Button type="submit" data-testid="client-save-btn">{editing ? "Update" : "Create"}</Button></DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        }
      />

      <div className="p-8 space-y-6">
        <div className="relative max-w-md">
          <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input placeholder="Search clients…" value={q} onChange={(e)=>setQ(e.target.value)} onKeyDown={(e)=> e.key==='Enter' && load()} className="pl-9" data-testid="clients-search-input" />
        </div>

        <Card className="border-border/70 overflow-hidden">
          <div className="grid grid-cols-12 px-6 py-3 border-b border-border n-overline">
            <div className="col-span-4">Name</div>
            <div className="col-span-3">Company</div>
            <div className="col-span-3">Contact</div>
            <div className="col-span-1">Status</div>
            <div className="col-span-1 text-right">Actions</div>
          </div>
          {clients.length === 0 && <div className="p-8 text-center text-sm text-muted-foreground">No clients yet. Create your first one.</div>}
          {clients.map((c) => (
            <div key={c.id} className="grid grid-cols-12 px-6 py-4 border-b border-border/60 last:border-0 items-center text-sm" data-testid={`client-row-${c.id}`}>
              <div className="col-span-4">
                <Link to={`/clients/${c.id}`} className="font-medium hover:underline" data-testid={`client-link-${c.id}`}>{c.name}</Link>
                <div className="flex gap-1 mt-1 flex-wrap">
                  {(c.tags || []).slice(0,3).map((t) => <Badge key={t} variant="secondary" className="text-[10px]">{t}</Badge>)}
                </div>
              </div>
              <div className="col-span-3 text-muted-foreground">{c.company || "—"}</div>
              <div className="col-span-3 text-muted-foreground">{c.email || c.phone || "—"}</div>
              <div className="col-span-1"><Badge variant={c.status==="active"?"default":"outline"}>{c.status}</Badge></div>
              <div className="col-span-1 flex gap-1 justify-end">
                <Button variant="ghost" size="icon" onClick={()=>openEdit(c)} data-testid={`edit-client-${c.id}`}><Pencil className="h-4 w-4" /></Button>
                <Button variant="ghost" size="icon" onClick={()=>remove(c.id)} data-testid={`delete-client-${c.id}`}><Trash2 className="h-4 w-4" /></Button>
              </div>
            </div>
          ))}
        </Card>
      </div>
    </>
  );
}
