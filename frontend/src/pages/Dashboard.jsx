import { useEffect, useState } from "react";
import { api } from "../lib/apiClient";
import PageHeader from "../components/layout/PageHeader";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Button } from "../components/ui/button";
import { formatCurrency, formatDate } from "../lib/format";
import { useAuth } from "../lib/authContext";
import { useLanguage } from "../i18n";

import {
  ArrowUpRight,
  DollarSign,
  Users,
  TrendingUp,
  Receipt,
  Plus,
  ArrowRight,
  Clock3,
  CheckCircle2,
  AlertCircle,
  FileText,
} from "lucide-react";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
  CartesianGrid,
} from "recharts";

import { useNavigate } from "react-router-dom";


function Kpi({
  label,
  value,
  icon: Icon,
  sub,
  testid,
}) {
  return (
    <Card
      className="
        group
        relative
        overflow-hidden
        border-border/70
        transition-all
        duration-200
        hover:-translate-y-0.5
        hover:shadow-md
      "
    >
      <CardContent className="p-5 sm:p-6">

        <div className="flex items-start justify-between gap-4">

          <div className="min-w-0">

            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {label}
            </p>

            <div
              className="mt-2 text-2xl sm:text-3xl font-bold tracking-tight truncate"
              data-testid={`${testid}-value`}
            >
              {value}
            </div>

            {sub && (
              <p className="mt-2 text-xs text-muted-foreground">
                {sub}
              </p>
            )}

          </div>

          <div
            className="
              flex
              h-10
              w-10
              shrink-0
              items-center
              justify-center
              rounded-xl
              border
              border-border
              bg-muted/60
              transition-transform
              duration-200
              group-hover:scale-105
            "
          >
            <Icon className="h-4 w-4" />
          </div>

        </div>

      </CardContent>
    </Card>
  );
}


function SectionHeader({
  title,
  description,
  action,
}) {
  return (
    <div className="flex items-center justify-between gap-4">

      <div>
        <h2 className="text-sm font-semibold">
          {title}
        </h2>

        {description && (
          <p className="mt-1 text-xs text-muted-foreground">
            {description}
          </p>
        )}
      </div>

      {action}

    </div>
  );
}


function ActivityIcon({ type }) {
  if (
    type === "invoice_paid" ||
    type === "payment_received"
  ) {
    return (
      <CheckCircle2 className="h-4 w-4" />
    );
  }

  if (
    type === "invoice_created" ||
    type === "quote_created"
  ) {
    return (
      <FileText className="h-4 w-4" />
    );
  }

  return (
    <Clock3 className="h-4 w-4" />
  );
}


