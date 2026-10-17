// frontend/src/pages/Login/components/FindingCard.tsx
import React from "react";
import { ShieldAlert, Zap, FileCheck2 } from "lucide-react";

export interface FindingCardData {
  id: string;
  type: "case" | "breach" | "evidence";
  label: string;
  badge: string;
  badgeColor: "red" | "purple" | "emerald";
  title: string;
  body: string;
  footer: { left: string; right: string; rightColor: string };
  rotation: number; // degrees
  offsetX: number; // horizontal offset in px
}

interface FindingCardProps {
  data: FindingCardData;
  cardRef?: React.Ref<HTMLDivElement>;
  isDark: boolean;
  isConnectorHovered: boolean;
  submitPulse: boolean;
}

const ICON_MAP = {
  case: ShieldAlert,
  breach: Zap,
  evidence: FileCheck2,
};

const BORDER_COLOR = {
  red: "border-l-red-500",
  purple: "border-l-purple-500",
  emerald: "border-l-emerald-500",
};

const BADGE_CLASSES = {
  red: "bg-red-100 text-red-700 dark:bg-red-950/80 dark:text-red-300",
  purple: "bg-purple-100 text-purple-700 dark:bg-purple-950/80 dark:text-purple-300",
  emerald: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/80 dark:text-emerald-300",
};

const ICON_COLOR = {
  red: "text-red-500",
  purple: "text-purple-500",
  emerald: "text-emerald-500",
};

const RIGHT_COLOR_MAP: Record<string, string> = {
  red: "text-red-500 dark:text-red-400",
  purple: "text-purple-500 dark:text-purple-400",
  emerald: "text-emerald-500 dark:text-emerald-400",
};

export const FindingCard: React.FC<FindingCardProps> = ({
  data,
  cardRef,
  isDark: _isDark,
  isConnectorHovered,
  submitPulse,
}) => {
  const Icon = ICON_MAP[data.type];
  const isHighlighted = isConnectorHovered || submitPulse;

  return (
    <div
      ref={cardRef}
      aria-hidden="true"
      style={{
        transform: `translateX(${data.offsetX}px) rotate(${data.rotation}deg)`,
        transition: "box-shadow 0.3s ease, transform 0.35s ease",
        willChange: "transform",
      }}
      className={[
        "w-full max-w-[340px] xl:max-w-[360px] p-3 xl:p-4 rounded-xl select-none relative",
        "bg-white/95 dark:bg-slate-900/95",
        "border border-slate-200/90 dark:border-slate-800/90",
        `border-l-[3.5px] ${BORDER_COLOR[data.badgeColor]}`,
        isHighlighted
          ? "shadow-2xl scale-[1.02]"
          : "shadow-md hover:shadow-lg",
        "backdrop-blur-md",
      ].join(" ")}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] xl:text-[10.5px] font-mono font-bold text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
          <Icon className={`w-3.5 h-3.5 ${ICON_COLOR[data.badgeColor]}`} />
          {data.label}
        </span>
        <span className={`px-1.5 py-0.5 rounded text-[9px] xl:text-[9.5px] font-bold uppercase tracking-wider ${BADGE_CLASSES[data.badgeColor]}`}>
          {data.badge}
        </span>
      </div>
      <h4 className="text-[11.5px] xl:text-xs font-bold text-slate-900 dark:text-slate-100 leading-snug">
        {data.title}
      </h4>
      <p className="text-[10.5px] xl:text-[11px] text-slate-500 dark:text-slate-400 mt-1 leading-relaxed line-clamp-2">
        {data.body}
      </p>
      <div className="mt-2 pt-1.5 border-t border-slate-100 dark:border-slate-800/60 flex items-center justify-between text-[9.5px] xl:text-[10px] font-mono text-slate-400">
        <span>{data.footer.left}</span>
        <span className={`font-semibold ${RIGHT_COLOR_MAP[data.footer.rightColor] || ""}`}>
          {data.footer.right}
        </span>
      </div>
    </div>
  );
};

export const FINDING_CARDS: FindingCardData[] = [
  {
    id: "case",
    type: "case",
    label: "CASE #8942",
    badge: "High Risk",
    badgeColor: "red",
    title: "Guaranteed Returns",
    body: "18% yield assurance given without mandatory risk disclosure.",
    footer: { left: "RM: Vikram M.", right: "Flagged", rightColor: "red" },
    rotation: -1.5,
    offsetX: -20,
  },
  {
    id: "breach",
    type: "breach",
    label: "STATUTORY BREACH",
    badge: "SEBI MF Regs",
    badgeColor: "purple",
    title: "AMFI Code Violation",
    body: "Unregistered promise of assured yield explicitly prohibited.",
    footer: { left: "Confidence", right: "98.7%", rightColor: "purple" },
    rotation: 1.5,
    offsetX: 32,
  },
  {
    id: "evidence",
    type: "evidence",
    label: "EVIDENCE CHAIN",
    badge: "Audit Ready",
    badgeColor: "emerald",
    title: "Forensic Match",
    body: "\"...guaranteed 18% annualised returns with zero downside\" — Cloud DLP: PAN ████",
    footer: { left: "Ledger sealed", right: "Verified", rightColor: "emerald" },
    rotation: -1.0,
    offsetX: -10,
  },
];
