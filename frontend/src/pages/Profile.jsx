
import { useEffect, useState } from "react";
import PageHeader from "../components/layout/PageHeader";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "../components/ui/tabs";
import { Badge } from "../components/ui/badge";
import { Avatar, AvatarFallback } from "../components/ui/avatar";
import { api } from "../lib/apiClient";
import { toast } from "sonner";
import { useAuth } from "../lib/authContext";
import { initials, formatDate } from "../lib/format";
import {
  Shield,
  Monitor,
  Smartphone,
  Tablet,
  Trash2,
  LogOut,
} from "lucide-react";
import { useLanguage } from "../i18n";

function DeviceIcon({ device }) {
  if (!device) return <Monitor className="h-4 w-4" />;
  if (device.includes("Mobile")) {
    return <Smartphone className="h-4 w-4" />;
  }
  if (device.includes("Tablet")) {
    return <Tablet className="h-4 w-4" />;
  }
  return <Monitor className="h-4 w-4" />;
}

export default function Profile() {
  const { user, refresh } = useAuth();
  const { t } = useLanguage();

  const [details, setDetails] = useState({
    name: "",
    phone: "",
    avatar_url: "",
  });

  const [pw, setPw] = useState({
    current_password: "",
    new_password: "",
    confirm: "",
  });

  const [savingDetails, setSavingDetails] = useState(false);
  const [savingPw, setSavingPw] = useState(false);
  const [sessions, setSessions] = useState([]);

  useEffect(() => {
    if (user) {
      setDetails({
        name: user.name || "",
        phone: user.phone || "",
        avatar_url: user.avatar_url || "",
      });
    }
  }, [user]);

  const loadSessions = async () => {
    try {
      const { data } = await api.get("/profile/sessions");
      setSessions(data);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  const saveDetails = async (e) => {
    e.preventDefault();
    setSavingDetails(true);

    try {
      await api.patch("/profile/me", details);
      await refresh();
      toast.success(t("profileUpdated"));
    } catch (err) {
      toast.error(
        err?.response?.data?.detail || t("failed")
      );
    } finally {
      setSavingDetails(false);
    }
  };

  const changePw = async (e) => {
    e.preventDefault();

    if (pw.new_password !== pw.confirm) {
      toast.error(t("newPasswordsDoNotMatch"));
      return;
    }

    if (pw.new_password.length < 8) {
      toast.error(t("passwordMinLength"));
      return;
    }

    setSavingPw(true);

    try {
      await api.post("/profile/change-password", {
        current_password: pw.current_password,
        new_password: pw.new_password,
      });

      setPw({
        current_password: "",
        new_password: "",
        confirm: "",
      });

      toast.success(t("passwordChanged"));
    } catch (err) {
      toast.error(
        err?.response?.data?.detail || t("failed")
      );
    } finally {
      setSavingPw(false);
    }
  };

  const revokeSession = async (sid) => {
    if (!window.confirm(t("signThisDeviceOutConfirm"))) {
      return;
    }

    try {
      await api.delete(`/profile/sessions/${sid}`);
      toast.success(t("sessionRevoked"));
      loadSessions();
    } catch {
      toast.error(t("failed"));
    }
  };

  const revokeOthers = async () => {
    if (!window.confirm(t("signOutOtherDevicesConfirm"))) {
      return;
    }

    try {
      const { data } = await api.post(
        "/profile/sessions/revoke-others"
      );

      toast.success(
        `${t("signedOut")} ${data.revoked} ${
          data.revoked === 1
            ? t("otherSession")
            : t("otherSessions")
        }`
      );

      loadSessions();
    } catch {
      toast.error(t("failed"));
    }
  };

  return (
    <>
      <PageHeader
        title={t("yourProfile")}
        description={t("profileDescription")}
      />

      <div className="p-8 max-w-3xl space-y-6">

        {/* Profile summary */}
        <Card className="p-6 border-border/70">

          <div className="flex items-center gap-4">

            <Avatar className="h-16 w-16">
              <AvatarFallback className="bg-foreground text-background text-lg">
                {initials(user?.name || user?.email)}
              </AvatarFallback>
            </Avatar>

            <div className="flex-1">

              <div className="text-lg font-semibold">
                {user?.name || user?.email}
              </div>

              <div className="text-sm text-muted-foreground">
                {user?.email}
              </div>

              <div className="flex gap-1 mt-2">

                {user?.platform_role && (
                  <Badge className="gap-1">
                    <Shield className="h-3 w-3" />
                    {user.platform_role.replace("_", " ")}
                  </Badge>
                )}

                {user?.protected && (
                  <Badge variant="outline">
                    {t("protected")}
                  </Badge>
                )}

                <Badge variant="secondary">
                  {user?.role}
                </Badge>

              </div>

            </div>
          </div>
        </Card>

        <Tabs defaultValue="details">

          <TabsList>

            <TabsTrigger
              value="details"
              data-testid="profile-tab-details"
            >
              {t("details")}
            </TabsTrigger>

            <TabsTrigger
              value="password"
              data-testid="profile-tab-password"
            >
              {t("password")}
            </TabsTrigger>

            <TabsTrigger
              value="sessions"
              data-testid="profile-tab-sessions"
            >
              {t("sessions")} ({sessions.length})
            </TabsTrigger>

          </TabsList>

          {/* Details */}
          <TabsContent
            value="details"
            className="mt-4"
          >
            <Card className="p-6 border-border/70">

              <form
                onSubmit={saveDetails}
                className="space-y-4"
              >

                <div className="space-y-1.5">
                  <Label>
                    {t("fullName")}
                  </Label>

                  <Input
                    value={details.name}
                    onChange={(e) =>
                      setDetails({
                        ...details,
                        name: e.target.value,
                      })
                    }
                    data-testid="profile-name-input"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label>
                    {t("phone")}
                  </Label>

                  <Input
                    value={details.phone}
                    onChange={(e) =>
                      setDetails({
                        ...details,
                        phone: e.target.value,
                      })
                    }
                    data-testid="profile-phone-input"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label>
                    {t("avatarUrl")}
                  </Label>

                  <Input
                    value={details.avatar_url}
                    onChange={(e) =>
                      setDetails({
                        ...details,
                        avatar_url: e.target.value,
                      })
                    }
                    placeholder="https://…"
                  />
                </div>

                <Button
                  type="submit"
                  disabled={savingDetails}
                  data-testid="profile-save-details-btn"
                >
                  {savingDetails
                    ? t("saving")
                    : t("saveChanges")}
                </Button>

              </form>

            </Card>
          </TabsContent>

          {/* Password */}
          <TabsContent
            value="password"
            className="mt-4"
          >
            <Card className="p-6 border-border/70">

              <form
                onSubmit={changePw}
                className="space-y-4"
              >

                <div className="space-y-1.5">
                  <Label>
                    {t("currentPassword")}
                  </Label>

                  <Input
                    type="password"
                    value={pw.current_password}
                    onChange={(e) =>
                      setPw({
                        ...pw,
                        current_password:
                          e.target.value,
                      })
                    }
                    required
                    data-testid="profile-current-pw-input"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label>
                    {t("newPassword")}
                  </Label>

                  <Input
                    type="password"
                    value={pw.new_password}
                    onChange={(e) =>
                      setPw({
                        ...pw,
                        new_password:
                          e.target.value,
                      })
                    }
                    minLength={8}
                    required
                    data-testid="profile-new-pw-input"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label>
                    {t("confirmNewPassword")}
                  </Label>

                  <Input
                    type="password"
                    value={pw.confirm}
                    onChange={(e) =>
                      setPw({
                        ...pw,
                        confirm: e.target.value,
                      })
                    }
                    minLength={8}
                    required
                    data-testid="profile-confirm-pw-input"
                  />
                </div>

                <Button
                  type="submit"
                  disabled={savingPw}
                  data-testid="profile-change-pw-btn"
                >
                  {savingPw
                    ? t("changing")
                    : t("changePassword")}
                </Button>

              </form>

            </Card>
          </TabsContent>

          {/* Sessions */}
          <TabsContent
            value="sessions"
            className="mt-4"
          >

            <div className="flex items-center justify-between mb-3">

              <p className="text-sm text-muted-foreground">
                {t("sessionsDescription")}
              </p>

              <Button
                variant="outline"
                size="sm"
                onClick={revokeOthers}
                disabled={sessions.length < 2}
                data-testid="revoke-others-btn"
              >
                <LogOut className="h-4 w-4 mr-1" />
                {t("signOutOtherDevices")}
              </Button>

            </div>

            <Card className="border-border/70">

              {sessions.length === 0 && (
                <div className="p-8 text-center text-sm text-muted-foreground">
                  {t("noActiveSessions")}
                </div>
              )}

              {sessions.map((s) => (

                <div
                  key={s.id}
                  className="flex items-center justify-between px-6 py-4 border-b border-border/60 last:border-0 text-sm"
                  data-testid={`session-row-${s.id}`}
                >

                  <div className="flex items-center gap-3">

                    <DeviceIcon device={s.device} />

                    <div>

                      <div className="font-medium flex items-center gap-2">

                        {s.device ||
                          t("unknownDevice")}

                        {s.is_current && (
                          <Badge
                            className="text-[10px]"
                            data-testid="session-current-badge"
                          >
                            {t("thisDevice")}
                          </Badge>
                        )}

                      </div>

                      <div className="text-xs text-muted-foreground">
                        IP {s.ip || "—"} ·{" "}
                        {t("signedIn")}{" "}
                        {formatDate(s.created_at)}
                      </div>

                    </div>

                  </div>

                  {!s.is_current && (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() =>
                        revokeSession(s.id)
                      }
                      data-testid={`revoke-session-${s.id}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}

                </div>

              ))}

            </Card>

          </TabsContent>

        </Tabs>
      </div>
    </>
  );
}