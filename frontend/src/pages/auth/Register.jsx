import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { useAuth } from "../../lib/authContext";
import { toast } from "sonner";

export default function Register() {
  const nav = useNavigate();
  const { register } = useAuth();
  const [form, setForm] = useState({ name: "", company_name: "", email: "", password: "" });
  const [loading, setLoading] = useState(false);

  const update = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function onSubmit(e) {
    e.preventDefault();
    setLoading(true);
    try {
      await register(form);
      toast.success("Workspace created");
      nav("/");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Registration failed");
    } finally { setLoading(false); }
  }

  return (
    <div className="min-h-screen grid md:grid-cols-2">
      <div className="hidden md:flex flex-col justify-between bg-foreground text-background p-12">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-md bg-background text-foreground flex items-center justify-center font-black">N</div>
          <div className="text-lg font-semibold tracking-tight">NED Tech CRM</div>
        </div>
        <div className="space-y-6">
          <p className="text-xs uppercase tracking-[0.3em] opacity-70">Create your workspace</p>
          <h2 className="text-4xl lg:text-5xl font-black leading-[1.05] tracking-tight">
            The modular business OS your team will actually use.
          </h2>
          <p className="text-base opacity-70 max-w-md">Enable only the modules you need. Add more as you grow.</p>
        </div>
        <p className="text-xs opacity-60">© {new Date().getFullYear()} NED Tech Media</p>
      </div>

      <div className="flex items-center justify-center p-8">
        <form onSubmit={onSubmit} className="w-full max-w-sm space-y-6" data-testid="register-form">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Create workspace</h1>
            <p className="text-sm text-muted-foreground mt-1">Start your NED Tech CRM in 30 seconds</p>
          </div>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="company">Company name</Label>
              <Input id="company" value={form.company_name} onChange={update("company_name")} required data-testid="register-company-input" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="name">Your name</Label>
              <Input id="name" value={form.name} onChange={update("name")} required data-testid="register-name-input" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Work email</Label>
              <Input id="email" type="email" value={form.email} onChange={update("email")} required data-testid="register-email-input" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" value={form.password} onChange={update("password")} required minLength={8} data-testid="register-password-input" />
            </div>
          </div>
          <Button type="submit" className="w-full" disabled={loading} data-testid="register-submit-btn">
            {loading ? "Creating…" : "Create workspace"}
          </Button>
          <div className="text-sm text-center text-muted-foreground">
            Already have an account?{" "}
            <Link to="/auth/login" className="underline text-foreground" data-testid="link-login">Sign in</Link>
          </div>
        </form>
      </div>
    </div>
  );
}
