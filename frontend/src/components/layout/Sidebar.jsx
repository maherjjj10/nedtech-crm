import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";

import {
  LayoutDashboard,
  Users,
  TrendingUp,
  ListChecks,
  FileText,
  FileSignature,
  Package,
  UserCog,
  Sparkles,
  Settings,
  LogOut,
  Sun,
  Moon,
  CreditCard,
  Menu,
  X,
  Shield,
  User,
  Truck,
  ChevronLeft,
  ChevronRight,
  Search,
  BriefcaseBusiness,
} from "lucide-react";

import { Button } from "../ui/button";
import { useTheme } from "../../lib/themeContext";
import { useAuth } from "../../lib/authContext";
import { Avatar, AvatarFallback } from "../ui/avatar";
import { initials } from "../../lib/format";
import LanguageSwitcher from "./LanguageSwitcher";
import { useLanguage } from "../../i18n";


/*
 * Navigation groups
 *
 * Every labelKey MUST match the translation key.
 */
const NAV_GROUPS = [
  {
    title: "overview",
    fallbackTitle: "Overview",
    items: [
      {
        to: "/",
        labelKey: "dashboard",
        icon: LayoutDashboard,
        testid: "nav-dashboard",
        end: true,
        permission: "dashboard",
      },
    ],
  },

  {
    title: "sales",
    fallbackTitle: "Sales",
    items: [
      {
        to: "/clients",
        labelKey: "clients",
        icon: Users,
        testid: "nav-clients",
        permission: "crm",
      },
      {
        to: "/pipeline",
        labelKey: "pipeline",
        icon: TrendingUp,
        testid: "nav-pipeline",
        permission: "sales",
      },
      {
        to: "/tasks",
        labelKey: "tasks",
        icon: ListChecks,
        testid: "nav-tasks",
        permission: "tasks",
      },
    ],
  },

  {
    title: "management",
    fallbackTitle: "Management",
    items: [
      {
        to: "/suppliers",
        labelKey: "suppliers",
        icon: Truck,
        testid: "nav-suppliers",
        permission: "crm",
      },
      {
        to: "/products",
        labelKey: "products",
        icon: Package,
        testid: "nav-products",
        permission: "products",
      },
      {
        to: "/employees",
        labelKey: "employees",
        icon: UserCog,
        testid: "nav-employees",
        permission: "hr",
      },
    ],
  },

  {
    title: "finance",
    fallbackTitle: "Finance",
    items: [
      {
        to: "/finance",
        labelKey: "finance",
        icon: FileText,
        testid: "nav-finance",
        permission: "finance",
      },
      {
        to: "/contracts",
        labelKey: "contracts",
        icon: FileSignature,
        testid: "nav-contracts",
        permission: "contracts",
      },
      {
        to: "/billing",
        labelKey: "billing",
        icon: CreditCard,
        testid: "nav-billing",
        permission: "billing",
      },
    ],
  },

  {
    title: "administration",
    fallbackTitle: "Administration",
    items: [
      {
        to: "/ai",
        labelKey: "aiAssistant",
        icon: Sparkles,
        testid: "nav-ai",
        permission: "ai",
      },
      {
        to: "/profile",
        labelKey: "profile",
        icon: User,
        testid: "nav-profile",
        permission: "profile",
      },
      {
        to: "/settings",
        labelKey: "settings",
        icon: Settings,
        testid: "nav-settings",
        permission: "settings",
      },
    ],
  },
];


