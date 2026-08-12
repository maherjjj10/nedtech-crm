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
import { Avatar, AvatarFallback } from "../components/ui/avatar";
import { api } from "../lib/apiClient";
import {
  Plus,
  Trash2,
  Copy,
  Mail,
  Check,
  X,
} from "lucide-react";
import { toast } from "sonner";
import {
  formatCurrency,
  initials,
  formatDate,
} from "../lib/format";
import { useLanguage } from "../i18n";

const DEFAULT_PERMISSIONS = {
  dashboard: true,
  crm: true,
  sales: true,
  tasks: true,
  finance: false,
  products: false,
  hr: false,
  ai: false,
  calendar: true,
  contracts: true,
  billing: false,
  profile: true,
  settings: false,
};

const EMPTY_EMP = {
  name: "",
  email: "",
  phone: "",
  role: "employee",
  department: "",
  position: "",
  salary: 0,
  currency: "USD",
  status: "active",
  permissions: { ...DEFAULT_PERMISSIONS },
};

const EMPTY_INV = {
  email: "",
  role: "employee",
  name: "",
  permissions: { ...DEFAULT_PERMISSIONS },
};

const ROLE_LABELS = {
  admin: "admin",
  manager: "manager",
  employee: "employee",
  viewer: "viewer",
};

