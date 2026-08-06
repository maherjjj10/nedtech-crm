import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import { Toaster } from "../ui/sonner";

export default function AppShell() {
  return (
    <div className="flex h-screen bg-background text-foreground">
      <Sidebar />
      <main className="flex-1 overflow-y-auto n-scroll pt-14 md:pt-0" data-testid="app-main">
        <Outlet />
      </main>
      <Toaster position="top-right" richColors />
    </div>
  );
}
