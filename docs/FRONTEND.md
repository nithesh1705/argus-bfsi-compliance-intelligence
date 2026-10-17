# ARGUS — Frontend Architecture & UI System

Technical specification of the React 18 frontend, route table, design tokens, dual-theme engine with the animated owl toggle, and shared components.

[Back to documentation index](./INDEX.md) | [Next: Configuration Reference](./CONFIGURATION.md)

---

## Table of Contents

- [Frontend Overview](#frontend-overview)
- [Route Architecture & Table](#route-architecture--table)
- [Page Specifications & API Integration](#page-specifications--api-integration)
- [Theme System & Animated Owl Toggle](#theme-system--animated-owl-toggle)
- [Shared Component Library](#shared-component-library)
- [Build, Environment & Docker Configuration](#build-environment--docker-configuration)
- [Related Documents](#related-documents)

---

## Frontend Overview

The ARGUS user interface is built with **React 18**, **TypeScript**, **Vite**, and **Tailwind CSS**. It is designed specifically for financial compliance officers and wealth management supervisors, prioritizing high-density telemetry, clear visual hierarchy, sub-second interactive waveform rendering, and accessibility.

- **Source Root:** [`../frontend/src/`](../frontend/src/)
- **Router Configuration:** [`../frontend/src/router.tsx`](../frontend/src/router.tsx)
- **Design Tokens & Global Styles:** [`../frontend/src/styles/globals.css`](../frontend/src/styles/globals.css)

---

## Route Architecture & Table

Routes are managed using React Router v6 with authenticated route protection ([`../frontend/src/components/auth/ProtectedRoute.tsx`](../frontend/src/components/auth/ProtectedRoute.tsx)) and dynamic role-based dashboard redirection:

| Route Path | Component | Protected | Target Role | Primary Purpose |
|---|---|:---:|---|---|
| `/login` | `Login` | No | Public | User authentication with animated waveform |
| `/` | `DashboardRoute` | Yes | Audit Officer / Admin | Role-aware landing: Operational Dashboard or Executive Analytics |
| `/ai-investigation` | `AIInvestigation` | Yes | Audit Officer / Admin | Interactive compliance chat assistant |
| `/calls` | `Calls` | Yes | Audit Officer / Admin | Filterable surveillance call roster |
| `/calls/:callId` | `CallDetail` | Yes | Audit Officer / Admin | Waveform audio player, synchronized transcript, and case list |
| `/cases` | `ComplianceCases` | Yes | Audit Officer / Admin | Filterable compliance cases list with `needs_review` flag |
| `/cases/:caseId` | `CaseDetail` | Yes | Audit Officer / Admin | Assembled Evidence Chain with click-to-audio seek |
| `/rm-analytics` | `RMAnalytics` | Yes | Audit Officer / Admin | Relationship Manager risk roster and surveillance metrics |
| `/rm-analytics/:rmId` | `RMDetail` | Yes | Audit Officer / Admin | Deep-dive RM compliance dossier with email report modal |
| `/regulations` | `Regulations` | Yes | Audit Officer / Admin | Regulatory corpus management, PDF preview, and chunk indexing |
| `/settings` | `Settings` | Yes | Audit Officer / Admin | System parameters, model IDs, and provider status |
| `/observability` | `Observability` | Yes | Admin / Audit Officer | Real-time APM telemetry, stage latency distributions, and health |
| `/admin/manage` | `AdminManagement` | Yes | Admin | Master Data CRUD (Users, RMs, Customers, Products, Authorities) |

Source implementation: [`../frontend/src/router.tsx`](../frontend/src/router.tsx)

---

## Page Specifications & API Integration

### 1. Login Page (`/login`)
- **Source:** [`../frontend/src/pages/Login/index.tsx`](../frontend/src/pages/Login/index.tsx)
- **Features:** Dynamic HTML5 canvas waveform animation ([`AudioWaveCanvas.tsx`](../frontend/src/pages/Login/components/AudioWaveCanvas.tsx)) that reacts to user typing; animated preview violation cards ([`FindingCard.tsx`](../frontend/src/pages/Login/components/FindingCard.tsx)); theme toggle.
- **API Calls:** `POST /api/auth/login`.

### 2. Operational Dashboard (`/` for Audit Officer)
- **Source:** [`../frontend/src/pages/Dashboard/index.tsx`](../frontend/src/pages/Dashboard/index.tsx)
- **Features:** Metric cards (Calls Monitored, Violations, Open Cases, Avg Latency), trend charts, violation category breakdown, recent critical cases table with instant navigation.
- **API Calls:** `GET /api/dashboard/summary`.

### 3. Executive Analytics (`/` for Admin)
- **Source:** [`../frontend/src/pages/AdminDashboard/index.tsx`](../frontend/src/pages/AdminDashboard/index.tsx)
- **Features:** Date-range filterable executive compliance analytics, cross-branch violation heatmaps, risk distribution graphs.
- **API Calls:** `GET /api/admin/analytics`.

### 4. AI Investigation (`/ai-investigation`)
- **Source:** [`../frontend/src/pages/AIInvestigation/index.tsx`](../frontend/src/pages/AIInvestigation/index.tsx)
- **Features:** Multi-turn conversational interface for querying surveillance history; renders markdown replies; displays structured tool calling badges and clickable grounded citations.
- **API Calls:** `POST /api/chat/message`.

### 5. Calls & Call Detail (`/calls`, `/calls/:callId`)
- **Source:** [`../frontend/src/pages/Calls/index.tsx`](../frontend/src/pages/Calls/index.tsx), [`../frontend/src/pages/Calls/CallDetail.tsx`](../frontend/src/pages/Calls/CallDetail.tsx)
- **Features:** Filterable call list; detailed call view featuring WaveSurfer.js audio waveform player with play/pause, timecode display, and synchronized speaker transcript viewer. Clicking a transcript segment seeks the audio player to that exact millisecond.
- **API Calls:** `GET /api/calls`, `GET /api/calls/{call_id}`, `GET /api/calls/{call_id}/audio`.

### 6. Compliance Cases & Evidence Chain (`/cases`, `/cases/:caseId`)
- **Source:** [`../frontend/src/pages/ComplianceCases/index.tsx`](../frontend/src/pages/ComplianceCases/index.tsx), [`../frontend/src/pages/ComplianceCases/CaseDetail.tsx`](../frontend/src/pages/ComplianceCases/CaseDetail.tsx)
- **Features:** Case workflow management; Evidence Chain inspector displaying verbatim speech quotes, customer risk profile comparison, binding statutory citations with direct regulator links, forensic rationale, and interactive action buttons (Mark Reviewed, Dismiss, Escalate to Committee).
- **API Calls:** `GET /api/cases`, `GET /api/cases/{case_id}`, `PATCH /api/cases/{case_id}/status`, `POST /api/cases/{case_id}/escalate`.

### 7. RM Analytics & Detail (`/rm-analytics`, `/rm-analytics/:rmId`)
- **Source:** [`../frontend/src/pages/RMAnalytics/index.tsx`](../frontend/src/pages/RMAnalytics/index.tsx), [`../frontend/src/pages/RMAnalytics/RMDetail.tsx`](../frontend/src/pages/RMAnalytics/RMDetail.tsx)
- **Features:** Surveillance metrics across the RM roster; risk score rankings; individual RM dossier displaying historical call records, category breakdown, and the "Send Compliance Report" email modal ([`SendReportModal.tsx`](../frontend/src/components/reports/SendReportModal.tsx)).
- **API Calls:** `GET /api/rm`, `GET /api/rm/{rm_id}/analytics`, `POST /api/rm/{rm_id}/report/email`.

### 8. Regulations Management (`/regulations`)
- **Source:** [`../frontend/src/pages/Regulations/index.tsx`](../frontend/src/pages/Regulations/index.tsx)
- **Features:** Statutory corpus browser with total chunk counts; in-browser PDF preview stream modal; PDF download; drag-and-drop multipart upload for indexing new regulatory circulars.
- **API Calls:** `GET /api/regulations`, `GET /api/regulations/{doc_id}/preview`, `GET /api/regulations/{doc_id}/download`, `POST /api/regulations/upload`, `DELETE /api/regulations/{doc_id}`.

### 9. Settings (`/settings`)
- **Source:** [`../frontend/src/pages/Settings/index.tsx`](../frontend/src/pages/Settings/index.tsx)
- **Features:** Platform parameters; confidence threshold slider; AI Provider Execution Status table computed from real database findings; Cloud Trace deep link template configuration.
- **API Calls:** `GET /api/settings`, `PATCH /api/settings`, `GET /api/settings/provider-status`, `GET /api/system/health`.

### 10. Observability & APM Telemetry (`/observability`)
- **Source:** [`../frontend/src/pages/Observability/index.tsx`](../frontend/src/pages/Observability/index.tsx)
- **Features:** Headline pipeline performance metrics (mean, median, min, max durations); granular per-stage latency breakdown (ingestion, detection, investigation, archive); error ring buffer table; live service connectivity indicators.
- **API Calls:** `GET /api/observability/summary`, `GET /api/observability/pipeline`, `GET /api/observability/errors`, `GET /api/observability/services`.

### 11. Master Data CRUD (`/admin/manage`)
- **Source:** [`../frontend/src/pages/AdminManagement/index.tsx`](../frontend/src/pages/AdminManagement/index.tsx)
- **Features:** Administrative portal tabs to view, create, edit, and delete System Users, Relationship Managers, Customers, Product Schemes, and Regulatory Authorities.
- **API Calls:** `GET`, `POST`, `PUT`, `DELETE` on `/api/admin/*`.

---

## Theme System & Animated Owl Toggle

ARGUS implements a curated dual-theme system (Dark Mode by default and Light Mode) using tailored HSL color palettes defined in [`../frontend/src/styles/globals.css`](../frontend/src/styles/globals.css):
- **Dark Mode:** Deep slate-black canvas (`#06080F`, `#0B1120`), dark card surfaces (`#0F172A`), sharp borders (`#1E293B`), and vibrant accent indicators.
- **Light Mode:** High-contrast crisp paper canvas (`#F8FAFC`, `#F0F4FF`), clean white card surfaces (`#FFFFFF`), and soft borders (`#E2E8F0`).

### The Animated Owl Theme Toggle (`OwlThemeToggle.tsx`)
The centerpiece of the theme system is a custom SVG animated owl widget embedded at the bottom of the sidebar ([`../frontend/src/components/layout/OwlThemeToggle.tsx`](../frontend/src/components/layout/OwlThemeToggle.tsx)):
- **Expanded Sidebar State:** Renders a whimsical SVG nocturnal owl perched on a branch beneath an interactive sky (glowing crescent moon and stars in Dark Mode; warm radiant sun and clouds in Light Mode). Clicking toggles the theme with smooth CSS transitions.
- **Collapsed Sidebar State:** Shrinks to an icon-sized SVG perched owl with amber iris markings.
- **Accessibility:** Includes explicit `aria-label` ("Switch to light theme" / "Switch to dark theme"), full keyboard focus ring (`focus-visible`), and supports the `prefers-reduced-motion` media query.

---

## Shared Component Library

Re-usable components located in [`../frontend/src/components/shared/`](../frontend/src/components/shared/):

| Component | File Path | Key Capabilities |
|---|---|---|
| **AudioPlayer** | [`AudioPlayer.tsx`](../frontend/src/components/shared/AudioPlayer.tsx) | WaveSurfer.js waveform visualizer; supports play/pause, volume, seek, and jumping to specific second offsets. |
| **EvidenceChainPanel** | [`EvidenceChainPanel.tsx`](../frontend/src/components/shared/EvidenceChainPanel.tsx) | Structured presentation of raw quote, customer risk appetite, product risk class, citation label, and forensic rationale. |
| **TranscriptViewer** | [`TranscriptViewer.tsx`](../frontend/src/components/shared/TranscriptViewer.tsx) | Diarized speaker transcript stream with role tags (`RM`, `CUSTOMER`), search filtering, and click-to-audio sync. |
| **SeverityBadge** | [`SeverityBadge.tsx`](../frontend/src/components/shared/SeverityBadge.tsx) | Color-coded status badge (`HIGH`: red, `MEDIUM`: amber, `LOW`: blue). |
| **TrendChart** | [`TrendChart.tsx`](../frontend/src/components/shared/TrendChart.tsx) | Recharts time-series line chart tracking compliance cases and violation frequency. |
| **ChatMessageCard** | [`ChatMessageCard.tsx`](../frontend/src/components/shared/ChatMessageCard.tsx) | Formats assistant messages, function calling badges, and grounded citation chips. |
| **MarkdownRenderer** | [`MarkdownRenderer.tsx`](../frontend/src/components/shared/MarkdownRenderer.tsx) | Renders GitHub-flavored markdown with clean typography and syntax formatting. |

---

## Build, Environment & Docker Configuration

### Environment Variables
- `VITE_API_BASE_URL`: Base URL of the backend API (e.g. `http://localhost:8000` for local development, or `https://argus-backend-<PROJECT_NUMBER>.<REGION>.run.app` in production). Injected via Vite environment files or Cloud Run container environment.

### Production Multi-Stage Dockerfile
Defined in [`../frontend/Dockerfile`](../frontend/Dockerfile):
1. **Stage 1 (Builder):** Uses `node:20-alpine`, installs dependencies via `npm ci`, runs TypeScript type check (`tsc`), and compiles optimized production assets via `vite build`.
2. **Stage 2 (Server):** Uses lightweight `nginx:alpine`, copies built assets from `/app/dist` to `/usr/share/nginx/html`, and serves HTTP traffic with gzip compression and client-side SPA route rewrites (`try_files $uri $uri/ /index.html`).

---

## Related Documents

- [REST API Reference](./API.md)
- [Screenshot Gallery](./GLIMPSE.md)
- [System Architecture](./ARCHITECTURE.md)
- [Development Guide](./DEVELOPMENT.md)
