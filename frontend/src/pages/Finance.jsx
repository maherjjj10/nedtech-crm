import { useEffect, useState } from "react";
import PageHeader from "../components/layout/PageHeader";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "../components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "../components/ui/dialog";
import { Label } from "../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { api } from "../lib/apiClient";
import {
  Plus,
  Trash2,
  Download,
  Send,
  Copy,
  Wand2,
} from "lucide-react";
import { toast } from "sonner";
import { formatCurrency, formatDate } from "../lib/format";
import { useAuth } from "../lib/authContext";
import { useLanguage } from "../i18n";

const emptyInvoice = {
  client_id: "",
  client_name: "",
  issue_date: "",
  due_date: "",
  currency: "USD",
  status: "draft",
  items: [
    {
      description: "",
      quantity: 1,
      unit_price: 0,
      tax_rate: 0,
    },
  ],
  notes: "",
};

const emptyQuote = {
  client_id: "",
  client_name: "",
  issue_date: "",
  currency: "USD",
  status: "draft",
  items: [
    {
      description: "",
      quantity: 1,
      unit_price: 0,
      tax_rate: 0,
    },
  ],
  notes: "",
};

const emptyExpense = {
  date: "",
  category: "general",
  vendor: "",
  amount: 0,
  currency: "USD",
  tax_rate: 0,
  description: "",
};

function LineItemsEditor({ items, onChange, currency }) {
  const { t } = useLanguage();

  const up = (idx, key, val) =>
    onChange(
      items.map((it, i) =>
        i === idx
          ? {
              ...it,
              [key]:
                key === "description"
                  ? val
                  : Number(val),
            }
          : it
      )
    );

  const add = () =>
    onChange([
      ...items,
      {
        description: "",
        quantity: 1,
        unit_price: 0,
        tax_rate: 0,
      },
    ]);

  const rm = (idx) =>
    onChange(items.filter((_, i) => i !== idx));

  const subtotal = items.reduce(
    (sum, it) =>
      sum + it.quantity * it.unit_price,
    0
  );

  const tax = items.reduce(
    (sum, it) =>
      sum +
      it.quantity *
        it.unit_price *
        (it.tax_rate / 100),
    0
  );

  return (
    <>
      <div className="space-y-2">
        <div className="n-overline">
          {t("lineItems")}
        </div>

        {items.map((it, idx) => (
          <div
            key={idx}
            className="grid grid-cols-12 gap-2 items-center"
            data-testid={`line-item-row-${idx}`}
          >
            <Input
              className="col-span-5"
              placeholder={t("description")}
              value={it.description}
              onChange={(e) =>
                up(
                  idx,
                  "description",
                  e.target.value
                )
              }
              required
              data-testid={`line-desc-${idx}`}
            />

            <Input
              className="col-span-2"
              type="number"
              placeholder={t("quantity")}
              value={it.quantity}
              onChange={(e) =>
                up(
                  idx,
                  "quantity",
                  e.target.value
                )
              }
              data-testid={`line-qty-${idx}`}
            />

            <Input
              className="col-span-2"
              type="number"
              placeholder={t("price")}
              value={it.unit_price}
              onChange={(e) =>
                up(
                  idx,
                  "unit_price",
                  e.target.value
                )
              }
              data-testid={`line-price-${idx}`}
            />

            <Input
              className="col-span-2"
              type="number"
              placeholder={t("taxPercent")}
              value={it.tax_rate}
              onChange={(e) =>
                up(
                  idx,
                  "tax_rate",
                  e.target.value
                )
              }
              data-testid={`line-tax-${idx}`}
            />

            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => rm(idx)}
              className="col-span-1"
              data-testid={`line-remove-${idx}`}
              title={t("delete")}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        ))}

        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={add}
          data-testid="line-add-row"
        >
          <Plus className="h-3 w-3 mr-1" />
          {t("addRow")}
        </Button>
      </div>

      <div className="text-right space-y-0.5 border-t border-border pt-3">
        <div className="text-sm">
          {t("subtotal")}:{" "}
          <span className="font-medium">
            {formatCurrency(
              subtotal,
              currency
            )}
          </span>
        </div>

        <div className="text-sm">
          {t("tax")}:{" "}
          <span className="font-medium">
            {formatCurrency(
              tax,
              currency
            )}
          </span>
        </div>

        <div className="text-lg font-bold">
          {t("total")}:{" "}
          {formatCurrency(
            subtotal + tax,
            currency
          )}
        </div>
      </div>
    </>
  );
}

