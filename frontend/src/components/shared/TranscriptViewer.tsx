import React, { useRef, useEffect } from "react";
import { TranscriptSegment } from "../../types";
import { cn } from "../../lib/utils";
import { User, Headphones, Clock, AlertTriangle } from "lucide-react";

interface TranscriptViewerProps {
  segments: TranscriptSegment[];
  activeTime?: number;
  onSeekToTime?: (seconds: number) => void;
  className?: string;
  id?: string;
  highlightViolationId?: string;
}

export const TranscriptViewer: React.FC<TranscriptViewerProps> = ({
  segments,
  activeTime = 0,
  onSeekToTime,
  className,
  id,
}) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const activeSegmentRef = useRef<HTMLDivElement>(null);
  const lastActiveIdRef = useRef<string | null>(null);

  // Find currently active segment
  const activeSegment = segments.find(
    (s) => activeTime >= s.start_time && activeTime <= s.end_time
  );

  useEffect(() => {
    if (activeSegment && activeSegment.id !== lastActiveIdRef.current) {
      lastActiveIdRef.current = activeSegment.id;

      if (activeSegmentRef.current && scrollContainerRef.current) {
        const container = scrollContainerRef.current;
        const elem = activeSegmentRef.current;

        const elemTop = elem.offsetTop - container.offsetTop;
        const containerHeight = container.clientHeight;

        container.scrollTo({
          top: Math.max(0, elemTop - containerHeight / 3),
          behavior: "smooth",
        });
      }
    }
  }, [activeSegment]);

  return (
    <div
      id={id}
      className={cn(
        "bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-4 shadow-sm flex flex-col overflow-hidden",
        className
      )}
    >
      <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800 mb-3 shrink-0">
        <div className="flex items-center gap-2">
          <Headphones className="w-4 h-4 text-slate-500" />
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            Call Audio Transcript
          </h3>
          <span className="text-xs text-slate-500 font-mono">
            ({segments.length} segments)
          </span>
        </div>
      </div>

      <div ref={scrollContainerRef} className="flex-1 overflow-y-auto space-y-3 pr-1 min-h-0 relative">
        {segments.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 py-12">
            <Headphones className="w-8 h-8 mb-2 opacity-40" />
            <p className="text-sm font-medium">No transcript segments recorded for this call.</p>
          </div>
        ) : (
          segments.map((segment) => {
            const isRM = segment.speaker === "RM";
            const isViolating = Boolean(segment.is_violation);
            const isCurrentlyPlaying =
              activeTime >= segment.start_time && activeTime <= segment.end_time;

            const englishText = segment.text_english || segment.text || "";
            const originalText = segment.text_original || "";
            const hasDifferentOriginal =
              originalText &&
              englishText &&
              originalText.trim().toLowerCase() !== englishText.trim().toLowerCase();

            return (
              <div
                key={segment.id}
                ref={isCurrentlyPlaying ? activeSegmentRef : undefined}
                className={cn(
                  "p-3 rounded-lg border transition-all text-sm leading-relaxed",
                  isViolating
                    ? "bg-red-50/80 border-red-300 dark:bg-red-950/30 dark:border-red-800 shadow-sm ring-1 ring-red-400/30"
                    : isCurrentlyPlaying
                      ? "bg-blue-50/50 border-blue-300 dark:bg-blue-950/30 dark:border-blue-800 ring-1 ring-blue-500/30"
                      : "bg-slate-50/40 border-slate-100 dark:bg-slate-950/40 dark:border-slate-800/70"
                )}
              >
                {/* Header row: Speaker & Clickable Timestamp */}
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <div
                      className={cn(
                        "w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold",
                        isRM
                          ? "bg-blue-100 text-blue-700 dark:bg-blue-900/60 dark:text-blue-300"
                          : "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/60 dark:text-emerald-300"
                      )}
                    >
                      {isRM ? "RM" : <User className="w-3 h-3" />}
                    </div>
                    <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                      {segment.speaker_name}
                    </span>

                    {isViolating && (
                      <span className="inline-flex items-center gap-1 text-[11px] font-bold font-mono bg-red-100 text-red-700 dark:bg-red-900/60 dark:text-red-200 px-2 py-0.5 rounded border border-red-300 dark:border-red-800">
                        <AlertTriangle className="w-3 h-3" />
                        FLAGGED VIOLATION
                      </span>
                    )}
                  </div>

                  {/* Clickable timestamp marker that jumps audio */}
                  <button
                    type="button"
                    onClick={() => onSeekToTime && onSeekToTime(segment.start_time)}
                    className={cn(
                      "inline-flex items-center gap-1 px-2 py-0.5 rounded font-mono text-xs font-medium transition-colors cursor-pointer group",
                      isViolating
                        ? "bg-red-200/90 text-red-900 dark:bg-red-900/70 dark:text-red-200 hover:bg-red-300"
                        : "bg-slate-200/70 text-slate-700 dark:bg-slate-800 dark:text-slate-300 hover:bg-slate-300 dark:hover:bg-slate-700"
                    )}
                    title={`Jump audio to ${segment.timestamp_display}`}
                  >
                    <Clock className="w-3 h-3 text-slate-500 group-hover:text-slate-900 dark:group-hover:text-slate-100" />
                    <span>[{segment.timestamp_display}]</span>
                  </button>
                </div>

                {/* Spoken Text — English Transcript */}
                <div className="space-y-1 mt-1">
                  <p
                    className={cn(
                      "text-slate-800 dark:text-slate-200 font-normal leading-relaxed",
                      isViolating && "font-semibold text-red-950 dark:text-red-100"
                    )}
                  >
                    {englishText}
                  </p>

                  {/* Vernacular Original Sub-block if multilingual */}
                  {hasDifferentOriginal && (
                    <div className="pt-1 text-xs text-slate-500 dark:text-slate-400 italic flex items-start gap-1">
                      <span className="not-italic font-mono uppercase text-[10px] tracking-wider px-1 py-0.2 bg-slate-200/60 dark:bg-slate-800 rounded text-slate-600 dark:text-slate-300 shrink-0">
                        Original Spoken
                      </span>
                      <span>&ldquo;{originalText}&rdquo;</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
