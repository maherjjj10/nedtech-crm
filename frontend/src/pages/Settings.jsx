import { useEffect, useState } from "react";
import PageHeader from "../components/layout/PageHeader";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card } from "../components/ui/card";
import { Label } from "../components/ui/label";
import { Switch } from "../components/ui/switch";
import { Badge } from "../components/ui/badge";
import { api } from "../lib/apiClient";
import { toast } from "sonner";
import { useAuth } from "../lib/authContext";
import {
  Calendar as CalendarIcon,
  Check,
  Link as LinkIcon,
} from "lucide-react";
import { useLanguage } from "../i18n";

export default function Settings() {
  const { tenant, refresh } = useAuth();
  const { t } = useLanguage();

  const [form, setForm] = useState({
    name: "",
    currency: "USD",
    vat_rate: 0,
    locale: "en",
    address: "",
    phone: "",
    website: "",
    iban: "",
    kvk_number: "",
    vat_number: "",
  });

  const [modules, setModules] = useState({});
  const [calendar, setCalendar] = useState(null);

  const MODULE_LABELS = {
    crm: t("moduleCrm"),
    sales: t("moduleSales"),
    tasks: t("moduleTasks"),
    finance: t("moduleFinance"),
    products: t("moduleProducts"),
    hr: t("moduleHr"),
    files: t("moduleFiles"),
    calendar: t("moduleCalendar"),
    reports: t("moduleReports"),
    ai: t("moduleAi"),
    inventory: t("moduleInventory"),
    pos: t("modulePos"),
    orders: t("moduleOrders"),
    marketing: t("moduleMarketing"),
    website: t("moduleWebsite"),
    portal: t("modulePortal"),
    accounting: t("moduleAccounting"),
    payroll: t("modulePayroll"),
  };

  useEffect(() => {
    if (tenant) {
      setForm({
        name: tenant.name || "",
        currency: tenant.currency || "USD",
        vat_rate: tenant.vat_rate || 0,
        locale: tenant.locale || "en",
        address: tenant.address || "",
        phone: tenant.phone || "",
        website: tenant.website || "",
        iban: tenant.iban || "",
        kvk_number: tenant.kvk_number || "",
        vat_number: tenant.vat_number || "",
      });

      setModules(tenant.modules || {});
    }

    api
      .get("/calendar/status")
      .then((r) => setCalendar(r.data))
      .catch(() => {});
  }, [tenant]);

  const updateField = (field, value) => {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const connectCalendar = async () => {
    try {
      const { data } = await api.get("/calendar/connect");
      window.location.href = data.authorize_url;
    } catch (err) {
      toast.error(
        err?.response?.data?.detail ||
          t("googleCredentialsRequired")
      );
    }
  };

  const save = async (e) => {
    e.preventDefault();

    try {
      await api.patch("/tenants/me", {
        ...form,
        vat_rate: Number(form.vat_rate),
      });

      toast.success(t("settingsSaved"));
      refresh();
    } catch (err) {
      toast.error(
        err?.response?.data?.detail ||
          t("failed")
      );
    }
  };

  const toggle = async (mod, enabled) => {
    setModules((m) => ({
      ...m,
      [mod]: enabled,
    }));

    try {
      await api.post("/tenants/me/modules", {
        module: mod,
        enabled,
      });

      toast.success(
        `${MODULE_LABELS[mod]} ${
          enabled ? t("enabled") : t("disabled")
        }`
      );

      refresh();
    } catch {
      toast.error(t("failed"));
    }
  };

  return (
    <>
      <PageHeader
        title={t("settings")}
        description={t("settingsDescription")}
      />

      <div className="p-8 grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Company */}
        <Card className="p-6 border-border/70">
          <h3 className="text-lg font-semibold mb-4">
            {t("company")}
          </h3>

          <form
            onSubmit={save}
            className="space-y-3"
          >
            <div className="grid grid-cols-2 gap-3">

              {/* Company Name */}
              <div className="space-y-1.5 col-span-2">
                <Label>{t("companyName")}</Label>

                <Input
                  value={form.name}
                  onChange={(e) =>
                    updateField("name", e.target.value)
                  }
                  data-testid="tenant-name-input"
                />
              </div>

              {/* Currency */}
              <div className="space-y-1.5">
                <Label>{t("currency")}</Label>

                <Input
                  value={form.currency}
                  onChange={(e) =>
                    updateField("currency", e.target.value)
                  }
                />
              </div>

              {/* VAT Rate */}
              <div className="space-y-1.5">
                <Label>{t("vatTaxPercent")}</Label>

                <Input
                  type="number"
                  value={form.vat_rate}
                  onChange={(e) =>
                    updateField("vat_rate", e.target.value)
                  }
                />
              </div>

              {/* Website */}
              <div className="space-y-1.5">
                <Label>{t("website")}</Label>

                <Input
                  value={form.website}
                  onChange={(e) =>
                    updateField("website", e.target.value)
                  }
                />
              </div>

              {/* Phone */}
              <div className="space-y-1.5">
                <Label>{t("phone")}</Label>

                <Input
                  value={form.phone}
                  onChange={(e) =>
                    updateField("phone", e.target.value)
                  }
                />
              </div>

              {/* Address */}
              <div className="space-y-1.5 col-span-2">
                <Label>{t("address")}</Label>

                <Input
                  value={form.address}
                  onChange={(e) =>
                    updateField("address", e.target.value)
                  }
                />
              </div>

              {/* IBAN */}
              <div className="space-y-1.5">
                <Label>IBAN</Label>

                <Input
                  value={form.iban}
                  onChange={(e) =>
                    updateField("iban", e.target.value)
                  }
                  placeholder="NL00 BANK 0000 0000 00"
                  autoComplete="off"
                />
              </div>

              {/* KVK */}
              <div className="space-y-1.5">
                <Label>KVK-nummer</Label>

                <Input
                  value={form.kvk_number}
                  onChange={(e) =>
                    updateField(
                      "kvk_number",
                      e.target.value
                    )
                  }
                  placeholder="12345678"
                  autoComplete="off"
                />
              </div>

              {/* VAT / BTW Number */}
              <div className="space-y-1.5 col-span-2">
                <Label>BTW-nummer</Label>

                <Input
                  value={form.vat_number}
                  onChange={(e) =>
                    updateField(
                      "vat_number",
                      e.target.value
                    )
                  }
                  placeholder="NL123456789B01"
                  autoComplete="off"
                />
              </div>
            </div>

            <Button
              type="submit"
              data-testid="save-settings-btn"
            >
              {t("saveChanges")}
            </Button>
          </form>
        </Card>

        {/* Google Calendar */}
        <Card className="p-6 border-border/70 lg:col-span-2">
          <div className="flex items-center gap-2 mb-1">
            <CalendarIcon className="h-4 w-4" />

            <h3 className="text-lg font-semibold">
              {t("googleCalendarSync")}
            </h3>

            {calendar?.connected && (
              <Badge className="ml-1">
                <Check className="h-3 w-3 mr-1" />
                {t("connected")}
              </Badge>
            )}
          </div>

          <p className="text-xs text-muted-foreground mb-4">
            {calendar?.configured
              ? t("calendarConfiguredDescription")
              : t("calendarNotConfiguredDescription")}
          </p>

          <Button
            onClick={connectCalendar}
            disabled={!calendar?.configured}
            data-testid="connect-calendar-btn"
          >
            <LinkIcon className="h-4 w-4 mr-1" />

            {calendar?.connected
              ? t("reconnectGoogleCalendar")
              : t("connectGoogleCalendar")}
          </Button>
        </Card>

        {/* Modules */}
        <Card className="p-6 border-border/70">
          <h3 className="text-lg font-semibold mb-1">
            {t("modules")}
          </h3>

          <p className="text-xs text-muted-foreground mb-4">
            {t("modulesDescription")}
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {Object.entries(MODULE_LABELS).map(
              ([code, label]) => (
                <div
                  key={code}
                  className="flex items-center justify-between px-3 py-2 rounded-md border border-border/60"
                >
                  <span className="text-sm">
                    {label}
                  </span>

                  <Switch
                    checked={!!modules[code]}
                    onCheckedChange={(v) =>
                      toggle(code, v)
                    }
                    data-testid={`module-toggle-${code}`}
                  />
                </div>
              )
            )}
          </div>
        </Card>
      </div>
    </>
  );
}