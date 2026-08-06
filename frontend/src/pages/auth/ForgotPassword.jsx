import { useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api/v1`;

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [devUrl, setDevUrl] = useState("");

  async function onSubmit(e) {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await axios.post(`${API}/auth/forgot-password`, { email: email.trim() });
      setSent(true);
      if (data.dev_reset_url) setDevUrl(data.dev_reset_url);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Something went wrong");
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
          <p className="text-xs uppercase tracking-[0.3em] opacity-70">Recover access</p>
          <h2 className="text-4xl lg:text-5xl font-black leading-[1.05] tracking-tight">Locked out? We&apos;ve got you.</h2>
          <p className="text-base opacity-70 max-w-md">Enter your email and we&apos;ll send you a secure link to reset your password.</p>
        </div>
        <p className="text-xs opacity-60">© {new Date().getFullYear()} NED Tech Media</p>
      </div>

      <div className="flex items-center justify-center p-8">
        {!sent ? (
          <form onSubmit={onSubmit} className="w-full max-w-sm space-y-6" data-testid="forgot-form">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Forgot password</h1>
              <p className="text-sm text-muted-foreground mt-1">We&apos;ll email you a reset link.</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" value={email} onChange={(e)=>setEmail(e.target.value)} required data-testid="forgot-email-input" />
            </div>
            <Button type="submit" className="w-full" disabled={loading} data-testid="forgot-submit-btn">
              {loading ? "Sending…" : "Send reset link"}
            </Button>
            <div className="text-sm text-center text-muted-foreground">
              Remembered it? <Link to="/auth/login" className="underline text-foreground">Sign in</Link>
            </div>
          </form>
        ) : (
          <div className="w-full max-w-sm space-y-4" data-testid="forgot-success">
            <h1 className="text-3xl font-bold tracking-tight">Check your email</h1>
            <p className="text-sm text-muted-foreground">If an account exists for <b>{email}</b>, you&apos;ll receive a link to reset your password within a minute. The link is valid for 1 hour.</p>
            {devUrl && (
              <div className="rounded-md border border-border p-3 text-xs">
                <div className="n-overline mb-1">Dev mode — email not configured</div>
                <a className="underline break-all" href={devUrl}>{devUrl}</a>
              </div>
            )}
            <Link to="/auth/login" className="underline text-sm">Back to sign in</Link>
          </div>
        )}
      </div>
    </div>
  );
}
