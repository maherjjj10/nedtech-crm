import { useEffect, useState } from "react";
import PageHeader from "../components/layout/PageHeader";
import { Card } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import { api } from "../lib/apiClient";
import { toast } from "sonner";
import { UserCog, LogIn, Shield, Users } from "lucide-react";
import { useAuth } from "../lib/authContext";
import { formatDate } from "../lib/format";

export default function Platform() {
  const { user, refresh } = useAuth();
  const [tenants, setTenants] = useState([]);
  const [audit, setAudit] = useState([]);
  const [users, setUsers] = useState([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(null);

  const isPlatform = user?.platform_role === "platform_owner" || user?.platform_role === "super_admin";

  const load = async () => {
    if (!isPlatform) return;
    const [t, a] = await Promise.all([api.get("/platform/tenants"), api.get("/platform/audit")]);
    setTenants(t.data); setAudit(a.data);
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [isPlatform]);

  const searchUsers = async () => {
    const { data } = await api.get("/platform/users", { params: q ? { q } : {} });
    setUsers(data);
  };

  const impersonate = async (tid, name) => {
    setLoading(tid);
    try {
      // save original token so user can exit impersonation cleanly
      const original = localStorage.getItem("ned_token");
      localStorage.setItem("ned_token_original", original);
      const { data } = await api.post("/platform/impersonate", { tenant_id: tid, reason: "support" });
      localStorage.setItem("ned_token", data.access_token);
      await refresh();
      toast.success(`Now viewing as ${name}`);
      window.location.href = "/";
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Impersonation failed");
    } finally { setLoading(null); }
  };

  if (!isPlatform) {
    return (
      <>
        <PageHeader title="Platform admin" description="Cross-tenant super-admin surface." />
        <div className="p-8"><Card className="p-8 border-border/70 text-center text-sm text-muted-foreground">You need platform_owner or super_admin privileges to see this page.</Card></div>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Platform admin"
        description="Every tenant, every user, every audit event — under one glass."
        right={<Badge className="gap-1"><Shield className="h-3 w-3" />{user.platform_role.replace("_", " ")}</Badge>}
      />

      <div className="p-8 space-y-6">
        <Tabs defaultValue="tenants">
          <TabsList>
            <TabsTrigger value="tenants" data-testid="platform-tab-tenants">Tenants ({tenants.length})</TabsTrigger>
            <TabsTrigger value="users" data-testid="platform-tab-users">Users</TabsTrigger>
            <TabsTrigger value="audit" data-testid="platform-tab-audit">Audit log</TabsTrigger>
          </TabsList>

          <TabsContent value="tenants" className="mt-6">
            <Card className="border-border/70">
              <div className="grid grid-cols-12 px-6 py-3 border-b border-border n-overline">
                <div className="col-span-4">Workspace</div><div className="col-span-2">Users</div><div className="col-span-2">Plan</div><div className="col-span-2">Created</div><div className="col-span-2 text-right">Action</div>
              </div>
              {tenants.map((t) => (
                <div key={t.id} className="grid grid-cols-12 px-6 py-4 border-b border-border/60 last:border-0 items-center text-sm" data-testid={`platform-tenant-${t.id}`}>
                  <div className="col-span-4">
                    <div className="font-medium">{t.name}</div>
                    <div className="text-xs text-muted-foreground">{t.slug}</div>
                  </div>
                  <div className="col-span-2 flex items-center gap-1"><Users className="h-3.5 w-3.5" /> {t.user_count}</div>
                  <div className="col-span-2"><Badge variant={t.billing?.plan ? "default" : "outline"}>{t.billing?.plan?.replace("_monthly", "") || "free"}</Badge></div>
                  <div className="col-span-2 text-muted-foreground text-xs">{formatDate(t.created_at)}</div>
                  <div className="col-span-2 text-right">
                    <Button size="sm" variant="outline" onClick={() => impersonate(t.id, t.name)} disabled={loading === t.id} data-testid={`impersonate-${t.id}`}>
                      <LogIn className="h-3 w-3 mr-1" />{loading === t.id ? "…" : "Impersonate"}
                    </Button>
                  </div>
                </div>
              ))}
            </Card>
          </TabsContent>

          <TabsContent value="users" className="mt-6">
            <div className="flex gap-2 mb-4 max-w-md">
              <Input placeholder="Search users by email or name…" value={q} onChange={(e)=>setQ(e.target.value)} onKeyDown={(e)=>e.key==='Enter' && searchUsers()} data-testid="platform-users-search" />
              <Button onClick={searchUsers}>Search</Button>
            </div>
            <Card className="border-border/70">
              {users.length === 0 && <div className="p-8 text-center text-sm text-muted-foreground">Search to see users.</div>}
              {users.map((u) => (
                <div key={u.id} className="flex items-center justify-between px-6 py-3 border-b border-border/60 last:border-0 text-sm">
                  <div className="flex items-center gap-3">
                    <UserCog className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <div className="font-medium">{u.name || u.email}</div>
                      <div className="text-xs text-muted-foreground">{u.email}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {u.platform_role && <Badge>{u.platform_role.replace("_", " ")}</Badge>}
                    {u.protected && <Badge variant="outline"><Shield className="h-3 w-3 mr-1" />protected</Badge>}
                    <Badge variant="secondary">{u.role || "viewer"}</Badge>
                  </div>
                </div>
              ))}
            </Card>
          </TabsContent>

          <TabsContent value="audit" className="mt-6">
            <Card className="border-border/70">
              {audit.length === 0 && <div className="p-8 text-center text-sm text-muted-foreground">No audit events yet.</div>}
              {audit.map((a) => (
                <div key={a.id} className="px-6 py-3 border-b border-border/60 last:border-0 text-sm">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-[10px]">{a.action}</Badge>
                      <span className="font-medium">{a.actor_email}</span>
                    </div>
                    <span className="text-xs text-muted-foreground">{formatDate(a.created_at)}</span>
                  </div>
                  {a.target_tenant && <div className="text-xs text-muted-foreground mt-1">Target tenant: {a.target_tenant}</div>}
                  {a.meta && Object.keys(a.meta).length > 0 && <pre className="text-[10px] text-muted-foreground mt-1 whitespace-pre-wrap">{JSON.stringify(a.meta, null, 2)}</pre>}
                </div>
              ))}
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </>
  );
}
