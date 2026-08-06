import { useEffect, useState } from "react";
import PageHeader from "../components/layout/PageHeader";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "../components/ui/dialog";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Avatar, AvatarFallback } from "../components/ui/avatar";
import { api } from "../lib/apiClient";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { formatCurrency, initials } from "../lib/format";

const EMPTY = { name: "", email: "", phone: "", role: "member", department: "", position: "", salary: 0, currency: "USD", status: "active" };

export default function Employees() {
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);

  const load = async () => { const { data } = await api.get("/employees"); setItems(data); };
  useEffect(() => { load(); }, []);

  const save = async (e) => {
    e.preventDefault();
    try {
      await api.post("/employees", { ...form, salary: Number(form.salary) });
      toast.success("Saved"); setOpen(false); setForm(EMPTY); load();
    } catch { toast.error("Failed"); }
  };
  const remove = async (id) => { await api.delete(`/employees/${id}`); load(); };

  return (
    <>
      <PageHeader
        title="Team"
        description="Your people, their roles, and how they get things done."
        right={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild><Button data-testid="new-employee-btn"><Plus className="h-4 w-4 mr-1" />New team member</Button></DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle>Add team member</DialogTitle></DialogHeader>
              <form onSubmit={save} className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5 col-span-2"><Label>Name</Label><Input value={form.name} onChange={(e)=>setForm({...form, name:e.target.value})} required data-testid="employee-name-input" /></div>
                  <div className="space-y-1.5"><Label>Email</Label><Input type="email" value={form.email} onChange={(e)=>setForm({...form, email:e.target.value})} /></div>
                  <div className="space-y-1.5"><Label>Phone</Label><Input value={form.phone} onChange={(e)=>setForm({...form, phone:e.target.value})} /></div>
                  <div className="space-y-1.5"><Label>Role</Label>
                    <Select value={form.role} onValueChange={(v)=>setForm({...form, role:v})}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent><SelectItem value="owner">Owner</SelectItem><SelectItem value="admin">Admin</SelectItem><SelectItem value="manager">Manager</SelectItem><SelectItem value="member">Member</SelectItem></SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5"><Label>Department</Label><Input value={form.department} onChange={(e)=>setForm({...form, department:e.target.value})} /></div>
                  <div className="space-y-1.5"><Label>Position</Label><Input value={form.position} onChange={(e)=>setForm({...form, position:e.target.value})} /></div>
                  <div className="space-y-1.5"><Label>Salary</Label><Input type="number" value={form.salary} onChange={(e)=>setForm({...form, salary:e.target.value})} /></div>
                </div>
                <DialogFooter><Button type="submit" data-testid="employee-save-btn">Save</Button></DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        }
      />
      <div className="p-8">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.length === 0 && <div className="col-span-full p-8 text-center text-sm text-muted-foreground border border-dashed border-border rounded-lg">No team members yet.</div>}
          {items.map((e) => (
            <Card key={e.id} className="p-5 n-card-hover border-border/70">
              <div className="flex items-start justify-between">
                <div className="flex gap-3">
                  <Avatar><AvatarFallback className="bg-foreground text-background">{initials(e.name)}</AvatarFallback></Avatar>
                  <div>
                    <div className="font-semibold">{e.name}</div>
                    <div className="text-xs text-muted-foreground">{e.position || e.role}</div>
                  </div>
                </div>
                <Button variant="ghost" size="icon" onClick={()=>remove(e.id)}><Trash2 className="h-4 w-4" /></Button>
              </div>
              <div className="mt-4 space-y-1 text-xs text-muted-foreground">
                {e.email && <div>{e.email}</div>}
                {e.department && <div>{e.department}</div>}
                <div className="flex items-center gap-2 mt-2">
                  <Badge variant="outline">{e.role}</Badge>
                  <span className="font-semibold text-foreground">{formatCurrency(e.salary, e.currency)}</span>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </>
  );
}
