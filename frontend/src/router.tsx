import React from "react";
import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { AdminDashboard } from "./pages/AdminDashboard";
import { AdminManagement } from "./pages/AdminManagement";
import { AIInvestigation } from "./pages/AIInvestigation";
import { Calls } from "./pages/Calls";
import { CallDetail } from "./pages/Calls/CallDetail";
import { ComplianceCases } from "./pages/ComplianceCases";
import { CaseDetail } from "./pages/ComplianceCases/CaseDetail";
import { RMAnalytics } from "./pages/RMAnalytics";
import { RMDetail } from "./pages/RMAnalytics/RMDetail";
import { Regulations } from "./pages/Regulations";
import { Settings } from "./pages/Settings";
import { Observability } from "./pages/Observability";
import { useAuth } from "./context/AuthContext";
import { usePageTitle } from "./hooks/usePageTitle";

const RootWrapper: React.FC = () => {
  usePageTitle();
  return <Outlet />;
};

const DashboardRoute: React.FC = () => {
  const { user } = useAuth();
  if (user?.role === "Admin") {
    return <AdminDashboard />;
  }
  return <Dashboard />;
};

export const router = createBrowserRouter([
  {
    element: <RootWrapper />,
    children: [
      {
        path: "/login",
        element: <Login />,
      },
      {
        path: "/",
        element: (
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        ),
        children: [
      {
        index: true,
        element: <DashboardRoute />,
      },
      {
        path: "admin/manage",
        element: <AdminManagement />,
      },
      {
        path: "ai-investigation",
        element: <AIInvestigation />,
      },
      {
        path: "calls",
        element: <Calls />,
      },
      {
        path: "calls/:callId",
        element: <CallDetail />,
      },
      {
        path: "cases",
        element: <ComplianceCases />,
      },
      {
        path: "cases/:caseId",
        element: <CaseDetail />,
      },
      {
        path: "rm-analytics",
        element: <RMAnalytics />,
      },
      {
        path: "rm-analytics/:rmId",
        element: <RMDetail />,
      },
      {
        path: "regulations",
        element: <Regulations />,
      },
      {
        path: "settings",
        element: <Settings />,
      },
      {
        path: "observability",
        element: <Observability />,
      },
      {
        path: "*",
        element: <Navigate to="/" replace />,
      },
    ],
  },
  ],
},
]);
