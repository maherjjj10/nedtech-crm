import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Button } from "../components/ui/button";
import { toast } from "sonner";
import { useAuth } from "../lib/authContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api/v1`;

export default function InviteAccept() {
  const { token } = useParams();
  const nav = useNavigate();
  const { refresh } = useAuth();
  const [invite, setInvite] = useState(null);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ name: "", password: "" });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    axios.get(`${API}/invites/${token}`)
      .then(r => setInvite(r.data))
      .catch(e => setError(e?.response?.data?.detail || "Invitation not found"));
  }, [token]);

  const accept = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await axios.post(`${API}/invites/${token}/accept`, form);
      localStorage.setItem("ned_token", data.access_token);
      await refresh();
      toast.success("Welcome to the team!");
      nav("/");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to accept invitation");
    } finally { setLoading(false); }
  };

  if (error) return <div className="min-h-screen flex items-center justify-center p-6"><Card className="p-8 max-w-md w-full text-center border-border/70"><h2 className="text-xl font-bold">Invitation error</h2><p className="text-sm text-muted-foreground mt-2">{error}</p></Card></div>;
  if (!invite) return <div className="min-h-screen flex items-center justify-center text-sm text-muted-foreground">Loading invitation…</div>;

  return (
    <div className="min-h-screen grid md:grid-cols-2">
      <div className="hidden md:flex flex-col justify-between bg-foreground text-background p-12">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-md bg-background text-foreground flex items-center justify-center font-black">N</div>
          <div className="text-lg font-semibold tracking-tight">NED Tech CRM</div>
        </div>
        <div className="space-y-6">
          <p className="text-xs uppercase tracking-[0.3em] opacity-70">You&apos;re invited</p>
          <h2 className="text-4xl lg:text-5xl font-black leading-[1.05] tracking-tight">
            Join {invite.tenant_name || "the workspace"} on NED Tech CRM.
          </h2>
          <p className="text-base opacity-70 max-w-md">You&apos;ll join as <b>{invite.role}</b>. Set a password to get started.</p>
        </div>
        <p className="text-xs opacity-60">Invited by {invite.invited_by}</p>
      </div>

      <div className="flex items-center justify-center p-8">
        <form onSubmit={accept} className="w-full max-w-sm space-y-6" data-testid="invite-accept-form">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Accept invitation</h1>
            <p className="text-sm text-muted-foreground mt-1">Joining as <b>{invite.email}</b></p>
          </div>
          <div className="space-y-4">
            <div className="space-y-2"><Label>Your name</Label><Input value={form.name} onChange={(e)=>setForm({...form, name:e.target.value})} required data-testid="invite-name-input" /></div>
            <div className="space-y-2"><Label>Set password</Label><Input type="password" value={form.password} onChange={(e)=>setForm({...form, password:e.target.value})} required minLength={8} data-testid="invite-password-input" /></div>
          </div>
          <Button type="submit" className="w-full" disabled={loading} data-testid="invite-accept-btn">
            {loading ? "Joining…" : "Join workspace"}
          </Button>
        </form>
      </div>
    </div>
  );
}
