// frontend/src/services/systemService.ts
import { useQuery } from "@tanstack/react-query";
import { api } from "./api";

export interface ServiceHealth {
  name: string;
  status: string;
  type: "live_probe" | "last_known";
  latency_ms?: number | null;
  details?: string | null;
}

export interface SystemHealthResponse {
  status: "HEALTHY" | "DEGRADED";
  mock_mode: boolean;
  provider_mode: string;
  environment: string;
  project_id?: string;
  active_models: {
    flash: string;
    transcribe: string;
  };
  trace_deep_link_template?: string;
  services: {
    cloud_sql?: ServiceHealth;
    cloud_storage?: ServiceHealth;
    vertex_ai?: ServiceHealth;
    file_search?: ServiceHealth;
    dlp?: ServiceHealth;
    [key: string]: any;
  };
}

export interface StageLatencyStats {
  mean: number;
  median: number;
  min: number;
  max: number;
  count: number;
}

export interface PipelineDiagnosticsResponse {
  end_to_end: StageLatencyStats;
  stages: Record<string, StageLatencyStats>;
}

export const systemService = {
  getHealth: () => api.get<SystemHealthResponse>("/api/system/health"),
  getDiagnostics: () => api.get<PipelineDiagnosticsResponse>("/api/system/diagnostics"),
};

export const SYSTEM_QUERY_KEYS = {
  all: ["system"] as const,
  health: () => [...SYSTEM_QUERY_KEYS.all, "health"] as const,
  diagnostics: () => [...SYSTEM_QUERY_KEYS.all, "diagnostics"] as const,
};

export function useSystemHealth() {
  return useQuery({
    queryKey: SYSTEM_QUERY_KEYS.health(),
    queryFn: systemService.getHealth,
    refetchInterval: 15000, // Background refresh every 15s
  });
}

export function useSystemDiagnostics() {
  return useQuery({
    queryKey: SYSTEM_QUERY_KEYS.diagnostics(),
    queryFn: systemService.getDiagnostics,
  });
}