function QuoteForm({ initial, onSave, clients = [] }) {
  const { t } = useLanguage();
  const [form, setForm] = useState(initial);
  const [clientSearch, setClientSearch] = useState("");

  const filteredClients = clients.filter((client) => {
    const search = clientSearch.trim().toLowerCase();
    if (!search) return true;

    return [
      client.name,
      client.company,
      client.contact_person,
      client.email,
      client.phone,
      client.vat_number,
      client.address,
    ]
      .filter(Boolean)
      .some((value) =>
        String(value).toLowerCase().includes(search)
      );
  });

  const selectedClient =
    clients.find(
      (client) =>
        String(client.id) === String(form.client_id)
    ) || null;

  const selectClient = (clientId) => {
    if (clientId === "__none__") {
      setForm((f) => ({
        ...f,
        client_id: "",
        client_name: "",
      }));
      return;
    }

    const client = clients.find(
      (c) => String(c.id) === String(clientId)
    );

    if (!client) return;

    setForm((f) => ({
      ...f,
      client_id: client.id,
      client_name: client.name || "",
    }));
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();

        if (!form.client_id) {
          toast.error(t("selectClientRequired"));
          return;
        }

        onSave(form);
      }}
      className="space-y-4"
    >
      <div className="grid grid-cols-2 gap-3">
        {/* CRM CLIENT */}
        <div className="space-y-1.5 col-span-2">
          <Label>{t("clientName")}</Label>

          <Select
            value={form.client_id || "__none__"}
            onValueChange={selectClient}
          >
            <SelectTrigger
              data-testid="quote-client-select"
              className="w-full"
            >
              <SelectValue
                placeholder={t("selectClient")}
              />
            </SelectTrigger>

            <SelectContent>
              <div
                className="p-2 border-b"
                onKeyDown={(e) => e.stopPropagation()}
              >
                <Input
                  autoFocus
                  placeholder={t("searchClients")}
                  value={clientSearch}
                  onChange={(e) =>
                    setClientSearch(e.target.value)
                  }
                  onKeyDown={(e) => e.stopPropagation()}
                  className="h-9"
                />
              </div>

              <SelectItem value="__none__">
                {t("selectClient")}
              </SelectItem>

              {filteredClients.length === 0 && (
                <div className="px-3 py-6 text-center text-sm text-muted-foreground">
                  {t("noClientsFound")}
                </div>
              )}

              {filteredClients.map((client) => (
                <SelectItem
                  key={client.id}
                  value={String(client.id)}
                >
                  {client.company
                    ? `${client.company} — ${client.name || ""}`
                    : client.name ||
                      client.email ||
                      client.id}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* CLIENT DETAILS */}
        {selectedClient && (
          <div className="col-span-2">
            <Card className="p-4 bg-muted/30 border-border/70">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 text-sm">
                <div>
                  <span className="text-muted-foreground">
                    {t("client")}:
                  </span>{" "}
                  <span className="font-medium">
                    {selectedClient.name || "—"}
                  </span>
                </div>

                <div>
                  <span className="text-muted-foreground">
                    {t("company")}:
                  </span>{" "}
                  <span className="font-medium">
                    {selectedClient.company || "—"}
                  </span>
                </div>

                <div>
                  <span className="text-muted-foreground">
                    {t("contact")}:
                  </span>{" "}
                  <span className="font-medium">
                    {selectedClient.contact_person || "—"}
                  </span>
                </div>

                <div>
                  <span className="text-muted-foreground">
                    {t("email")}:
                  </span>{" "}
                  <span className="font-medium">
                    {selectedClient.email || "—"}
                  </span>
                </div>

                <div>
                  <span className="text-muted-foreground">
                    {t("phone")}:
                  </span>{" "}
                  <span className="font-medium">
                    {selectedClient.phone || "—"}
                  </span>
                </div>

                <div>
                  <span className="text-muted-foreground">
                    {t("vat")}:
                  </span>{" "}
                  <span className="font-medium">
                    {selectedClient.vat_number || "—"}
                  </span>
                </div>

                <div className="md:col-span-2">
                  <span className="text-muted-foreground">
                    {t("address")}:
                  </span>{" "}
                  <span className="font-medium">
                    {selectedClient.address || "—"}
                  </span>
                </div>
              </div>
            </Card>
          </div>
        )}

        <div className="space-y-1.5">
          <Label>{t("issueDate")}</Label>
          <Input
            type="date"
            value={form.issue_date}
            onChange={(e) =>
              setForm({
                ...form,
                issue_date: e.target.value,
              })
            }
          />
        </div>

        <div className="space-y-1.5">
          <Label>{t("currency")}</Label>
          <Input
            value={form.currency}
            onChange={(e) =>
              setForm({
                ...form,
                currency: e.target.value,
              })
            }
          />
        </div>

        <div className="space-y-1.5 col-span-2">
          <Label>{t("notes")}</Label>
          <Input
            value={form.notes || ""}
            onChange={(e) =>
              setForm({
                ...form,
                notes: e.target.value,
              })
            }
          />
        </div>
      </div>

      <LineItemsEditor
        items={form.items}
        onChange={(items) =>
          setForm({
            ...form,
            items,
          })
        }
        currency={form.currency}
      />

      <DialogFooter>
        <Button
          type="submit"
          data-testid="quote-save-btn"
        >
          {t("saveQuote")}
        </Button>
      </DialogFooter>
    </form>
  );
}

