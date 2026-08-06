import { useEffect, useState } from "react";
import { api } from "../lib/apiClient";
import PageHeader from "../components/layout/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { formatCurrency, formatDate } from "../lib/format";
import { useAuth } from "../lib/authContext";
import { ArrowUpRight, DollarSign, Users, ListChecks, TrendingUp } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from "recharts";

const Kpi = ({ label, value, icon: Icon, sub, testid }) => (
  <Card className="n-card-hover border-border/70" data-testid={testid}>
    <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
      <CardTitle className="n-overline">{label}</CardTitle>
      <Icon className="h-4 w-4 text-muted-foreground" />
    </CardHeader>
    <CardContent>
      <div className="text-2xl sm:text-3xl font-bold tracking-tight" data-testid={`${testid}-value`}>{value}</div>
      {sub && <div className="text-xs text-muted-foreground mt-1">{sub}</div>}
    </CardContent>
  </Card>
);

export default function Dashboard() {
  const { tenant } = useAuth();
  const [data, setData] = useState(null);
  const currency = tenant?.currency || "USD";

  useEffect(() => {
    api.get("/dashboard/overview").then((r) => setData(r.data)).catch(() => {});
  }, []);

  const k = data?.kpis || {};
  const trend = data?.trend || [];

  return (
    <>
      <PageHeader
        title={`Welcome back${tenant?.name ? `, ${tenant.name}` : ""}`}
        description="Your business at a glance — revenue, pipeline, and today's focus."
        testid="dashboard-header"
      />

      <div className="p-8 space-y-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Kpi label="Revenue" value={formatCurrency(k.revenue, currency)} icon={DollarSign} sub="Paid invoices" testid="kpi-revenue" />
          <Kpi label="Expenses" value={formatCurrency(k.expenses, currency)} icon={ArrowUpRight} sub="All time" testid="kpi-expenses" />
          <Kpi label="Profit" value={formatCurrency(k.profit, currency)} icon={TrendingUp} sub="Revenue − Expenses" testid="kpi-profit" />
          <Kpi label="Active clients" value={k.active_clients ?? 0} icon={Users} sub={`${k.open_tasks ?? 0} open tasks`} testid="kpi-clients" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card className="lg:col-span-2 border-border/70">
            <CardHeader>
              <CardTitle className="text-base">Revenue trend</CardTitle>
              <p className="text-xs text-muted-foreground">Last 6 months</p>
            </CardHeader>
            <CardContent className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trend}>
                  <defs>
                    <linearGradient id="revColor" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="hsl(var(--foreground))" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="hsl(var(--foreground))" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="month" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                  <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                  <Tooltip contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
                  <Area type="monotone" dataKey="revenue" stroke="hsl(var(--foreground))" fill="url(#revColor)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card className="border-border/70">
            <CardHeader>
              <CardTitle className="text-base">Upcoming invoices</CardTitle>
              <p className="text-xs text-muted-foreground">Next 30 days</p>
            </CardHeader>
            <CardContent className="space-y-3" data-testid="upcoming-invoices">
              {(data?.upcoming_invoices || []).length === 0 && (
                <p className="text-sm text-muted-foreground">No upcoming invoices.</p>
              )}
              {(data?.upcoming_invoices || []).map((inv) => (
                <div key={inv.id} className="flex items-center justify-between text-sm border-b border-border/60 pb-2 last:border-0">
                  <div>
                    <div className="font-medium">{inv.number}</div>
                    <div className="text-xs text-muted-foreground">{inv.client_name || "—"} · due {formatDate(inv.due_date)}</div>
                  </div>
                  <div className="font-semibold">{formatCurrency(inv.amount, inv.currency || currency)}</div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        <Card className="border-border/70">
          <CardHeader>
            <CardTitle className="text-base">Recent activity</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3" data-testid="activity-list">
              {(data?.activity || []).length === 0 && <li className="text-sm text-muted-foreground">Nothing yet — create your first client or deal.</li>}
              {(data?.activity || []).map((a) => (
                <li key={a.id} className="flex items-start gap-3 text-sm">
                  <div className="mt-1.5 h-1.5 w-1.5 rounded-full bg-foreground/70" />
                  <div className="flex-1">
                    <div>{a.message}</div>
                    <div className="text-xs text-muted-foreground">{formatDate(a.created_at)} · {a.actor}</div>
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
