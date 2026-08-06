import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { useAuth } from "../../lib/authContext";
import { toast } from "sonner";

export default function Login() {
  const nav = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      toast.success("Welcome back");
      nav("/");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Login failed");
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
          <p className="text-xs uppercase tracking-[0.3em] opacity-70">Enterprise business OS</p>
          <h2 className="text-4xl lg:text-5xl font-black leading-[1.05] tracking-tight">
            Run every part of your business from one workspace.
          </h2>
          <p className="text-base opacity-70 max-w-md">CRM, sales, projects, finance, HR and AI — all modular, all yours.</p>
        </div>
        <p className="text-xs opacity-60">© {new Date().getFullYear()} NED Tech Media</p>
      </div>

      <div className="flex items-center justify-center p-8">
        <form onSubmit={onSubmit} className="w-full max-w-sm space-y-6" data-testid="login-form">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Sign in</h1>
            <p className="text-sm text-muted-foreground mt-1">Enter your credentials to continue</p>
          </div>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required data-testid="login-email-input" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required data-testid="login-password-input" />
            </div>
          </div>

          <Button type="submit" className="w-full" disabled={loading} data-testid="login-submit-btn">
            {loading ? "Signing in…" : "Sign in"}
          </Button>

          <div className="text-sm text-center text-muted-foreground">
            Don&apos;t have an account?{" "}
            <Link to="/auth/register" className="underline text-foreground" data-testid="link-register">Create workspace</Link>
          </div>
        </form>
      </div>
    </div>
  );
}
