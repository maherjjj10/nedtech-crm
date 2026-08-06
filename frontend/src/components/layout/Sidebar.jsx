import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { LayoutDashboard, Users, TrendingUp, ListChecks, FileText, FileSignature, Package, UserCog, Sparkles, Settings, LogOut, Sun, Moon, CreditCard, Menu, X, Shield, User } from "lucide-react";
import { Button } from "../ui/button";
import { useTheme } from "../../lib/themeContext";
import { useAuth } from "../../lib/authContext";
import { Avatar, AvatarFallback } from "../ui/avatar";
import { initials } from "../../lib/format";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, testid: "nav-dashboard", end: true },
  { to: "/clients", label: "Clients", icon: Users, testid: "nav-clients" },
  { to: "/pipeline", label: "Sales Pipeline", icon: TrendingUp, testid: "nav-pipeline" },
  { to: "/tasks", label: "Tasks", icon: ListChecks, testid: "nav-tasks" },
  { to: "/finance", label: "Finance", icon: FileText, testid: "nav-finance" },
  { to: "/contracts", label: "Contracts", icon: FileSignature, testid: "nav-contracts" },
  { to: "/products", label: "Products & Services", icon: Package, testid: "nav-products" },
  { to: "/employees", label: "Employees", icon: UserCog, testid: "nav-employees" },
  { to: "/ai", label: "AI Assistant", icon: Sparkles, testid: "nav-ai" },
  { to: "/billing", label: "Billing", icon: CreditCard, testid: "nav-billing" },
  { to: "/profile", label: "Profile", icon: User, testid: "nav-profile" },
  { to: "/settings", label: "Settings", icon: Settings, testid: "nav-settings" },
];

function SidebarContent({ onNavigate }) {
  const { theme, toggle } = useTheme();
  const { user, tenant, logout } = useAuth();
  const location = useLocation();

  const isPlatformAdmin = user?.platform_role === "platform_owner" || user?.platform_role === "super_admin";
  const navItems = isPlatformAdmin
    ? [...NAV, { to: "/platform", label: "Platform Admin", icon: Shield, testid: "nav-platform" }]
    : NAV;

  return (
    <>
      <div className="px-6 py-6 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-md bg-foreground text-background flex items-center justify-center font-black" data-testid="brand-mark">
            N
          </div>
          <div className="leading-tight">
            <div className="text-sm font-semibold" data-testid="workspace-name">{tenant?.name || "Workspace"}</div>
            <div className="n-overline text-[10px]">NED Tech CRM</div>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1 n-scroll overflow-y-auto">
        {navItems.map((n) => {
          const Icon = n.icon;
          const active = n.end ? location.pathname === n.to : (location.pathname === n.to || location.pathname.startsWith(n.to + "/"));
          return (
            <NavLink
              key={n.to}
              to={n.to}
              onClick={onNavigate}
              data-testid={n.testid}
              className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors duration-150 ${
                active
                  ? "bg-accent text-accent-foreground font-medium"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{n.label}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="border-t border-border p-3 space-y-2">
        <div className="flex items-center gap-3 px-2 py-2">
          <Avatar className="h-8 w-8">
            <AvatarFallback className="text-xs bg-foreground text-background">{initials(user?.name || user?.email)}</AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium truncate" data-testid="user-name">{user?.name}</div>
            <div className="text-xs text-muted-foreground truncate">{user?.email}</div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="flex-1" onClick={toggle} data-testid="toggle-theme">
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            <span className="ml-2 text-xs">{theme === "dark" ? "Light" : "Dark"}</span>
          </Button>
          <Button variant="ghost" size="sm" onClick={logout} data-testid="logout-btn">
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </>
  );
}

export default function Sidebar() {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* Mobile top bar with hamburger */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-40 flex items-center justify-between px-4 h-14 border-b border-border bg-background">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-md bg-foreground text-background flex items-center justify-center font-black text-sm">N</div>
          <div className="text-sm font-semibold">NED Tech CRM</div>
        </div>
        <Button variant="ghost" size="icon" onClick={() => setOpen(true)} data-testid="mobile-menu-btn">
          <Menu className="h-5 w-5" />
        </Button>
      </div>

      {/* Desktop sidebar */}
      <aside className="hidden md:flex flex-col w-64 shrink-0 border-r border-border bg-card" data-testid="app-sidebar">
        <SidebarContent />
      </aside>

      {/* Mobile drawer */}
      {open && (
        <>
          <div className="md:hidden fixed inset-0 z-50 bg-black/60" onClick={() => setOpen(false)} />
          <aside className="md:hidden fixed inset-y-0 left-0 z-50 flex flex-col w-72 border-r border-border bg-card animate-in slide-in-from-left duration-200" data-testid="mobile-sidebar">
            <div className="flex justify-end p-2">
              <Button variant="ghost" size="icon" onClick={() => setOpen(false)} data-testid="mobile-close-btn">
                <X className="h-5 w-5" />
              </Button>
            </div>
            <SidebarContent onNavigate={() => setOpen(false)} />
          </aside>
        </>
      )}
    </>
  );
}
