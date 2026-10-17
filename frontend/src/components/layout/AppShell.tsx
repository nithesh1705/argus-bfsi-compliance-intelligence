import React from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { SidebarProvider } from "../../context/SidebarContext";
import { LogoutModal } from "../common/LogoutModal";

export const AppShell: React.FC = () => {
  return (
    <SidebarProvider>
      <div className="flex h-screen overflow-hidden bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 antialiased font-sans">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0 h-screen overflow-y-auto transition-all duration-300 relative">
          <Topbar />
          <main className="flex-1 p-6">
            <Outlet />
          </main>
        </div>
      </div>
      <LogoutModal />
    </SidebarProvider>
  );
};
