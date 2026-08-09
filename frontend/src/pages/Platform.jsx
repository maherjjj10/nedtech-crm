import { useCallback, useEffect, useState } from "react";
import PageHeader from "../components/layout/PageHeader";
import { Card } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
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
  DialogFooter,
} from "../components/ui/dialog";
import { api } from "../lib/apiClient";
import { toast } from "sonner";
import {
  UserCog,
  LogIn,
  Shield,
  Users,
  Search,
  ArrowUp,
} from "lucide-react";
import { useAuth } from "../lib/authContext";
import { formatDate, formatCurrency } from "../lib/format";

export default function Platform() {
  const { user, refresh } = useAuth();

  const [tenants, setTenants] = useState([]);
  const [audit, setAudit] = useState([]);
  const [users, setUsers] = useState([]);
  const [userQ, setUserQ] = useState("");
  const [globalQ, setGlobalQ] = useState("");
  const [searchResults, setSearchResults] = useState(null);
  const [loading, setLoading] = useState(null);
  const [roleTarget, setRoleTarget] = useState(null);
  const [rolePatch, setRolePatch] = useState({
    platform_role: "",
    tenant_role: "",
  });

  const isPlatform =
    user?.platform_role === "platform_owner" ||
    user?.platform_role === "super_admin";

  const isOwner = user?.platform_role === "platform_owner";

  const load = useCallback(async () => {
    if (!isPlatform) return;

    const [t, a] = await Promise.all([
      api.get("/platform/tenants"),
      api.get("/platform/audit"),
    ]);

    setTenants(t.data);
    setAudit(a.data);
  }, [isPlatform]);

  useEffect(() => {
    load();
  }, [load]);

  const runGlobalSearch = async () => {
    if (globalQ.length < 2) {
      toast.info("Type at least 2 characters");
      return;
    }

    const { data } = await api.get("/platform/search", {
      params: { q: globalQ },
    });

    setSearchResults(data);
  };

  const searchUsers = async () => {
    const { data } = await api.get("/platform/users", {
      params: userQ ? { q: userQ } : {},
    });

    setUsers(data);
  };

  const impersonate = async (tid, name) => {
    setLoading(tid);

    try {
      const original = localStorage.getItem("ned_token");

      localStorage.setItem("ned_token_original", original);

      const { data } = await api.post("/platform/impersonate", {
        tenant_id: tid,
        reason: "support",
      });

      localStorage.setItem("ned_token", data.access_token);

      await refresh();

      toast.success(
        `Impersonating ${name} — 30 min session`
      );

      window.location.href = "/";
    } catch (err) {
      toast.error(
        err?.response?.data?.detail ||
          "Impersonation failed"
      );
    } finally {
      setLoading(null);
    }
  };

  const openRole = (u) => {
    setRoleTarget(u);

    setRolePatch({
      platform_role: u.platform_role || "",
      tenant_role: u.role || "employee",
    });
  };

  const saveRole = async () => {
    try {
      const body = {};

      if (
        rolePatch.platform_role !==
        (roleTarget.platform_role || "")
      ) {
        body.platform_role =
          rolePatch.platform_role || null;
      }

      if (
        rolePatch.tenant_role !==
        (roleTarget.role || "")
      ) {
        body.tenant_role = rolePatch.tenant_role;
      }

      if (Object.keys(body).length === 0) {
        setRoleTarget(null);
        return;
      }

      await api.patch(
        `/platform/users/${roleTarget.id}/role`,
        body
      );

      toast.success("Role updated");

      setRoleTarget(null);

      await searchUsers();
      await load();
    } catch (err) {
      toast.error(
        err?.response?.data?.detail || "Failed"
      );
    }
  };

  if (!isPlatform) {
    return (
      <>
        <PageHeader
          title="Platform admin"
          description="Cross-tenant super-admin surface."
        />

        <div className="p-8">
          <Card className="p-8 border-border/70 text-center text-sm text-muted-foreground">
            You need platform_owner or super_admin
            privileges to see this page.
          </Card>
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Platform admin"
        description="Every tenant, every user, every audit event — under one glass."
        right={
          <Badge className="gap-1">
            <Shield className="h-3 w-3" />
            {user.platform_role.replace("_", " ")}
          </Badge>
        }
      />

      <div className="p-8 space-y-6">
        <Card className="p-4 border-border/70">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />

              <Input
                placeholder="Search across every tenant, user, invoice or client…"
                value={globalQ}
                onChange={(e) =>
                  setGlobalQ(e.target.value)
                }
                onKeyDown={(e) =>
                  e.key === "Enter" &&
                  runGlobalSearch()
                }
                className="pl-9"
                data-testid="global-search-input"
              />
            </div>

            <Button
              onClick={runGlobalSearch}
              data-testid="global-search-btn"
            >
              Search
            </Button>
          </div>

          {searchResults && (
            <div
              className="mt-4 space-y-4"
              data-testid="global-search-results"
            >
              {[
                "tenants",
                "users",
                "invoices",
                "clients",
              ].map((kind) => {
                const rows = searchResults[kind] || [];

                if (rows.length === 0) return null;

                return (
                  <div key={kind}>
                    <div className="n-overline mb-2">
                      {kind} ({rows.length})
                    </div>

                    <div className="space-y-1">
                      {rows.map((r) => (
                        <div
                          key={r.id}
                          className="flex items-center justify-between text-sm px-3 py-2 rounded border border-border/60"
                        >
                          {kind === "tenants" && (
                            <>
                              <span>{r.name}</span>

                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() =>
                                  impersonate(
                                    r.id,
                                    r.name
                                  )
                                }
                              >
                                <LogIn className="h-3 w-3 mr-1" />
                                Impersonate
                              </Button>
                            </>
                          )}

                          {kind === "users" && (
                            <>
                              <span>
                                {r.name || r.email} ·{" "}
                                <span className="text-muted-foreground text-xs">
                                  {r.email}
                                </span>
                              </span>

                              {r.platform_role && (
                                <Badge>
                                  {r.platform_role.replace(
                                    "_",
                                    " "
                                  )}
                                </Badge>
                              )}
                            </>
                          )}

                          {kind === "invoices" && (
                            <>
                              <span>
                                {r.number} —{" "}
                                {r.client_name || "—"}
                              </span>

                              <span className="font-semibold">
                                {formatCurrency(
                                  r.amount,
                                  r.currency
                                )}
                              </span>
                            </>
                          )}

                          {kind === "clients" && (
                            <span>
                              {r.name} —{" "}
                              {r.company ||
                                r.email ||
                                ""}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}

              {Object.values(searchResults).every(
                (v) => v.length === 0
              ) && (
                <div className="text-sm text-muted-foreground">
                  No matches found.
                </div>
              )}
            </div>
          )}
        </Card>

        <Tabs defaultValue="tenants">
          <TabsList>
            <TabsTrigger
              value="tenants"
              data-testid="platform-tab-tenants"
            >
              Tenants ({tenants.length})
            </TabsTrigger>

            <TabsTrigger
              value="users"
              data-testid="platform-tab-users"
            >
              Users
            </TabsTrigger>

            <TabsTrigger
              value="audit"
              data-testid="platform-tab-audit"
            >
              Audit log
            </TabsTrigger>
          </TabsList>

          <TabsContent
            value="tenants"
            className="mt-6"
          >
            <Card className="border-border/70">
              <div className="grid grid-cols-12 px-6 py-3 border-b border-border n-overline">
                <div className="col-span-4">
                  Workspace
                </div>

                <div className="col-span-2">
                  Users
                </div>

                <div className="col-span-2">
                  Plan
                </div>

                <div className="col-span-2">
                  Created
                </div>

                <div className="col-span-2 text-right">
                  Action
                </div>
              </div>

              {tenants.map((t) => (
                <div
                  key={t.id}
                  className="grid grid-cols-12 px-6 py-4 border-b border-border/60 last:border-0 items-center text-sm"
                  data-testid={`platform-tenant-${t.id}`}
                >
                  <div className="col-span-4">
                    <div className="font-medium">
                      {t.name}
                    </div>

                    <div className="text-xs text-muted-foreground">
                      {t.slug}
                    </div>
                  </div>

                  <div className="col-span-2 flex items-center gap-1">
                    <Users className="h-3.5 w-3.5" />
                    {t.user_count}
                  </div>

                  <div className="col-span-2">
                    <Badge
                      variant={
                        t.billing?.plan
                          ? "default"
                          : "outline"
                      }
                    >
                      {t.billing?.plan?.replace(
                        "_monthly",
                        ""
                      ) || "free"}
                    </Badge>
                  </div>

                  <div className="col-span-2 text-muted-foreground text-xs">
                    {formatDate(t.created_at)}
                  </div>

                  <div className="col-span-2 text-right">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        impersonate(
                          t.id,
                          t.name
                        )
                      }
                      disabled={loading === t.id}
                      data-testid={`impersonate-${t.id}`}
                    >
                      <LogIn className="h-3 w-3 mr-1" />

                      {loading === t.id
                        ? "…"
                        : "Impersonate"}
                    </Button>
                  </div>
                </div>
              ))}
            </Card>
          </TabsContent>

          <TabsContent
            value="users"
            className="mt-6"
          >
            <div className="flex gap-2 mb-4 max-w-md">
              <Input
                placeholder="Search users…"
                value={userQ}
                onChange={(e) =>
                  setUserQ(e.target.value)
                }
                onKeyDown={(e) =>
                  e.key === "Enter" &&
                  searchUsers()
                }
                data-testid="platform-users-search"
              />

              <Button onClick={searchUsers}>
                Search
              </Button>
            </div>

            <Card className="border-border/70">
              {users.length === 0 && (
                <div className="p-8 text-center text-sm text-muted-foreground">
                  Search to see users.
                </div>
              )}

              {users.map((u) => {
                const canEdit =
                  !u.protected &&
                  u.platform_role !==
                    "platform_owner";

                return (
                  <div
                    key={u.id}
                    className="flex items-center justify-between px-6 py-3 border-b border-border/60 last:border-0 text-sm"
                    data-testid={`user-row-${u.id}`}
                  >
                    <div className="flex items-center gap-3">
                      <UserCog className="h-4 w-4 text-muted-foreground" />

                      <div>
                        <div className="font-medium">
                          {u.name || u.email}
                        </div>

                        <div className="text-xs text-muted-foreground">
                          {u.email}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {u.platform_role && (
                        <Badge>
                          {u.platform_role.replace(
                            "_",
                            " "
                          )}
                        </Badge>
                      )}

                      {u.protected && (
                        <Badge variant="outline">
                          <Shield className="h-3 w-3 mr-1" />
                          protected
                        </Badge>
                      )}

                      <Badge variant="secondary">
                        {u.role || "viewer"}
                      </Badge>

                      {canEdit && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            openRole(u)
                          }
                          data-testid={`edit-role-${u.id}`}
                        >
                          <ArrowUp className="h-3 w-3 mr-1" />
                          Change role
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}
            </Card>
          </TabsContent>

          <TabsContent
            value="audit"
            className="mt-6"
          >
            <Card className="border-border/70">
              {audit.length === 0 && (
                <div className="p-8 text-center text-sm text-muted-foreground">
                  No audit events yet.
                </div>
              )}

              {audit.map((a) => (
                <div
                  key={a.id}
                  className="px-6 py-3 border-b border-border/60 last:border-0 text-sm"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge
                        variant="outline"
                        className="text-[10px]"
                      >
                        {a.action}
                      </Badge>

                      <span className="font-medium">
                        {a.actor_email}
                      </span>
                    </div>

                    <span className="text-xs text-muted-foreground">
                      {formatDate(a.created_at)}
                    </span>
                  </div>

                  {a.target_tenant && (
                    <div className="text-xs text-muted-foreground mt-1">
                      Target tenant:{" "}
                      {a.target_tenant}
                    </div>
                  )}

                  {a.meta &&
                    Object.keys(a.meta).length > 0 && (
                      <pre className="text-[10px] text-muted-foreground mt-1 whitespace-pre-wrap">
                        {JSON.stringify(
                          a.meta,
                          null,
                          2
                        )}
                      </pre>
                    )}
                </div>
              ))}
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      <Dialog
        open={!!roleTarget}
        onOpenChange={(o) =>
          !o && setRoleTarget(null)
        }
      >
        <DialogContent data-testid="role-dialog">
          <DialogHeader>
            <DialogTitle>
              Change role — {roleTarget?.email}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <div className="n-overline mb-2">
                Platform role
              </div>

              <div className="grid grid-cols-2 gap-2">
                <Button
                  variant={
                    rolePatch.platform_role === ""
                      ? "default"
                      : "outline"
                  }
                  size="sm"
                  onClick={() =>
                    setRolePatch({
                      ...rolePatch,
                      platform_role: "",
                    })
                  }
                >
                  None
                </Button>

                <Button
                  variant={
                    rolePatch.platform_role ===
                    "super_admin"
                      ? "default"
                      : "outline"
                  }
                  size="sm"
                  onClick={() =>
                    setRolePatch({
                      ...rolePatch,
                      platform_role:
                        "super_admin",
                    })
                  }
                  disabled={!isOwner}
                  data-testid="grant-super-admin-btn"
                >
                  Super admin
                </Button>
              </div>

              {!isOwner && (
                <div className="text-xs text-muted-foreground mt-1">
                  Only platform_owner can grant
                  super_admin.
                </div>
              )}
            </div>

            <div>
              <div className="n-overline mb-2">
                Tenant role
              </div>

              <div className="grid grid-cols-4 gap-2">
                {[
                  "admin",
                  "manager",
                  "employee",
                  "viewer",
                ].map((r) => (
                  <Button
                    key={r}
                    variant={
                      rolePatch.tenant_role === r
                        ? "default"
                        : "outline"
                    }
                    size="sm"
                    onClick={() =>
                      setRolePatch({
                        ...rolePatch,
                        tenant_role: r,
                      })
                    }
                  >
                    {r}
                  </Button>
                ))}
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() =>
                setRoleTarget(null)
              }
            >
              Cancel
            </Button>

            <Button
              onClick={saveRole}
              data-testid="save-role-btn"
            >
              Save role
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}