export default function Employees() {
  const { t } = useLanguage();

  const [items, setItems] = useState([]);
  const [invites, setInvites] = useState([]);

  const [openEmp, setOpenEmp] = useState(false);
  const [openInv, setOpenInv] = useState(false);

  const [empForm, setEmpForm] = useState(EMPTY_EMP);
  const [invForm, setInvForm] = useState(EMPTY_INV);

  const [lastInvite, setLastInvite] = useState(null);

  const permissionOptions = [
    {
      key: "dashboard",
      label: t("dashboard"),
      description: t("permissionDashboard"),
    },
    {
      key: "crm",
      label: t("crmClients"),
      description: t("permissionCrm"),
    },
    {
      key: "sales",
      label: t("salesPipeline"),
      description: t("permissionSales"),
    },
    {
      key: "tasks",
      label: t("tasksProjects"),
      description: t("permissionTasks"),
    },
    {
      key: "finance",
      label: t("finance"),
      description: t("permissionFinance"),
    },
    {
      key: "products",
      label: t("productsServices"),
      description: t("permissionProducts"),
    },
    {
      key: "hr",
      label: t("employeesHr"),
      description: t("permissionHr"),
    },
    {
      key: "ai",
      label: t("aiAssistant"),
      description: t("permissionAi"),
    },
    {
      key: "calendar",
      label: t("calendar"),
      description: t("permissionCalendar"),
    },
    {
      key: "contracts",
      label: t("contracts"),
      description: t("permissionContracts"),
    },
    {
      key: "billing",
      label: t("billing"),
      description: t("permissionBilling"),
    },
    {
      key: "profile",
      label: t("profile"),
      description: t("permissionProfile"),
    },
    {
      key: "settings",
      label: t("settings"),
      description: t("permissionSettings"),
    },
  ];

  const allPermissions = () => {
    const permissions = {};

    permissionOptions.forEach((permission) => {
      permissions[permission.key] = true;
    });

    return permissions;
  };

  const clearPermissions = () => {
    const permissions = {};

    permissionOptions.forEach((permission) => {
      permissions[permission.key] = false;
    });

    return permissions;
  };

  const load = async () => {
    try {
      const [employeesResponse, invitesResponse] =
        await Promise.all([
          api.get("/employees"),
          api.get("/tenants/me/invites"),
        ]);

      setItems(employeesResponse.data || []);
      setInvites(invitesResponse.data || []);
    } catch (error) {
      toast.error(
        error?.response?.data?.detail ||
          t("failedLoadTeam")
      );
    }
  };

  useEffect(() => {
    load();
  }, []);

  const setEmployeePermission = (key, value) => {
    setEmpForm((current) => ({
      ...current,
      permissions: {
        ...current.permissions,
        [key]: value,
      },
    }));
  };

  const selectAllEmployeePermissions = () => {
    setEmpForm((current) => ({
      ...current,
      permissions: allPermissions(),
    }));
  };

  const clearEmployeePermissions = () => {
    setEmpForm((current) => ({
      ...current,
      permissions: clearPermissions(),
    }));
  };

  const setInvitePermission = (key, value) => {
    setInvForm((current) => ({
      ...current,
      permissions: {
        ...current.permissions,
        [key]: value,
      },
    }));
  };

  const selectAllInvitePermissions = () => {
    setInvForm((current) => ({
      ...current,
      permissions: allPermissions(),
    }));
  };

  const clearInvitePermissions = () => {
    setInvForm((current) => ({
      ...current,
      permissions: clearPermissions(),
    }));
  };

  const saveEmp = async (e) => {
    e.preventDefault();

    try {
      await api.post("/employees", {
        ...empForm,
        salary: Number(empForm.salary || 0),
        permissions: empForm.permissions,
      });

      toast.success(t("teamMemberCreated"));

      setOpenEmp(false);

      setEmpForm({
        ...EMPTY_EMP,
        permissions: { ...DEFAULT_PERMISSIONS },
      });

      await load();
    } catch (error) {
      toast.error(
        error?.response?.data?.detail ||
          t("failedCreateTeamMember")
      );
    }
  };

  const removeEmp = async (id) => {
    try {
      await api.delete(`/employees/${id}`);

      toast.success(t("teamMemberDeleted"));

      await load();
    } catch (error) {
      toast.error(
        error?.response?.data?.detail ||
          t("failedDeleteTeamMember")
      );
    }
  };

  const sendInvite = async (e) => {
    e.preventDefault();

    try {
      const { data } = await api.post(
        "/tenants/me/invites",
        {
          email: invForm.email,
          name: invForm.name || null,
          role: invForm.role,
          permissions: invForm.permissions,
        }
      );

      setLastInvite(data);

      if (data.email?.sent) {
        toast.success(t("invitationEmailSent"));
      } else {
        toast.info(t("inviteReady"));
      }

      setInvForm({
        ...EMPTY_INV,
        permissions: { ...DEFAULT_PERMISSIONS },
      });

      await load();
    } catch (error) {
      toast.error(
        error?.response?.data?.detail ||
          t("failedSendInvitation")
      );
    }
  };

  const copyLink = async (url) => {
    if (!url) return;

    try {
      await navigator.clipboard.writeText(url);
      toast.success(t("inviteLinkCopied"));
    } catch {
      toast.error(t("couldNotCopyInvite"));
    }
  };

  const revoke = async (id) => {
    try {
      await api.delete(
        `/tenants/me/invites/${id}`
      );

      toast.success(t("invitationRevoked"));

      await load();
    } catch (error) {
      toast.error(
        error?.response?.data?.detail ||
          t("failedRevokeInvitation")
      );
    }
  };

  const PermissionSelector = ({
    permissions,
    onChange,
    onSelectAll,
    onClearAll,
  }) => {
    return (
      <div className="space-y-3 border border-border rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="font-medium text-sm">
              {t("permissions")}
            </div>

            <div className="text-xs text-muted-foreground">
              {t("permissionsDescription")}
            </div>
          </div>

          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onSelectAll}
            >
              <Check className="h-3 w-3 mr-1" />
              {t("all")}
            </Button>

            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onClearAll}
            >
              <X className="h-3 w-3 mr-1" />
              {t("none")}
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {permissionOptions.map((permission) => {
            const enabled =
              permissions?.[permission.key] === true;

            return (
              <button
                key={permission.key}
                type="button"
                onClick={() =>
                  onChange(
                    permission.key,
                    !enabled
                  )
                }
                className={[
                  "flex items-start gap-3 text-left",
                  "rounded-lg border p-3",
                  "transition-colors",
                  enabled
                    ? "border-foreground/30 bg-muted"
                    : "border-border hover:bg-muted/50",
                ].join(" ")}
              >
                <div
                  className={[
                    "mt-0.5 h-4 w-4 rounded border",
                    "flex items-center justify-center",
                    enabled
                      ? "bg-foreground border-foreground"
                      : "border-muted-foreground",
                  ].join(" ")}
                >
                  {enabled && (
                    <Check className="h-3 w-3 text-background" />
                  )}
                </div>

                <div className="min-w-0">
                  <div className="text-sm font-medium">
                    {permission.label}
                  </div>

                  <div className="text-[11px] text-muted-foreground">
                    {permission.description}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    );
  };

  const roleLabel = (role) => {
    if (role === "admin") return t("admin");
    if (role === "manager") return t("manager");
    if (role === "employee") return t("employee");
    if (role === "viewer") return t("viewer");

    return role;
  };

  return (
    <>
      <PageHeader
        title={t("team")}
        description={t("teamDescription")}
      />

      <div className="p-8">
        <Tabs defaultValue="members">

          <TabsList data-testid="team-tabs">
            <TabsTrigger value="members">
              {t("members")} ({items.length})
            </TabsTrigger>

            <TabsTrigger value="invites">
              {t("invitations")} ({invites.length})
            </TabsTrigger>
          </TabsList>

          {/* MEMBERS */}

          <TabsContent
            value="members"
            className="mt-6"
          >
            <div className="flex justify-end mb-3">
              <Dialog
                open={openEmp}
                onOpenChange={setOpenEmp}
              >
                <DialogTrigger asChild>
                  <Button data-testid="new-employee-btn">
                    <Plus className="h-4 w-4 mr-1" />
                    {t("newTeamMember")}
                  </Button>
                </DialogTrigger>

                <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">

                  <DialogHeader>
                    <DialogTitle>
                      {t("addTeamMember")}
                    </DialogTitle>
                  </DialogHeader>

                  <form
                    onSubmit={saveEmp}
                    className="space-y-5"
                  >
                    <div className="grid grid-cols-2 gap-3">

                      <div className="space-y-1.5 col-span-2">
                        <Label>{t("name")}</Label>

                        <Input
                          value={empForm.name}
                          onChange={(e) =>
                            setEmpForm({
                              ...empForm,
                              name: e.target.value,
                            })
                          }
                          required
                          data-testid="employee-name-input"
                        />
                      </div>

                      <div className="space-y-1.5">
                        <Label>{t("email")}</Label>

                        <Input
                          type="email"
                          value={empForm.email}
                          onChange={(e) =>
                            setEmpForm({
                              ...empForm,
                              email: e.target.value,
                            })
                          }
                        />
                      </div>

                      <div className="space-y-1.5">
                        <Label>{t("phone")}</Label>

                        <Input
                          value={empForm.phone}
                          onChange={(e) =>
                            setEmpForm({
                              ...empForm,
                              phone: e.target.value,
                            })
                          }
                        />
                      </div>

                      <div className="space-y-1.5">
                        <Label>{t("role")}</Label>

                        <Select
                          value={empForm.role}
                          onValueChange={(value) =>
                            setEmpForm({
                              ...empForm,
                              role: value,
                            })
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>

                          <SelectContent>
                            <SelectItem value="admin">
                              {t("admin")}
                            </SelectItem>

                            <SelectItem value="manager">
                              {t("manager")}
                            </SelectItem>

                            <SelectItem value="employee">
                              {t("employee")}
                            </SelectItem>

                            <SelectItem value="viewer">
                              {t("viewer")}
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-1.5">
                        <Label>{t("department")}</Label>

                        <Input
                          value={empForm.department}
                          onChange={(e) =>
                            setEmpForm({
                              ...empForm,
                              department: e.target.value,
                            })
                          }
                        />
                      </div>

                      <div className="space-y-1.5">
                        <Label>{t("position")}</Label>

                        <Input
                          value={empForm.position}
                          onChange={(e) =>
                            setEmpForm({
                              ...empForm,
                              position: e.target.value,
                            })
                          }
                        />
                      </div>

                      <div className="space-y-1.5">
                        <Label>{t("salary")}</Label>

                        <Input
                          type="number"
                          value={empForm.salary}
                          onChange={(e) =>
                            setEmpForm({
                              ...empForm,
                              salary: e.target.value,
                            })
                          }
                        />
                      </div>

                    </div>

                    <PermissionSelector
                      permissions={empForm.permissions}
                      onChange={setEmployeePermission}
                      onSelectAll={selectAllEmployeePermissions}
                      onClearAll={clearEmployeePermissions}
                    />

                    <DialogFooter>
                      <Button
                        type="submit"
                        data-testid="employee-save-btn"
                      >
                        {t("save")}
                      </Button>
                    </DialogFooter>

                  </form>
                </DialogContent>
              </Dialog>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">

              {items.length === 0 && (
                <div className="col-span-full p-8 text-center text-sm text-muted-foreground border border-dashed border-border rounded-lg">
                  {t("noTeamMembers")}
                </div>
              )}

              {items.map((employee) => (
                <Card
                  key={employee.id}
                  className="p-5 n-card-hover border-border/70"
                >
                  <div className="flex items-start justify-between">

                    <div className="flex gap-3">
                      <Avatar>
                        <AvatarFallback className="bg-foreground text-background">
                          {initials(employee.name)}
                        </AvatarFallback>
                      </Avatar>

                      <div>
                        <div className="font-semibold">
                          {employee.name}
                        </div>

                        <div className="text-xs text-muted-foreground">
                          {employee.position ||
                            roleLabel(employee.role)}
                        </div>
                      </div>
                    </div>

                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() =>
                        removeEmp(employee.id)
                      }
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>

                  </div>

                  <div className="mt-4 space-y-2 text-xs text-muted-foreground">

                    {employee.email && (
                      <div>{employee.email}</div>
                    )}

                    {employee.department && (
                      <div>{employee.department}</div>
                    )}

                    <div className="flex items-center gap-2 mt-2">
                      <Badge variant="outline">
                        {roleLabel(employee.role)}
                      </Badge>

                      <span className="font-semibold text-foreground">
                        {formatCurrency(
                          employee.salary,
                          employee.currency
                        )}
                      </span>
                    </div>

                    <div className="pt-2">
                      <div className="text-[10px] uppercase tracking-wide mb-1">
                        {t("access")}
                      </div>

                      <div className="flex flex-wrap gap-1">

                        {permissionOptions
                          .filter(
                            (permission) =>
                              employee.permissions?.[
                                permission.key
                              ]
                          )
                          .slice(0, 5)
                          .map((permission) => (
                            <Badge
                              key={permission.key}
                              variant="secondary"
                              className="text-[10px]"
                            >
                              {permission.label}
                            </Badge>
                          ))}

                        {permissionOptions.filter(
                          (permission) =>
                            employee.permissions?.[
                              permission.key
                            ]
                        ).length > 5 && (
                          <Badge
                            variant="secondary"
                            className="text-[10px]"
                          >
                            +
                            {permissionOptions.filter(
                              (permission) =>
                                employee.permissions?.[
                                  permission.key
                                ]
                            ).length - 5}
                          </Badge>
                        )}

                      </div>
                    </div>

                  </div>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* INVITATIONS */}

          <TabsContent
            value="invites"
            className="mt-6"
          >
            <div className="flex justify-between items-end mb-3">

              <p className="text-sm text-muted-foreground max-w-lg">
                {t("inviteDescription")}
              </p>

              <Dialog
                open={openInv}
                onOpenChange={(open) => {
                  setOpenInv(open);

                  if (!open) {
                    setLastInvite(null);
                  }
                }}
              >
                <DialogTrigger asChild>
                  <Button data-testid="new-invite-btn">
                    <Mail className="h-4 w-4 mr-1" />
                    {t("invite")}
                  </Button>
                </DialogTrigger>

                <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">

                  <DialogHeader>
                    <DialogTitle>
                      {t("inviteTeammate")}
                    </DialogTitle>
                  </DialogHeader>

                  {!lastInvite ? (
                    <form
                      onSubmit={sendInvite}
                      className="space-y-5"
                    >

                      <div className="space-y-1.5">
                        <Label>{t("name")}</Label>

                        <Input
                          value={invForm.name}
                          onChange={(e) =>
                            setInvForm({
                              ...invForm,
                              name: e.target.value,
                            })
                          }
                          placeholder={t("optional")}
                        />
                      </div>

                      <div className="space-y-1.5">
                        <Label>{t("email")}</Label>

                        <Input
                          type="email"
                          value={invForm.email}
                          onChange={(e) =>
                            setInvForm({
                              ...invForm,
                              email: e.target.value,
                            })
                          }
                          required
                          data-testid="invite-email-input"
                        />
                      </div>

                      <div className="space-y-1.5">
                        <Label>{t("role")}</Label>

                        <Select
                          value={invForm.role}
                          onValueChange={(value) =>
                            setInvForm({
                              ...invForm,
                              role: value,
                            })
                          }
                        >
                          <SelectTrigger data-testid="invite-role-select">
                            <SelectValue />
                          </SelectTrigger>

                          <SelectContent>
                            <SelectItem value="admin">
                              {t("admin")}
                            </SelectItem>

                            <SelectItem value="manager">
                              {t("manager")}
                            </SelectItem>

                            <SelectItem value="employee">
                              {t("employee")}
                            </SelectItem>

                            <SelectItem value="viewer">
                              {t("viewer")}
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <PermissionSelector
                        permissions={invForm.permissions}
                        onChange={setInvitePermission}
                        onSelectAll={selectAllInvitePermissions}
                        onClearAll={clearInvitePermissions}
                      />

                      <DialogFooter>
                        <Button
                          type="submit"
                          data-testid="invite-send-btn"
                        >
                          {t("sendInvitation")}
                        </Button>
                      </DialogFooter>

                    </form>
                  ) : (
                    <div className="space-y-4">

                      <div className="text-sm">
                        {lastInvite.email?.sent
                          ? `✅ ${t("invitationEmailSent")}`
                          : t("emailNotConfigured")}
                      </div>

                      <div
                        className="p-3 bg-muted rounded-md text-xs break-all font-mono"
                        data-testid="invite-link"
                      >
                        {lastInvite.invite?.invite_url}
                      </div>

                      <DialogFooter>

                        <Button
                          variant="outline"
                          onClick={() =>
                            copyLink(
                              lastInvite.invite?.invite_url
                            )
                          }
                          data-testid="copy-invite-btn"
                        >
                          <Copy className="h-4 w-4 mr-1" />
                          {t("copyLink")}
                        </Button>

                        <Button
                          onClick={() => {
                            setLastInvite(null);
                            setOpenInv(false);
                          }}
                        >
                          {t("done")}
                        </Button>

                      </DialogFooter>

                    </div>
                  )}

                </DialogContent>
              </Dialog>
            </div>

            <Card className="border-border/70">

              {invites.length === 0 && (
                <div className="p-8 text-center text-sm text-muted-foreground">
                  {t("noPendingInvitations")}
                </div>
              )}

              {invites.map((invite) => (
                <div
                  key={invite.id}
                  className="flex items-center justify-between px-6 py-4 border-b border-border/60 last:border-0 text-sm"
                  data-testid={`invite-row-${invite.id}`}
                >
                  <div>

                    <div className="font-medium">
                      {invite.email}
                    </div>

                    <div className="text-xs text-muted-foreground">
                      {t("invited")}{" "}
                      {formatDate(invite.created_at)}
                      {" · "}

                      <Badge
                        variant="outline"
                        className="ml-1 text-[10px]"
                      >
                        {roleLabel(invite.role)}
                      </Badge>
                    </div>

                    <div className="flex flex-wrap gap-1 mt-2">

                      {permissionOptions
                        .filter(
                          (permission) =>
                            invite.permissions?.[
                              permission.key
                            ]
                        )
                        .slice(0, 4)
                        .map((permission) => (
                          <Badge
                            key={permission.key}
                            variant="secondary"
                            className="text-[10px]"
                          >
                            {permission.label}
                          </Badge>
                        ))}

                    </div>
                  </div>

                  <div className="flex gap-1">

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        copyLink(invite.invite_url)
                      }
                    >
                      <Copy className="h-3 w-3 mr-1" />
                      {t("copyLink")}
                    </Button>

                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() =>
                        revoke(invite.id)
                      }
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>

                  </div>
                </div>
              ))}

            </Card>
          </TabsContent>

        </Tabs>
      </div>
    </>
  );
}