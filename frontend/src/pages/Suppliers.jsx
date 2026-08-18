import { useCallback, useEffect, useState } from "react";

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

import {
  Plus,
  Search,
  Trash2,
  Pencil,
  Eye,
} from "lucide-react";

import { toast } from "sonner";
import { useLanguage } from "../i18n";


const EMPTY = {
  name: "",
  company: "",
  contact_person: "",
  email: "",
  phone: "",
  vat_number: "",
  kvk_number: "",
  address: "",
  postal_code: "",
  city: "",
  country: "Netherlands",
  iban: "",
  website: "",
  status: "active",
  notes: "",
};


export default function Suppliers() {
  const { t } = useLanguage();

  const [suppliers, setSuppliers] = useState([]);
  const [q, setQ] = useState("");

  const [open, setOpen] = useState(false);
  const [viewOpen, setViewOpen] = useState(false);

  const [editing, setEditing] = useState(null);
  const [viewing, setViewing] = useState(null);

  const [form, setForm] = useState(EMPTY);


  const load = useCallback(async (search = "") => {
    try {
      const { data } = await api.get("/suppliers", {
        params: search ? { q: search } : {},
      });

      setSuppliers(data || []);
    } catch (err) {
      toast.error(
        err?.response?.data?.detail ||
        t("supplierLoadFailed")
      );
    }
  }, [t]);


  useEffect(() => {
    load();
  }, [load]);


  const openNew = () => {
    setEditing(null);
    setForm({ ...EMPTY });
    setOpen(true);
  };


  const openEdit = (supplier) => {
    setEditing(supplier);

    setForm({
      ...EMPTY,
      ...supplier,
    });

    setOpen(true);
  };


  const openView = (supplier) => {
    setViewing(supplier);
    setViewOpen(true);
  };


  const save = async (e) => {
    e.preventDefault();

    try {
      const payload = {
        name: form.name,
        company: form.company || null,
        contact_person: form.contact_person || null,
        email: form.email || null,
        phone: form.phone || null,
        vat_number: form.vat_number || null,
        kvk_number: form.kvk_number || null,
        address: form.address || null,
        postal_code: form.postal_code || null,
        city: form.city || null,
        country: form.country || "Netherlands",
        iban: form.iban || null,
        website: form.website || null,
        status: form.status || "active",
        notes: form.notes || null,
      };


      if (editing) {
        await api.patch(
          `/suppliers/${editing.id}`,
          payload
        );

        toast.success(
          t("supplierUpdated")
        );
      } else {
        await api.post(
          "/suppliers",
          payload
        );

        toast.success(
          t("supplierCreated")
        );
      }


      setOpen(false);
      setEditing(null);
      setForm({ ...EMPTY });

      await load(q);

    } catch (err) {
      toast.error(
        err?.response?.data?.detail ||
        t("supplierSaveFailed")
      );
    }
  };


  const remove = async (id) => {
    if (!window.confirm(t("supplierDeleteConfirm"))) {
      return;
    }

    try {
      await api.delete(`/suppliers/${id}`);

      toast.success(
        t("supplierDeleted")
      );

      await load(q);

    } catch (err) {
      toast.error(
        err?.response?.data?.detail ||
        t("supplierDeleteFailed")
      );
    }
  };


  const updateField = (field, value) => {
    setForm((prev) => ({
      ...prev,
      [field]: value,
    }));
  };


  const ViewField = ({ label, value }) => (
    <div className="space-y-1">
      <div className="text-xs font-medium text-muted-foreground">
        {label}
      </div>

      <div className="text-sm min-h-[20px]">
        {value || "—"}
      </div>
    </div>
  );


  return (
    <>
      <PageHeader
        title={t("suppliers")}
        description={t("suppliersDescription")}
        right={
          <Dialog
            open={open}
            onOpenChange={setOpen}
          >

            <DialogTrigger asChild>
              <Button onClick={openNew}>
                <Plus className="h-4 w-4 mr-2" />
                {t("newSupplier")}
              </Button>
            </DialogTrigger>


            <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">

              <DialogHeader>
                <DialogTitle>
                  {editing
                    ? t("editSupplier")
                    : t("newSupplier")}
                </DialogTitle>
              </DialogHeader>


              <form
                onSubmit={save}
                className="space-y-4"
              >

                <div className="space-y-2">
                  <Label>{t("supplierName")}</Label>

                  <Input
                    value={form.name}
                    onChange={(e) =>
                      updateField(
                        "name",
                        e.target.value
                      )
                    }
                    required
                  />
                </div>


                <div className="space-y-2">
                  <Label>{t("company")}</Label>

                  <Input
                    value={form.company}
                    onChange={(e) =>
                      updateField(
                        "company",
                        e.target.value
                      )
                    }
                  />
                </div>


                <div className="space-y-2">
                  <Label>{t("contactPerson")}</Label>

                  <Input
                    value={form.contact_person}
                    onChange={(e) =>
                      updateField(
                        "contact_person",
                        e.target.value
                      )
                    }
                  />
                </div>


                <div className="space-y-2">
                  <Label>{t("email")}</Label>

                  <Input
                    type="email"
                    value={form.email}
                    onChange={(e) =>
                      updateField(
                        "email",
                        e.target.value
                      )
                    }
                  />
                </div>


                <div className="space-y-2">
                  <Label>{t("phone")}</Label>

                  <Input
                    value={form.phone}
                    onChange={(e) =>
                      updateField(
                        "phone",
                        e.target.value
                      )
                    }
                  />
                </div>


                <div className="space-y-2">
                  <Label>{t("vatNumber")}</Label>

                  <Input
                    value={form.vat_number}
                    onChange={(e) =>
                      updateField(
                        "vat_number",
                        e.target.value
                      )
                    }
                  />
                </div>


                <div className="space-y-2">
                  <Label>{t("kvkNumber")}</Label>

                  <Input
                    value={form.kvk_number}
                    onChange={(e) =>
                      updateField(
                        "kvk_number",
                        e.target.value
                      )
                    }
                  />
                </div>


                <div className="space-y-2">
                  <Label>{t("address")}</Label>

                  <Input
                    value={form.address}
                    onChange={(e) =>
                      updateField(
                        "address",
                        e.target.value
                      )
                    }
                  />
                </div>


                <div className="space-y-2">
                  <Label>{t("postalCode")}</Label>

                  <Input
                    value={form.postal_code}
                    onChange={(e) =>
                      updateField(
                        "postal_code",
                        e.target.value
                      )
                    }
                  />
                </div>


                <div className="space-y-2">
                  <Label>{t("city")}</Label>

                  <Input
                    value={form.city}
                    onChange={(e) =>
                      updateField(
                        "city",
                        e.target.value
                      )
                    }
                  />
                </div>


                <div className="space-y-2">
                  <Label>{t("country")}</Label>

                  <Input
                    value={form.country}
                    onChange={(e) =>
                      updateField(
                        "country",
                        e.target.value
                      )
                    }
                  />
                </div>


                <div className="space-y-2">
                  <Label>{t("iban")}</Label>

                  <Input
                    value={form.iban}
                    onChange={(e) =>
                      updateField(
                        "iban",
                        e.target.value
                      )
                    }
                  />
                </div>


                <div className="space-y-2">
                  <Label>{t("website")}</Label>

                  <Input
                    value={form.website}
                    onChange={(e) =>
                      updateField(
                        "website",
                        e.target.value
                      )
                    }
                  />
                </div>


                <div className="space-y-2">
                  <Label>{t("status")}</Label>

                  <select
                    value={form.status}
                    onChange={(e) =>
                      updateField(
                        "status",
                        e.target.value
                      )
                    }
                    className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
                  >
                    <option value="active">
                      {t("active")}
                    </option>

                    <option value="inactive">
                      {t("inactive")}
                    </option>
                  </select>
                </div>


                <div className="space-y-2">
                  <Label>{t("notes")}</Label>

                  <Textarea
                    value={form.notes}
                    onChange={(e) =>
                      updateField(
                        "notes",
                        e.target.value
                      )
                    }
                  />
                </div>


                <DialogFooter>
                  <Button type="submit">
                    {editing
                      ? t("updateSupplier")
                      : t("createSupplier")}
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
            placeholder={t("searchSuppliers")}
            value={q}
            onChange={(e) =>
              setQ(e.target.value)
            }
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                load(q);
              }
            }}
            className="pl-9"
          />

        </div>


        {/* Supplier table */}
        <Card className="border-border/70 overflow-hidden">

          <div className="grid grid-cols-12 px-6 py-3 border-b border-border n-overline">

            <div className="col-span-3">
              {t("supplierName")}
            </div>

            <div className="col-span-3">
              {t("company")}
            </div>

            <div className="col-span-2">
              {t("contact")}
            </div>

            <div className="col-span-2">
              {t("vatKvk")}
            </div>

            <div className="col-span-1">
              {t("status")}
            </div>

            <div className="col-span-1 text-right">
              {t("actions")}
            </div>

          </div>


          {suppliers.length === 0 && (
            <div className="p-8 text-center text-sm text-muted-foreground">
              {t("noSuppliers")}
            </div>
          )}


          {suppliers.map((supplier) => (
            <div
              key={supplier.id}
              className="grid grid-cols-12 px-6 py-4 border-b border-border/60 last:border-0 items-center text-sm"
            >

              <div className="col-span-3">
                <div className="font-medium">
                  {supplier.name}
                </div>

                {supplier.contact_person && (
                  <div className="text-xs text-muted-foreground mt-1">
                    {supplier.contact_person}
                  </div>
                )}
              </div>


              <div className="col-span-3 text-muted-foreground">
                {supplier.company || "—"}
              </div>


              <div className="col-span-2 text-muted-foreground">
                {supplier.email ||
                  supplier.phone ||
                  "—"}
              </div>


              <div className="col-span-2 text-muted-foreground">

                {supplier.vat_number ||
                supplier.kvk_number ? (
                  <>
                    {supplier.vat_number && (
                      <div>
                        {t("vatShort")}:{" "}
                        {supplier.vat_number}
                      </div>
                    )}

                    {supplier.kvk_number && (
                      <div>
                        {t("kvkShort")}:{" "}
                        {supplier.kvk_number}
                      </div>
                    )}
                  </>
                ) : (
                  "—"
                )}

              </div>


              <div className="col-span-1">

                <Badge
                  variant={
                    supplier.status === "active"
                      ? "default"
                      : "outline"
                  }
                >
                  {supplier.status === "active"
                    ? t("active")
                    : t("inactive")}
                </Badge>

              </div>


              {/* ACTIONS */}
              <div className="col-span-1 flex gap-1 justify-end">

                {/* VIEW */}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() =>
                    openView(supplier)
                  }
                  title={t("view")}
                  data-testid={`view-supplier-${supplier.id}`}
                >
                  <Eye className="h-4 w-4" />
                </Button>


                {/* EDIT */}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() =>
                    openEdit(supplier)
                  }
                  title={t("edit")}
                  data-testid={`edit-supplier-${supplier.id}`}
                >
                  <Pencil className="h-4 w-4" />
                </Button>


                {/* DELETE */}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() =>
                    remove(supplier.id)
                  }
                  title={t("delete")}
                  data-testid={`delete-supplier-${supplier.id}`}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>

              </div>

            </div>
          ))}

        </Card>

      </div>


      {/* =========================================
          VIEW SUPPLIER
      ========================================= */}

      <Dialog
        open={viewOpen}
        onOpenChange={setViewOpen}
      >

        <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">

          <DialogHeader>
            <DialogTitle>
              {t("supplierDetails")}
            </DialogTitle>
          </DialogHeader>


          {viewing && (
            <div className="space-y-6">

              {/* Supplier header */}
              <div className="rounded-lg border border-border p-4 bg-muted/20">

                <div className="flex items-start justify-between gap-4">

                  <div>

                    <h2 className="text-lg font-semibold">
                      {viewing.name}
                    </h2>

                    {viewing.company && (
                      <p className="text-sm text-muted-foreground mt-1">
                        {viewing.company}
                      </p>
                    )}

                  </div>


                  <Badge
                    variant={
                      viewing.status === "active"
                        ? "default"
                        : "outline"
                    }
                  >
                    {viewing.status === "active"
                      ? t("active")
                      : t("inactive")}
                  </Badge>

                </div>

              </div>


              {/* General information */}
              <div className="space-y-3">

                <h3 className="text-sm font-semibold">
                  {t("generalInformation")}
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

                  <ViewField
                    label={t("supplierName")}
                    value={viewing.name}
                  />

                  <ViewField
                    label={t("company")}
                    value={viewing.company}
                  />

                  <ViewField
                    label={t("contactPerson")}
                    value={viewing.contact_person}
                  />

                  <ViewField
                    label={t("email")}
                    value={viewing.email}
                  />

                  <ViewField
                    label={t("phone")}
                    value={viewing.phone}
                  />

                  <ViewField
                    label={t("website")}
                    value={viewing.website}
                  />

                </div>

              </div>


              {/* Business information */}
              <div className="space-y-3">

                <h3 className="text-sm font-semibold">
                  {t("businessInformation")}
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

                  <ViewField
                    label={t("vatNumber")}
                    value={viewing.vat_number}
                  />

                  <ViewField
                    label={t("kvkNumber")}
                    value={viewing.kvk_number}
                  />

                </div>

              </div>


              {/* Address */}
              <div className="space-y-3">

                <h3 className="text-sm font-semibold">
                  {t("addressInformation")}
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

                  <ViewField
                    label={t("address")}
                    value={viewing.address}
                  />

                  <ViewField
                    label={t("postalCode")}
                    value={viewing.postal_code}
                  />

                  <ViewField
                    label={t("city")}
                    value={viewing.city}
                  />

                  <ViewField
                    label={t("country")}
                    value={viewing.country}
                  />

                </div>

              </div>


              {/* Banking */}
              <div className="space-y-3">

                <h3 className="text-sm font-semibold">
                  {t("bankingInformation")}
                </h3>

                <ViewField
                  label={t("iban")}
                  value={viewing.iban}
                />

              </div>


              {/* Notes */}
              <div className="space-y-3">

                <h3 className="text-sm font-semibold">
                  {t("notes")}
                </h3>

                <div className="rounded-md border border-border p-4 text-sm whitespace-pre-wrap">
                  {viewing.notes || "—"}
                </div>

              </div>


              {/* Footer */}
              <DialogFooter>

                <Button
                  variant="outline"
                  onClick={() => {
                    setViewOpen(false);
                    openEdit(viewing);
                  }}
                >
                  <Pencil className="h-4 w-4 mr-2" />
                  {t("edit")}
                </Button>


                <Button
                  onClick={() =>
                    setViewOpen(false)
                  }
                >
                  {t("close")}
                </Button>

              </DialogFooter>

            </div>
          )}

        </DialogContent>

      </Dialog>

    </>
  );
}