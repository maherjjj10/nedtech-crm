import { useCallback, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import PageHeader from "../components/layout/PageHeader";
import { Card } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Textarea } from "../components/ui/textarea";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import { Avatar, AvatarFallback } from "../components/ui/avatar";
import { api } from "../lib/apiClient";
import { toast } from "sonner";
import { formatCurrency, formatDate, initials } from "../lib/format";
import { ArrowLeft, Trash2 } from "lucide-react";
import { useAuth } from "../lib/authContext";

export default function ClientDetail() {
  const { id } = useParams();
  const { tenant } = useAuth();
  const [data, setData] = useState(null);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

 const load = useCallback(async () => {
  try {
    const { data } = await api.get(`/clients/${id}/timeline`);
    setData(data);
  } catch {
    toast.error("Client not found");
  }
}, [id]);

useEffect(() => {
  load();
}, [load]);

  const addNote = async (e) => {
    e.preventDefault();
    if (!note.trim()) return;
    setSaving(true);
    try {
      await api.post(`/clients/${id}/notes`, { body: note });
      setNote(""); load();
    } catch { toast.error("Failed to add note"); }
    finally { setSaving(false); }
  };

  const removeNote = async (nid) => {
    await api.delete(`/clients/${id}/notes/${nid}`);
    load();
  };

  if (!data) return <div className="p-8 text-sm text-muted-foreground">Loading…</div>;
  const c = data.client;
  const s = data.stats || {};

  return (
    <>
      <PageHeader
        title={c.name}
        description={c.company || c.email || "Client 360"}
        right={
          <Link to="/clients"><Button variant="outline" size="sm"><ArrowLeft className="h-4 w-4 mr-1" />All clients</Button></Link>
        }
      />

      <div className="p-8 space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card className="p-4 border-border/70"><div className="n-overline">Deals</div><div className="text-xl font-bold mt-1">{s.deal_count ?? 0}</div></Card>
          <Card className="p-4 border-border/70"><div className="n-overline">Won</div><div className="text-xl font-bold mt-1">{formatCurrency(s.won_value, tenant?.currency)}</div></Card>
          <Card className="p-4 border-border/70"><div className="n-overline">Invoices</div><div className="text-xl font-bold mt-1">{s.invoice_count ?? 0}</div></Card>
          <Card className="p-4 border-border/70"><div className="n-overline">Paid</div><div className="text-xl font-bold mt-1">{formatCurrency(s.paid_value, tenant?.currency)}</div></Card>
          <Card className="p-4 border-border/70"><div className="n-overline">Outstanding</div><div className="text-xl font-bold mt-1">{formatCurrency(s.outstanding, tenant?.currency)}</div></Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="p-6 border-border/70 lg:col-span-1">
            <div className="flex items-center gap-3 mb-4">
              <Avatar><AvatarFallback className="bg-foreground text-background">{initials(c.name)}</AvatarFallback></Avatar>
              <div>
                <div className="font-semibold">{c.name}</div>
                <Badge variant={c.status==="active"?"default":"outline"}>{c.status}</Badge>
              </div>
            </div>
            <div className="space-y-2 text-sm text-muted-foreground">
              {c.company && <div><span className="n-overline block text-xs mb-0.5">Company</span><span className="text-foreground">{c.company}</span></div>}
              {c.contact_person && <div><span className="n-overline block text-xs mb-0.5">Contact person</span><span className="text-foreground">{c.contact_person}</span></div>}
              {c.email && <div><span className="n-overline block text-xs mb-0.5">Email</span><span className="text-foreground">{c.email}</span></div>}
              {c.phone && <div><span className="n-overline block text-xs mb-0.5">Phone</span><span className="text-foreground">{c.phone}</span></div>}
              {c.vat_number && <div><span className="n-overline block text-xs mb-0.5">VAT number</span><span className="text-foreground font-mono text-xs">{c.vat_number}</span></div>}
              {c.website && <div><span className="n-overline block text-xs mb-0.5">Website</span><a className="underline text-foreground" href={c.website} target="_blank" rel="noreferrer">{c.website}</a></div>}
              {c.address && <div><span className="n-overline block text-xs mb-0.5">Address</span><span className="text-foreground">{c.address}</span></div>}
              {(c.tags || []).length > 0 && (
                <div><span className="n-overline block text-xs mb-1">Tags</span>
                  <div className="flex gap-1 flex-wrap">{c.tags.map(t => <Badge key={t} variant="secondary" className="text-[10px]">{t}</Badge>)}</div>
                </div>
              )}
            </div>
          </Card>

          <div className="lg:col-span-2">
            <Tabs defaultValue="timeline">
              <TabsList data-testid="client-tabs">
                <TabsTrigger value="timeline">Timeline</TabsTrigger>
                <TabsTrigger value="notes">Notes</TabsTrigger>
                <TabsTrigger value="deals">Deals</TabsTrigger>
                <TabsTrigger value="invoices">Invoices</TabsTrigger>
                <TabsTrigger value="contracts" data-testid="tab-contracts">Contracts</TabsTrigger>
              </TabsList>

              <TabsContent value="timeline" className="mt-4">
                <Card className="p-6 border-border/70">
                  <ul className="space-y-3">
                    {(data.activities || []).length === 0 && <li className="text-sm text-muted-foreground">No activity yet.</li>}
                    {data.activities.map((a) => (
                      <li key={a.id} className="flex items-start gap-3 text-sm border-l-2 border-border/60 pl-4 pb-3 last:pb-0">
                        <div>
                          <div>{a.message}</div>
                          <div className="text-xs text-muted-foreground mt-0.5">{formatDate(a.created_at)} · {a.actor}</div>
                        </div>
                      </li>
                    ))}
                  </ul>
                </Card>
              </TabsContent>

              <TabsContent value="notes" className="mt-4">
                <Card className="p-6 border-border/70 space-y-4">
                  <form onSubmit={addNote} className="space-y-2">
                    <Textarea placeholder="Write a note about this client…" value={note} onChange={(e)=>setNote(e.target.value)} data-testid="client-note-input" />
                    <div className="flex justify-end"><Button type="submit" size="sm" disabled={saving} data-testid="client-note-save-btn">Add note</Button></div>
                  </form>
                  <div className="space-y-3">
                    {(data.notes || []).length === 0 && <div className="text-sm text-muted-foreground">No notes yet.</div>}
                    {(data.notes || []).map((n) => (
                      <div key={n.id} className="p-3 rounded-md border border-border/60">
                        <div className="text-sm whitespace-pre-wrap">{n.body}</div>
                        <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
                          <span>{n.author_email} · {formatDate(n.created_at)}</span>
                          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={()=>removeNote(n.id)}><Trash2 className="h-3 w-3" /></Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              </TabsContent>

              <TabsContent value="deals" className="mt-4">
                <Card className="border-border/70">
                  {(data.deals || []).length === 0 && <div className="p-6 text-sm text-muted-foreground">No deals yet.</div>}
                  {(data.deals || []).map(d => (
                    <div key={d.id} className="flex items-center justify-between px-6 py-3 border-b border-border/60 last:border-0 text-sm">
                      <div><div className="font-medium">{d.title}</div><div className="text-xs text-muted-foreground">{d.stage}</div></div>
                      <div className="font-semibold">{formatCurrency(d.value, d.currency)}</div>
                    </div>
                  ))}
                </Card>
              </TabsContent>

              <TabsContent value="invoices" className="mt-4">
                <Card className="border-border/70">
                  {(data.invoices || []).length === 0 && <div className="p-6 text-sm text-muted-foreground">No invoices yet.</div>}
                  {(data.invoices || []).map(inv => (
                    <div key={inv.id} className="flex items-center justify-between px-6 py-3 border-b border-border/60 last:border-0 text-sm">
                      <div><div className="font-medium">{inv.number}</div><div className="text-xs text-muted-foreground">{formatDate(inv.due_date)} · {inv.status}</div></div>
                      <div className="font-semibold">{formatCurrency(inv.amount, inv.currency)}</div>
                    </div>
                  ))}
                </Card>
              </TabsContent>

              <TabsContent value="contracts" className="mt-4">
                <Card className="border-border/70">
                  {(data.contracts || []).length === 0 && (
                    <div className="p-6 text-sm text-muted-foreground">
                      No contracts yet. <Link className="underline" to="/contracts">Go to Contracts →</Link>
                    </div>
                  )}
                  {(data.contracts || []).map(ct => (
                    <div key={ct.id} className="flex items-center justify-between px-6 py-3 border-b border-border/60 last:border-0 text-sm" data-testid={`client-contract-${ct.id}`}>
                      <div className="min-w-0">
                        <div className="font-medium truncate">{ct.title}</div>
                        <div className="text-xs text-muted-foreground">
                          {ct.verification_id ? `${ct.verification_id} · ` : ""}
                          created {formatDate(ct.created_at)}
                          {ct.contract_amount ? ` · ${formatCurrency(ct.contract_amount, ct.currency)}` : ""}
                        </div>
                      </div>
                      <Badge variant={["signed","completed"].includes(ct.status) ? "default" : "outline"}>{ct.status}</Badge>
                    </div>
                  ))}
                </Card>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </div>
    </>
  );
}
