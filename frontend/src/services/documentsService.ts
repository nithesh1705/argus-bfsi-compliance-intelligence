// frontend/src/services/documentsService.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, API_BASE_URL } from "./api";

export interface DocumentItem {
  document_id: string;
  document_name: string;
  filename?: string;
  regulator: string;
  document_type?: string;
  status: string;
  year?: number;
  chunk_count: number;
  indexed_status: string;
  source_url?: string;
  storage_path?: string;
  file_size_bytes?: number;
  created_at?: string;
}

export interface DocumentsResponse {
  total: number;
  items: DocumentItem[];
}

export interface DocumentDetailResponse {
  document: DocumentItem;
  chunks: Array<{
    chunk_id: string;
    clause: string;
    citation_label: string;
    status: string;
    year: number;
    page_number: number;
    chunk_text: string;
  }>;
  chunk_count: number;
}

export const documentsService = {
  listDocuments: () => api.get<DocumentsResponse>("/api/documents"),

  getDocument: (docId: string) =>
    api.get<DocumentDetailResponse>(`/api/documents/${encodeURIComponent(docId)}`),

  deleteDocument: (docId: string) =>
    api.delete<{ success: boolean; message: string }>(`/api/documents/${encodeURIComponent(docId)}`),

  uploadDocument: async (formData: FormData) => {
    const token = localStorage.getItem("argus_auth_token");
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    const response = await fetch(`${API_BASE_URL}/api/documents/upload`, {
      method: "POST",
      headers,
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ message: response.statusText }));
      throw new Error(err.detail || err.message || "Failed to upload document");
    }
    return response.json();
  },

  getPreviewUrl: (docId: string) =>
    `${API_BASE_URL}/api/documents/${encodeURIComponent(docId)}/preview`,

  getDownloadUrl: (docId: string) =>
    `${API_BASE_URL}/api/documents/${encodeURIComponent(docId)}/download`,

  listAuthorities: (activeOnly?: boolean) =>
    api.get<Array<{
      authority_id: string;
      name: string;
      short_code: string;
      jurisdiction?: string;
      website_url?: string;
      description?: string;
      active: boolean;
      document_count?: number;
    }>>("/api/documents/authorities", { active_only: activeOnly ? "true" : undefined }),
};

export const DOCUMENTS_QUERY_KEY = ["documents", "list"] as const;
export const AUTHORITIES_QUERY_KEY = ["authorities", "list"] as const;

export function useDocumentsList() {
  return useQuery({
    queryKey: DOCUMENTS_QUERY_KEY,
    queryFn: documentsService.listDocuments,
  });
}

export function useAuthoritiesList(activeOnly?: boolean) {
  return useQuery({
    queryKey: [...AUTHORITIES_QUERY_KEY, activeOnly],
    queryFn: () => documentsService.listAuthorities(activeOnly),
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) => documentsService.uploadDocument(formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: AUTHORITIES_QUERY_KEY });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (docId: string) => documentsService.deleteDocument(docId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: AUTHORITIES_QUERY_KEY });
    },
  });
}

