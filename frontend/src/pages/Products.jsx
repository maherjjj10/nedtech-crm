import { useEffect, useState } from "react";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { api } from "../lib/apiClient";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { formatCurrency } from "../lib/format";
import { useLanguage } from "../i18n";

const EMPTY = {
  name: "",
  kind: "product",
  sku: "",
  category: "",
  price: 0,
  cost: 0,
  currency: "USD",
  tax_rate: 0,
  description: "",
  active: true,
};

export default function Products() {
  const { t } = useLanguage();

  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);

  const load = async () => {
    const { data } = await api.get("/products");
    setItems(data);
  };

  useEffect(() => {
    load();
  }, []);

  const save = async (e) => {
    e.preventDefault();

    try {
      await api.post("/products", {
        ...form,
        price: Number(form.price),
        cost: Number(form.cost),
        tax_rate: Number(form.tax_rate),
      });

      toast.success(t("productSaved"));
      setOpen(false);
      setForm(EMPTY);
      load();
    } catch {
      toast.error(t("failed"));
    }
  };

  const remove = async (id) => {
    await api.delete(`/products/${id}`);
    load();
  };

  return (
    <>
      <PageHeader
        title={t("productsServices")}
        description={t("productsDescription")}
        right={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button data-testid="new-product-btn">
                <Plus className="h-4 w-4 mr-1" />
                {t("newItem")}
              </Button>
            </DialogTrigger>

            <DialogContent>
              <DialogHeader>
                <DialogTitle>
                  {t("newProductService")}
                </DialogTitle>
              </DialogHeader>

              <form
                onSubmit={save}
                className="space-y-3"
              >
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5 col-span-2">
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
                      data-testid="product-name-input"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label>{t("type")}</Label>

                    <Select
                      value={form.kind}
                      onValueChange={(v) =>
                        setForm({
                          ...form,
                          kind: v,
                        })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>

                      <SelectContent>
                        <SelectItem value="product">
                          {t("product")}
                        </SelectItem>

                        <SelectItem value="service">
                          {t("service")}
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-1.5">
                    <Label>{t("category")}</Label>

                    <Input
                      value={form.category}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          category: e.target.value,
                        })
                      }
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label>{t("sku")}</Label>

                    <Input
                      value={form.sku}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          sku: e.target.value,
                        })
                      }
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label>{t("price")}</Label>

                    <Input
                      type="number"
                      value={form.price}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          price: e.target.value,
                        })
                      }
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label>{t("cost")}</Label>

                    <Input
                      type="number"
                      value={form.cost}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          cost: e.target.value,
                        })
                      }
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label>{t("taxPercent")}</Label>

                    <Input
                      type="number"
                      value={form.tax_rate}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          tax_rate: e.target.value,
                        })
                      }
                    />
                  </div>
                </div>

                <DialogFooter>
                  <Button
                    type="submit"
                    data-testid="product-save-btn"
                  >
                    {t("save")}
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        }
      />

      <div className="p-8">
        <Card className="border-border/70">
          <div className="grid grid-cols-12 px-6 py-3 border-b border-border n-overline">
            <div className="col-span-5">
              {t("name")}
            </div>

            <div className="col-span-2">
              {t("type")}
            </div>

            <div className="col-span-2">
              {t("category")}
            </div>

            <div className="col-span-2 text-right">
              {t("price")}
            </div>

            <div className="col-span-1" />
          </div>

          {items.length === 0 && (
            <div className="p-8 text-center text-sm text-muted-foreground">
              {t("noProductsYet")}
            </div>
          )}

          {items.map((p) => (
            <div
              key={p.id}
              className="grid grid-cols-12 px-6 py-4 border-b border-border/60 last:border-0 items-center text-sm"
            >
              <div className="col-span-5">
                <div className="font-medium">
                  {p.name}
                </div>

                <div className="text-xs text-muted-foreground">
                  {p.sku || "—"}
                </div>
              </div>

              <div className="col-span-2">
                <Badge variant="outline">
                  {p.kind === "product"
                    ? t("product")
                    : t("service")}
                </Badge>
              </div>

              <div className="col-span-2 text-muted-foreground">
                {p.category || "—"}
              </div>

              <div className="col-span-2 text-right font-semibold">
                {formatCurrency(
                  p.price,
                  p.currency
                )}
              </div>

              <div className="col-span-1 text-right">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => remove(p.id)}
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