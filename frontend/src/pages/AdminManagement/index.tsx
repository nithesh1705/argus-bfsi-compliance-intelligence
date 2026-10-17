import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  adminService,
  UserItem,
  RMItem,
  CustomerItem,
  ProductItem,
  AuthorityItem,
} from "../../services/adminService";
import { LoadingState } from "../../components/shared/LoadingState";
import { ErrorState } from "../../components/shared/ErrorState";
import {
  Database,
  Users,
  UserPlus,
  Briefcase,
  UserCheck,
  Package,
  Search,
  Plus,
  Edit2,
  Trash2,
  X,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Shield,
  Layers,
  FileText,
  Landmark,
  ExternalLink,
  Globe,
} from "lucide-react";

type ManagementTab = "users" | "rms" | "customers" | "products" | "authorities";

export const AdminManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ManagementTab>("users");
  const [searchQuery, setSearchQuery] = useState("");
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const queryClient = useQueryClient();

  const showNotification = (type: "success" | "error", message: string) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 4000);
  };

  // Queries
  const usersQuery = useQuery({ queryKey: ["admin", "users"], queryFn: adminService.listUsers });
  const rmsQuery = useQuery({ queryKey: ["admin", "rms"], queryFn: adminService.listRMs });
  const customersQuery = useQuery({ queryKey: ["admin", "customers"], queryFn: adminService.listCustomers });
  const productsQuery = useQuery({ queryKey: ["admin", "products"], queryFn: adminService.listProducts });
  const authoritiesQuery = useQuery({ queryKey: ["admin", "authorities"], queryFn: () => adminService.listAuthorities() });

  // Modal States
  const [userModal, setUserModal] = useState<{ open: boolean; mode: "create" | "edit"; data?: UserItem }>({ open: false, mode: "create" });
  const [rmModal, setRmModal] = useState<{ open: boolean; mode: "create" | "edit"; data?: RMItem }>({ open: false, mode: "create" });
  const [customerModal, setCustomerModal] = useState<{ open: boolean; mode: "create" | "edit"; data?: CustomerItem }>({ open: false, mode: "create" });
  const [productModal, setProductModal] = useState<{ open: boolean; mode: "create" | "edit"; data?: ProductItem }>({ open: false, mode: "create" });
  const [authorityModal, setAuthorityModal] = useState<{ open: boolean; mode: "create" | "edit"; data?: AuthorityItem }>({ open: false, mode: "create" });
  const [deleteModal, setDeleteModal] = useState<{ open: boolean; type: ManagementTab; id: string; name: string } | null>(null);

  // Form States
  const [userForm, setUserForm] = useState({ username: "", email: "", password: "", role: "Audit Officer", team: "Compliance", full_name: "", is_active: true });
  const [rmForm, setRmForm] = useState({ rm_id: "", full_name: "", branch: "Main Branch", active: true });
  const [customerForm, setCustomerForm] = useState({ customer_id: "", full_name: "", mobile_number: "+91 98765 00000", risk_profile: "Moderate", investment_experience: "Intermediate", kyc_status: "VERIFIED" });
  const [productForm, setProductForm] = useState({ product_id: "", product_name: "", risk_class: "Moderate Risk", suitable_risk_profiles: "Moderate, Aggressive", disclosure_requirements: "Standard SEBI MF Scheme Document" });
  const [authorityForm, setAuthorityForm] = useState({ authority_id: "", short_code: "", name: "", jurisdiction: "Securities & Capital Markets", website_url: "https://", description: "", active: true });

  // Open User Edit
  const openEditUser = (u: UserItem) => {
    setUserForm({
      username: u.username,
      email: u.email,
      password: "",
      role: u.role,
      team: u.team || "Compliance",
      full_name: u.full_name || u.username,
      is_active: u.is_active,
    });
    setUserModal({ open: true, mode: "edit", data: u });
  };

  // Open RM Edit
  const openEditRM = (r: RMItem) => {
    setRmForm({
      rm_id: r.rm_id,
      full_name: r.full_name,
      branch: r.branch || "",
      active: r.active,
    });
    setRmModal({ open: true, mode: "edit", data: r });
  };

  // Open Customer Edit
  const openEditCustomer = (c: CustomerItem) => {
    setCustomerForm({
      customer_id: c.customer_id,
      full_name: c.full_name,
      mobile_number: c.mobile_number || "",
      risk_profile: c.risk_profile || "Moderate",
      investment_experience: c.investment_experience || "Intermediate",
      kyc_status: c.kyc_status || "VERIFIED",
    });
    setCustomerModal({ open: true, mode: "edit", data: c });
  };

  // Open Product Edit
  const openEditProduct = (p: ProductItem) => {
    setProductForm({
      product_id: p.product_id,
      product_name: p.product_name,
      risk_class: p.risk_class || "Moderate Risk",
      suitable_risk_profiles: p.suitable_risk_profiles || "Moderate",
      disclosure_requirements: p.disclosure_requirements || "",
    });
    setProductModal({ open: true, mode: "edit", data: p });
  };

  // Open Authority Edit
  const openEditAuthority = (a: AuthorityItem) => {
    setAuthorityForm({
      authority_id: a.authority_id,
      short_code: a.short_code,
      name: a.name,
      jurisdiction: a.jurisdiction || "India",
      website_url: a.website_url || "",
      description: a.description || "",
      active: a.active,
    });
    setAuthorityModal({ open: true, mode: "edit", data: a });
  };

  // Submit Handlers
  const handleSaveUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (userModal.mode === "create") {
        await adminService.createUser(userForm);
        showNotification("success", `User '${userForm.username}' created successfully.`);
      } else if (userModal.data) {
        await adminService.updateUser(userModal.data.user_id, userForm);
        showNotification("success", `User '${userModal.data.user_id}' updated successfully.`);
      }
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      setUserModal({ open: false, mode: "create" });
    } catch (err: any) {
      showNotification("error", err.message || "Operation failed");
    }
  };

  const handleSaveRM = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (rmModal.mode === "create") {
        await adminService.createRM(rmForm);
        showNotification("success", `RM '${rmForm.full_name}' added successfully.`);
      } else if (rmModal.data) {
        await adminService.updateRM(rmModal.data.rm_id, rmForm);
        showNotification("success", `RM '${rmModal.data.rm_id}' updated successfully.`);
      }
      queryClient.invalidateQueries({ queryKey: ["admin", "rms"] });
      setRmModal({ open: false, mode: "create" });
    } catch (err: any) {
      showNotification("error", err.message || "Operation failed");
    }
  };

  const handleSaveCustomer = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (customerModal.mode === "create") {
        await adminService.createCustomer(customerForm);
        showNotification("success", `Customer '${customerForm.full_name}' added successfully.`);
      } else if (customerModal.data) {
        await adminService.updateCustomer(customerModal.data.customer_id, customerForm);
        showNotification("success", `Customer '${customerModal.data.customer_id}' updated.`);
      }
      queryClient.invalidateQueries({ queryKey: ["admin", "customers"] });
      setCustomerModal({ open: false, mode: "create" });
    } catch (err: any) {
      showNotification("error", err.message || "Operation failed");
    }
  };

  const handleSaveProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (productModal.mode === "create") {
        await adminService.createProduct(productForm);
        showNotification("success", `Product '${productForm.product_name}' registered.`);
      } else if (productModal.data) {
        await adminService.updateProduct(productModal.data.product_id, productForm);
        showNotification("success", `Product '${productModal.data.product_id}' updated.`);
      }
      queryClient.invalidateQueries({ queryKey: ["admin", "products"] });
      setProductModal({ open: false, mode: "create" });
    } catch (err: any) {
      showNotification("error", err.message || "Operation failed");
    }
  };

  const handleSaveAuthority = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (authorityModal.mode === "create") {
        await adminService.createAuthority(authorityForm);
        showNotification("success", `Regulatory Authority '${authorityForm.short_code}' created successfully.`);
      } else if (authorityModal.data) {
        await adminService.updateAuthority(authorityModal.data.authority_id, authorityForm);
        showNotification("success", `Regulatory Authority '${authorityModal.data.short_code}' updated.`);
      }
      queryClient.invalidateQueries({ queryKey: ["admin", "authorities"] });
      queryClient.invalidateQueries({ queryKey: ["authorities"] });
      setAuthorityModal({ open: false, mode: "create" });
    } catch (err: any) {
      showNotification("error", err.message || "Operation failed");
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteModal) return;
    try {
      if (deleteModal.type === "users") {
        await adminService.deleteUser(deleteModal.id);
        queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      } else if (deleteModal.type === "rms") {
        await adminService.deleteRM(deleteModal.id);
        queryClient.invalidateQueries({ queryKey: ["admin", "rms"] });
      } else if (deleteModal.type === "customers") {
        await adminService.deleteCustomer(deleteModal.id);
        queryClient.invalidateQueries({ queryKey: ["admin", "customers"] });
      } else if (deleteModal.type === "products") {
        await adminService.deleteProduct(deleteModal.id);
        queryClient.invalidateQueries({ queryKey: ["admin", "products"] });
      } else if (deleteModal.type === "authorities") {
        await adminService.deleteAuthority(deleteModal.id);
        queryClient.invalidateQueries({ queryKey: ["admin", "authorities"] });
        queryClient.invalidateQueries({ queryKey: ["authorities"] });
      }
      showNotification("success", `Record '${deleteModal.name}' deleted.`);
      setDeleteModal(null);
    } catch (err: any) {
      showNotification("error", err.message || "Delete failed");
    }
  };

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
          <button onClick={() => setNotification(null)} className="ml-2 text-slate-400 hover:text-slate-600">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Database className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            Master Data & User Access Management
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Admin CRUD operations on user identities, relationship managers, customer profiles, and mutual fund schemes.
          </p>
        </div>

        {/* Create Button */}
        <div>
          {activeTab === "users" && (
            <button
              onClick={() => {
                setUserForm({ username: "", email: "", password: "", role: "Audit Officer", team: "Compliance", full_name: "", is_active: true });
                setUserModal({ open: true, mode: "create" });
              }}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-sm transition-colors"
            >
              <UserPlus className="w-4 h-4" />
              <span>Add New User</span>
            </button>
          )}
          {activeTab === "rms" && (
            <button
              onClick={() => {
                setRmForm({ rm_id: "", full_name: "", branch: "Main Branch", active: true });
                setRmModal({ open: true, mode: "create" });
              }}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-sm transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>Register New RM</span>
            </button>
          )}
          {activeTab === "customers" && (
            <button
              onClick={() => {
                setCustomerForm({ customer_id: "", full_name: "", mobile_number: "+91 98765 00000", risk_profile: "Moderate", investment_experience: "Intermediate", kyc_status: "VERIFIED" });
                setCustomerModal({ open: true, mode: "create" });
              }}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-sm transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>Add Customer Profile</span>
            </button>
          )}
          {activeTab === "products" && (
            <button
              onClick={() => {
                setProductForm({ product_id: "", product_name: "", risk_class: "Moderate Risk", suitable_risk_profiles: "Moderate, Aggressive", disclosure_requirements: "Standard SEBI MF Scheme Document" });
                setProductModal({ open: true, mode: "create" });
              }}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-sm transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>Register Fund / Scheme</span>
            </button>
          )}
          {activeTab === "authorities" && (
            <button
              onClick={() => {
                setAuthorityForm({ authority_id: "", short_code: "", name: "", jurisdiction: "Securities & Capital Markets", website_url: "https://", description: "", active: true });
                setAuthorityModal({ open: true, mode: "create" });
              }}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-sm transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>Add Regulatory Authority</span>
            </button>
          )}
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 gap-6 text-xs font-semibold overflow-x-auto">
        <button
          onClick={() => { setActiveTab("users"); setSearchQuery(""); }}
          className={`pb-3 flex items-center gap-2 border-b-2 whitespace-nowrap transition-colors ${
            activeTab === "users" ? "border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400" : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          }`}
        >
          <Users className="w-4 h-4" />
          <span>System Users ({usersQuery.data?.length || 0})</span>
        </button>
        <button
          onClick={() => { setActiveTab("rms"); setSearchQuery(""); }}
          className={`pb-3 flex items-center gap-2 border-b-2 whitespace-nowrap transition-colors ${
            activeTab === "rms" ? "border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400" : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          }`}
        >
          <Briefcase className="w-4 h-4" />
          <span>Relationship Managers ({rmsQuery.data?.length || 0})</span>
        </button>
        <button
          onClick={() => { setActiveTab("customers"); setSearchQuery(""); }}
          className={`pb-3 flex items-center gap-2 border-b-2 whitespace-nowrap transition-colors ${
            activeTab === "customers" ? "border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400" : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          }`}
        >
          <UserCheck className="w-4 h-4" />
          <span>Customers ({customersQuery.data?.length || 0})</span>
        </button>
        <button
          onClick={() => { setActiveTab("products"); setSearchQuery(""); }}
          className={`pb-3 flex items-center gap-2 border-b-2 whitespace-nowrap transition-colors ${
            activeTab === "products" ? "border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400" : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          }`}
        >
          <Package className="w-4 h-4" />
          <span>Mutual Funds & Products ({productsQuery.data?.length || 0})</span>
        </button>
        <button
          onClick={() => { setActiveTab("authorities"); setSearchQuery(""); }}
          className={`pb-3 flex items-center gap-2 border-b-2 whitespace-nowrap transition-colors ${
            activeTab === "authorities" ? "border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400" : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          }`}
        >
          <Landmark className="w-4 h-4" />
          <span>Regulatory Authorities ({authoritiesQuery.data?.length || 0})</span>
        </button>
      </div>

      {/* Main Table Container */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm overflow-hidden">
        {/* Search Bar */}
        <div className="p-3.5 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/20 flex items-center justify-between">
          <div className="relative max-w-sm flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder={`Search ${activeTab}...`}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md text-xs focus:outline-none"
            />
          </div>
        </div>

        {/* TAB 1: USERS */}
        {activeTab === "users" && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-950/60 border-b border-slate-200 dark:border-slate-800 text-slate-500 uppercase font-semibold">
                <tr>
                  <th className="py-3 px-4">User</th>
                  <th className="py-3 px-4">Role</th>
                  <th className="py-3 px-4">Team</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Last Login</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
                {(usersQuery.data || [])
                  .filter((u) => u.username.toLowerCase().includes(searchQuery.toLowerCase()) || u.full_name?.toLowerCase().includes(searchQuery.toLowerCase()) || u.email.toLowerCase().includes(searchQuery.toLowerCase()))
                  .map((u) => (
                    <tr key={u.user_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-900 dark:text-slate-100">{u.full_name || u.username}</div>
                        <div className="text-[11px] text-slate-400 font-mono">@{u.username} • {u.email}</div>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          u.role === "Admin"
                            ? "bg-purple-50 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300 border border-purple-200"
                            : "bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border border-blue-200"
                        }`}>
                          {u.role}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-600 dark:text-slate-300">{u.team || "Compliance"}</td>
                      <td className="py-3 px-4">
                        <span className={`inline-flex items-center gap-1 text-[11px] font-semibold ${u.is_active ? "text-emerald-600" : "text-slate-400"}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${u.is_active ? "bg-emerald-500" : "bg-slate-400"}`} />
                          {u.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-slate-500">{u.last_login_at || "Never"}</td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button onClick={() => openEditUser(u)} className="p-1.5 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950/50 rounded" title="Edit User">
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                          <button onClick={() => setDeleteModal({ open: true, type: "users", id: u.user_id, name: u.username })} className="p-1.5 text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/50 rounded" title="Delete User">
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}

        {/* TAB 2: RMS */}
        {activeTab === "rms" && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-950/60 border-b border-slate-200 dark:border-slate-800 text-slate-500 uppercase font-semibold">
                <tr>
                  <th className="py-3 px-4">RM ID & Name</th>
                  <th className="py-3 px-4">Branch</th>
                  <th className="py-3 px-4">Joined Date</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
                {(rmsQuery.data || [])
                  .filter((r) => r.full_name.toLowerCase().includes(searchQuery.toLowerCase()) || r.rm_id.toLowerCase().includes(searchQuery.toLowerCase()) || r.branch.toLowerCase().includes(searchQuery.toLowerCase()))
                  .map((r) => (
                    <tr key={r.rm_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-900 dark:text-slate-100">{r.full_name}</div>
                        <div className="text-[11px] text-slate-400 font-mono">ID: {r.rm_id}</div>
                      </td>
                      <td className="py-3 px-4 text-slate-700 dark:text-slate-300 font-medium">{r.branch}</td>
                      <td className="py-3 px-4 font-mono text-[11px] text-slate-500">{r.joined_date || "—"}</td>
                      <td className="py-3 px-4">
                        <span className={`inline-flex items-center gap-1 text-[11px] font-semibold ${r.active ? "text-emerald-600" : "text-slate-400"}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${r.active ? "bg-emerald-500" : "bg-slate-400"}`} />
                          {r.active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button onClick={() => openEditRM(r)} className="p-1.5 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950/50 rounded" title="Edit RM">
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                          <button onClick={() => setDeleteModal({ open: true, type: "rms", id: r.rm_id, name: r.full_name })} className="p-1.5 text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/50 rounded" title="Delete RM">
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}

        {/* TAB 3: CUSTOMERS */}
        {activeTab === "customers" && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-950/60 border-b border-slate-200 dark:border-slate-800 text-slate-500 uppercase font-semibold">
                <tr>
                  <th className="py-3 px-4">Customer ID & Name</th>
                  <th className="py-3 px-4">Mobile</th>
                  <th className="py-3 px-4">Risk Profile</th>
                  <th className="py-3 px-4">Experience</th>
                  <th className="py-3 px-4">KYC Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
                {(customersQuery.data || [])
                  .filter((c) => c.full_name.toLowerCase().includes(searchQuery.toLowerCase()) || c.customer_id.toLowerCase().includes(searchQuery.toLowerCase()))
                  .map((c) => (
                    <tr key={c.customer_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-900 dark:text-slate-100">{c.full_name}</div>
                        <div className="text-[11px] text-slate-400 font-mono">ID: {c.customer_id}</div>
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-slate-600 dark:text-slate-400">{c.mobile_number}</td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          c.risk_profile.toLowerCase().includes("agg")
                            ? "bg-rose-50 text-rose-700 border border-rose-200"
                            : "bg-blue-50 text-blue-700 border border-blue-200"
                        }`}>
                          {c.risk_profile}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-600 dark:text-slate-400">{c.investment_experience}</td>
                      <td className="py-3 px-4">
                        <span className="text-[11px] font-semibold text-emerald-600">{c.kyc_status}</span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button onClick={() => openEditCustomer(c)} className="p-1.5 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950/50 rounded" title="Edit Customer">
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                          <button onClick={() => setDeleteModal({ open: true, type: "customers", id: c.customer_id, name: c.full_name })} className="p-1.5 text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/50 rounded" title="Delete Customer">
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}

        {/* TAB 4: PRODUCTS */}
        {activeTab === "products" && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-950/60 border-b border-slate-200 dark:border-slate-800 text-slate-500 uppercase font-semibold">
                <tr>
                  <th className="py-3 px-4">Product ID & Name</th>
                  <th className="py-3 px-4">Risk Class</th>
                  <th className="py-3 px-4">Suitable Risk Profiles</th>
                  <th className="py-3 px-4">Mandatory Disclosure</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
                {(productsQuery.data || [])
                  .filter((p) => p.product_name.toLowerCase().includes(searchQuery.toLowerCase()) || p.product_id.toLowerCase().includes(searchQuery.toLowerCase()))
                  .map((p) => (
                    <tr key={p.product_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-900 dark:text-slate-100">{p.product_name}</div>
                        <div className="text-[11px] text-slate-400 font-mono">ID: {p.product_id}</div>
                      </td>
                      <td className="py-3 px-4 font-semibold text-amber-600 dark:text-amber-400">{p.risk_class}</td>
                      <td className="py-3 px-4 text-slate-600 dark:text-slate-400">{p.suitable_risk_profiles}</td>
                      <td className="py-3 px-4 text-slate-500 max-w-xs truncate" title={p.disclosure_requirements}>
                        {p.disclosure_requirements}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button onClick={() => openEditProduct(p)} className="p-1.5 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950/50 rounded" title="Edit Product">
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                          <button onClick={() => setDeleteModal({ open: true, type: "products", id: p.product_id, name: p.product_name })} className="p-1.5 text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/50 rounded" title="Delete Product">
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}

        {/* TAB 5: REGULATORY AUTHORITIES */}
        {activeTab === "authorities" && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-950/60 border-b border-slate-200 dark:border-slate-800 text-slate-500 uppercase font-semibold">
                <tr>
                  <th className="py-3 px-4">Authority Code & Name</th>
                  <th className="py-3 px-4">Jurisdiction</th>
                  <th className="py-3 px-4">Official Portal</th>
                  <th className="py-3 px-4">Description / Mandate</th>
                  <th className="py-3 px-4">Regulations</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
                {(authoritiesQuery.data || [])
                  .filter((a) =>
                    a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                    a.short_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
                    (a.jurisdiction || "").toLowerCase().includes(searchQuery.toLowerCase())
                  )
                  .map((a) => (
                    <tr key={a.authority_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold border ${
                            a.short_code === "SEBI"
                              ? "bg-blue-50 dark:bg-blue-950/50 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-900"
                              : a.short_code === "AMFI"
                              ? "bg-purple-50 dark:bg-purple-950/50 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-900"
                              : a.short_code === "RBI"
                              ? "bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-900"
                              : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700"
                          }`}>
                            {a.short_code}
                          </span>
                          <span className="font-semibold text-slate-900 dark:text-slate-100">{a.name}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-slate-600 dark:text-slate-400 font-medium">
                        {a.jurisdiction}
                      </td>
                      <td className="py-3 px-4">
                        {a.website_url ? (
                          <a
                            href={a.website_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400 hover:underline font-mono text-[11px]"
                          >
                            <Globe className="w-3 h-3 shrink-0" />
                            <span className="truncate max-w-[130px]">{a.website_url.replace(/^https?:\/\//, '')}</span>
                            <ExternalLink className="w-2.5 h-2.5 shrink-0" />
                          </a>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-slate-500 max-w-xs truncate" title={a.description}>
                        {a.description || "—"}
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                          {a.document_count || 0} docs
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          a.active
                            ? "bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                            : "bg-slate-100 dark:bg-slate-800 text-slate-500 border border-slate-200 dark:border-slate-700"
                        }`}>
                          {a.active ? "ACTIVE" : "INACTIVE"}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => openEditAuthority(a)}
                            className="p-1.5 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950/50 rounded"
                            title="Edit Authority"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => setDeleteModal({ open: true, type: "authorities", id: a.authority_id, name: `${a.short_code} (${a.name})` })}
                            className="p-1.5 text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/50 rounded"
                            title="Delete Authority"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ==================================================================== */}
      {/* USER MODAL */}
      {/* ==================================================================== */}
      {userModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-2xl w-full max-w-md overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/70 dark:bg-slate-950/40">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                {userModal.mode === "create" ? "Add New System User" : `Edit User: ${userModal.data?.username}`}
              </h3>
              <button onClick={() => setUserModal({ open: false, mode: "create" })} className="text-slate-400 hover:text-slate-600"><X className="w-4 h-4" /></button>
            </div>
            <form onSubmit={handleSaveUser} className="p-5 space-y-3.5 text-xs">
              <div>
                <label className="block font-semibold mb-1">Username *</label>
                <input required type="text" value={userForm.username} onChange={(e) => setUserForm({ ...userForm, username: e.target.value })} className="w-full px-3 py-2 border rounded-md dark:bg-slate-800 dark:border-slate-700" />
              </div>
              <div>
                <label className="block font-semibold mb-1">Full Name</label>
                <input type="text" value={userForm.full_name} onChange={(e) => setUserForm({ ...userForm, full_name: e.target.value })} className="w-full px-3 py-2 border rounded-md dark:bg-slate-800 dark:border-slate-700" />
              </div>
              <div>
                <label className="block font-semibold mb-1">Email Address *</label>
                <input required type="email" value={userForm.email} onChange={(e) => setUserForm({ ...userForm, email: e.target.value })} className="w-full px-3 py-2 border rounded-md dark:bg-slate-800 dark:border-slate-700" />
              </div>
              <div>
                <label className="block font-semibold mb-1">{userModal.mode === "create" ? "Password *" : "New Password (leave blank to keep current)"}</label>
                <input type="password" required={userModal.mode === "create"} value={userForm.password} onChange={(e) => setUserForm({ ...userForm, password: e.target.value })} className="w-full px-3 py-2 border rounded-md dark:bg-slate-800 dark:border-slate-700" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold mb-1">System Role</label>
                  <select value={userForm.role} onChange={(e) => setUserForm({ ...userForm, role: e.target.value })} className="w-full px-3 py-2 border rounded-md dark:bg-slate-800 dark:border-slate-700">
                    <option value="Audit Officer">Audit Officer</option>
                    <option value="Admin">Admin</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">Team</label>
                  <input type="text" value={userForm.team} onChange={(e) => setUserForm({ ...userForm, team: e.target.value })} className="w-full px-3 py-2 border rounded-md dark:bg-slate-800 dark:border-slate-700" />
                </div>
              </div>
              <div className="pt-2 flex justify-end gap-2">
                <button type="button" onClick={() => setUserModal({ open: false, mode: "create" })} className="px-3 py-1.5 text-slate-600 rounded">Cancel</button>
                <button type="submit" className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded">Save User</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* RM MODAL */}
      {/* ==================================================================== */}
      {rmModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-2xl w-full max-w-md overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/70 dark:bg-slate-950/40">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                {rmModal.mode === "create" ? "Register Relationship Manager" : `Edit RM: ${rmModal.data?.rm_id}`}
              </h3>
              <button onClick={() => setRmModal({ open: false, mode: "create" })} className="text-slate-400 hover:text-slate-600"><X className="w-4 h-4" /></button>
            </div>
            <form onSubmit={handleSaveRM} className="p-5 space-y-3.5 text-xs">
              {rmModal.mode === "create" && (
                <div>
                  <label className="block font-semibold mb-1">RM ID (e.g., RM-006)</label>
                  <input type="text" placeholder="Leave empty for auto-generated" value={rmForm.rm_id} onChange={(e) => setRmForm({ ...rmForm, rm_id: e.target.value })} className="w-full px-3 py-2 border rounded-md dark:bg-slate-800 dark:border-slate-700" />
                </div>
              )}
              <div>
                <label className="block font-semibold mb-1">Full Name *</label>
                <input required type="text" value={rmForm.full_name} onChange={(e) => setRmForm({ ...rmForm, full_name: e.target.value })} className="w-full px-3 py-2 border rounded-md dark:bg-slate-800 dark:border-slate-700" />
              </div>
              <div>
                <label className="block font-semibold mb-1">Branch Location *</label>
                <input required type="text" value={rmForm.branch} onChange={(e) => setRmForm({ ...rmForm, branch: e.target.value })} className="w-full px-3 py-2 border rounded-md dark:bg-slate-800 dark:border-slate-700" />
              </div>
              <div className="pt-2 flex justify-end gap-2">
                <button type="button" onClick={() => setRmModal({ open: false, mode: "create" })} className="px-3 py-1.5 text-slate-600 rounded">Cancel</button>
                <button type="submit" className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded">Save RM</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* CUSTOMER MODAL */}
      {/* ==================================================================== */}
      {customerModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-2xl w-full max-w-md overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/70 dark:bg-slate-950/40">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                {customerModal.mode === "create" ? "Add Customer Profile" : `Edit Customer: ${customerModal.data?.customer_id}`}
              </h3>
              <button onClick={() => setCustomerModal({ open: false, mode: "create" })} className="text-slate-400 hover:text-slate-600"><X className="w-4 h-4" /></button>
            </div>
            <form onSubmit={handleSaveCustomer} className="p-5 space-y-3.5 text-xs">
              <div>
                <label className="block font-semibold mb-1">Full Name *</label>
                <input required type="text" value={customerForm.full_name} onChange={(e) => setCustomerForm({ ...customerForm, full_name: e.target.value })} className="w-full px-3 py-2 border rounded-md dark:bg-slate-800 dark:border-slate-700" />
              </div>
              <div>
                <label className="block font-semibold mb-1">Mobile Number</label>
                <input type="text" value={customerForm.mobile_number} onChange={(e) => setCustomerForm({ ...customerForm, mobile_number: e.target.value })} className="w-full px-3 py-2 border rounded-md dark:bg-slate-800 dark:border-slate-700" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold mb-1">Risk Profile</label>
                  <select value={customerForm.risk_profile} onChange={(e) => setCustomerForm({ ...customerForm, risk_profile: e.target.value })} className="w-full px-3 py-2 border rounded-md dark:bg-slate-800 dark:border-slate-700">
                    <option value="Conservative">Conservative</option>
                    <option value="Moderate">Moderate</option>
                    <option value="Aggressive">Aggressive</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">KYC Status</label>
                  <select value={customerForm.kyc_status} onChange={(e) => setCustomerForm({ ...customerForm, kyc_status: e.target.value })} className="w-full px-3 py-2 border rounded-md dark:bg-slate-800 dark:border-slate-700">
                    <option value="VERIFIED">VERIFIED</option>
                    <option value="PENDING">PENDING</option>
                    <option value="REJECTED">REJECTED</option>
                  </select>
                </div>
              </div>
              <div className="pt-2 flex justify-end gap-2">
                <button type="button" onClick={() => setCustomerModal({ open: false, mode: "create" })} className="px-3 py-1.5 text-slate-600 rounded">Cancel</button>
                <button type="submit" className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded">Save Customer</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* PRODUCT MODAL */}
      {/* ==================================================================== */}
      {productModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-2xl w-full max-w-md overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/70 dark:bg-slate-950/40">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                {productModal.mode === "create" ? "Register Mutual Fund Product" : `Edit Product: ${productModal.data?.product_id}`}
              </h3>
              <button onClick={() => setProductModal({ open: false, mode: "create" })} className="text-slate-400 hover:text-slate-600"><X className="w-4 h-4" /></button>
            </div>
            <form onSubmit={handleSaveProduct} className="p-5 space-y-3.5 text-xs">
              <div>
                <label className="block font-semibold mb-1">Product / Fund Name *</label>
                <input required type="text" value={productForm.product_name} onChange={(e) => setProductForm({ ...productForm, product_name: e.target.value })} className="w-full px-3 py-2 border rounded-md dark:bg-slate-800 dark:border-slate-700" />
              </div>
              <div>
                <label className="block font-semibold mb-1">Risk Classification</label>
                <select value={productForm.risk_class} onChange={(e) => setProductForm({ ...productForm, risk_class: e.target.value })} className="w-full px-3 py-2 border rounded-md dark:bg-slate-800 dark:border-slate-700">
                  <option value="Low Risk">Low Risk</option>
                  <option value="Moderate Risk">Moderate Risk</option>
                  <option value="High Risk">High Risk</option>
                  <option value="Very High Risk">Very High Risk</option>
                </select>
              </div>
              <div>
                <label className="block font-semibold mb-1">Suitable Risk Profiles</label>
                <input type="text" value={productForm.suitable_risk_profiles} onChange={(e) => setProductForm({ ...productForm, suitable_risk_profiles: e.target.value })} className="w-full px-3 py-2 border rounded-md dark:bg-slate-800 dark:border-slate-700" />
              </div>
              <div>
                <label className="block font-semibold mb-1">Disclosure Requirements</label>
                <textarea rows={2} value={productForm.disclosure_requirements} onChange={(e) => setProductForm({ ...productForm, disclosure_requirements: e.target.value })} className="w-full px-3 py-2 border rounded-md dark:bg-slate-800 dark:border-slate-700" />
              </div>
              <div className="pt-2 flex justify-end gap-2">
                <button type="button" onClick={() => setProductModal({ open: false, mode: "create" })} className="px-3 py-1.5 text-slate-600 rounded">Cancel</button>
                <button type="submit" className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded">Save Product</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* AUTHORITY MODAL */}
      {/* ==================================================================== */}
      {authorityModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-2xl w-full max-w-md overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/70 dark:bg-slate-950/40">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <Landmark className="w-4 h-4 text-blue-600" />
                {authorityModal.mode === "create" ? "Add Regulatory Authority" : `Edit Authority: ${authorityModal.data?.short_code}`}
              </h3>
              <button onClick={() => setAuthorityModal({ open: false, mode: "create" })} className="text-slate-400 hover:text-slate-600"><X className="w-4 h-4" /></button>
            </div>
            <form onSubmit={handleSaveAuthority} className="p-5 space-y-3.5 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold mb-1">Short Code *</label>
                  <input
                    required
                    type="text"
                    placeholder="e.g. SEBI, AMFI, RBI"
                    value={authorityForm.short_code}
                    onChange={(e) => setAuthorityForm({ ...authorityForm, short_code: e.target.value.toUpperCase() })}
                    className="w-full px-3 py-2 border rounded-md dark:bg-slate-800 dark:border-slate-700 font-mono"
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Jurisdiction / Scope</label>
                  <input
                    type="text"
                    placeholder="e.g. Securities & Capital Markets"
                    value={authorityForm.jurisdiction}
                    onChange={(e) => setAuthorityForm({ ...authorityForm, jurisdiction: e.target.value })}
                    className="w-full px-3 py-2 border rounded-md dark:bg-slate-800 dark:border-slate-700"
                  />
                </div>
              </div>
              <div>
                <label className="block font-semibold mb-1">Full Authority Name *</label>
                <input
                  required
                  type="text"
                  placeholder="e.g. Securities and Exchange Board of India"
                  value={authorityForm.name}
                  onChange={(e) => setAuthorityForm({ ...authorityForm, name: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md dark:bg-slate-800 dark:border-slate-700"
                />
              </div>
              <div>
                <label className="block font-semibold mb-1">Official Portal URL</label>
                <input
                  type="url"
                  placeholder="https://www.sebi.gov.in"
                  value={authorityForm.website_url}
                  onChange={(e) => setAuthorityForm({ ...authorityForm, website_url: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md dark:bg-slate-800 dark:border-slate-700 font-mono text-[11px]"
                />
              </div>
              <div>
                <label className="block font-semibold mb-1">Mandate & Description</label>
                <textarea
                  rows={2}
                  placeholder="Statutory regulatory body overseeing..."
                  value={authorityForm.description}
                  onChange={(e) => setAuthorityForm({ ...authorityForm, description: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md dark:bg-slate-800 dark:border-slate-700"
                />
              </div>
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="auth_active"
                  checked={authorityForm.active}
                  onChange={(e) => setAuthorityForm({ ...authorityForm, active: e.target.checked })}
                  className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="auth_active" className="text-xs text-slate-700 dark:text-slate-300 font-medium">
                  Active in Compliance Engine & Regulations Corpus
                </label>
              </div>
              <div className="pt-2 flex justify-end gap-2">
                <button type="button" onClick={() => setAuthorityModal({ open: false, mode: "create" })} className="px-3 py-1.5 text-slate-600 rounded">Cancel</button>
                <button type="submit" className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded">Save Authority</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* DELETE MODAL */}
      {/* ==================================================================== */}
      {deleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-2xl w-full max-w-sm p-5 space-y-4">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-full bg-rose-50 text-rose-600 shrink-0">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">Confirm Deletion</h3>
                <p className="text-xs text-slate-500 mt-1">
                  Are you sure you want to permanently delete <strong>{deleteModal.name}</strong>?
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setDeleteModal(null)} className="px-3 py-1.5 text-xs text-slate-600 rounded">Cancel</button>
              <button onClick={handleDeleteConfirm} className="px-4 py-1.5 text-xs bg-rose-600 hover:bg-rose-700 text-white font-semibold rounded">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
