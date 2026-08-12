import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import PageHeader from "../components/layout/PageHeader";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "../components/ui/dialog";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { api } from "../lib/apiClient";
import { Plus, Search, Trash2, Pencil } from "lucide-react";
import { toast } from "sonner";
import { useLanguage } from "../i18n";

const EMPTY = {
  name: "",
  email: "",
  phone: "",
  company: "",
  contact_person: "",
  vat_number: "",
  address: "",
  website: "",
  tags: [],
  status: "active",
  notes: "",
};

export default function Clients() {
  const { t } = useLanguage();

  const [clients, setClients] = useState([]);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);

  const load = useCallback(async (search = "") => {
    const { data } = await api.get("/clients", {
      params: search ? { q: search } : {},
    });

    setClients(data);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const openNew = () => {
    setEditing(null);
    setForm(EMPTY);
    setOpen(true);
  };

  const openEdit = (c) => {
    setEditing(c);
    setForm({
      ...EMPTY,
      ...c,
      tags: c.tags || [],
    });
    setOpen(true);
  };

  const save = async (e) => {
    e.preventDefault();

    try {
      const payload = {
        ...form,
        tags: Array.isArray(form.tags)
          ? form.tags
          : String(form.tags || "")
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean),
      };

      if (editing) {
        await api.patch(`/clients/${editing.id}`, payload);
      } else {
        await api.post("/clients", payload);
      }

      toast.success(
        editing ? t("clientUpdated") : t("clientCreated")
      );

      setOpen(false);
      load(q);
    } catch (err) {
      toast.error(
        err?.response?.data?.detail || t("saveFailed")
      );
    }
  };

  const remove = async (id) => {
    if (!window.confirm(t("deleteClientConfirm"))) return;

    try {
      await api.delete(`/clients/${id}`);

      toast.success(t("deleted"));
      load(q);
    } catch (err) {
      toast.error(
        err?.response?.data?.detail || t("deleteFailed")
      );
    }
  };

  return (
    <>
      <PageHeader
        title={t("clients")}
        description={t("clientsDescription")}
        right={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button onClick={openNew}>
                <Plus className="h-4 w-4 mr-2" />
                {t("newClient")}
              </Button>
            </DialogTrigger>

            <DialogContent className="sm:max-w-[600px]">
              <DialogHeader>
                <DialogTitle>
                  {editing ? t("editClient") : t("newClient")}
                </DialogTitle>
              </DialogHeader>

              <form onSubmit={save} className="space-y-4">

                <div className="space-y-2">
                  <Label>{t("name")}</Label>
                  <Input
                    value={form.name}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        name: e.target.value,
                      })
                    }
                    required
                    data-testid="client-name-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label>{t("email")}</Label>
                  <Input
                    type="email"
                    value={form.email || ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        email: e.target.value,
                      })
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label>{t("phone")}</Label>
                  <Input
                    value={form.phone || ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        phone: e.target.value,
                      })
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label>{t("company")}</Label>
                  <Input
                    value={form.company || ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        company: e.target.value,
                      })
                    }
                    data-testid="client-company-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label>{t("contactPerson")}</Label>
                  <Input
                    value={form.contact_person || ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        contact_person: e.target.value,
                      })
                    }
                    data-testid="client-contact-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label>{t("vatNumber")}</Label>
                  <Input
                    value={form.vat_number || ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        vat_number: e.target.value,
                      })
                    }
                    data-testid="client-vat-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label>{t("website")}</Label>
                  <Input
                    value={form.website || ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        website: e.target.value,
                      })
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label>{t("address")}</Label>
                  <Input
                    value={form.address || ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        address: e.target.value,
                      })
                    }
                    data-testid="client-address-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label>{t("tagsCommaSeparated")}</Label>
                  <Input
                    value={
                      Array.isArray(form.tags)
                        ? form.tags.join(", ")
                        : form.tags
                    }
                    onChange={(e) =>
                      setForm({
                        ...form,
                        tags: e.target.value,
                      })
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label>{t("notes")}</Label>
                  <Textarea
                    value={form.notes || ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        notes: e.target.value,
                      })
                    }
                  />
                </div>

                <DialogFooter>
                  <Button type="submit">
                    {editing ? t("update") : t("create")}
                  </Button>
                </DialogFooter>

              </form>
            </DialogContent>
          </Dialog>
        }
      />

      <div className="p-8 space-y-6">

        {/* Search */}
        <div className="relative max-w-md">
          <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />

          <Input
            placeholder={t("searchClients")}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) =>
              e.key === "Enter" && load(q)
            }
            className="pl-9"
            data-testid="clients-search-input"
          />
        </div>

        {/* Clients table */}
        <Card className="border-border/70 overflow-hidden">

          <div className="grid grid-cols-12 px-6 py-3 border-b border-border n-overline">
            <div className="col-span-4">{t("name")}</div>
            <div className="col-span-3">{t("company")}</div>
            <div className="col-span-3">{t("contact")}</div>
            <div className="col-span-1">{t("status")}</div>
            <div className="col-span-1 text-right">
              {t("actions")}
            </div>
          </div>

          {clients.length === 0 && (
            <div className="p-8 text-center text-sm text-muted-foreground">
              {t("noClientsYet")}
            </div>
          )}

          {clients.map((c) => (
            <div
              key={c.id}
              className="grid grid-cols-12 px-6 py-4 border-b border-border/60 last:border-0 items-center text-sm"
              data-testid={`client-row-${c.id}`}
            >
              <div className="col-span-4">
                <Link
                  to={`/clients/${c.id}`}
                  className="font-medium hover:underline"
                  data-testid={`client-link-${c.id}`}
                >
                  {c.name}
                </Link>

                <div className="flex gap-1 mt-1 flex-wrap">
                  {(c.tags || [])
                    .slice(0, 3)
                    .map((tag) => (
                      <Badge
                        key={tag}
                        variant="secondary"
                        className="text-[10px]"
                      >
                        {tag}
                      </Badge>
                    ))}
                </div>
              </div>

              <div className="col-span-3 text-muted-foreground">
                {c.company || "—"}
              </div>

              <div className="col-span-3 text-muted-foreground">
                {c.email || c.phone || "—"}
              </div>

              <div className="col-span-1">
                <Badge
                  variant={
                    c.status === "active"
                      ? "default"
                      : "outline"
                  }
                >
                  {c.status === "active"
                    ? t("active")
                    : t("inactive")}
                </Badge>
              </div>

              <div className="col-span-1 flex gap-1 justify-end">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => openEdit(c)}
                  data-testid={`edit-client-${c.id}`}
                  title={t("edit")}
                >
                  <Pencil className="h-4 w-4" />
                </Button>

                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => remove(c.id)}
                  data-testid={`delete-client-${c.id}`}
                  title={t("delete")}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}

        </Card>
      </div>
    </>
  );
}