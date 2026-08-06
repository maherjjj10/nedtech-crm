import { useEffect, useState } from "react";
import PageHeader from "../components/layout/PageHeader";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import { Badge } from "../components/ui/badge";
import { Avatar, AvatarFallback } from "../components/ui/avatar";
import { api } from "../lib/apiClient";
import { toast } from "sonner";
import { useAuth } from "../lib/authContext";
import { initials } from "../lib/format";
import { Shield } from "lucide-react";

export default function Profile() {
  const { user, refresh } = useAuth();
  const [details, setDetails] = useState({ name: "", phone: "", avatar_url: "" });
  const [pw, setPw] = useState({ current_password: "", new_password: "", confirm: "" });
  const [savingDetails, setSavingDetails] = useState(false);
  const [savingPw, setSavingPw] = useState(false);

  useEffect(() => {
    if (user) setDetails({ name: user.name || "", phone: user.phone || "", avatar_url: user.avatar_url || "" });
  }, [user]);

  const saveDetails = async (e) => {
    e.preventDefault();
    setSavingDetails(true);
    try {
      await api.patch("/profile/me", details);
      await refresh();
      toast.success("Profile updated");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed");
    } finally { setSavingDetails(false); }
  };

  const changePw = async (e) => {
    e.preventDefault();
    if (pw.new_password !== pw.confirm) { toast.error("New passwords don't match"); return; }
    if (pw.new_password.length < 8) { toast.error("Password must be at least 8 characters"); return; }
    setSavingPw(true);
    try {
      await api.post("/profile/change-password", { current_password: pw.current_password, new_password: pw.new_password });
      setPw({ current_password: "", new_password: "", confirm: "" });
      toast.success("Password changed");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed");
    } finally { setSavingPw(false); }
  };

  return (
    <>
      <PageHeader title="Your profile" description="Manage your account details and password." />
      <div className="p-8 max-w-3xl space-y-6">
        <Card className="p-6 border-border/70">
          <div className="flex items-center gap-4">
            <Avatar className="h-16 w-16"><AvatarFallback className="bg-foreground text-background text-lg">{initials(user?.name || user?.email)}</AvatarFallback></Avatar>
            <div className="flex-1">
              <div className="text-lg font-semibold">{user?.name || user?.email}</div>
              <div className="text-sm text-muted-foreground">{user?.email}</div>
              <div className="flex gap-1 mt-2">
                {user?.platform_role && <Badge className="gap-1"><Shield className="h-3 w-3" />{user.platform_role.replace("_", " ")}</Badge>}
                {user?.protected && <Badge variant="outline">protected</Badge>}
                <Badge variant="secondary">{user?.role}</Badge>
              </div>
            </div>
          </div>
        </Card>

        <Tabs defaultValue="details">
          <TabsList><TabsTrigger value="details" data-testid="profile-tab-details">Details</TabsTrigger><TabsTrigger value="password" data-testid="profile-tab-password">Password</TabsTrigger></TabsList>

          <TabsContent value="details" className="mt-4">
            <Card className="p-6 border-border/70">
              <form onSubmit={saveDetails} className="space-y-4">
                <div className="space-y-1.5"><Label>Full name</Label><Input value={details.name} onChange={(e)=>setDetails({...details, name:e.target.value})} data-testid="profile-name-input" /></div>
                <div className="space-y-1.5"><Label>Phone</Label><Input value={details.phone} onChange={(e)=>setDetails({...details, phone:e.target.value})} data-testid="profile-phone-input" /></div>
                <div className="space-y-1.5"><Label>Avatar URL</Label><Input value={details.avatar_url} onChange={(e)=>setDetails({...details, avatar_url:e.target.value})} placeholder="https://…" /></div>
                <Button type="submit" disabled={savingDetails} data-testid="profile-save-details-btn">{savingDetails ? "Saving…" : "Save changes"}</Button>
              </form>
            </Card>
          </TabsContent>

          <TabsContent value="password" className="mt-4">
            <Card className="p-6 border-border/70">
              <form onSubmit={changePw} className="space-y-4">
                <div className="space-y-1.5"><Label>Current password</Label><Input type="password" value={pw.current_password} onChange={(e)=>setPw({...pw, current_password:e.target.value})} required data-testid="profile-current-pw-input" /></div>
                <div className="space-y-1.5"><Label>New password</Label><Input type="password" value={pw.new_password} onChange={(e)=>setPw({...pw, new_password:e.target.value})} minLength={8} required data-testid="profile-new-pw-input" /></div>
                <div className="space-y-1.5"><Label>Confirm new password</Label><Input type="password" value={pw.confirm} onChange={(e)=>setPw({...pw, confirm:e.target.value})} minLength={8} required data-testid="profile-confirm-pw-input" /></div>
                <Button type="submit" disabled={savingPw} data-testid="profile-change-pw-btn">{savingPw ? "Changing…" : "Change password"}</Button>
              </form>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </>
  );
}
