import React, { useRef, useState, useEffect, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useCallDetail, callsService } from "../../services/callsService";
import { useCasesList } from "../../services/casesService";
import { AudioPlayer, AudioPlayerRef } from "../../components/shared/AudioPlayer";
import { TranscriptViewer } from "../../components/shared/TranscriptViewer";
import { SeverityBadge } from "../../components/shared/SeverityBadge";
import { LoadingState } from "../../components/shared/LoadingState";
import { ErrorState } from "../../components/shared/ErrorState";
import { TranscriptSegment } from "../../types";
import {
  ArrowLeft,
  Phone,
  Calendar,
  Clock,
  ShieldAlert,
  ShieldCheck,
  ExternalLink,
  ArrowRight,
  Copy,
  Check,
  Filter,
} from "lucide-react";

export const CallDetail: React.FC = () => {
  const { callId } = useParams<{ callId: string }>();
  const navigate = useNavigate();
  const playerRef = useRef<AudioPlayerRef>(null);
  const [activeTime, setActiveTime] = useState(0);
  const [copiedCaseId, setCopiedCaseId] = useState<string | null>(null);

  const handleCopyCaseId = (cId: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    navigator.clipboard.writeText(cId);
    setCopiedCaseId(cId);
    setTimeout(() => {
      setCopiedCaseId(null);
    }, 2000);
  };

  const formatConfidence = (val: any): string | null => {
    if (val === undefined || val === null || val === "") return null;
    const num = Number(val);
    if (isNaN(num)) return null;
    const pct = num <= 1 ? Math.round(num * 100) : Math.round(num);
    return `${pct}%`;
  };

  const { data: callDoc, isLoading, isError, error, refetch } = useCallDetail(callId || "");
  const { data: casesData, isLoading: isLoadingCases } = useCasesList({ call_id: callId });

  const handleSeek = (seconds: number) => {
    if (playerRef.current) {
      playerRef.current.seekTo(seconds);
    }
  };

  if (isLoading) {
    return <LoadingState message={`Retrieving call dossier ${callId}...`} />;
  }

  if (isError || !callDoc) {
    return (
      <ErrorState
        title="Call Dossier Not Found"
        message={error instanceof Error ? error.message : `Unable to locate call ${callId}`}
        onRetry={() => refetch()}
      />
    );
  }

  const isFlagged = Boolean(
    callDoc.has_violation ||
    callDoc.case_id ||
    (callDoc.cases && callDoc.cases.length > 0) ||
    (callDoc.finding_ids && callDoc.finding_ids.length > 0) ||
    (callDoc.findings && callDoc.findings.length > 0)
  );

  const primaryCaseId =
    callDoc.case_id ||
    (callDoc.cases && callDoc.cases[0]?.case_id) ||
    (callDoc.finding_ids && callDoc.finding_ids[0]?.replace("FND-", "CASE-")) ||
    (callDoc.findings && callDoc.findings[0]?.finding_id?.replace("FND-", "CASE-"));

  const associatedCases: Array<{ case_id: string; status?: string; category?: string; severity?: string }> =
    callDoc.cases && callDoc.cases.length > 0
      ? callDoc.cases
      : primaryCaseId
      ? [{ case_id: primaryCaseId, status: "OPEN" }]
      : [];

  const rawSegments = callDoc.transcript_segments || callDoc.transcript || [];
  const segments: TranscriptSegment[] = rawSegments.map((s: any, idx: number) => {
    const startSec = s.start_time !== undefined ? Number(s.start_time) : (s.start_ms !== undefined ? s.start_ms / 1000 : 0);
    const endSec = s.end_time !== undefined ? Number(s.end_time) : (s.end_ms !== undefined ? s.end_ms / 1000 : startSec + 5);
    const m = Math.floor(startSec / 60);
    const sec = Math.floor(startSec % 60);
    const speakerRole = String(s.speaker || s.role || (s.speaker_label === "spk_0" ? "RM" : "CUSTOMER")).toUpperCase();
    const isRM = speakerRole.includes("RM");

    return {
      id: s.segment_id || `seg-${idx}`,
      speaker: (isRM ? "RM" : "CUSTOMER") as any,
      speaker_name: isRM ? (callDoc.rm_name || `RM (${callDoc.rm_id || "RM"})`) : (callDoc.customer_name || `Client (${callDoc.customer_id || "Client"})`),
      text: s.text_english || s.text || s.text_original || "",
      text_english: s.text_english || s.text || "",
      text_original: s.text_original || "",
      start_time: startSec,
      end_time: endSec,
      timestamp_display: s.timestamp_display || `${m.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`,
      is_violation: Boolean(s.is_violation),
    };
  });

  const audioUrl = callsService.getAudioUrl(callId || "");
  const durationSec = callDoc.duration_seconds || 120;
  const durationDisplay = `${Math.floor(durationSec / 60)}:${String(Math.floor(durationSec % 60)).padStart(2, "0")}`;

  // Phase 12: Stage timer durations for this specific call
  const tStart = callDoc.processing_started_at ? new Date(callDoc.processing_started_at).getTime() : null;
  const tIndex = callDoc.indexed_at ? new Date(callDoc.indexed_at).getTime() : null;
  const tDetect = callDoc.detection_completed_at ? new Date(callDoc.detection_completed_at).getTime() : null;
  const tInvest = callDoc.investigation_completed_at ? new Date(callDoc.investigation_completed_at).getTime() : null;

  const ingestDuration = callDoc.ingest_duration_s != null ? Number(callDoc.ingest_duration_s).toFixed(1) : ((tStart && tIndex && tIndex >= tStart) ? ((tIndex - tStart) / 1000).toFixed(1) : null);
  const detectDuration = callDoc.detect_duration_s != null ? Number(callDoc.detect_duration_s).toFixed(1) : ((tIndex && tDetect && tDetect >= tIndex && (tDetect - tIndex) <= 7200000) ? ((tDetect - tIndex) / 1000).toFixed(1) : null);
  const investDuration = callDoc.invest_duration_s != null ? Number(callDoc.invest_duration_s).toFixed(1) : ((tDetect && tInvest && tInvest >= tDetect && (tInvest - tDetect) <= 7200000) ? ((tInvest - tDetect) / 1000).toFixed(1) : null);
  const e2eDuration = callDoc.e2e_duration_s != null ? Number(callDoc.e2e_duration_s).toFixed(1) : ((tStart && tInvest && tInvest >= tStart && (tInvest - tStart) <= 7200000) ? ((tInvest - tStart) / 1000).toFixed(1) : null);

  // Merge cases from useCasesList and callDoc.cases
  const queriedCases: any[] = casesData?.items || [];
  const embeddedCases: any[] = (callDoc as any)?.cases || [];

  const casesMap = new Map<string, any>();
  queriedCases.forEach((c) => casesMap.set(c.case_id, c));
  embeddedCases.forEach((c) => {
    if (!casesMap.has(c.case_id)) {
      casesMap.set(c.case_id, c);
    }
  });

  if (casesMap.size === 0 && primaryCaseId) {
    casesMap.set(primaryCaseId, {
      case_id: primaryCaseId,
      status: "OPEN",
      priority: callDoc.findings?.[0]?.severity || "HIGH",
      severity: callDoc.findings?.[0]?.severity || "HIGH",
      category: callDoc.findings?.[0]?.category,
      finding: callDoc.findings?.[0],
    });
  }

  const casesList = Array.from(casesMap.values());

  return (
    <div className="space-y-5">
      {/* Top Breadcrumb & Navigation */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <button
          onClick={() => navigate("/calls")}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Calls List
        </button>

        {casesList.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 font-mono">
              {casesList.length} {casesList.length === 1 ? "Case" : "Cases"} Linked
            </span>
          </div>
        )}
      </div>

      {/* Call Header Card */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-700 dark:text-slate-300">
              <Phone className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-lg font-bold font-mono text-slate-900 dark:text-slate-100">
                  {callDoc.call_id || callDoc.id}
                </h1>
                {Boolean(callDoc.has_violation) ? (
                  <SeverityBadge severity={callDoc.findings?.[0]?.severity || (callDoc as any).severity || "HIGH"} size="sm" />
                ) : (
                  <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">
                    CLEAN
                  </span>
                )}
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                  {callDoc.processing_status || (callDoc as any).status || "PROCESSED"}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Recorded conversation between RM {callDoc.rm_name || callDoc.rm_id} and Customer {callDoc.customer_name || callDoc.customer_id}
              </p>
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-4 text-xs text-slate-600 dark:text-slate-400 font-mono">
              <div className="flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-slate-400" />
                <span>Duration: {durationDisplay}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Calendar className="w-4 h-4 text-slate-400" />
                <span>{callDoc.date_time || "Recent"}</span>
              </div>
            </div>

            {/* Processing Timeline */}
            <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-slate-500 font-mono">
              <Clock className="w-3 h-3 text-slate-400 shrink-0" />
              <span className="text-slate-600 dark:text-slate-400 font-sans font-semibold not-italic mr-0.5">Timeline:</span>
              <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                Ingested {ingestDuration ? `${ingestDuration}s` : "—"}
              </span>
              <ArrowRight className="w-2.5 h-2.5 text-slate-400 shrink-0" />
              <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                Detected {detectDuration ? `${detectDuration}s` : "—"}
              </span>
              <ArrowRight className="w-2.5 h-2.5 text-slate-400 shrink-0" />
              <span className="px-1.5 py-0.5 rounded bg-blue-50 dark:bg-blue-950/50 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-900 font-semibold">
                Investigated {investDuration ? `${investDuration}s` : "—"}
              </span>
              {e2eDuration && (
                <span className="text-slate-400 ml-1">
                  · Total <strong className="text-slate-700 dark:text-slate-300">{e2eDuration}s</strong>
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid: Left Column drives natural height, Right Column stretches with absolute inner transcript */}
      <div
        id="call-detail-grid"
        className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch overflow-x-hidden"
      >
        {/* Left Column: Audio Waveform Player, RM/Client Cards, and Cases List */}
        <div id="left-column" className="lg:col-span-6 flex flex-col space-y-4 min-h-[420px]">
          {/* Playable call thing */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-4 shadow-sm shrink-0">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">
              Acoustic Surveillance Playback
            </h3>
            <AudioPlayer
              ref={playerRef}
              audioUrl={audioUrl}
              onTimeUpdate={(t) => setActiveTime(t)}
            />
          </div>

          {/* Two cards: RM and Customer */}
          <div className="grid grid-cols-2 gap-4 shrink-0">
            <div className="p-3.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-sm">
              <span className="text-[11px] text-slate-400 uppercase font-semibold tracking-wider">
                Relationship Manager
              </span>
              <p className="text-sm font-bold text-slate-900 dark:text-slate-100 mt-1">
                {callDoc.rm_name || callDoc.rm_id}
              </p>
              <span className="text-xs text-slate-500 font-mono mt-0.5 block">{callDoc.rm_id}</span>
            </div>
            <div className="p-3.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-sm">
              <span className="text-[11px] text-slate-400 uppercase font-semibold tracking-wider">
                Client / Counterparty
              </span>
              <p className="text-sm font-bold text-slate-900 dark:text-slate-100 mt-1">
                {callDoc.customer_name || callDoc.customer_id}
              </p>
              <span className="text-xs text-slate-500 font-mono mt-0.5 block">{callDoc.customer_id}</span>
            </div>
          </div>

          {/* Below that: List of Cases of this particular call */}
          <div
            id="compliance-cases-card"
            className="flex-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-4 shadow-sm flex flex-col"
          >
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-100 dark:border-slate-800 shrink-0">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-red-600 dark:text-red-400" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">
                  Compliance Cases
                </h3>
                <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-semibold">
                  {casesList.length}
                </span>
              </div>
              {isLoadingCases && (
                <span className="text-[11px] text-slate-400 animate-pulse">Updating cases...</span>
              )}
            </div>

            {casesList.length === 0 ? (
              <div className="flex-1 min-h-[140px] flex flex-col items-center justify-center p-6 text-center rounded-lg bg-slate-50/50 dark:bg-slate-800/20 border border-dashed border-slate-200 dark:border-slate-800/80">
                <ShieldCheck className="w-8 h-8 text-emerald-500 mb-2 opacity-80" />
                <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  No Compliance Cases Found
                </p>
                <p className="text-[11px] text-slate-500 mt-1 max-w-xs">
                  This call has passed surveillance screening with zero flagged violations.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {casesList.map((c) => {
                  const caseId = c.case_id;
                  const severity = c.finding?.severity || c.severity || c.priority || "HIGH";
                  const status = c.status || "OPEN";
                  const category = c.finding?.category || c.category || (callDoc.findings?.[0]?.category);
                  const confidence = c.finding?.confidence || c.confidence;
                  const citation = c.finding?.regulation_citation_label || c.regulation_citation_label;
                  const isCopied = copiedCaseId === caseId;

                  return (
                    <div
                      key={caseId}
                      className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800/80 bg-slate-50/70 dark:bg-slate-950/50 hover:border-slate-300 dark:hover:border-slate-700/80 hover:bg-slate-100/60 dark:hover:bg-slate-950/70 transition-all space-y-2.5 shadow-xs"
                    >
                      {/* Top Row: Case ID, Severity, Status */}
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono font-bold text-slate-900 dark:text-slate-100">
                            {caseId}
                          </span>
                          <SeverityBadge severity={severity} size="sm" />
                          <span
                            className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-bold uppercase tracking-wider ${
                              status === "RESOLVED"
                                ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border dark:border-emerald-800/60"
                                : "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 dark:border dark:border-amber-800/60"
                            }`}
                          >
                            {status}
                          </span>
                        </div>

                        {/* Actions: Copy Case ID and Go to Particular Case Page */}
                        <div className="flex items-center gap-1.5">
                          {/* Copy Case ID Button */}
                          <button
                            type="button"
                            onClick={(e) => handleCopyCaseId(caseId, e)}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded border border-slate-300 dark:border-slate-700/80 bg-white dark:bg-slate-900/90 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 transition-colors shadow-xs cursor-pointer active:scale-95"
                            title="Copy Case ID to clipboard"
                          >
                            {isCopied ? (
                              <>
                                <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                                <span className="text-emerald-600 dark:text-emerald-400 font-semibold text-[11px]">
                                  Copied!
                                </span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
                                <span className="text-[11px]">Copy ID</span>
                              </>
                            )}
                          </button>

                          {/* Navigate to Particular Case Page Button */}
                          <button
                            type="button"
                            onClick={() => navigate(`/cases/${caseId}`)}
                            className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded bg-red-600 hover:bg-red-700 active:bg-red-800 text-white transition-colors shadow-xs cursor-pointer"
                            title={`Navigate to Case ${caseId}`}
                          >
                            <span>Go to Case</span>
                            <ArrowRight className="w-3 h-3" />
                          </button>
                        </div>
                      </div>

                      {/* Category & Confidence Details */}
                      {(category || citation || confidence !== undefined) && (
                        <div className="pt-2 border-t border-slate-200/70 dark:border-slate-800/80 text-xs space-y-1">
                          <div className="flex flex-wrap items-center gap-2">
                            {category && (
                              <span className="font-semibold text-slate-800 dark:text-slate-200">
                                {category.replace(/_/g, " ")}
                              </span>
                            )}
                            {formatConfidence(confidence) && (
                              <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                                Confidence: {formatConfidence(confidence)}
                              </span>
                            )}
                          </div>
                          {citation && (
                            <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-1 font-mono">
                              {citation}
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Interactive Transcript - position relative wrapper, absolute inner card on lg+ */}
        <div
          id="right-column"
          className="lg:col-span-6 relative w-full min-h-[420px] max-lg:h-[60vh] max-lg:max-h-[60vh]"
        >
          <TranscriptViewer
            id="transcript-viewer-card"
            segments={segments}
            activeTime={activeTime}
            onSeekToTime={handleSeek}
            className="lg:absolute lg:inset-0 w-full h-full"
          />
        </div>
      </div>
    </div>
  );
};
