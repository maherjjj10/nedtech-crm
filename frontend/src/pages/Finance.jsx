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
import { api } from "../lib/apiClient";
import { Plus, Trash2, Download } from "lucide-react";
import { toast } from "sonner";
import { formatCurrency, formatDate } from "../lib/format";
import { useAuth } from "../lib/authContext";

const emptyInvoice = { client_name: "", issue_date: "", due_date: "", currency: "USD", status: "draft", items: [{ description: "", quantity: 1, unit_price: 0, tax_rate: 0 }], notes: "" };
const emptyExpense = { date: "", category: "general", vendor: "", amount: 0, currency: "USD", tax_rate: 0, description: "" };

function InvoiceForm({ initial, onSave }) {
  const [form, setForm] = useState(initial);
  const upItem = (idx, key, val) => setForm(f => ({ ...f, items: f.items.map((it, i) => i===idx ? { ...it, [key]: key==='description' ? val : Number(val) } : it) }));
  const addRow = () => setForm(f => ({ ...f, items: [...f.items, { description: "", quantity: 1, unit_price: 0, tax_rate: 0 }] }));
  const rm = (idx) => setForm(f => ({ ...f, items: f.items.filter((_, i) => i !== idx) }));
  const subtotal = form.items.reduce((s, it) => s + (it.quantity * it.unit_price), 0);
  const tax = form.items.reduce((s, it) => s + (it.quantity * it.unit_price) * (it.tax_rate/100), 0);

  return (
    <form onSubmit={(e)=>{e.preventDefault(); onSave(form);}} className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5 col-span-2"><Label>Client name</Label><Input value={form.client_name} onChange={(e)=>setForm({...form, client_name:e.target.value})} required data-testid="invoice-client-input" /></div>
        <div className="space-y-1.5"><Label>Issue date</Label><Input type="date" value={form.issue_date} onChange={(e)=>setForm({...form, issue_date:e.target.value})} /></div>
        <div className="space-y-1.5"><Label>Due date</Label><Input type="date" value={form.due_date} onChange={(e)=>setForm({...form, due_date:e.target.value})} /></div>
        <div className="space-y-1.5"><Label>Currency</Label><Input value={form.currency} onChange={(e)=>setForm({...form, currency:e.target.value})} /></div>
        <div className="space-y-1.5"><Label>Status</Label>
          <Select value={form.status} onValueChange={(v)=>setForm({...form, status:v})}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent><SelectItem value="draft">Draft</SelectItem><SelectItem value="sent">Sent</SelectItem><SelectItem value="paid">Paid</SelectItem><SelectItem value="overdue">Overdue</SelectItem><SelectItem value="cancelled">Cancelled</SelectItem></SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <div className="n-overline">Line items</div>
        {form.items.map((it, idx) => (
          <div key={idx} className="grid grid-cols-12 gap-2 items-center">
            <Input className="col-span-5" placeholder="Description" value={it.description} onChange={(e)=>upItem(idx,'description',e.target.value)} required />
            <Input className="col-span-2" type="number" placeholder="Qty" value={it.quantity} onChange={(e)=>upItem(idx,'quantity',e.target.value)} />
            <Input className="col-span-2" type="number" placeholder="Price" value={it.unit_price} onChange={(e)=>upItem(idx,'unit_price',e.target.value)} />
            <Input className="col-span-2" type="number" placeholder="Tax %" value={it.tax_rate} onChange={(e)=>upItem(idx,'tax_rate',e.target.value)} />
            <Button type="button" variant="ghost" size="icon" onClick={()=>rm(idx)} className="col-span-1"><Trash2 className="h-4 w-4" /></Button>
          </div>
        ))}
        <Button type="button" variant="outline" size="sm" onClick={addRow}><Plus className="h-3 w-3 mr-1" />Add row</Button>
      </div>

      <div className="text-right space-y-0.5 border-t border-border pt-3">
        <div className="text-sm">Subtotal: <span className="font-medium">{formatCurrency(subtotal, form.currency)}</span></div>
        <div className="text-sm">Tax: <span className="font-medium">{formatCurrency(tax, form.currency)}</span></div>
        <div className="text-lg font-bold">Total: {formatCurrency(subtotal + tax, form.currency)}</div>
      </div>

      <DialogFooter><Button type="submit" data-testid="invoice-save-btn">Save invoice</Button></DialogFooter>
    </form>
  );
}