function InvoiceForm({
  initial,
  onSave,
  clients,
}) {
  const { t } = useLanguage();
  const [form, setForm] = useState(initial);
  const [clientSearch, setClientSearch] = useState("");

  const selectedClient =
    clients.find(
      (client) =>
        String(client.id) ===
        String(form.client_id)
    ) || null;

  const filteredClients = clients.filter((client) => {
    const search = clientSearch.trim().toLowerCase();

    if (!search) return true;

    return [
      client.name,
      client.company,
      client.contact_person,
      client.email,
      client.phone,
      client.vat_number,
      client.address,
    ]
      .filter(Boolean)
      .some((value) =>
        String(value)
          .toLowerCase()
          .includes(search)
      );
  });

  const selectClient = (clientId) => {
    if (clientId === "__none__") {
      setForm((f) => ({
        ...f,
        client_id: "",
        client_name: "",
      }));
      return;
    }

    const client = clients.find(
      (c) =>
        String(c.id) ===
        String(clientId)
    );

    if (!client) return;

    setForm((f) => ({
      ...f,
      client_id: client.id,
      client_name: client.name || "",
    }));
  };

  const upItem = (idx, key, val) =>
    setForm((f) => ({
      ...f,
      items: f.items.map((it, i) =>
        i === idx
          ? {
              ...it,
              [key]:
                key === "description"
                  ? val
                  : Number(val),
            }
          : it
      ),
    }));

  const addRow = () =>
    setForm((f) => ({
      ...f,
      items: [
        ...f.items,
        {
          description: "",
          quantity: 1,
          unit_price: 0,
          tax_rate: 0,
        },
      ],
    }));

  const rm = (idx) =>
    setForm((f) => ({
      ...f,
      items: f.items.filter(
        (_, i) => i !== idx
      ),
    }));

  const subtotal = form.items.reduce(
    (sum, it) =>
      sum + it.quantity * it.unit_price,
    0
  );

  const tax = form.items.reduce(
    (sum, it) =>
      sum +
      it.quantity *
        it.unit_price *
        (it.tax_rate / 100),
    0
  );

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();

        if (!form.client_id) {
          toast.error(
            "Please select a client from the CRM."
          );
          return;
        }

        onSave(form);
      }}
      className="space-y-4"
    >
      <div className="grid grid-cols-2 gap-3">
   {/* CLIENT SELECTOR */}
<div className="space-y-1.5 col-span-2">
  <Label>
    {t("clientName")}
  </Label>

  <Select
    value={form.client_id || "__none__"}
    onValueChange={selectClient}
  >
    <SelectTrigger
      data-testid="invoice-client-select"
      className="w-full"
    >
      <SelectValue placeholder="Select client from CRM" />
    </SelectTrigger>

    <SelectContent>
      <div
        className="p-2 border-b"
        onKeyDown={(e) => e.stopPropagation()}
      >
        <Input
          autoFocus
          placeholder="Search clients..."
          value={clientSearch}
          onChange={(e) =>
            setClientSearch(e.target.value)
          }
          onKeyDown={(e) => e.stopPropagation()}
          className="h-9"
        />
      </div>

      <SelectItem value="__none__">
        Select client from CRM
      </SelectItem>

      {filteredClients.length === 0 && (
        <div className="px-3 py-6 text-center text-sm text-muted-foreground">
          No clients found
        </div>
      )}

      {filteredClients.map((client) => (
        <SelectItem
          key={client.id}
          value={String(client.id)}
        >
          {client.company
            ? `${client.company} — ${client.name || ""}`
            : client.name ||
              client.email ||
              client.id}
        </SelectItem>
      ))}
    </SelectContent>
  </Select>
