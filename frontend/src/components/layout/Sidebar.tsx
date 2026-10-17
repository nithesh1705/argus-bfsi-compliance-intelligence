import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Bot,
  PhoneCall,
  ShieldAlert,
  Users,
  FileCheck2,
  Settings,
  Shield,
  Activity,
  ChevronLeft,
  ChevronRight,
  Database,
  LogOut,
} from "lucide-react";
import { cn } from "../../lib/utils";
import { useSidebar } from "../../context/SidebarContext";
import { useAuth } from "../../context/AuthContext";
import { OwlThemeToggle } from "./OwlThemeToggle";

export const Sidebar: React.FC = () => {
  const { isCollapsed, toggleSidebar } = useSidebar();
  const { user, openLogoutModal } = useAuth();

  const isAdmin = user?.role === "Admin";

  const navItems = isAdmin
    ? [
        { label: "Executive Analytics", path: "/", icon: LayoutDashboard },
        { label: "Master Data CRUD", path: "/admin/manage", icon: Database },
        { label: "Regulations", path: "/regulations", icon: FileCheck2 },
        { label: "Observability", path: "/observability", icon: Activity },
        { label: "Settings", path: "/settings", icon: Settings },
      ]
    : [
        { label: "Operational Dashboard", path: "/", icon: LayoutDashboard },
        { label: "AI Investigation", path: "/ai-investigation", icon: Bot },
        { label: "Calls", path: "/calls", icon: PhoneCall },
        { label: "Compliance Cases", path: "/cases", icon: ShieldAlert },
        { label: "RM Analytics", path: "/rm-analytics", icon: Users },
        { label: "Regulations", path: "/regulations", icon: FileCheck2 },
        { label: "Settings", path: "/settings", icon: Settings },
      ];

  return (
    <aside
      className={cn(
        "bg-white dark:bg-slate-900 border-r border-slate-200/90 dark:border-slate-800/90 flex flex-col shrink-0 transition-all duration-300 ease-in-out z-30",
        "h-screen sticky top-0",
        "shadow-[4px_0_24px_-4px_rgba(0,0,0,0.06)] dark:shadow-[4px_0_24px_-4px_rgba(0,0,0,0.3)]",
        isCollapsed ? "w-[68px]" : "w-64"
      )}
    >
      {/* Brand Header */}
      <div
        className={cn(
          "h-14 flex items-center border-b border-slate-200 dark:border-slate-800 transition-all duration-300",
          isCollapsed ? "justify-center px-3" : "gap-2.5 px-6"
        )}
      >
        <img
          src="/icon.png"
          alt="ARGUS Logo"
          className="w-8 h-8 rounded-lg object-contain shadow-md shrink-0 ring-1 ring-slate-200 dark:ring-slate-800"
        />

        {/* Brand Text — only visible when expanded */}
        <div
          className={cn(
            "overflow-hidden transition-all duration-300",
            isCollapsed ? "w-0 opacity-0" : "w-auto opacity-100"
          )}
        >
          <h1 className="font-bold text-sm tracking-wider text-slate-900 dark:text-slate-100 flex items-center gap-1.5 whitespace-nowrap">
            ARGUS
          </h1>
          <p className="text-[10px] text-slate-400 tracking-tight whitespace-nowrap">
            Compliance Intelligence AI
          </p>
        </div>
      </div>

      {/* Navigation list */}
      <nav className="flex-1 px-2 py-4 space-y-0.5 overflow-y-auto overflow-x-hidden">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              title={isCollapsed ? item.label : undefined}
              className={({ isActive }) =>
                cn(
                  "flex items-center rounded-md text-xs font-medium transition-all duration-200 group relative",
                  isCollapsed ? "px-0 py-2.5 justify-center" : "gap-3 px-3.5 py-2.5",
                  isActive
                    ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 font-semibold shadow-sm"
                    : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/60"
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icon
                    className={cn(
                      "w-4 h-4 shrink-0 transition-colors",
                      isActive
                        ? "text-red-400 dark:text-red-600"
                        : "text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300"
                    )}
                  />

                  {/* Nav label — only visible when expanded */}
                  <span
                    className={cn(
                      "overflow-hidden whitespace-nowrap transition-all duration-300",
                      isCollapsed ? "w-0 opacity-0" : "w-auto opacity-100"
                    )}
                  >
                    {item.label}
                  </span>

                  {/* Tooltip on collapsed state */}
                  {isCollapsed && (
                    <div className="absolute left-full ml-3 px-2 py-1 bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 text-xs rounded-md opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-150 whitespace-nowrap z-50 shadow-lg">
                      {item.label}
                    </div>
                  )}
                </>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* 3. Owl Theme Toggle Area */}
      <div className={cn("transition-all duration-300 shrink-0", isCollapsed ? "px-2 py-2" : "px-3 py-2")}>
        <OwlThemeToggle isCollapsed={isCollapsed} />
      </div>

      {/* 4. Thin Horizontal Divider */}
      <div className="mx-3 border-t border-slate-200 dark:border-slate-800 shrink-0" />

      {/* 5. Logout Action Area (Replaces SEBI / AMFI Section) */}
      <div className="shrink-0">
        {!isCollapsed ? (
          <div className="px-3 py-1.5">
            <button
              type="button"
              onClick={openLogoutModal}
              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 border border-transparent hover:border-red-200/50 dark:hover:border-red-900/40 transition-colors cursor-pointer group"
            >
              <LogOut className="w-4 h-4 shrink-0 transition-transform group-hover:-translate-x-0.5" />
              <span className="truncate">Sign Out</span>
            </button>
          </div>
        ) : (
          <div className="py-1.5 flex justify-center">
            <button
              type="button"
              onClick={openLogoutModal}
              title="Sign Out"
              className="p-2 rounded-lg text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Collapse / Expand Toggle Button */}
        <div className={cn("pb-3", isCollapsed ? "flex justify-center" : "px-3")}>
          <button
            type="button"
            onClick={toggleSidebar}
            title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
            className={cn(
              "flex items-center gap-2 rounded-md text-xs font-medium text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-all cursor-pointer",
              isCollapsed ? "p-2 justify-center" : "w-full px-3 py-2"
            )}
          >
            {isCollapsed ? (
              <ChevronRight className="w-4 h-4 shrink-0" />
            ) : (
              <>
                <ChevronLeft className="w-4 h-4 shrink-0" />
                <span>Collapse</span>
              </>
            )}
          </button>
        </div>
      </div>
    </aside>
  );
};
