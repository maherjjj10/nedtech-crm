import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import ImpersonationBanner from "./ImpersonationBanner";
import { Toaster } from "../ui/sonner";

export default function AppShell() {
  return (
    <div className="app-shell flex min-h-[100dvh] w-full overflow-hidden bg-background text-foreground">
      <Sidebar />

      <main
        className="
          app-main
          min-w-0
          flex-1
          overflow-x-hidden
          overflow-y-auto
          n-scroll
          pt-14
          lg:pt-0
        "
        data-testid="app-main"
      >
        <ImpersonationBanner />

        <Outlet />
      </main>

      <Toaster
        position="top-right"
        richColors
        closeButton
        toastOptions={{
          classNames: {
            toast: "max-w-[calc(100vw-2rem)]",
          },
        }}
      />
    </div>
  );
}