</div>

        {/* CLIENT DETAILS */}
        {selectedClient && (
          <div className="col-span-2">
            <Card className="p-4 bg-muted/30 border-border/70">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 text-sm">
                <div>
                  <span className="text-muted-foreground">
                    Client:
                  </span>{" "}
                  <span className="font-medium">
                    {selectedClient.name ||
                      "—"}
                  </span>
                </div>

                <div>
                  <span className="text-muted-foreground">
                    Company:
                  </span>{" "}
                  <span className="font-medium">
                    {selectedClient.company ||
                      "—"}
                  </span>
                </div>

                <div>
                  <span className="text-muted-foreground">
                    Contact:
                  </span>{" "}
                  <span className="font-medium">
                    {selectedClient.contact_person ||
                      "—"}
                  </span>
                </div>

                <div>
                  <span className="text-muted-foreground">
                    Email:
                  </span>{" "}
                  <span className="font-medium">
                    {selectedClient.email ||
                      "—"}
                  </span>
                </div>

                <div>
                  <span className="text-muted-foreground">
                    Phone:
                  </span>{" "}
                  <span className="font-medium">
                    {selectedClient.phone ||
                      "—"}
                  </span>
                </div>

                <div>
                  <span className="text-muted-foreground">
                    VAT:
                  </span>{" "}
                  <span className="font-medium">
                    {selectedClient.vat_number ||
                      "—"}
                  </span>
                </div>

                <div className="md:col-span-2">
                  <span className="text-muted-foreground">
                    Address:
                  </span>{" "}
                  <span className="font-medium">
                    {selectedClient.address ||
                      "—"}
                  </span>
                </div>
              </div>
            </Card>
          </div>
        )}

        <div className="space-y-1.5">
          <Label>{t("issueDate")}</Label>

          <Input
            type="date"
            value={form.issue_date}
            onChange={(e) =>
              setForm({
                ...form,
                issue_date: e.target.value,
              })
            }
          />
        </div>

        <div className="space-y-1.5">
          <Label>{t("dueDate")}</Label>

          <Input
            type="date"
            value={form.due_date}
            onChange={(e) =>
              setForm({
                ...form,
                due_date: e.target.value,
              })
            }
          />
        </div>

        <div className="space-y-1.5">
          <Label>{t("currency")}</Label>

          <Input
            value={form.currency}
            onChange={(e) =>
              setForm({
                ...form,
                currency: e.target.value,
              })
            }
          />
        </div>

        <div className="space-y-1.5">
          <Label>{t("status")}</Label>

          <Select
            value={form.status}
            onValueChange={(v) =>
              setForm({
                ...form,
                status: v,
              })
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>

            <SelectContent>
              <SelectItem value="draft">
                {t("draft")}
              </SelectItem>

              <SelectItem value="sent">
                {t("sent")}
              </SelectItem>

              <SelectItem value="paid">
                {t("paid")}
              </SelectItem>

              <SelectItem value="overdue">
                {t("overdue")}
              </SelectItem>

              <SelectItem value="cancelled">
                {t("cancelled")}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <div className="n-overline">
          {t("lineItems")}
        </div>

        {form.items.map((it, idx) => (
          <div
            key={idx}
            className="grid grid-cols-12 gap-2 items-center"
          >
            <Input
              className="col-span-5"
              placeholder={t("description")}
              value={it.description}
              onChange={(e) =>
                upItem(
                  idx,
                  "description",
                  e.target.value
                )
              }
              required
            />

            <Input
              className="col-span-2"
              type="number"
              placeholder={t("quantity")}
              value={it.quantity}
              onChange={(e) =>
                upItem(
                  idx,
                  "quantity",
                  e.target.value
                )
              }
            />

            <Input
              className="col-span-2"
              type="number"
              placeholder={t("price")}
              value={it.unit_price}
              onChange={(e) =>
                upItem(
                  idx,
                  "unit_price",
                  e.target.value
                )
              }
            />

            <Input
              className="col-span-2"
              type="number"
              placeholder={t("taxPercent")}
              value={it.tax_rate}
              onChange={(e) =>
                upItem(
                  idx,
                  "tax_rate",
                  e.target.value
                )
              }
            />

            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => rm(idx)}
              className="col-span-1"
              title={t("delete")}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        ))}

        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={addRow}
        >
          <Plus className="h-3 w-3 mr-1" />
          {t("addRow")}
        </Button>
      </div>

      <div className="text-right space-y-0.5 border-t border-border pt-3">
        <div className="text-sm">
          {t("subtotal")}:{" "}
          <span className="font-medium">
            {formatCurrency(
              subtotal,
              form.currency
            )}
          </span>
        </div>

        <div className="text-sm">
          {t("tax")}:{" "}
          <span className="font-medium">
            {formatCurrency(
              tax,
              form.currency
            )}
          </span>
        </div>

        <div className="text-lg font-bold">
          {t("total")}:{" "}
          {formatCurrency(
            subtotal + tax,
            form.currency
          )}
        </div>
      </div>

      <DialogFooter>
        <Button
          type="submit"
          data-testid="invoice-save-btn"
        >
          {t("saveInvoice")}
        </Button>
      </DialogFooter>
    </form>
  );
}

