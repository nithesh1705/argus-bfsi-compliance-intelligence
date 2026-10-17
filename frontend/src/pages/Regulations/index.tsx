import React, { useState, useRef } from "react";
import {
  useDocumentsList,
  useUploadDocument,
  useDeleteDocument,
  useAuthoritiesList,
  documentsService,
  DocumentItem,
} from "../../services/documentsService";
import { useAuth } from "../../context/AuthContext";
import { useQuery } from "@tanstack/react-query";
import { LoadingState } from "../../components/shared/LoadingState";
import { ErrorState } from "../../components/shared/ErrorState";
import {
  FileCheck2,
  Upload,
  Search,
  CheckCircle2,
  FileText,
  Layers,
  Eye,
  Download,
  Trash2,
  X,
  AlertTriangle,
  FileUp,
  ExternalLink,
  RefreshCw,
  File,
  Info,
  Calendar,
  Database,
  SlidersHorizontal,
} from "lucide-react";

export const Regulations: React.FC = () => {
  const { user } = useAuth();
  const isAdmin = user?.role === "Admin";

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIssuer, setSelectedIssuer] = useState<string>("ALL");

  // Modal States
  const [previewDoc, setPreviewDoc] = useState<DocumentItem | null>(null);
  const [previewTab, setPreviewTab] = useState<"viewer" | "chunks">("viewer");
  const [chunkFilter, setChunkFilter] = useState("");

  const [deleteDoc, setDeleteDoc] = useState<DocumentItem | null>(null);
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  // Upload Form State
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadDocName, setUploadDocName] = useState("");
  const [uploadRegulator, setUploadRegulator] = useState("SEBI");
  const [uploadDocType, setUploadDocType] = useState("REGULATION");
  const [uploadStatus, setUploadStatus] = useState("current");
  const [uploadYear, setUploadYear] = useState<number>(new Date().getFullYear());
  const [uploadSourceUrl, setUploadSourceUrl] = useState("");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data, isLoading, isError, error, refetch, isFetching } = useDocumentsList();
  const { data: authoritiesData } = useAuthoritiesList();
  const authorities = authoritiesData || [
    { authority_id: "SEBI", short_code: "SEBI", name: "Securities and Exchange Board of India", active: true },
    { authority_id: "AMFI", short_code: "AMFI", name: "Association of Mutual Funds in India", active: true },
  ];
  const uploadMutation = useUploadDocument();
  const deleteMutation = useDeleteDocument();

  // Fetch chunks if preview modal is open and on chunks tab
  const { data: detailData, isLoading: isLoadingDetail } = useQuery({
    queryKey: ["document", "detail", previewDoc?.document_id],
    queryFn: () => (previewDoc ? documentsService.getDocument(previewDoc.document_id) : null),
    enabled: !!previewDoc && previewTab === "chunks",
  });

  const showNotification = (type: "success" | "error", message: string) => {
    setNotification({ type, message });
    setTimeout(() => {
      setNotification(null);
    }, 5000);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setUploadFile(file);
      if (!uploadDocName) {
        // Derive clean title from filename
        const cleanName = file.name
          .replace(/\.[^/.]+$/, "")
          .replace(/[_-]+/g, " ")
          .trim();
        setUploadDocName(cleanName);
      }
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      setUploadError("Please select a document file (.pdf or .txt) to upload.");
      return;
    }
    setUploadError(null);

    const formData = new FormData();
    formData.append("file", uploadFile);
    formData.append("document_name", uploadDocName);
    formData.append("regulator", uploadRegulator);
    formData.append("document_type", uploadDocType);
    formData.append("status", uploadStatus);
    formData.append("year", String(uploadYear));
    if (uploadSourceUrl) {
      formData.append("source_url", uploadSourceUrl);
    }

    try {
      const res = await uploadMutation.mutateAsync(formData);
      showNotification("success", res.message || "Document successfully uploaded and indexed.");
      setIsUploadOpen(false);
      // Reset form
      setUploadFile(null);
      setUploadDocName("");
      setUploadSourceUrl("");
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err: any) {
      setUploadError(err.message || "Failed to upload document");
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteDoc) return;
    try {
      const res = await deleteMutation.mutateAsync(deleteDoc.document_id);
      showNotification("success", res.message || `Document '${deleteDoc.document_name}' deleted.`);
      setDeleteDoc(null);
    } catch (err: any) {
      showNotification("error", err.message || "Failed to delete document");
    }
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes || bytes === 0) return "—";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  if (isLoading) {
    return <LoadingState message="Retrieving statutory regulatory corpus from Cloud SQL & Cloud Storage..." />;
  }

  if (isError || !data) {
    return (
      <ErrorState
        title="Failed to Load Regulations"
        message={error instanceof Error ? error.message : "Cloud SQL regulations registry unreachable"}
        onRetry={() => refetch()}
      />
    );
  }

  const items = data.items || [];

  const filteredDocs = items.filter((doc) => {
    const query = searchQuery.toLowerCase();
    const matchesSearch =
      (doc.document_name || "").toLowerCase().includes(query) ||
      (doc.document_id || "").toLowerCase().includes(query) ||
      (doc.filename || "").toLowerCase().includes(query) ||
      (doc.regulator || "").toLowerCase().includes(query);

    const matchesIssuer =
      selectedIssuer === "ALL" ||
      (doc.regulator || "").toUpperCase().includes(selectedIssuer.toUpperCase());

    return matchesSearch && matchesIssuer;
  });

  const totalChunks = items.reduce((acc, d) => acc + (d.chunk_count || 0), 0);
  const sebiCount = items.filter((d) => (d.regulator || "").toUpperCase().includes("SEBI")).length;
  const amfiCount = items.filter((d) => (d.regulator || "").toUpperCase().includes("AMFI")).length;

  const filteredChunks = (detailData?.chunks || []).filter((c) => {
    if (!chunkFilter) return true;
    const q = chunkFilter.toLowerCase();
    return (
      c.clause.toLowerCase().includes(q) ||
      c.citation_label.toLowerCase().includes(q) ||
      c.chunk_text.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {notification && (
        <div
          className={`fixed top-5 right-5 z-50 flex items-center gap-3 px-4 py-3 rounded-lg shadow-xl border text-sm transition-all duration-300 ${
            notification.type === "success"
              ? "bg-emerald-50 dark:bg-emerald-950/90 text-emerald-800 dark:text-emerald-200 border-emerald-300 dark:border-emerald-800"
              : "bg-rose-50 dark:bg-rose-950/90 text-rose-800 dark:text-rose-200 border-rose-300 dark:border-rose-800"
          }`}
        >
          {notification.type === "success" ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-rose-600 dark:text-rose-400 shrink-0" />
          )}
          <span className="font-medium">{notification.message}</span>
          <button
            onClick={() => setNotification(null)}
            className="ml-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <FileCheck2 className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            Regulatory Corpus & Statutory Guidelines
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage statutory master documents, preview circulars, download regulatory files, and index new compliance directives.
          </p>
        </div>

        {/* Action Header Buttons */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            title="Refresh Corpus Registry"
            className="px-3 py-2 bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 rounded-lg text-xs font-semibold flex items-center gap-1.5 border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 shadow-sm transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? "animate-spin text-blue-500" : ""}`} />
            <span>Refresh</span>
          </button>

          {isAdmin ? (
            <button
              type="button"
              onClick={() => setIsUploadOpen(true)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-sm shadow-blue-500/20 transition-all hover:shadow"
            >
              <Upload className="w-4 h-4" />
              <span>Upload New Regulation</span>
            </button>
          ) : (
            <div title="Regulatory document upload is restricted to Administrators.">
              <button
                type="button"
                disabled
                className="px-3.5 py-2 bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500 rounded-lg text-xs font-semibold flex items-center gap-2 cursor-not-allowed border border-slate-200 dark:border-slate-700"
              >
                <Upload className="w-3.5 h-3.5 text-slate-400" />
                <span>Upload (Admin Only)</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Corpus Statistics Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
          <span className="text-xs font-semibold uppercase text-slate-400">Total Statutory Corpus</span>
          <p className="text-2xl font-mono font-bold text-slate-900 dark:text-slate-100 mt-1">
            {items.length} Master Documents
          </p>
          <span className="text-[11px] text-slate-500 truncate block" title={authorities.map((a) => `${a.short_code} (${items.filter((d) => (d.regulator || "").toUpperCase().includes(a.short_code.toUpperCase())).length})`).join(" • ")}>
            {authorities
              .map((a) => `${a.short_code} (${items.filter((d) => (d.regulator || "").toUpperCase().includes(a.short_code.toUpperCase())).length})`)
              .join(" • ")}
          </span>
        </div>
        <div className="p-4 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
          <span className="text-xs font-semibold uppercase text-slate-400">Indexed Statutory Chunks</span>
          <p className="text-2xl font-mono font-bold text-blue-600 dark:text-blue-400 mt-1">
            {totalChunks.toLocaleString()} Chunks
          </p>
          <span className="text-[11px] text-slate-500">Real-time retrieval & clause citation</span>
        </div>
        <div className="p-4 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
          <span className="text-xs font-semibold uppercase text-slate-400">Corpus Integrity & Storage</span>
          <p className="text-2xl font-mono font-bold text-emerald-600 dark:text-emerald-400 mt-1">
            Cloud SQL & GCS Synced
          </p>
          <span className="text-[11px] text-slate-500">Authoritative GCS storage with live PDF preview</span>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3 bg-slate-50/50 dark:bg-slate-950/20">
          <div className="relative min-w-[280px] flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search regulatory documents by title, ID, or file..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 placeholder:text-slate-400"
            />
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Authority:</span>
            <select
              value={selectedIssuer}
              onChange={(e) => setSelectedIssuer(e.target.value)}
              className="px-2.5 py-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded text-xs text-slate-800 dark:text-slate-200 focus:outline-none"
            >
              <option value="ALL">All Authorities ({items.length} Docs)</option>
              {authorities.map((auth) => {
                const count = items.filter((d) => (d.regulator || "").toUpperCase().includes(auth.short_code.toUpperCase())).length;
                return (
                  <option key={auth.short_code} value={auth.short_code}>
                    {auth.short_code} ({count}) — {auth.name}
                  </option>
                );
              })}
            </select>
          </div>
        </div>

        {/* Documents Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 dark:bg-slate-950/60 border-b border-slate-200 dark:border-slate-800 text-xs font-semibold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="py-3 px-4">Document Title & Filename</th>
                <th className="py-3 px-4">Authority</th>
                <th className="py-3 px-4">Status & Year</th>
                <th className="py-3 px-4">Indexed Chunks</th>
                <th className="py-3 px-4">File Size</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
              {filteredDocs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    <FileText className="w-8 h-8 text-slate-300 dark:text-slate-600 mx-auto mb-2" />
                    <p className="font-medium">No matching regulatory documents found</p>
                    <p className="text-xs text-slate-400 mt-1">Try refining your search filter or upload a new regulation.</p>
                  </td>
                </tr>
              ) : (
                filteredDocs.map((doc) => (
                  <tr
                    key={doc.document_id}
                    className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors"
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-start gap-2.5">
                        <FileText className="w-4 h-4 text-blue-500 mt-1 shrink-0" />
                        <div>
                          <p className="font-semibold text-slate-900 dark:text-slate-100 leading-snug">
                            {doc.document_name}
                          </p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                              ID: {doc.document_id}
                            </span>
                            {doc.filename && (
                              <span className="text-[11px] font-mono text-slate-400 max-w-[280px] truncate" title={doc.filename}>
                                • {doc.filename}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-bold ${
                          (doc.regulator || "").toUpperCase().includes("SEBI")
                            ? "bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300 border border-blue-200 dark:border-blue-900"
                            : (doc.regulator || "").toUpperCase().includes("AMFI")
                            ? "bg-purple-50 text-purple-700 dark:bg-purple-950/50 dark:text-purple-300 border border-purple-200 dark:border-purple-900"
                            : (doc.regulator || "").toUpperCase().includes("RBI")
                            ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-900"
                            : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-200 dark:border-slate-700"
                        }`}
                      >
                        {doc.regulator || "SEBI"}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex flex-col">
                        <span
                          className={`text-xs font-semibold capitalize ${
                            doc.status === "current"
                              ? "text-emerald-600 dark:text-emerald-400"
                              : "text-amber-600 dark:text-amber-400"
                          }`}
                        >
                          {doc.status || "current"}
                        </span>
                        <span className="text-[11px] text-slate-400">Year: {doc.year || 2026}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 font-mono text-xs text-slate-700 dark:text-slate-300">
                      <span className="flex items-center gap-1">
                        <Layers className="w-3.5 h-3.5 text-slate-400" />
                        {doc.chunk_count} chunks
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-xs text-slate-600 dark:text-slate-400">
                      {formatFileSize(doc.file_size_bytes)}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {/* Preview Button */}
                        <button
                          type="button"
                          onClick={() => {
                            setPreviewDoc(doc);
                            setPreviewTab("viewer");
                          }}
                          className="px-2.5 py-1.5 rounded-md text-xs font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 dark:text-blue-300 dark:bg-blue-950/50 dark:hover:bg-blue-900/50 border border-blue-200 dark:border-blue-900 flex items-center gap-1 transition-colors"
                          title="Preview Document & Statutory Chunks"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>Preview</span>
                        </button>

                        {/* Download Button */}
                        <a
                          href={documentsService.getDownloadUrl(doc.document_id)}
                          download
                          className="p-1.5 rounded-md text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 dark:text-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 transition-colors"
                          title="Download Regulatory Document File"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </a>

                        {/* Delete Button (Admin Only) */}
                        {isAdmin && (
                          <button
                            type="button"
                            onClick={() => setDeleteDoc(doc)}
                            className="p-1.5 rounded-md text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 dark:text-rose-400 dark:bg-rose-950/40 dark:hover:bg-rose-900/50 border border-rose-200 dark:border-rose-900/60 transition-colors"
                            title="Delete Document (Admin Only)"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ==================================================================== */}
      {/* PREVIEW MODAL / DRAWER */}
      {/* ==================================================================== */}
      {previewDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-2xl w-full max-w-5xl h-[90vh] flex flex-col overflow-hidden">
            {/* Modal Header */}
            <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/70 dark:bg-slate-950/40">
              <div className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-blue-600 dark:text-blue-400 shrink-0" />
                <div>
                  <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 leading-tight">
                    {previewDoc.document_name}
                  </h3>
                  <div className="flex items-center gap-2 mt-0.5 text-xs text-slate-500">
                    <span className="font-mono">ID: {previewDoc.document_id}</span>
                    <span>•</span>
                    <span className="font-semibold text-blue-600 dark:text-blue-400">{previewDoc.regulator}</span>
                    <span>•</span>
                    <span>{previewDoc.chunk_count} Statutory Chunks</span>
                    {previewDoc.file_size_bytes ? (
                      <>
                        <span>•</span>
                        <span>{formatFileSize(previewDoc.file_size_bytes)}</span>
                      </>
                    ) : null}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <a
                  href={documentsService.getDownloadUrl(previewDoc.document_id)}
                  download
                  className="px-3 py-1.5 rounded-md text-xs font-semibold text-slate-700 bg-white dark:text-slate-200 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center gap-1.5 shadow-sm transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download</span>
                </a>
                <button
                  type="button"
                  onClick={() => setPreviewDoc(null)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Navigation Tabs */}
            <div className="px-5 border-b border-slate-200 dark:border-slate-800 flex items-center gap-4 bg-white dark:bg-slate-900 text-xs">
              <button
                type="button"
                onClick={() => setPreviewTab("viewer")}
                className={`py-3 font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
                  previewTab === "viewer"
                    ? "border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400"
                    : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                }`}
              >
                <File className="w-3.5 h-3.5" />
                <span>Document Viewer</span>
              </button>
              <button
                type="button"
                onClick={() => setPreviewTab("chunks")}
                className={`py-3 font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
                  previewTab === "chunks"
                    ? "border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400"
                    : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                <span>Statutory Chunks & Clauses ({previewDoc.chunk_count})</span>
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-hidden bg-slate-100 dark:bg-slate-950/50 p-2">
              {previewTab === "viewer" ? (
                <div className="w-full h-full rounded-lg overflow-hidden bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                  <iframe
                    src={documentsService.getPreviewUrl(previewDoc.document_id)}
                    title={previewDoc.document_name}
                    className="w-full h-full border-0"
                  />
                </div>
              ) : (
                <div className="w-full h-full flex flex-col bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 overflow-hidden">
                  {/* Search in chunks */}
                  <div className="p-3 border-b border-slate-200 dark:border-slate-800 flex items-center gap-2 bg-slate-50/50 dark:bg-slate-950/20">
                    <Search className="w-4 h-4 text-slate-400" />
                    <input
                      type="text"
                      placeholder="Search within indexed clauses and statutory text..."
                      value={chunkFilter}
                      onChange={(e) => setChunkFilter(e.target.value)}
                      className="w-full text-xs bg-transparent border-none focus:outline-none placeholder:text-slate-400"
                    />
                    {chunkFilter && (
                      <button
                        onClick={() => setChunkFilter("")}
                        className="text-xs text-slate-400 hover:text-slate-600"
                      >
                        Clear
                      </button>
                    )}
                  </div>

                  {/* Chunks List */}
                  <div className="flex-1 overflow-y-auto p-4 space-y-3">
                    {isLoadingDetail ? (
                      <div className="py-12 text-center text-xs text-slate-500">
                        <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-blue-500" />
                        Loading authoritative chunks from Cloud SQL registry...
                      </div>
                    ) : filteredChunks.length === 0 ? (
                      <div className="py-12 text-center text-xs text-slate-500">
                        No chunks match your search query.
                      </div>
                    ) : (
                      filteredChunks.map((chunk, idx) => (
                        <div
                          key={chunk.chunk_id || idx}
                          className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-950/40 text-xs space-y-2 hover:border-slate-300 dark:hover:border-slate-700 transition-colors"
                        >
                          <div className="flex items-center justify-between text-[11px] font-mono text-slate-500">
                            <span className="font-semibold text-blue-600 dark:text-blue-400">
                              {chunk.citation_label || chunk.clause}
                            </span>
                            <span className="bg-slate-200 dark:bg-slate-800 px-2 py-0.5 rounded text-[10px]">
                              Page {chunk.page_number}
                            </span>
                          </div>
                          <p className="text-slate-800 dark:text-slate-200 leading-relaxed font-sans">
                            {chunk.chunk_text}
                          </p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* UPLOAD MODAL */}
      {/* ==================================================================== */}
      {isUploadOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-2xl w-full max-w-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/70 dark:bg-slate-950/40">
              <div className="flex items-center gap-2.5">
                <FileUp className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                  Upload Regulatory Document
                </h3>
              </div>
              <button
                type="button"
                onClick={() => {
                  setIsUploadOpen(false);
                  setUploadError(null);
                }}
                className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} className="p-5 space-y-4 text-xs">
              {uploadError && (
                <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{uploadError}</span>
                </div>
              )}

              {/* File Dropzone */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Document File (PDF or Plaintext) *
                </label>
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-slate-300 dark:border-slate-700 hover:border-blue-500 dark:hover:border-blue-400 rounded-lg p-5 text-center cursor-pointer transition-colors bg-slate-50/50 dark:bg-slate-950/30"
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.txt"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  {uploadFile ? (
                    <div className="flex items-center justify-center gap-2 text-slate-800 dark:text-slate-200">
                      <FileText className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                      <span className="font-semibold">{uploadFile.name}</span>
                      <span className="text-slate-400">({formatFileSize(uploadFile.size)})</span>
                    </div>
                  ) : (
                    <div className="space-y-1">
                      <Upload className="w-6 h-6 text-slate-400 mx-auto" />
                      <p className="font-semibold text-slate-700 dark:text-slate-300">
                        Click or drag statutory PDF / TXT here
                      </p>
                      <p className="text-[11px] text-slate-400">Supports PDF directives, circulars, and codes of conduct</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Document Name */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Document Title *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g., SEBI Master Circular on Portfolio Managers 2026"
                  value={uploadDocName}
                  onChange={(e) => setUploadDocName(e.target.value)}
                  className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              {/* Authority & Type Grid */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Regulatory Authority
                  </label>
                  <select
                    value={uploadRegulator}
                    onChange={(e) => setUploadRegulator(e.target.value)}
                    className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md text-xs focus:outline-none"
                  >
                    {authorities.filter((a) => a.active).map((auth) => (
                      <option key={auth.short_code} value={auth.short_code}>
                        {auth.short_code} — {auth.name}
                      </option>
                    ))}
                    {authorities.length === 0 && (
                      <>
                        <option value="SEBI">SEBI (Securities & Exchange Board)</option>
                        <option value="AMFI">AMFI (Association of Mutual Funds)</option>
                      </>
                    )}
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Document Classification
                  </label>
                  <select
                    value={uploadDocType}
                    onChange={(e) => setUploadDocType(e.target.value)}
                    className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md text-xs focus:outline-none"
                  >
                    <option value="REGULATION">Statutory Regulation</option>
                    <option value="MASTER_CIRCULAR">Master Circular</option>
                    <option value="CODE_OF_CONDUCT">Code of Conduct</option>
                    <option value="CODE_OF_ETHICS">Code of Ethics</option>
                    <option value="ADVISORY">Advisory / Circular</option>
                  </select>
                </div>
              </div>

              {/* Status & Year Grid */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Corpus Status
                  </label>
                  <select
                    value={uploadStatus}
                    onChange={(e) => setUploadStatus(e.target.value)}
                    className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md text-xs focus:outline-none"
                  >
                    <option value="current">Current / In Force</option>
                    <option value="historical">Historical / Superseded</option>
                    <option value="draft">Draft / Exposure</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Publication Year
                  </label>
                  <input
                    type="number"
                    value={uploadYear}
                    onChange={(e) => setUploadYear(Number(e.target.value))}
                    min={1990}
                    max={2035}
                    className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md text-xs focus:outline-none"
                  />
                </div>
              </div>

              {/* Source URL */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Authoritative Source URL (Optional)
                </label>
                <input
                  type="url"
                  placeholder="https://www.sebi.gov.in/legal/..."
                  value={uploadSourceUrl}
                  onChange={(e) => setUploadSourceUrl(e.target.value)}
                  className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 text-[11px] text-blue-800 dark:text-blue-300 flex items-start gap-2">
                <Info className="w-4 h-4 shrink-0 mt-0.5 text-blue-600 dark:text-blue-400" />
                <span>
                  The file will be securely written to Google Cloud Storage (GCS). PyMuPDF will extract sections, and chunks will be automatically indexed into the Cloud SQL registry.
                </span>
              </div>

              {/* Submit Buttons */}
              <div className="pt-2 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setIsUploadOpen(false)}
                  disabled={uploadMutation.isPending}
                  className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploadMutation.isPending}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-sm transition-all disabled:opacity-50"
                >
                  {uploadMutation.isPending ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Indexing & Storing...</span>
                    </>
                  ) : (
                    <>
                      <Upload className="w-3.5 h-3.5" />
                      <span>Upload & Index Document</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* DELETE CONFIRMATION MODAL */}
      {/* ==================================================================== */}
      {deleteDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-2xl w-full max-w-md p-5 space-y-4">
            <div className="flex items-start gap-3">
              <div className="p-2.5 rounded-full bg-rose-50 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400 shrink-0">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                  Delete Regulatory Document?
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  Are you sure you want to delete <span className="font-semibold text-slate-800 dark:text-slate-200">"{deleteDoc.document_name}"</span>?
                </p>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/50 text-xs text-amber-800 dark:text-amber-300">
              This will permanently delete the binary file from Google Cloud Storage and prune all <strong>{deleteDoc.chunk_count} statutory chunks</strong> from the Cloud SQL registry.
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                type="button"
                onClick={() => setDeleteDoc(null)}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteConfirm}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-all disabled:opacity-50"
              >
                {deleteMutation.isPending ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Deleting...</span>
                  </>
                ) : (
                  <>
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Delete Document</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
