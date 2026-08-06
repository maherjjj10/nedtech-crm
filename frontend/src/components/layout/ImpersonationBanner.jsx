import { useAuth } from "../../lib/authContext";
import { Button } from "../ui/button";
import { LogOut } from "lucide-react";
import { toast } from "sonner";
import { api } from "../../lib/apiClient";

export default function ImpersonationBanner() {
  const { user, refresh } = useAuth();
  const isImpersonating = user?.impersonating_from || localStorage.getItem("ned_token_original");
  if (!isImpersonating) return null;

  const stop = async () => {
    try {
      // Restore original token first — the backend also issues one; either works.
      const orig = localStorage.getItem("ned_token_original");
      if (orig) {
        localStorage.setItem("ned_token", orig);
        localStorage.removeItem("ned_token_original");
      } else {
        const { data } = await api.post("/platform/impersonate/stop");
        localStorage.setItem("ned_token", data.access_token);
      }
      await refresh();
      toast.success("Exited impersonation");
      window.location.href = "/platform";
    } catch (err) {
      toast.error("Failed to exit impersonation");
    }
  };

  return (
    <div className="w-full bg-foreground text-background text-xs px-4 py-2 flex items-center justify-between gap-3 sticky top-0 z-30" data-testid="impersonation-banner">
      <div>
        <span className="font-semibold uppercase tracking-[0.2em] text-[10px] opacity-80 mr-2">Impersonating</span>
        <span>You are viewing this workspace as a support session. All actions are audit-logged.</span>
      </div>
      <Button size="sm" variant="secondary" onClick={stop} data-testid="exit-impersonation-btn">
        <LogOut className="h-3.5 w-3.5 mr-1" />Exit impersonation
      </Button>
    </div>
  );
}
