import { useEffect, useState } from "react";
import PageHeader from "../components/layout/PageHeader";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "../components/ui/dialog";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Avatar, AvatarFallback } from "../components/ui/avatar";
import { api } from "../lib/apiClient";
import { Plus, Trash2, Copy, Mail } from "lucide-react";
import { toast } from "sonner";
import { formatCurrency, initials, formatDate } from "../lib/format";

const EMPTY_EMP = { name: "", email: "", phone: "", role: "member", department: "", position: "", salary: 0, currency: "USD", status: "active" };
const EMPTY_INV = { email: "", role: "member" };

export default function Employees() {
  const [items, setItems] = useState([]);
  const [invites, setInvites] = useState([]);
  const [openEmp, setOpenEmp] = useState(false);
  const [openInv, setOpenInv] = useState(false);
  const [empForm, setEmpForm] = useState(EMPTY_EMP);
  const [invForm, setInvForm] = useState(EMPTY_INV);
  const [lastInvite, setLastInvite] = useState(null);

  const load = async () => {
    const [e, i] = await Promise.all([api.get("/employees"), api.get("/tenants/me/invites")]);
    setItems(e.data); setInvites(i.data);
  };
  useEffect(() => { load(); }, []);

  const saveEmp = async (e) => {
    e.preventDefault();
    try {
      await api.post("/employees", { ...empForm, salary: Number(empForm.salary) });
      toast.success("Saved"); setOpenEmp(false); setEmpForm(EMPTY_EMP); load();
    } catch { toast.error("Failed"); }
  };
  const removeEmp = async (id) => { await api.delete(`/employees/${id}`); load(); };

  const sendInvite = async (e) => {
    e.preventDefault();
    try {
      const { data } = await api.post("/tenants/me/invites", invForm);
      setLastInvite(data);
      if (data.email?.sent) toast.success("Invitation email sent");
      else toast.info("Invite ready — copy the link to share manually");
      setInvForm(EMPTY_INV); load();
    } catch (err) { toast.error(err?.response?.data?.detail || "Failed"); }
  };

  const copyLink = (url) => {
    navigator.clipboard.writeText(url);
    toast.success("Invite link copied");
  };
  const revoke = async (id) => { await api.delete(`/tenants/me/invites/${id}`); load(); };

  return (
    <>
      <PageHeader title="Team" description="Your people, their roles, and how they get things done." />
      <div className="p-8">
        <Tabs defaultValue="members">
          <TabsList data-testid="team-tabs">
            <TabsTrigger value="members">Members ({items.length})</TabsTrigger>
            <TabsTrigger value="invites">Invitations ({invites.length})</TabsTrigger>
          </TabsList>

          <TabsContent value="members" className="mt-6">
            <div className="flex justify-end mb-3">
              <Dialog open={openEmp} onOpenChange={setOpenEmp}>
                <DialogTrigger asChild><Button data-testid="new-employee-btn"><Plus className="h-4 w-4 mr-1" />New team member</Button></DialogTrigger>
                <DialogContent>
                  <DialogHeader><DialogTitle>Add team member</DialogTitle></DialogHeader>
                  <form onSubmit={saveEmp} className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5 col-span-2"><Label>Name</Label><Input value={empForm.name} onChange={(e)=>setEmpForm({...empForm, name:e.target.value})} required data-testid="employee-name-input" /></div>
                      <div className="space-y-1.5"><Label>Email</Label><Input type="email" value={empForm.email} onChange={(e)=>setEmpForm({...empForm, email:e.target.value})} /></div>
                      <div className="space-y-1.5"><Label>Phone</Label><Input value={empForm.phone} onChange={(e)=>setEmpForm({...empForm, phone:e.target.value})} /></div>
                      <div className="space-y-1.5"><Label>Role</Label>
                        <Select value={empForm.role} onValueChange={(v)=>setEmpForm({...empForm, role:v})}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent><SelectItem value="owner">Owner</SelectItem><SelectItem value="admin">Admin</SelectItem><SelectItem value="manager">Manager</SelectItem><SelectItem value="member">Member</SelectItem></SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-1.5"><Label>Department</Label><Input value={empForm.department} onChange={(e)=>setEmpForm({...empForm, department:e.target.value})} /></div>
                      <div className="space-y-1.5"><Label>Position</Label><Input value={empForm.position} onChange={(e)=>setEmpForm({...empForm, position:e.target.value})} /></div>
                      <div className="space-y-1.5"><Label>Salary</Label><Input type="number" value={empForm.salary} onChange={(e)=>setEmpForm({...empForm, salary:e.target.value})} /></div>
                    </div>
                    <DialogFooter><Button type="submit" data-testid="employee-save-btn">Save</Button></DialogFooter>
                  </form>
                </DialogContent>
              </Dialog>
            </div>

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
                    <Button variant="ghost" size="icon" onClick={()=>removeEmp(e.id)}><Trash2 className="h-4 w-4" /></Button>
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
          </TabsContent>

          <TabsContent value="invites" className="mt-6">
            <div className="flex justify-between items-end mb-3">
              <p className="text-sm text-muted-foreground max-w-lg">Invite teammates by email. They&apos;ll get a link to set a password and join your workspace with the role you pick.</p>
              <Dialog open={openInv} onOpenChange={(o)=>{setOpenInv(o); if (!o) setLastInvite(null);}}>
                <DialogTrigger asChild><Button data-testid="new-invite-btn"><Mail className="h-4 w-4 mr-1" />Invite</Button></DialogTrigger>
                <DialogContent data-testid="invite-dialog">
                  <DialogHeader><DialogTitle>Invite teammate</DialogTitle></DialogHeader>
                  {!lastInvite ? (
                    <form onSubmit={sendInvite} className="space-y-3">
                      <div className="space-y-1.5"><Label>Email</Label><Input type="email" value={invForm.email} onChange={(e)=>setInvForm({...invForm, email:e.target.value})} required data-testid="invite-email-input" /></div>
                      <div className="space-y-1.5"><Label>Role</Label>
                        <Select value={invForm.role} onValueChange={(v)=>setInvForm({...invForm, role:v})}>
                          <SelectTrigger data-testid="invite-role-select"><SelectValue /></SelectTrigger>
                          <SelectContent><SelectItem value="admin">Admin</SelectItem><SelectItem value="manager">Manager</SelectItem><SelectItem value="member">Member</SelectItem></SelectContent>
                        </Select>
                      </div>
                      <DialogFooter><Button type="submit" data-testid="invite-send-btn">Send invitation</Button></DialogFooter>
                    </form>
                  ) : (
                    <div className="space-y-4">
                      <div className="text-sm">
                        {lastInvite.email?.sent
                          ? "✅ Invitation email sent."
                          : "Email is not yet configured on your workspace. Copy the invite link below and share it manually — it works the same."}
                      </div>
                      <div className="p-3 bg-muted rounded-md text-xs break-all font-mono" data-testid="invite-link">{lastInvite.invite?.invite_url}</div>
                      <DialogFooter>
                        <Button variant="outline" onClick={()=>copyLink(lastInvite.invite?.invite_url)} data-testid="copy-invite-btn"><Copy className="h-4 w-4 mr-1" />Copy link</Button>
                        <Button onClick={()=>{setLastInvite(null); setOpenInv(false);}}>Done</Button>
                      </DialogFooter>
                    </div>
                  )}
                </DialogContent>
              </Dialog>
            </div>

            <Card className="border-border/70">
              {invites.length === 0 && <div className="p-8 text-center text-sm text-muted-foreground">No pending invitations.</div>}
              {invites.map((i) => (
                <div key={i.id} className="flex items-center justify-between px-6 py-4 border-b border-border/60 last:border-0 text-sm" data-testid={`invite-row-${i.id}`}>
                  <div>
                    <div className="font-medium">{i.email}</div>
                    <div className="text-xs text-muted-foreground">Invited {formatDate(i.created_at)} · <Badge variant="outline" className="ml-1 text-[10px]">{i.role}</Badge></div>
                  </div>
                  <div className="flex gap-1">
                    <Button variant="outline" size="sm" onClick={()=>copyLink(i.invite_url)}><Copy className="h-3 w-3 mr-1" />Copy link</Button>
                    <Button variant="ghost" size="icon" onClick={()=>revoke(i.id)}><Trash2 className="h-4 w-4" /></Button>
                  </div>
                </div>
              ))}
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </>
  );
}