function SidebarContent({
  onNavigate,
  collapsed,
  onToggleCollapse,
}) {
  const { theme, toggle } = useTheme();

  const {
    user,
    tenant,
    logout,
    can,
    isPlatformAdmin,
  } = useAuth();

  const { t } = useLanguage();

  const location = useLocation();


  /*
   * Check whether a route is currently active.
   */
  const isActive = (item) => {
    if (item.end) {
      return location.pathname === item.to;
    }

    return (
      location.pathname === item.to ||
      location.pathname.startsWith(item.to + "/")
    );
  };


  /*
   * Platform administration is added
   * as a separate navigation item.
   */
  const platformItem = isPlatformAdmin
    ? {
        to: "/platform",
        labelKey: "platformAdmin",
        fallbackLabel: "Platform Admin",
        icon: Shield,
        testid: "nav-platform",
      }
    : null;


  return (
    <div className="flex flex-col h-full">


      {/* =====================================================
          HEADER
      ====================================================== */}

      <div
        className={`border-b border-border transition-all duration-200 ${
          collapsed ? "px-3 py-4" : "px-4 py-4"
        }`}
      >

        <div
          className={`flex items-center ${
            collapsed ? "justify-center" : "gap-3"
          }`}
        >

          {/* Logo */}

          <div
            className="h-9 w-9 shrink-0 rounded-lg bg-foreground text-background flex items-center justify-center font-black shadow-sm"
            data-testid="brand-mark"
          >
            N
          </div>


          {/* Workspace name */}

          {!collapsed && (
            <div className="leading-tight min-w-0 flex-1">

              <div
                className="text-sm font-semibold truncate"
                data-testid="workspace-name"
              >
                {tenant?.name || t("workspace")}
              </div>

              <div className="n-overline text-[10px] mt-0.5">
                NED Tech CRM
              </div>

            </div>
          )}


          {/* Collapse button */}

          {!collapsed && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 shrink-0"
              onClick={onToggleCollapse}
              title="Collapse sidebar"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
          )}

        </div>


        {/* Expand button */}

        {collapsed && (
          <div className="flex justify-center mt-3">

            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={onToggleCollapse}
              title="Expand sidebar"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>

          </div>
        )}

      </div>


      {/* =====================================================
          QUICK SEARCH
      ====================================================== */}

      {!collapsed && (
        <div className="px-3 pt-3">

          <button
            type="button"
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-border bg-background/50 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors text-sm"
          >

            <Search className="h-4 w-4 shrink-0" />

            <span className="flex-1 text-left">
              Search
            </span>

            <kbd className="hidden lg:inline-flex items-center rounded border border-border px-1.5 py-0.5 text-[10px] font-medium">
              Ctrl K
            </kbd>

          </button>

        </div>
      )}


      {/* =====================================================
          NAVIGATION
      ====================================================== */}

      <nav className="flex-1 px-3 py-4 n-scroll overflow-y-auto">

        <div className="space-y-5">

          {NAV_GROUPS.map((group) => {

            const visibleItems = group.items.filter((item) =>
              can(item.permission)
            );

            if (!visibleItems.length) {
              return null;
            }


            return (
              <div key={group.title}>

                {/* Group title */}

                {!collapsed && (
                  <div className="px-3 mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
                    {group.title === "overview"
                      ? "Overview"
                      : group.title === "sales"
                      ? "Sales"
                      : group.title === "management"
                      ? "Management"
                      : group.title === "finance"
                      ? "Finance"
                      : "Administration"}
                  </div>
                )}


                <div className="space-y-1">

                  {visibleItems.map((item) => {

                    const Icon = item.icon;
                    const active = isActive(item);

                    const label = item.labelKey
                      ? t(item.labelKey)
                      : item.fallbackLabel;


                    return (
                      <NavLink
                        key={item.to}
                        to={item.to}
                        onClick={onNavigate}
                        data-testid={item.testid}
                        title={collapsed ? label : undefined}
                        className={`group relative flex items-center rounded-lg text-sm transition-all duration-150 ${
                          collapsed
                            ? "justify-center px-2 py-2.5"
                            : "gap-3 px-3 py-2.5"
                        } ${
                          active
                            ? "bg-accent text-accent-foreground font-medium shadow-sm"
                            : "text-muted-foreground hover:bg-accent/70 hover:text-accent-foreground"
                        }`}
                      >

                        {/* Active indicator */}

                        {active && (
                          <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-full bg-foreground" />
                        )}


                        <Icon
                          className={`h-4 w-4 shrink-0 transition-transform duration-150 ${
                            active
                              ? "scale-105"
                              : "group-hover:scale-105"
                          }`}
                        />


                        {!collapsed && (
                          <span className="truncate">
                            {label}
                          </span>
                        )}

                      </NavLink>
                    );
                  })}

                </div>

              </div>
            );
          })}


          {/* =================================================
              PLATFORM ADMIN
          ================================================== */}

          {platformItem && (
            <div>

              {!collapsed && (
                <div className="px-3 mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
                  Platform
                </div>
              )}

              <NavLink
                to={platformItem.to}
                onClick={onNavigate}
                data-testid={platformItem.testid}
                title={
                  collapsed
                    ? platformItem.fallbackLabel
                    : undefined
                }
                className={`group relative flex items-center rounded-lg text-sm transition-all duration-150 ${
                  collapsed
                    ? "justify-center px-2 py-2.5"
                    : "gap-3 px-3 py-2.5"
                } ${
                  isActive(platformItem)
                    ? "bg-accent text-accent-foreground font-medium shadow-sm"
                    : "text-muted-foreground hover:bg-accent/70 hover:text-accent-foreground"
                }`}
              >

                <Shield className="h-4 w-4 shrink-0" />

                {!collapsed && (
                  <span>
                    {platformItem.labelKey
                      ? t(platformItem.labelKey)
                      : platformItem.fallbackLabel}
                  </span>
                )}

              </NavLink>

            </div>
          )}

        </div>

      </nav>


      {/* =====================================================
          USER FOOTER
      ====================================================== */}

      <div
        className={`border-t border-border ${
          collapsed ? "p-2" : "p-3"
        }`}
      >

        {/* User */}

        <div
          className={`flex items-center ${
            collapsed
              ? "justify-center"
              : "gap-3 px-2"
          } py-2`}
        >

          <Avatar className="h-8 w-8 shrink-0">

            <AvatarFallback className="text-xs bg-foreground text-background">
              {initials(
                user?.name ||
                user?.email
              )}
            </AvatarFallback>

          </Avatar>


          {!collapsed && (
            <div className="flex-1 min-w-0">

              <div
                className="text-sm font-medium truncate"
                data-testid="user-name"
              >
                {user?.name}
              </div>

              <div className="text-xs text-muted-foreground truncate">
                {user?.email}
              </div>

            </div>
          )}

        </div>


        {/* Language */}

        {!collapsed && (
          <div className="mt-2">
            <LanguageSwitcher />
          </div>
        )}


        {/* Theme + Logout */}

        <div
          className={`flex gap-2 mt-2 ${
            collapsed
              ? "flex-col"
              : "flex-row"
          }`}
        >

          <Button
            variant="outline"
            size="sm"
            className={
              collapsed
                ? "w-full h-9"
                : "flex-1"
            }
            onClick={toggle}
            data-testid="toggle-theme"
            title={
              theme === "dark"
                ? "Light"
                : "Dark"
            }
          >

            {theme === "dark" ? (
              <Sun className="h-4 w-4" />
            ) : (
              <Moon className="h-4 w-4" />
            )}

            {!collapsed && (
              <span className="ml-2 text-xs">
                {theme === "dark"
                  ? "Light"
                  : "Dark"}
              </span>
            )}

          </Button>


          <Button
            variant="ghost"
            size="sm"
            className={
              collapsed
                ? "w-full h-9"
                : ""
            }
            onClick={logout}
            data-testid="logout-btn"
            title={t("logout")}
          >

            <LogOut className="h-4 w-4" />

          </Button>

        </div>

      </div>

    </div>
  );
}