export default function Finance() {
  const { tenant } = useAuth();
  const { t } = useLanguage();

  const [invoices, setInvoices] = useState([]);
  const [quotes, setQuotes] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [summary, setSummary] = useState({});
  const [clients, setClients] = useState([]);

  const [openInv, setOpenInv] = useState(false);
  const [openQuote, setOpenQuote] = useState(false);
  const [openExp, setOpenExp] = useState(false);

  const [expenseForm, setExpenseForm] =
    useState(emptyExpense);

  const load = async () => {
    try {
      const [
        i,
        q,
        e,
        s,
        c,
      ] = await Promise.all([
        api.get("/invoices"),
        api.get("/quotes"),
        api.get("/expenses"),
        api.get("/reports/summary"),
        api.get("/clients"),
      ]);

      setInvoices(i.data);
      setQuotes(q.data);
      setExpenses(e.data);
      setSummary(s.data);
      setClients(
        Array.isArray(c.data)
          ? c.data
          : []
      );
    } catch (error) {
      console.error(
        "Finance load error:",
        error
      );

      toast.error(
        t("loadFailed")
      );
    }
  };

  useEffect(() => {
    load();
  }, []);

  const saveInvoice = async (form) => {
    try {
      await api.post(
        "/invoices",
        form
      );

      toast.success(
        t("invoiceCreated")
      );

      setOpenInv(false);
      load();
    } catch (e) {
      console.error(
        "Invoice save error:",
        e
      );

      toast.error(
        e?.response?.data?.detail ||
          t("saveFailed")
      );
    }
  };

  const saveQuote = async (form) => {
    try {
      if (!form.client_id) {
        toast.error(t("selectClientRequired"));
        return;
      }

      await api.post(
        "/quotes",
        form
      );

      toast.success(
        t("quoteCreated")
      );

      setOpenQuote(false);
      load();
    } catch {
      toast.error(
        t("saveFailed")
      );
    }
  };

  const shareQuote = async (id) => {
    try {
      const { data } =
        await api.post(
          `/quotes/${id}/share`
        );

      await navigator.clipboard.writeText(
        data.public_url
      );

      toast.success(
        t("publicLinkCopied")
      );

      load();
    } catch (e) {
      toast.error(
        e?.response?.data?.detail ||
          t("failed")
      );
    }
  };

  const convertQuote = async (id) => {
    try {
      await api.post(
        `/quotes/${id}/convert`,
        {
          create_project: false,
        }
      );

      toast.success(
        t("invoiceCreatedFromQuote")
      );

      load();
    } catch (e) {
      toast.error(
        e?.response?.data?.detail ||
          t("failed")
      );
    }
  };

  const deleteQuote = async (id) => {
    if (
      !window.confirm(
        t("deleteQuoteConfirm")
      )
    ) {
      return;
    }

    try {
      await api.delete(
        `/quotes/${id}`
      );

      load();
    } catch (e) {
      toast.error(
        e?.response?.data?.detail ||
          t("failed")
      );
    }
  };

  const saveExpense = async (e) => {
    e.preventDefault();

    try {
      await api.post(
        "/expenses",
        {
          ...expenseForm,
          amount: Number(
            expenseForm.amount
          ),
          tax_rate: Number(
            expenseForm.tax_rate
          ),
        }
      );

      toast.success(
        t("expenseAdded")
      );

      setOpenExp(false);
      setExpenseForm(
        emptyExpense
      );

      load();
    } catch {
      toast.error(
        t("saveFailed")
      );
    }
  };

  const downloadPdf = async (id, number) => {
  try {
    /*
     * Use the SAME language currently used by the CRM UI.
     *
     * We intentionally do NOT use localStorage here because
     * the language selector / i18n system is the real source
     * of truth for the active UI language.
     *
     * The translated value of "finance" tells us which language
     * is currently active.
     */

    let pdfLanguage = "en";

    const financeLabel = String(
      t("finance") || ""
    )
      .trim()
      .toLowerCase();

    if (financeLabel === "financiën") {
      pdfLanguage = "nl";
    } else if (financeLabel === "finanzen") {
      pdfLanguage = "de";
    } else if (financeLabel === "finance") {
      pdfLanguage = "en";
    }

    console.log(
      "CRM UI language:",
      financeLabel
    );

    console.log(
      "Invoice PDF language:",
      pdfLanguage
    );

    const res = await api.get(
      `/invoices/${id}/pdf`,
      {
        params: {
          lang: pdfLanguage,
        },
        responseType: "blob",
      }
    );

    const url =
      window.URL.createObjectURL(
        new Blob([res.data], {
          type: "application/pdf",
        })
      );

    const a =
      document.createElement("a");

    a.href = url;

    a.download = `${
      number || "invoice"
    }.pdf`;

    document.body.appendChild(a);

    a.click();

    a.remove();

    window.URL.revokeObjectURL(url);
  } catch (e) {
    console.error(
      "Invoice PDF download error:",
      e
    );

    toast.error(
      t("downloadFailed")
    );
  }
};

  return (
    <>
      <PageHeader
        title={t("finance")}
        description={t(
          "financeDescription"
        )}
      />

      <div className="p-8 space-y-6">
        {/* KPI */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="p-5 border-border/70">
            <div className="n-overline">
              {t("revenue")}
            </div>

            <div className="text-2xl font-bold mt-1">
              {formatCurrency(
                summary.revenue,
                tenant?.currency
              )}
            </div>
          </Card>

          <Card className="p-5 border-border/70">
            <div className="n-overline">
              {t("outstanding")}
            </div>

            <div className="text-2xl font-bold mt-1">
              {formatCurrency(
                summary.outstanding,
                tenant?.currency
              )}
            </div>
          </Card>

          <Card className="p-5 border-border/70">
            <div className="n-overline">
              {t("expenses")}
            </div>

            <div className="text-2xl font-bold mt-1">
              {formatCurrency(
                summary.expenses,
                tenant?.currency
              )}
            </div>
          </Card>

          <Card className="p-5 border-border/70">
            <div className="n-overline">
              {t("profit")}
            </div>

            <div className="text-2xl font-bold mt-1">
              {formatCurrency(
                summary.profit,
                tenant?.currency
              )}
            </div>
          </Card>
        </div>

        <Tabs defaultValue="invoices">
          <TabsList data-testid="finance-tabs">
            <TabsTrigger
              value="invoices"
              data-testid="tab-invoices"
            >
              {t("invoices")}
            </TabsTrigger>

            <TabsTrigger
              value="quotes"
              data-testid="tab-quotes"
            >
              {t("quotes")}
            </TabsTrigger>

            <TabsTrigger
              value="expenses"
              data-testid="tab-expenses"
            >
              {t("expenses")}
            </TabsTrigger>
          </TabsList>

          {/* ============================= */}
          {/* INVOICES */}
          {/* ============================= */}

          <TabsContent
            value="invoices"
            className="mt-6"
          >
            <div className="flex justify-end mb-3">
              <Dialog
                open={openInv}
                onOpenChange={
                  setOpenInv
                }
              >
                <DialogTrigger asChild>
                  <Button
                    data-testid="new-invoice-btn"
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    {t("newInvoice")}
                  </Button>
                </DialogTrigger>

                <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
                  <DialogHeader>
                    <DialogTitle>
                      {t("newInvoice")}
                    </DialogTitle>
                  </DialogHeader>

                  <InvoiceForm
                    initial={{
                      ...emptyInvoice,
                      currency:
                        tenant?.currency ||
                        "USD",
                    }}
                    clients={clients}
                    onSave={
                      saveInvoice
                    }
                  />
                </DialogContent>
              </Dialog>
            </div>

            <Card className="border-border/70">
              <div className="grid grid-cols-12 px-6 py-3 border-b border-border n-overline">
                <div className="col-span-2">
                  {t("number")}
                </div>

                <div className="col-span-4">
                  {t("client")}
                </div>

                <div className="col-span-2">
                  {t("due")}
                </div>

                <div className="col-span-2">
                  {t("status")}
                </div>

                <div className="col-span-2 text-right">
                  {t("total")}
                </div>
              </div>

              {invoices.length === 0 && (
                <div className="p-8 text-center text-sm text-muted-foreground">
                  {t("noInvoicesYet")}
                </div>
              )}

              {invoices.map((inv) => (
                <div
                  key={inv.id}
                  className="grid grid-cols-12 px-6 py-4 border-b border-border/60 last:border-0 items-center text-sm"
                  data-testid={`invoice-row-${inv.id}`}
                >
                  <div className="col-span-2 font-medium">
                    {inv.number}
                  </div>

                  <div className="col-span-4">
                    {inv.client_name ||
                      "—"}
                  </div>

                  <div className="col-span-2 text-muted-foreground">
                    {formatDate(
                      inv.due_date
                    )}
                  </div>

                  <div className="col-span-2">
                    <Badge
                      variant={
                        inv.status ===
                        "paid"
                          ? "default"
                          : "outline"
                      }
                    >
                      {t(
                        `invoiceStatus_${inv.status}`
                      )}
                    </Badge>
                  </div>

                  <div className="col-span-2 text-right flex items-center justify-end gap-2">
                    <span className="font-semibold">
                      {formatCurrency(
                        inv.totals?.total,
                        inv.currency
                      )}
                    </span>

                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() =>
                        downloadPdf(
                          inv.id,
                          inv.number
                        )
                      }
                      data-testid={`download-invoice-${inv.id}`}
                      title={t(
                        "download"
                      )}
                    >
                      <Download className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </Card>
          </TabsContent>

          {/* ============================= */}
          {/* QUOTES */}
          {/* ============================= */}

          <TabsContent
            value="quotes"
            className="mt-6"
          >
            <div className="flex justify-end mb-3">
              <Dialog
                open={openQuote}
                onOpenChange={
                  setOpenQuote
                }
              >
                <DialogTrigger asChild>
                  <Button
                    data-testid="new-quote-btn"
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    {t("newQuote")}
                  </Button>
                </DialogTrigger>

                <DialogContent className="max-w-2xl">
                  <DialogHeader>
                    <DialogTitle>
                      {t("newQuote")}
                    </DialogTitle>
                  </DialogHeader>

                  <QuoteForm
                    initial={{
                      ...emptyQuote,
                      currency:
                        tenant?.currency ||
                        "USD",
                    }}
                    clients={clients}
                    onSave={
                      saveQuote
                    }
                  />
                </DialogContent>
              </Dialog>
            </div>

            <Card className="border-border/70">
              <div className="grid grid-cols-12 px-6 py-3 border-b border-border n-overline">
                <div className="col-span-2">
                  {t("number")}
                </div>

                <div className="col-span-3">
                  {t("client")}
                </div>

                <div className="col-span-2">
                  {t("status")}
                </div>

                <div className="col-span-2 text-right">
                  {t("total")}
                </div>

                <div className="col-span-3 text-right">
                  {t("actions")}
                </div>
              </div>

              {quotes.length === 0 && (
                <div className="p-8 text-center text-sm text-muted-foreground">
                  {t("noQuotesYet")}
                </div>
              )}

              {quotes.map((q) => (
                <div
                  key={q.id}
                  className="grid grid-cols-12 px-6 py-4 border-b border-border/60 last:border-0 items-center text-sm"
                  data-testid={`quote-row-${q.id}`}
                >
                  <div className="col-span-2 font-medium">
                    {q.number}
                  </div>

                  <div className="col-span-3">
                    {q.client_name ||
                      "—"}
                  </div>

                  <div className="col-span-2">
                    <Badge
                      variant={
                        q.status ===
                          "accepted" ||
                        q.status ===
                          "converted"
                          ? "default"
                          : "outline"
                      }
                    >
                      {t(
                        `quoteStatus_${q.status}`
                      )}
                    </Badge>
                  </div>

                  <div className="col-span-2 text-right font-semibold">
                    {formatCurrency(
                      q.totals?.total,
                      q.currency
                    )}
                  </div>

                  <div className="col-span-3 text-right flex items-center justify-end gap-1">
                    {q.status !==
                      "converted" &&
                      q.status !==
                        "accepted" &&
                      q.status !==
                        "rejected" && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() =>
                            shareQuote(
                              q.id
                            )
                          }
                          data-testid={`share-quote-${q.id}`}
                        >
                          <Send className="h-3 w-3 mr-1" />
                          {t("share")}
                        </Button>
                      )}

                    {q.share_token &&
                      q.status !==
                        "converted" && (
                        <Button
                          variant="ghost"
                          size="icon"
                          title={t(
                            "copyLink"
                          )}
                          onClick={async () => {
                            const url = `${window.location.origin}/public/quote/${q.share_token}`;

                            await navigator.clipboard.writeText(
                              url
                            );

                            toast.success(
                              t(
                                "linkCopied"
                              )
                            );
                          }}
                          data-testid={`copy-quote-${q.id}`}
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      )}

                    {q.status ===
                      "accepted" && (
                      <Button
                        size="sm"
                        onClick={() =>
                          convertQuote(
                            q.id
                          )
                        }
                        data-testid={`convert-quote-${q.id}`}
                      >
                        <Wand2 className="h-3 w-3 mr-1" />
                        {t("convert")}
                      </Button>
                    )}

                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() =>
                        deleteQuote(
                          q.id
                        )
                      }
                      data-testid={`delete-quote-${q.id}`}
                      title={t(
                        "delete"
                      )}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </Card>
          </TabsContent>

          {/* ============================= */}
          {/* EXPENSES */}
          {/* ============================= */}

          <TabsContent
            value="expenses"
            className="mt-6"
          >
            <div className="flex justify-end mb-3">
              <Dialog
                open={openExp}
                onOpenChange={
                  setOpenExp
                }
              >
                <DialogTrigger asChild>
                  <Button
                    data-testid="new-expense-btn"
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    {t("newExpense")}
                  </Button>
                </DialogTrigger>

                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>
                      {t("newExpense")}
                    </DialogTitle>
                  </DialogHeader>

                  <form
                    onSubmit={
                      saveExpense
                    }
                    className="space-y-3"
                  >
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5 col-span-2">
                        <Label>
                          {t("vendor")}
                        </Label>

                        <Input
                          value={
                            expenseForm.vendor
                          }
                          onChange={(e) =>
                            setExpenseForm({
                              ...expenseForm,
                              vendor:
                                e.target
                                  .value,
                            })
                          }
                        />
                      </div>

                      <div className="space-y-1.5">
                        <Label>
                          {t("category")}
                        </Label>

                        <Input
                          value={
                            expenseForm.category
                          }
                          onChange={(e) =>
                            setExpenseForm({
                              ...expenseForm,
                              category:
                                e.target
                                  .value,
                            })
                          }
                        />
                      </div>

                      <div className="space-y-1.5">
                        <Label>
                          {t("date")}
                        </Label>

                        <Input
                          type="date"
                          value={
                            expenseForm.date
                          }
                          onChange={(e) =>
                            setExpenseForm({
                              ...expenseForm,
                              date: e.target
                                .value,
                            })
                          }
                        />
                      </div>

                      <div className="space-y-1.5">
                        <Label>
                          {t("amount")}
                        </Label>

                        <Input
                          type="number"
                          value={
                            expenseForm.amount
                          }
                          onChange={(e) =>
                            setExpenseForm({
                              ...expenseForm,
                              amount:
                                e.target
                                  .value,
                            })
                          }
                          required
                        />
                      </div>

                      <div className="space-y-1.5">
                        <Label>
                          {t(
                            "taxPercent"
                          )}
                        </Label>

                        <Input
                          type="number"
                          value={
                            expenseForm.tax_rate
                          }
                          onChange={(e) =>
                            setExpenseForm({
                              ...expenseForm,
                              tax_rate:
                                e.target
                                  .value,
                            })
                          }
                        />
                      </div>

                      <div className="space-y-1.5 col-span-2">
                        <Label>
                          {t(
                            "description"
                          )}
                        </Label>

                        <Input
                          value={
                            expenseForm.description
                          }
                          onChange={(e) =>
                            setExpenseForm({
                              ...expenseForm,
                              description:
                                e.target
                                  .value,
                            })
                          }
                        />
                      </div>
                    </div>

                    <DialogFooter>
                      <Button
                        type="submit"
                        data-testid="expense-save-btn"
                      >
                        {t(
                          "saveExpense"
                        )}
                      </Button>
                    </DialogFooter>
                  </form>
                </DialogContent>
              </Dialog>
            </div>

            <Card className="border-border/70">
              {expenses.length === 0 && (
                <div className="p-8 text-center text-sm text-muted-foreground">
                  {t(
                    "noExpensesYet"
                  )}
                </div>
              )}

              {expenses.map(
                (expense) => (
                  <div
                    key={expense.id}
                    className="flex items-center justify-between px-6 py-3 border-b border-border/60 last:border-0 text-sm"
                  >
                    <div>
                      <div className="font-medium">
                        {expense.vendor ||
                          expense.description ||
                          t("expense")}
                      </div>

                      <div className="text-xs text-muted-foreground">
                        {expense.category} ·{" "}
                        {formatDate(
                          expense.date
                        )}
                      </div>
                    </div>

                    <div className="font-semibold">
                      {formatCurrency(
                        expense.amount *
                          (1 +
                            (expense.tax_rate ||
                              0) /
                              100),
                        expense.currency
                      )}
                    </div>
                  </div>
                )
              )}
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </>
  );
}