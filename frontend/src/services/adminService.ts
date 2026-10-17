// frontend/src/services/adminService.ts
import { api } from "./api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

export interface AdminAnalyticsData {
  kpis: {
    total_calls: number;
    clean_calls: number;
    violation_calls: number;
    clean_rate: number;
    total_cases: number;
    total_findings: number;
    statutory_documents: number;
    statutory_chunks: number;
  };
  timeline: Array<{
    date: string;
    total_calls: number;
    clean_calls: number;
    violation_calls: number;
    total_findings: number;
  }>;
  severity_profile: {
    HIGH: number;
    MEDIUM: number;
    LOW: number;
  };
  categories: Array<{
    category: string;
    count: number;
  }>;
  case_statuses: Array<{
    status: string;
    count: number;
  }>;
  rm_risk: Array<{
    rm_id: string;
    name: string;
    branch: string;
    calls: number;
    violations: number;
    findings: number;
    risk_score: number;
  }>;
}

export interface UserItem {
  user_id: string;
  username: string;
  email: string;
  role: string;
  team: string;
  access_level: string;
  full_name: string;
  is_active: boolean;
  last_login_at?: string;
  created_at?: string;
}

export interface RMItem {
  rm_id: string;
  full_name: string;
  branch: string;
  joined_date?: string;
  active: boolean;
}

export interface CustomerItem {
  customer_id: string;
  full_name: string;
  mobile_number: string;
  risk_profile: string;
  investment_experience: string;
  kyc_status: string;
}

export interface ProductItem {
  product_id: string;
  product_name: string;
  risk_class: string;
  suitable_risk_profiles: string;
  disclosure_requirements: string;
}

export interface AuthorityItem {
  authority_id: string;
  name: string;
  short_code: string;
  jurisdiction?: string;
  website_url?: string;
  description?: string;
  active: boolean;
  document_count?: number;
  created_at?: string;
}

export const adminService = {
  getAnalytics: (startDate?: string, endDate?: string) =>
    api.get<AdminAnalyticsData>("/api/admin/analytics", {
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    }),

  // Users
  listUsers: () => api.get<UserItem[]>("/api/admin/users"),
  createUser: (data: Partial<UserItem> & { password: string }) => api.post<UserItem>("/api/admin/users", data),
  updateUser: (id: string, data: Partial<UserItem> & { password?: string }) => api.put<{ success: boolean; message: string }>(`/api/admin/users/${id}`, data),
  deleteUser: (id: string) => api.delete<{ success: boolean; message: string }>(`/api/admin/users/${id}`),

  // RMs
  listRMs: () => api.get<RMItem[]>("/api/admin/rms"),
  createRM: (data: Partial<RMItem>) => api.post<RMItem>("/api/admin/rms", data),
  updateRM: (id: string, data: Partial<RMItem>) => api.put<{ success: boolean; message: string }>(`/api/admin/rms/${id}`, data),
  deleteRM: (id: string) => api.delete<{ success: boolean; message: string }>(`/api/admin/rms/${id}`),

  // Customers
  listCustomers: () => api.get<CustomerItem[]>("/api/admin/customers"),
  createCustomer: (data: Partial<CustomerItem>) => api.post<CustomerItem>("/api/admin/customers", data),
  updateCustomer: (id: string, data: Partial<CustomerItem>) => api.put<{ success: boolean; message: string }>(`/api/admin/customers/${id}`, data),
  deleteCustomer: (id: string) => api.delete<{ success: boolean; message: string }>(`/api/admin/customers/${id}`),

  // Products / Funds
  listProducts: () => api.get<ProductItem[]>("/api/admin/products"),
  createProduct: (data: Partial<ProductItem>) => api.post<ProductItem>("/api/admin/products", data),
  updateProduct: (id: string, data: Partial<ProductItem>) => api.put<{ success: boolean; message: string }>(`/api/admin/products/${id}`, data),
  deleteProduct: (id: string) => api.delete<{ success: boolean; message: string }>(`/api/admin/products/${id}`),

  // Regulatory Authorities (SEBI, AMFI, etc.)
  listAuthorities: (activeOnly?: boolean) =>
    api.get<AuthorityItem[]>("/api/admin/authorities", { active_only: activeOnly ? "true" : undefined }),
  createAuthority: (data: Partial<AuthorityItem>) =>
    api.post<AuthorityItem>("/api/admin/authorities", data),
  updateAuthority: (id: string, data: Partial<AuthorityItem>) =>
    api.put<{ success: boolean; message: string }>(`/api/admin/authorities/${id}`, data),
  deleteAuthority: (id: string) =>
    api.delete<{ success: boolean; message: string }>(`/api/admin/authorities/${id}`),
};

export function useAdminAnalytics(startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["admin", "analytics", startDate, endDate],
    queryFn: () => adminService.getAnalytics(startDate, endDate),
  });
}