/* =========================================================
   MAIN SIDEBAR
========================================================= */

export default function Sidebar() {

  const [open, setOpen] = useState(false);

  const [collapsed, setCollapsed] = useState(false);


  return (
    <>


      {/* =====================================================
          MOBILE TOP BAR
      ====================================================== */}

      <div className="md:hidden flex items-center justify-between px-4 py-3 border-b border-border bg-card">

        <div className="flex items-center gap-2">

          <div className="h-8 w-8 rounded-lg bg-foreground text-background flex items-center justify-center font-black text-sm">
            N
          </div>

          <div className="text-sm font-semibold">
            NED Tech CRM
          </div>

        </div>


        <Button
          variant="ghost"
          size="icon"
          onClick={() => setOpen(true)}
          data-testid="mobile-menu-btn"
        >

          <Menu className="h-5 w-5" />

        </Button>

      </div>


      {/* =====================================================
          DESKTOP SIDEBAR
      ====================================================== */}

      <aside
        className={`hidden md:flex flex-col shrink-0 border-r border-border bg-card h-screen transition-all duration-200 ${
          collapsed
            ? "w-[72px]"
            : "w-64"
        }`}
        data-testid="app-sidebar"
      >

        <SidebarContent
          collapsed={collapsed}
          onToggleCollapse={() =>
            setCollapsed((value) => !value)
          }
        />

      </aside>


      {/* =====================================================
          MOBILE SIDEBAR
      ====================================================== */}

      {open && (
        <>

          {/* Overlay */}

          <div
            className="md:hidden fixed inset-0 z-50 bg-black/60 backdrop-blur-[1px]"
            onClick={() => setOpen(false)}
          />


          {/* Sidebar */}

          <aside
            className="md:hidden fixed inset-y-0 left-0 z-50 flex flex-col w-72 border-r border-border bg-card animate-in slide-in-from-left duration-200 shadow-xl"
            data-testid="mobile-sidebar"
          >

            {/* Close */}

            <div className="flex justify-end p-2">

              <Button
                variant="ghost"
                size="icon"
                onClick={() => setOpen(false)}
                data-testid="mobile-close-btn"
              >

                <X className="h-5 w-5" />

              </Button>

            </div>


            <div className="flex-1 min-h-0">

              <SidebarContent
                collapsed={false}
                onNavigate={() =>
                  setOpen(false)
                }
              />

            </div>

          </aside>

        </>
      )}

    </>
  );
}