export default function Finance() {
  const { tenant } = useAuth();
  const [invoices, setInvoices] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [summary, setSummary] = useState({});
  const [openInv, setOpenInv] = useState(false);
  const [openExp, setOpenExp] = useState(false);
  const [expenseForm, setExpenseForm] = useState(emptyExpense);

  const load = async () => {
    const [i, e, s] = await Promise.all([api.get("/invoices"), api.get("/expenses"), api.get("/reports/summary")]);
    setInvoices(i.data); setExpenses(e.data); setSummary(s.data);
  };
  useEffect(() => { load(); }, []);

  const saveInvoice = async (form) => {
    try { await api.post("/invoices", form); toast.success("Invoice created"); setOpenInv(false); load(); }
    catch { toast.error("Failed"); }
  };
  const saveExpense = async (e) => {
    e.preventDefault();
    try { await api.post("/expenses", { ...expenseForm, amount: Number(expenseForm.amount), tax_rate: Number(expenseForm.tax_rate) }); toast.success("Expense added"); setOpenExp(false); setExpenseForm(emptyExpense); load(); }
    catch { toast.error("Failed"); }
  };

  const downloadPdf = async (id, number) => {
    const res = await api.get(`/invoices/${id}/pdf`, { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
    const a = document.createElement("a"); a.href = url; a.download = `${number || "invoice"}.pdf`; a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <>
      <PageHeader
        title="Finance"
        description="Invoices, expenses and the numbers that keep the lights on."
      />
      <div className="p-8 space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="p-5 border-border/70"><div className="n-overline">Revenue</div><div className="text-2xl font-bold mt-1">{formatCurrency(summary.revenue, tenant?.currency)}</div></Card>
          <Card className="p-5 border-border/70"><div className="n-overline">Outstanding</div><div className="text-2xl font-bold mt-1">{formatCurrency(summary.outstanding, tenant?.currency)}</div></Card>
          <Card className="p-5 border-border/70"><div className="n-overline">Expenses</div><div className="text-2xl font-bold mt-1">{formatCurrency(summary.expenses, tenant?.currency)}</div></Card>
          <Card className="p-5 border-border/70"><div className="n-overline">Profit</div><div className="text-2xl font-bold mt-1">{formatCurrency(summary.profit, tenant?.currency)}</div></Card>
        </div>

        <Tabs defaultValue="invoices">
          <TabsList data-testid="finance-tabs"><TabsTrigger value="invoices">Invoices</TabsTrigger><TabsTrigger value="expenses">Expenses</TabsTrigger></TabsList>

          <TabsContent value="invoices" className="mt-6">
            <div className="flex justify-end mb-3">
              <Dialog open={openInv} onOpenChange={setOpenInv}>
                <DialogTrigger asChild><Button data-testid="new-invoice-btn"><Plus className="h-4 w-4 mr-1" />New invoice</Button></DialogTrigger>
                <DialogContent className="max-w-2xl">
                  <DialogHeader><DialogTitle>New invoice</DialogTitle></DialogHeader>
                  <InvoiceForm initial={{ ...emptyInvoice, currency: tenant?.currency || "USD" }} onSave={saveInvoice} />
                </DialogContent>
              </Dialog>
            </div>
            <Card className="border-border/70">
              <div className="grid grid-cols-12 px-6 py-3 border-b border-border n-overline">
                <div className="col-span-2">Number</div><div className="col-span-4">Client</div><div className="col-span-2">Due</div><div className="col-span-2">Status</div><div className="col-span-2 text-right">Total</div>
              </div>
              {invoices.length === 0 && <div className="p-8 text-center text-sm text-muted-foreground">No invoices yet.</div>}
              {invoices.map((inv) => (
                <div key={inv.id} className="grid grid-cols-12 px-6 py-4 border-b border-border/60 last:border-0 items-center text-sm" data-testid={`invoice-row-${inv.id}`}>
                  <div className="col-span-2 font-medium">{inv.number}</div>
                  <div className="col-span-4">{inv.client_name || "—"}</div>
                  <div className="col-span-2 text-muted-foreground">{formatDate(inv.due_date)}</div>
                  <div className="col-span-2"><Badge variant={inv.status==="paid"?"default":"outline"}>{inv.status}</Badge></div>
                  <div className="col-span-2 text-right flex items-center justify-end gap-2">
                    <span className="font-semibold">{formatCurrency(inv.totals?.total, inv.currency)}</span>
                    <Button variant="ghost" size="icon" onClick={()=>downloadPdf(inv.id, inv.number)} data-testid={`download-invoice-${inv.id}`}><Download className="h-4 w-4" /></Button>
                  </div>
                </div>
              ))}
            </Card>
          </TabsContent>

          <TabsContent value="expenses" className="mt-6">
            <div className="flex justify-end mb-3">
              <Dialog open={openExp} onOpenChange={setOpenExp}>
                <DialogTrigger asChild><Button data-testid="new-expense-btn"><Plus className="h-4 w-4 mr-1" />New expense</Button></DialogTrigger>
                <DialogContent>
                  <DialogHeader><DialogTitle>New expense</DialogTitle></DialogHeader>
                  <form onSubmit={saveExpense} className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5 col-span-2"><Label>Vendor</Label><Input value={expenseForm.vendor} onChange={(e)=>setExpenseForm({...expenseForm, vendor:e.target.value})} /></div>
                      <div className="space-y-1.5"><Label>Category</Label><Input value={expenseForm.category} onChange={(e)=>setExpenseForm({...expenseForm, category:e.target.value})} /></div>
                      <div className="space-y-1.5"><Label>Date</Label><Input type="date" value={expenseForm.date} onChange={(e)=>setExpenseForm({...expenseForm, date:e.target.value})} /></div>
                      <div className="space-y-1.5"><Label>Amount</Label><Input type="number" value={expenseForm.amount} onChange={(e)=>setExpenseForm({...expenseForm, amount:e.target.value})} required /></div>
                      <div className="space-y-1.5"><Label>Tax %</Label><Input type="number" value={expenseForm.tax_rate} onChange={(e)=>setExpenseForm({...expenseForm, tax_rate:e.target.value})} /></div>
                      <div className="space-y-1.5 col-span-2"><Label>Description</Label><Input value={expenseForm.description} onChange={(e)=>setExpenseForm({...expenseForm, description:e.target.value})} /></div>
                    </div>
                    <DialogFooter><Button type="submit" data-testid="expense-save-btn">Save expense</Button></DialogFooter>
                  </form>
                </DialogContent>
              </Dialog>
            </div>
            <Card className="border-border/70">
              {expenses.length === 0 && <div className="p-8 text-center text-sm text-muted-foreground">No expenses yet.</div>}
              {expenses.map((e) => (
                <div key={e.id} className="flex items-center justify-between px-6 py-3 border-b border-border/60 last:border-0 text-sm">
                  <div>
                    <div className="font-medium">{e.vendor || e.description || "Expense"}</div>
                    <div className="text-xs text-muted-foreground">{e.category} · {formatDate(e.date)}</div>
                  </div>
                  <div className="font-semibold">{formatCurrency(e.amount * (1 + (e.tax_rate||0)/100), e.currency)}</div>
                </div>
              ))}
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </>
  );
}