export default function Dashboard() {
  const { tenant } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const currency =
    tenant?.currency || "EUR";


  useEffect(() => {
    let mounted = true;

    setLoading(true);

    api
      .get("/dashboard/overview")
      .then((response) => {
        if (mounted) {
          setData(response.data);
        }
      })
      .catch(() => {
        if (mounted) {
          setData(null);
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, []);


  const k = data?.kpis || {};
  const trend = data?.trend || [];
  const upcomingInvoices =
    data?.upcoming_invoices || [];
  const activity =
    data?.activity || [];


  return (
    <>
      <PageHeader
        title={`${t("welcomeBack")}${
          tenant?.name
            ? `, ${tenant.name}`
            : ""
        }`}
        description={t(
          "dashboardDescription"
        )}
        testid="dashboard-header"
      />


      <div className="p-5 sm:p-8 space-y-8">

        {/* =================================================
            KPI OVERVIEW
        ================================================= */}

        <section>

          <SectionHeader
            title={t("overview")}
            description={t("dashboardDescription")}
          />

          <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">

            <Kpi
              label={t("revenue")}
              value={formatCurrency(
                k.revenue || 0,
                currency
              )}
              icon={DollarSign}
              sub={t("paidInvoices")}
              testid="kpi-revenue"
            />

            <Kpi
              label={t("expenses")}
              value={formatCurrency(
                k.expenses || 0,
                currency
              )}
              icon={ArrowUpRight}
              sub={t("allTime")}
              testid="kpi-expenses"
            />

            <Kpi
              label={t("profit")}
              value={formatCurrency(
                k.profit || 0,
                currency
              )}
              icon={TrendingUp}
              sub={t(
                "revenueMinusExpenses"
              )}
              testid="kpi-profit"
            />

            <Kpi
              label={t("activeClients")}
              value={
                k.active_clients ?? 0
              }
              icon={Users}
              sub={`${k.open_tasks ?? 0} ${t(
                "openTasks"
              )}`}
              testid="kpi-clients"
            />

          </div>

        </section>


        {/* =================================================
            QUICK ACTIONS
        ================================================= */}

        <section>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">

            <Button
              variant="outline"
              className="h-auto justify-start gap-3 p-4"
              onClick={() =>
                navigate(
                  "/clients?action=create"
                )
              }
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
                <Plus className="h-4 w-4" />
              </div>

              <div className="text-left">
                <div className="text-sm font-medium">
                  {t("createClient") ||
                    "Create Client"}
                </div>

                <div className="text-[11px] text-muted-foreground">
                  {t("clients")}
                </div>
              </div>
            </Button>


            <Button
              variant="outline"
              className="h-auto justify-start gap-3 p-4"
              onClick={() =>
                navigate(
                  "/suppliers?action=create"
                )
              }
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
                <Plus className="h-4 w-4" />
              </div>

              <div className="text-left">
                <div className="text-sm font-medium">
                  {t("createSupplier") ||
                    "Create Supplier"}
                </div>

                <div className="text-[11px] text-muted-foreground">
                  {t("suppliers")}
                </div>
              </div>
            </Button>


            <Button
              variant="outline"
              className="h-auto justify-start gap-3 p-4"
              onClick={() =>
                navigate(
                  "/tasks?action=create"
                )
              }
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
                <Plus className="h-4 w-4" />
              </div>

              <div className="text-left">
                <div className="text-sm font-medium">
                  {t("createTask") ||
                    "Create Task"}
                </div>

                <div className="text-[11px] text-muted-foreground">
                  {t("tasks")}
                </div>
              </div>
            </Button>


            <Button
              variant="outline"
              className="h-auto justify-start gap-3 p-4"
              onClick={() =>
                navigate(
                  "/finance?action=create-invoice"
                )
              }
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
                <Receipt className="h-4 w-4" />
              </div>

              <div className="text-left">
                <div className="text-sm font-medium">
                  {t("createInvoice") ||
                    "Create Invoice"}
                </div>

                <div className="text-[11px] text-muted-foreground">
                  {t("finance")}
                </div>
              </div>
            </Button>

          </div>

        </section>


        {/* =================================================
            REVENUE + INVOICES
        ================================================= */}

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">

          {/* REVENUE */}

          <Card className="xl:col-span-2 border-border/70 overflow-hidden">

            <CardHeader className="pb-3">

              <SectionHeader
                title={t("revenueTrend")}
                description={t(
                  "last6Months"
                )}
              />

            </CardHeader>


            <CardContent className="h-80">

              {loading ? (

                <div className="h-full flex items-center justify-center">

                  <div className="text-sm text-muted-foreground">
                    Loading...
                  </div>

                </div>

              ) : trend.length === 0 ? (

                <div className="h-full flex flex-col items-center justify-center text-center">

                  <TrendingUp className="h-8 w-8 text-muted-foreground/40" />

                  <p className="mt-3 text-sm font-medium">
                    {t("nothingYet")}
                  </p>

                  <p className="mt-1 text-xs text-muted-foreground">
                    {t("revenueTrend")}
                  </p>

                </div>

              ) : (

                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >
                  <AreaChart
                    data={trend}
                    margin={{
                      top: 10,
                      right: 8,
                      left: -20,
                      bottom: 0,
                    }}
                  >

                    <defs>

                      <linearGradient
                        id="dashboardRevenueGradient"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >

                        <stop
                          offset="0%"
                          stopColor="hsl(var(--foreground))"
                          stopOpacity={0.22}
                        />

                        <stop
                          offset="100%"
                          stopColor="hsl(var(--foreground))"
                          stopOpacity={0}
                        />

                      </linearGradient>

                    </defs>


                    <CartesianGrid
                      vertical={false}
                      strokeDasharray="3 3"
                      stroke="hsl(var(--border))"
                    />


                    <XAxis
                      dataKey="month"
                      axisLine={false}
                      tickLine={false}
                      tick={{
                        fontSize: 11,
                        fill: "hsl(var(--muted-foreground))",
                      }}
                    />


                    <YAxis
                      axisLine={false}
                      tickLine={false}
                      tick={{
                        fontSize: 11,
                        fill: "hsl(var(--muted-foreground))",
                      }}
                    />


                    <Tooltip
                      cursor={{
                        stroke:
                          "hsl(var(--border))",
                      }}
                      contentStyle={{
                        background:
                          "hsl(var(--popover))",
                        border:
                          "1px solid hsl(var(--border))",
                        borderRadius: 10,
                        fontSize: 12,
                      }}
                    />


                    <Area
                      type="monotone"
                      dataKey="revenue"
                      stroke="hsl(var(--foreground))"
                      fill="url(#dashboardRevenueGradient)"
                      strokeWidth={2}
                      dot={false}
                      activeDot={{
                        r: 4,
                      }}
                    />

                  </AreaChart>
                </ResponsiveContainer>

              )}

            </CardContent>

          </Card>


          {/* UPCOMING INVOICES */}

          <Card className="border-border/70">

            <CardHeader className="pb-3">

              <SectionHeader
                title={t(
                  "upcomingInvoices"
                )}
                description={t(
                  "next30Days"
                )}
                action={
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() =>
                      navigate(
                        "/finance"
                      )
                    }
                  >
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                }
              />

            </CardHeader>


            <CardContent
              className="space-y-2"
              data-testid="upcoming-invoices"
            >

              {upcomingInvoices.length ===
              0 ? (

                <div className="py-8 text-center">

                  <Receipt className="mx-auto h-8 w-8 text-muted-foreground/40" />

                  <p className="mt-3 text-sm font-medium">
                    {t(
                      "noUpcomingInvoices"
                    )}
                  </p>

                </div>

              ) : (

                upcomingInvoices.map(
                  (inv) => (
                    <div
                      key={inv.id}
                      className="
                        group
                        flex
                        items-center
                        justify-between
                        gap-3
                        rounded-lg
                        border
                        border-transparent
                        px-3
                        py-3
                        transition-colors
                        hover:border-border
                        hover:bg-muted/40
                      "
                    >

                      <div className="min-w-0">

                        <div className="font-medium text-sm truncate">
                          {inv.number}
                        </div>

                        <div className="mt-1 text-xs text-muted-foreground truncate">
                          {inv.client_name ||
                            "—"}
                        </div>

                        <div className="mt-1 text-[11px] text-muted-foreground">
                          {t("due")}{" "}
                          {formatDate(
                            inv.due_date
                          )}
                        </div>

                      </div>


                      <div className="text-right shrink-0">

                        <div className="font-semibold text-sm">
                          {formatCurrency(
                            inv.amount,
                            inv.currency ||
                              currency
                          )}
                        </div>

                      </div>

                    </div>
                  )
                )

              )}

            </CardContent>

          </Card>

        </div>


        {/* =================================================
            RECENT ACTIVITY
        ================================================= */}

        <Card className="border-border/70">

          <CardHeader className="pb-3">

            <SectionHeader
              title={t(
                "recentActivity"
              )}
              description={t(
                "nothingYet"
              )}
            />

          </CardHeader>


          <CardContent>

            {activity.length === 0 ? (

              <div className="py-10 text-center">

                <Clock3 className="mx-auto h-8 w-8 text-muted-foreground/40" />

                <p className="mt-3 text-sm font-medium">
                  {t("nothingYet")}
                </p>

              </div>

            ) : (

              <div
                className="relative"
                data-testid="activity-list"
              >

                <div className="absolute left-[15px] top-3 bottom-3 w-px bg-border" />


                <div className="space-y-5">

                  {activity.map(
                    (item) => (
                      <div
                        key={item.id}
                        className="relative flex gap-4"
                      >

                        <div
                          className="
                            relative
                            z-10
                            flex
                            h-8
                            w-8
                            shrink-0
                            items-center
                            justify-center
                            rounded-full
                            border
                            border-border
                            bg-background
                          "
                        >

                          <ActivityIcon
                            type={
                              item.type
                            }
                          />

                        </div>


                        <div className="min-w-0 flex-1 pt-0.5">

                          <div className="text-sm">
                            {item.message}
                          </div>

                          <div className="mt-1 text-xs text-muted-foreground">
                            {formatDate(
                              item.created_at
                            )}

                            {" · "}

                            {item.actor}
                          </div>

                        </div>

                      </div>
                    )
                  )}

                </div>

              </div>

            )}

          </CardContent>

        </Card>


        {/* =================================================
            FOOTER SUMMARY
        ================================================= */}

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">

          <Card className="border-border/70">

            <CardContent className="p-5">

              <div className="flex items-center gap-3">

                <div className="h-9 w-9 rounded-lg bg-muted flex items-center justify-center">
                  <Users className="h-4 w-4" />
                </div>

                <div>
                  <div className="text-xs text-muted-foreground">
                    {t("activeClients")}
                  </div>

                  <div className="mt-1 text-lg font-semibold">
                    {k.active_clients ??
                      0}
                  </div>
                </div>

              </div>

            </CardContent>

          </Card>


          <Card className="border-border/70">

            <CardContent className="p-5">

              <div className="flex items-center gap-3">

                <div className="h-9 w-9 rounded-lg bg-muted flex items-center justify-center">
                  <ListChecksIcon />
                </div>

                <div>
                  <div className="text-xs text-muted-foreground">
                    {t("openTasks")}
                  </div>

                  <div className="mt-1 text-lg font-semibold">
                    {k.open_tasks ??
                      0}
                  </div>
                </div>

              </div>

            </CardContent>

          </Card>


          <Card className="border-border/70">

            <CardContent className="p-5">

              <div className="flex items-center gap-3">

                <div className="h-9 w-9 rounded-lg bg-muted flex items-center justify-center">
                  <AlertCircle className="h-4 w-4" />
                </div>

                <div>
                  <div className="text-xs text-muted-foreground">
                    {t(
                      "upcomingInvoices"
                    )}
                  </div>

                  <div className="mt-1 text-lg font-semibold">
                    {
                      upcomingInvoices.length
                    }
                  </div>
                </div>

              </div>

            </CardContent>

          </Card>

        </div>

      </div>
    </>
  );
}


/*
 * Small local icon wrapper.
 * Keeps the dashboard dependency-free.
 */
function ListChecksIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-4 w-4"
    >
      <path d="M9 11l3 3L22 4" />
      <path d="M21 12v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h11" />
    </svg>
  );
}