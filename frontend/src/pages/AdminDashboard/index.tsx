import React, { useState } from "react";
import { useAdminAnalytics } from "../../services/adminService";
import { LoadingState } from "../../components/shared/LoadingState";
import { ErrorState } from "../../components/shared/ErrorState";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import {
  LayoutDashboard,
  Calendar,
  PhoneCall,
  ShieldAlert,
  ShieldCheck,
  FileCheck2,
  TrendingUp,
  AlertTriangle,
  Users,
  RefreshCw,
  SlidersHorizontal,
  ChevronRight,
  Sparkles,
} from "lucide-react";

const SEVERITY_COLORS: Record<string, string> = {
  HIGH: "#ef4444",
  MEDIUM: "#f59e0b",
  LOW: "#3b82f6",
};

const PIE_COLORS = ["#10b981", "#ef4444", "#f59e0b", "#6366f1", "#8b5cf6", "#ec4899"];

export const AdminDashboard: React.FC = () => {
  // Preset or custom date range
  const todayStr = new Date().toISOString().split("T")[0];
  const sevenDaysAgo = new Date(Date.now() - 7 * 86400000).toISOString().split("T")[0];

  const [preset, setPreset] = useState<"7d" | "14d" | "30d" | "all">("7d");
  const [startDate, setStartDate] = useState(sevenDaysAgo);
  const [endDate, setEndDate] = useState(todayStr);

  const { data, isLoading, isError, error, refetch, isFetching } = useAdminAnalytics(
    preset === "all" ? undefined : startDate,
    preset === "all" ? undefined : endDate
  );

  const handlePresetChange = (newPreset: "7d" | "14d" | "30d" | "all") => {
    setPreset(newPreset);
    const now = new Date();
    if (newPreset === "7d") {
      setStartDate(new Date(now.getTime() - 7 * 86400000).toISOString().split("T")[0]);
      setEndDate(now.toISOString().split("T")[0]);
    } else if (newPreset === "14d") {
      setStartDate(new Date(now.getTime() - 14 * 86400000).toISOString().split("T")[0]);
      setEndDate(now.toISOString().split("T")[0]);
    } else if (newPreset === "30d") {
      setStartDate(new Date(now.getTime() - 30 * 86400000).toISOString().split("T")[0]);
      setEndDate(now.toISOString().split("T")[0]);
    }
  };

  if (isLoading) {
    return <LoadingState message="Aggregating executive multi-dimensional surveillance telemetry..." />;
  }

  if (isError || !data) {
    return (
      <ErrorState
        title="Failed to Load Executive Analytics"
        message={error instanceof Error ? error.message : "Analytics engine unreachable"}
        onRetry={() => refetch()}
      />
    );
  }

  const { kpis, timeline, severity_profile, categories, case_statuses, rm_risk } = data;

  // Outcome Donut Data
  const outcomeData = [
    { name: "Clean Calls", value: kpis.clean_calls },
    { name: "With Infractions", value: kpis.violation_calls },
  ];

  // Severity Profile Bar Data
  const severityData = [
    { name: "High Severity", count: severity_profile.HIGH, fill: "#ef4444" },
    { name: "Medium Severity", count: severity_profile.MEDIUM, fill: "#f59e0b" },
    { name: "Low Severity", count: severity_profile.LOW, fill: "#3b82f6" },
  ];

  return (
    <div className="space-y-6">
      {/* Header & Date Range Filter */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <LayoutDashboard className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              Executive Surveillance Analytics & Telemetry
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Real-time interactive intelligence charts across audio calls, compliance cases, RM distributions, and statutory coverage.
          </p>
        </div>

        {/* Date Filter Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Quick Presets */}
          <div className="flex items-center bg-slate-100 dark:bg-slate-800 p-1 rounded-lg text-xs font-semibold">
            {(["7d", "14d", "30d", "all"] as const).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => handlePresetChange(p)}
                className={`px-3 py-1.5 rounded-md transition-all ${preset === p
                    ? "bg-white dark:bg-slate-900 text-blue-600 dark:text-blue-400 shadow-sm"
                    : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
                  }`}
              >
                {p === "7d" ? "Last 7 Days" : p === "14d" ? "Last 14 Days" : p === "30d" ? "Last 30 Days" : "All Time"}
              </button>
            ))}
          </div>

          {/* Custom Date Pickers */}
          {preset !== "all" && (
            <div className="flex items-center gap-1.5 text-xs">
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="px-2.5 py-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md text-xs text-slate-700 dark:text-slate-300 focus:outline-none"
              />
              <span className="text-slate-400">to</span>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="px-2.5 py-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md text-xs text-slate-700 dark:text-slate-300 focus:outline-none"
              />
            </div>
          )}

          <button
            onClick={() => refetch()}
            disabled={isFetching}
            title="Refresh Analytics"
            className="p-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 rounded-lg text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${isFetching ? "animate-spin text-blue-500" : ""}`} />
          </button>
        </div>
      </div>

      {/* KPI Cards Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Calls */}
        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase">
            <span>Monitored Surveillance Calls</span>
            <PhoneCall className="w-4 h-4 text-blue-500" />
          </div>
          <p className="text-3xl font-mono font-bold text-slate-900 dark:text-slate-100 mt-2">
            {kpis.total_calls.toLocaleString()}
          </p>
          <div className="flex items-center justify-between mt-2 text-xs">
            <span className="text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" />
              {kpis.clean_rate}% Clean Rate
            </span>
            <span className="text-slate-400">{kpis.clean_calls} clean calls</span>
          </div>
        </div>

        {/* Total Cases */}
        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase">
            <span>Compliance Cases Opened</span>
            <ShieldAlert className="w-4 h-4 text-rose-500" />
          </div>
          <p className="text-3xl font-mono font-bold text-slate-900 dark:text-slate-100 mt-2">
            {kpis.total_cases.toLocaleString()}
          </p>
          <div className="flex items-center gap-2 mt-2 text-[11px] font-mono">
            <span className="px-1.5 py-0.5 rounded bg-rose-50 text-rose-700 dark:bg-rose-950/50 dark:text-rose-300 font-bold border border-rose-200 dark:border-rose-900">
              HIGH: {severity_profile.HIGH}
            </span>
            <span className="px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300 font-bold border border-amber-200 dark:border-amber-900">
              MED: {severity_profile.MEDIUM}
            </span>
            <span className="px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300 font-bold border border-blue-200 dark:border-blue-900">
              LOW: {severity_profile.LOW}
            </span>
          </div>
        </div>

        {/* Total Findings */}
        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase">
            <span>Flagged Infractions</span>
            <AlertTriangle className="w-4 h-4 text-amber-500" />
          </div>
          <p className="text-3xl font-mono font-bold text-amber-600 dark:text-amber-400 mt-2">
            {kpis.total_findings.toLocaleString()}
          </p>
          <div className="flex items-center justify-between mt-2 text-xs text-slate-500">
            <span>From {kpis.violation_calls} non-compliant calls</span>
            <span className="font-semibold text-rose-600">Action Required</span>
          </div>
        </div>

        {/* Statutory Corpus */}
        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase">
            <span>Statutory Regulations Corpus</span>
            <FileCheck2 className="w-4 h-4 text-emerald-500" />
          </div>
          <p className="text-3xl font-mono font-bold text-slate-900 dark:text-slate-100 mt-2">
            {kpis.statutory_chunks.toLocaleString()}
          </p>
          <div className="flex items-center justify-between mt-2 text-xs text-slate-500">
            <span>{kpis.statutory_documents} Master Directives</span>
            <span className="text-emerald-600 font-semibold">100% Synced</span>
          </div>
        </div>
      </div>

      {/* ==================================================================== */}
      {/* CHARTS ROW 1: Large Timeline Area Chart & Surveillance Integrity */}
      {/* ==================================================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Timeline Chart */}
        <div className="lg:col-span-2 bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-blue-600" />
                Call Surveillance Volume & Infraction Trajectory
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Daily trend showing total monitored calls vs infractions detected
              </p>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1.5 text-blue-600 font-semibold">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-600" /> Total Calls
              </span>
              <span className="flex items-center gap-1.5 text-rose-500 font-semibold">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500" /> Infractions
              </span>
            </div>
          </div>

          <div className="h-72 w-full mt-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeline} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="callsGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="violGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.4} />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    border: "1px solid #1e293b",
                    borderRadius: "8px",
                    color: "#f8fafc",
                    fontSize: "12px",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="total_calls"
                  name="Total Calls"
                  stroke="#3b82f6"
                  strokeWidth={2.5}
                  fillOpacity={1}
                  fill="url(#callsGrad)"
                />
                <Area
                  type="monotone"
                  dataKey="violation_calls"
                  name="Infractions"
                  stroke="#ef4444"
                  strokeWidth={2.5}
                  fillOpacity={1}
                  fill="url(#violGrad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Outcome Donut Chart */}
        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col">
          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            Surveillance Clean Rate Ratio
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">Ratio of clean calls vs non-compliant calls</p>

          <div className="h-64 w-full mt-2 relative flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={outcomeData}
                  cx="50%"
                  cy="50%"
                  innerRadius={65}
                  outerRadius={95}
                  paddingAngle={5}
                  dataKey="value"
                >
                  <Cell fill="#10b981" />
                  <Cell fill="#ef4444" />
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    border: "1px solid #1e293b",
                    borderRadius: "8px",
                    color: "#f8fafc",
                    fontSize: "12px",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            {/* Center Label */}
            <div className="absolute text-center pointer-events-none">
              <span className="text-2xl font-mono font-bold text-slate-900 dark:text-slate-100">
                {kpis.clean_rate}%
              </span>
              <p className="text-[10px] text-slate-400 font-semibold uppercase">Clean</p>
            </div>
          </div>

          <div className="flex items-center justify-around text-xs font-semibold pt-2 border-t border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-emerald-500" />
              <span className="text-slate-700 dark:text-slate-300">Clean: {kpis.clean_calls}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-rose-500" />
              <span className="text-slate-700 dark:text-slate-300">Violations: {kpis.violation_calls}</span>
            </div>
          </div>
        </div>
      </div>

      {/* ==================================================================== */}
      {/* CHARTS ROW 2: Severity Bar Chart, Category Distribution, Case Status */}
      {/* ==================================================================== */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Severity Profile Bar Chart */}
        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col">
          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-500" />
            Infraction Severity Profile
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">Audit findings categorized by risk tier</p>

          <div className="h-60 w-full mt-3">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={severityData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.3} />
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    border: "1px solid #1e293b",
                    borderRadius: "8px",
                    color: "#f8fafc",
                    fontSize: "12px",
                  }}
                />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {severityData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Infractions by Category Chart */}
        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col">
          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-purple-600" />
            Violations by Regulatory Clause
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">Top compliance breach categories</p>

          <div className="h-60 w-full mt-3">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={categories.slice(0, 5)}
                layout="vertical"
                margin={{ top: 10, right: 20, left: 10, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.3} />
                <XAxis type="number" stroke="#94a3b8" fontSize={10} tickLine={false} />
                <YAxis
                  dataKey="category"
                  type="category"
                  stroke="#94a3b8"
                  fontSize={10}
                  tickLine={false}
                  width={110}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    border: "1px solid #1e293b",
                    borderRadius: "8px",
                    color: "#f8fafc",
                    fontSize: "12px",
                  }}
                />
                <Bar dataKey="count" fill="#8b5cf6" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Case Lifecycle Status Pie Chart */}
        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col">
          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-blue-600" />
            Compliance Case Resolution Status
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">Active investigation & review states</p>

          <div className="h-60 w-full mt-3">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={case_statuses}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  dataKey="count"
                  nameKey="status"
                  label={({ name, percent }: any) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {case_statuses.map((entry, index) => (
                    <Cell key={`cell-status-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    border: "1px solid #1e293b",
                    borderRadius: "8px",
                    color: "#f8fafc",
                    fontSize: "12px",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* ==================================================================== */}
      {/* CHARTS ROW 3: RM Surveillance Load & Infraction Risk Chart */}
      {/* ==================================================================== */}
      <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Users className="w-4 h-4 text-blue-600" />
              Relationship Manager (RM) Surveillance Load & Infraction Rate
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Call volume handled vs infraction findings per advisor
            </p>
          </div>
        </div>

        <div className="h-64 w-full mt-3">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={rm_risk} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.3} />
              <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} tickLine={false} />
              <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#0f172a",
                  border: "1px solid #1e293b",
                  borderRadius: "8px",
                  color: "#f8fafc",
                  fontSize: "12px",
                }}
              />
              <Legend />
              <Bar dataKey="calls" name="Calls Handled" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              <Bar dataKey="violations" name="Infraction Calls" fill="#ef4444" radius={[4, 4, 0, 0]} />
              <Bar dataKey="findings" name="Total Findings" fill="#f59e0b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
