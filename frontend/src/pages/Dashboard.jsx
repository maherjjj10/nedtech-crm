import { useEffect, useState } from "react";
import { api } from "../lib/apiClient";
import PageHeader from "../components/layout/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { formatCurrency, formatDate } from "../lib/format";
import { useAuth } from "../lib/authContext";
import { useLanguage } from "../i18n";
import {
  ArrowUpRight,
  DollarSign,
  Users,
  TrendingUp,
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

const Kpi = ({ label, value, icon: Icon, sub, testid }) => (
  <Card className="border-border/70">
    <CardContent className="p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>

          <div
            className="text-2xl sm:text-3xl font-bold tracking-tight"
            data-testid={`${testid}-value`}
          >
            {value}
          </div>

          {sub && (
            <p className="text-xs text-muted-foreground mt-1">
              {sub}
            </p>
          )}
        </div>

        <div className="h-10 w-10 rounded-lg bg-muted flex items-center justify-center">
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </CardContent>
  </Card>
);

export default function Dashboard() {
  const { tenant } = useAuth();
  const { t } = useLanguage();

  const [data, setData] = useState(null);

  const currency = tenant?.currency || "USD";

  useEffect(() => {
    api
      .get("/dashboard/overview")
      .then((r) => setData(r.data))
      .catch(() => {});
  }, []);

  const k = data?.kpis || {};
  const trend = data?.trend || [];

  return (
    <>
      <PageHeader
        title={`${t("welcomeBack")}${tenant?.name ? `, ${tenant.name}` : ""}`}
        description={t("dashboardDescription")}
        testid="dashboard-header"
      />

      <div className="p-8 space-y-8">

        {/* KPI CARDS */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">

          <Kpi
            label={t("revenue")}
            value={formatCurrency(k.revenue, currency)}
            icon={DollarSign}
            sub={t("paidInvoices")}
            testid="kpi-revenue"
          />

          <Kpi
            label={t("expenses")}
            value={formatCurrency(k.expenses, currency)}
            icon={ArrowUpRight}
            sub={t("allTime")}
            testid="kpi-expenses"
          />

          <Kpi
            label={t("profit")}
            value={formatCurrency(k.profit, currency)}
            icon={TrendingUp}
            sub={t("revenueMinusExpenses")}
            testid="kpi-profit"
          />

          <Kpi
            label={t("activeClients")}
            value={k.active_clients ?? 0}
            icon={Users}
            sub={`${k.open_tasks ?? 0} ${t("openTasks")}`}
            testid="kpi-clients"
          />

        </div>

        {/* CHART + UPCOMING INVOICES */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

          <Card className="lg:col-span-2 border-border/70">
            <CardHeader>
              <CardTitle className="text-base">
                {t("revenueTrend")}
              </CardTitle>

              <p className="text-xs text-muted-foreground">
                {t("last6Months")}
              </p>
            </CardHeader>

            <CardContent className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trend}>

                  <defs>
                    <linearGradient
                      id="revColor"
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop
                        offset="0%"
                        stopColor="hsl(var(--foreground))"
                        stopOpacity={0.35}
                      />

                      <stop
                        offset="100%"
                        stopColor="hsl(var(--foreground))"
                        stopOpacity={0}
                      />
                    </linearGradient>
                  </defs>

                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="hsl(var(--border))"
                  />

                  <XAxis
                    dataKey="month"
                    tick={{
                      fontSize: 11,
                      fill: "hsl(var(--muted-foreground))",
                    }}
                  />

                  <YAxis
                    tick={{
                      fontSize: 11,
                      fill: "hsl(var(--muted-foreground))",
                    }}
                  />

                  <Tooltip
                    contentStyle={{
                      background: "hsl(var(--popover))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />

                  <Area
                    type="monotone"
                    dataKey="revenue"
                    stroke="hsl(var(--foreground))"
                    fill="url(#revColor)"
                    strokeWidth={2}
                  />

                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* UPCOMING INVOICES */}
          <Card className="border-border/70">
            <CardHeader>
              <CardTitle className="text-base">
                {t("upcomingInvoices")}
              </CardTitle>

              <p className="text-xs text-muted-foreground">
                {t("next30Days")}
              </p>
            </CardHeader>

            <CardContent
              className="space-y-3"
              data-testid="upcoming-invoices"
            >

              {(data?.upcoming_invoices || []).length === 0 && (
                <p className="text-sm text-muted-foreground">
                  {t("noUpcomingInvoices")}
                </p>
              )}

              {(data?.upcoming_invoices || []).map((inv) => (
                <div
                  key={inv.id}
                  className="flex items-center justify-between text-sm border-b border-border/60 pb-2 last:border-0"
                >
                  <div>
                    <div className="font-medium">
                      {inv.number}
                    </div>

                    <div className="text-xs text-muted-foreground">
                      {inv.client_name || "—"} · {t("due")}{" "}
                      {formatDate(inv.due_date)}
                    </div>
                  </div>

                  <div className="font-semibold">
                    {formatCurrency(
                      inv.amount,
                      inv.currency || currency
                    )}
                  </div>
                </div>
              ))}

            </CardContent>
          </Card>

        </div>

        {/* RECENT ACTIVITY */}
        <Card className="border-border/70">
          <CardHeader>
            <CardTitle className="text-base">
              {t("recentActivity")}
            </CardTitle>
          </CardHeader>

          <CardContent>

            <ul
              className="space-y-3"
              data-testid="activity-list"
            >

              {(data?.activity || []).length === 0 && (
                <li className="text-sm text-muted-foreground">
                  {t("nothingYet")}
                </li>
              )}

              {(data?.activity || []).map((a) => (
                <li
                  key={a.id}
                  className="flex items-start gap-3 text-sm"
                >
                  <div className="mt-1.5 h-1.5 w-1.5 rounded-full bg-foreground/70" />

                  <div className="flex-1">

                    <div>{a.message}</div>

                    <div className="text-xs text-muted-foreground">
                      {formatDate(a.created_at)} · {a.actor}
                    </div>

                  </div>
                </li>
              ))}

            </ul>

          </CardContent>
        </Card>

      </div>
    </>
  );
}