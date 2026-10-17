// frontend/src/components/layout/OwlThemeToggle.tsx
import React from "react";
import { useTheme } from "../../context/ThemeContext";
import { cn } from "../../lib/utils";

interface OwlThemeToggleProps {
  isCollapsed: boolean;
}

export const OwlThemeToggle: React.FC<OwlThemeToggleProps> = ({ isCollapsed }) => {
  const { isDark, toggleTheme } = useTheme();

  const accessibleName = isDark ? "Switch to light theme" : "Switch to dark theme";

  return (
    <div className="w-full flex justify-center">
      <button
        type="button"
        onClick={toggleTheme}
        aria-label={accessibleName}
        title={isCollapsed ? accessibleName : undefined}
        className={cn(
          "group relative transition-colors duration-200 ease-in-out cursor-pointer select-none",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500/60 focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:focus-visible:ring-offset-slate-900",
          isCollapsed
            ? "w-11 h-11 rounded-xl flex items-center justify-center p-1 hover:bg-slate-100 dark:hover:bg-slate-800/80"
            : "w-full rounded-xl overflow-hidden border border-slate-200/80 dark:border-slate-800/80 hover:border-slate-300 dark:hover:border-slate-700 shadow-sm bg-white dark:bg-slate-900/60"
        )}
      >
        {isCollapsed ? (
          /* =========================================================================
             COLLAPSED STATE: Pure Owl Icon (reduced to 2/3 size, min 40x40 click target)
             ========================================================================= */
          <div className="w-9 h-9 flex items-center justify-center relative">
            <svg
              viewBox="78 12 44 54"
              className="w-6 h-6"
              aria-hidden="true"
              focusable="false"
            >
              <defs>
                <linearGradient id="collapsedOwlBodyDark" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#334155" />
                  <stop offset="100%" stopColor="#1E293B" />
                </linearGradient>
                <linearGradient id="collapsedOwlBodyLight" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#475569" />
                  <stop offset="100%" stopColor="#334155" />
                </linearGradient>
                <radialGradient id="collapsedAmberIris" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="#FEF08A" />
                  <stop offset="60%" stopColor="#F59E0B" />
                  <stop offset="100%" stopColor="#D97706" />
                </radialGradient>
              </defs>

              {/* Solid Perch spanning full width */}
              <path
                d="M 68 57.5 Q 100 60 132 57.5 L 132 63.5 Q 100 65.5 68 63.5 Z"
                fill={isDark ? "#334155" : "#78350F"}
                stroke={isDark ? "#475569" : "#92400E"}
                strokeWidth="0.7"
              />

              {/* Owl Body & Horn Tufts */}
              <path
                d="M 87 16 Q 100 21 113 16 Q 115.5 24 116 33 Q 117 44 114 54 Q 107 60 100 60 Q 93 60 86 54 Q 83 44 84 33 Q 84.5 24 87 16 Z"
                fill={isDark ? "url(#collapsedOwlBodyDark)" : "url(#collapsedOwlBodyLight)"}
                stroke={isDark ? "#475569" : "#64748B"}
                strokeWidth="0.9"
              />

              {/* Wing Contours */}
              <path
                d="M 85 35 Q 90 46 92 55"
                fill="none"
                stroke={isDark ? "#475569" : "#64748B"}
                strokeWidth="1.2"
                strokeLinecap="round"
              />
              <path
                d="M 115 35 Q 110 46 108 55"
                fill="none"
                stroke={isDark ? "#475569" : "#64748B"}
                strokeWidth="1.2"
                strokeLinecap="round"
              />

              {/* Chest Plate */}
              <path
                d="M 91 36 Q 100 38 109 36 Q 111 47 107 55 Q 100 58.5 93 55 Q 89 47 91 36 Z"
                fill={isDark ? "#0F172A" : "#F1F5F9"}
                stroke={isDark ? "#1E293B" : "#CBD5E1"}
                strokeWidth="0.6"
              />

              {/* Chest Feather Markings */}
              <path
                d="M 96 44 Q 100 46 104 44"
                fill="none"
                stroke={isDark ? "#334155" : "#94A3B8"}
                strokeWidth="1"
                strokeLinecap="round"
              />
              <path
                d="M 97 49 Q 100 51 103 49"
                fill="none"
                stroke={isDark ? "#334155" : "#94A3B8"}
                strokeWidth="1"
                strokeLinecap="round"
              />

              {/* Facial Disc Accent */}
              <path
                d="M 88 23 Q 100 25.5 112 23"
                fill="none"
                stroke={isDark ? "#64748B" : "#94A3B8"}
                strokeWidth="0.8"
              />

              {/* EYES: Watchful Open (Dark) vs Resting Closed (Light) */}
              {isDark ? (
                <g className="transition-opacity duration-300">
                  {/* Left Eye */}
                  <circle cx="93.5" cy="28.5" r="4.2" fill="#0F172A" stroke="#334155" strokeWidth="0.6" />
                  <circle cx="93.5" cy="28.5" r="3.4" fill="url(#collapsedAmberIris)" />
                  <circle cx="93.5" cy="28.5" r="1.8" fill="#090E17" />
                  <circle cx="94.6" cy="27.4" r="0.75" fill="#FFFFFF" />

                  {/* Right Eye */}
                  <circle cx="106.5" cy="28.5" r="4.2" fill="#0F172A" stroke="#334155" strokeWidth="0.6" />
                  <circle cx="106.5" cy="28.5" r="3.4" fill="url(#collapsedAmberIris)" />
                  <circle cx="106.5" cy="28.5" r="1.8" fill="#090E17" />
                  <circle cx="107.6" cy="27.4" r="0.75" fill="#FFFFFF" />
                </g>
              ) : (
                <g className="transition-opacity duration-300">
                  {/* Left Eye Closed (Resting) */}
                  <path
                    d="M 90.5 28.5 Q 93.5 32 96.5 28.5"
                    fill="none"
                    stroke="#1E293B"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                  {/* Right Eye Closed (Resting) */}
                  <path
                    d="M 103.5 28.5 Q 106.5 32 109.5 28.5"
                    fill="none"
                    stroke="#1E293B"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                </g>
              )}

              {/* Beak */}
              <polygon points="98.7,31 101.3,31 100,34.5" fill="#D97706" />

              {/* Claws Gripping Branch */}
              <path
                d="M 92 57 Q 92.5 60 93.5 58.5 M 94 57 Q 94.5 60.5 95.5 58.5"
                fill="none"
                stroke="#D97706"
                strokeWidth="1.4"
                strokeLinecap="round"
              />
              <path
                d="M 104.5 58.5 Q 105.5 60.5 106 57 M 106.5 58.5 Q 107.5 60 108 57"
                fill="none"
                stroke="#D97706"
                strokeWidth="1.4"
                strokeLinecap="round"
              />
            </svg>
          </div>
        ) : (
          /* =========================================================================
             EXPANDED STATE: Complete Compact Illustrated Scene (Owl + Sky + Celestial)
             ========================================================================= */
          <div className="w-full flex flex-col">
            <div className="relative w-full h-[64px] overflow-hidden">
              <svg
                viewBox="0 0 200 84"
                className="w-full h-full block"
                preserveAspectRatio="xMidYMid slice"
                aria-hidden="true"
                focusable="false"
              >
                <defs>
                  {/* Sky Gradients */}
                  <linearGradient id="nightSkyGrad" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor="#080E1E" />
                    <stop offset="55%" stopColor="#0F1E3A" />
                    <stop offset="100%" stopColor="#1B2D54" />
                  </linearGradient>
                  <linearGradient id="daySkyGrad" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor="#DCEEFB" />
                    <stop offset="55%" stopColor="#EBF4FC" />
                    <stop offset="100%" stopColor="#F5F9FD" />
                  </linearGradient>

                  {/* Branch Wood Gradients */}
                  <linearGradient id="branchWoodLight" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#A16207" />
                    <stop offset="40%" stopColor="#854D0E" />
                    <stop offset="100%" stopColor="#5B290B" />
                  </linearGradient>
                  <linearGradient id="branchWoodDark" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#475569" />
                    <stop offset="40%" stopColor="#334155" />
                    <stop offset="100%" stopColor="#1E293B" />
                  </linearGradient>

                  {/* Owl Body Gradients */}
                  <linearGradient id="owlBodyDark" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#334155" />
                    <stop offset="100%" stopColor="#1E293B" />
                  </linearGradient>
                  <linearGradient id="owlBodyLight" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#475569" />
                    <stop offset="100%" stopColor="#334155" />
                  </linearGradient>

                  {/* Eye Amber Glow */}
                  <radialGradient id="amberIrisGlow" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#FEF08A" />
                    <stop offset="30%" stopColor="#FBBF24" />
                    <stop offset="75%" stopColor="#F59E0B" />
                    <stop offset="100%" stopColor="#B45309" />
                  </radialGradient>

                  {/* Celestial Glow Filters */}
                  <filter id="moonGlow" x="-50%" y="-50%" width="200%" height="200%">
                    <feGaussianBlur in="SourceGraphic" stdDeviation="2.5" result="blur" />
                    <feMerge>
                      <feMergeNode in="blur" />
                      <feMergeNode in="SourceGraphic" />
                    </feMerge>
                  </filter>
                  <filter id="sunGlow" x="-50%" y="-50%" width="200%" height="200%">
                    <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur" />
                    <feMerge>
                      <feMergeNode in="blur" />
                      <feMergeNode in="SourceGraphic" />
                    </feMerge>
                  </filter>
                </defs>

                {/* 1. Sky Background */}
                <rect
                  x="0"
                  y="0"
                  width="200"
                  height="84"
                  fill={isDark ? "url(#nightSkyGrad)" : "url(#daySkyGrad)"}
                  className="transition-colors duration-400 ease-in-out"
                />

                {/* 2. Celestial Elements (Moon vs Sun) */}
                {isDark ? (
                  /* NIGHT SKY: Crescent Moon + Twinkling Stars */
                  <g className="transition-opacity duration-300">
                    {/* Stars */}
                    <circle cx="28" cy="20" r="0.9" fill="#FEF08A" opacity="0.85" className="animate-pulse" />
                    <circle cx="52" cy="34" r="0.75" fill="#FFFFFF" opacity="0.7" />
                    <circle cx="74" cy="18" r="0.9" fill="#FEF08A" opacity="0.8" />
                    <circle cx="140" cy="22" r="0.8" fill="#FFFFFF" opacity="0.75" />
                    <circle cx="188" cy="36" r="0.7" fill="#FEF08A" opacity="0.85" className="animate-pulse" />

                    {/* Small 4-point diamond star */}
                    <path
                      d="M 38 30 Q 38 32 40 32 Q 38 32 38 34 Q 38 32 36 32 Q 38 32 38 30 Z"
                      fill="#FEF08A"
                      opacity="0.9"
                    />

                    {/* Moon Halo Glow */}
                    <circle cx="170" cy="23" r="14" fill="#FEF08A" opacity="0.12" filter="url(#moonGlow)" />

                    {/* Elegant Crescent Moon */}
                    <path
                      d="M 167 16 A 7.5 7.5 0 1 0 176 29 A 6.2 6.2 0 1 1 167 16 Z"
                      fill="#FEF08A"
                      filter="url(#moonGlow)"
                    />
                  </g>
                ) : (
                  /* DAY SKY: Gentle Cloud Wisps + Radiant Golden Sun */
                  <g className="transition-opacity duration-300">
                    {/* Cloud Wisps */}
                    <path
                      d="M 20 28 Q 26 23 32 27 Q 37 24 42 28 Q 45 31 41 33 L 22 33 Z"
                      fill="#FFFFFF"
                      opacity="0.7"
                    />
                    <path
                      d="M 132 30 Q 138 25 144 29 Q 148 27 152 31 L 133 31 Z"
                      fill="#FFFFFF"
                      opacity="0.55"
                    />

                    {/* Sun Corona Glow */}
                    <circle cx="170" cy="24" r="15" fill="#F59E0B" opacity="0.18" filter="url(#sunGlow)" />

                    {/* Radiant Golden Sun */}
                    <circle cx="170" cy="24" r="7.5" fill="#F59E0B" />
                    <circle
                      cx="170"
                      cy="24"
                      r="11.5"
                      fill="none"
                      stroke="#FBBF24"
                      strokeWidth="1.2"
                      strokeDasharray="2.5 3"
                      opacity="0.8"
                    />
                  </g>
                )}

                {/* 3. Sturdy Natural Tree Bough solidly rooted to the left edge */}
                <g>
                  {/* Main limb anchored into left edge (x=0) */}
                  <path
                    d="M 0 44 C 20 48, 48 53, 76 56 C 92 57.5, 108 57.5, 124 56.5 C 148 55, 170 56.5, 188 58.5 C 191 60.5, 186 63, 174 63.5 C 142 64.5, 114 65, 78 64.5 C 44 64, 18 63, 0 69 Z"
                    fill={isDark ? "url(#branchWoodDark)" : "url(#branchWoodLight)"}
                    stroke={isDark ? "#3E4E6E" : "#92400E"}
                    strokeWidth="0.8"
                  />
                  {/* Top woodgrain highlight catching light */}
                  <path
                    d="M 2 46 C 24 50, 50 54.5, 78 57.2 C 95 58.2, 110 58.2, 126 57.2 C 150 56, 172 57.5, 185 59.5"
                    fill="none"
                    stroke={isDark ? "#64748B" : "#B45309"}
                    strokeWidth="0.75"
                    strokeLinecap="round"
                    opacity="0.8"
                  />
                  {/* Bark contour shadow line along lower rim */}
                  <path
                    d="M 0 63 C 24 61.5, 54 62.5, 84 63.5 C 114 64, 144 63.5, 172 62.5 C 166 64, 140 64.8, 110 65 C 76 65, 38 64.5, 0 69 Z"
                    fill={isDark ? "#0F172A" : "#451A03"}
                    opacity="0.7"
                  />
                  {/* Natural branch offshoot / node near base */}
                  <path
                    d="M 32 60 C 36 65, 42 68, 48 70 C 45 69, 39 66, 36 61"
                    fill="none"
                    stroke={isDark ? "#3E4E6E" : "#92400E"}
                    strokeWidth="0.8"
                  />
                  {/* Tender leaf sprout at branch node */}
                  <path
                    d="M 48 70 C 53 68, 56 71, 53 73 C 50 74, 48 72, 48 70 Z"
                    fill={isDark ? "#10B981" : "#16A34A"}
                  />
                  {/* Fresh leaf sprigs at branch tip */}
                  <path
                    d="M 176 58 C 182 53.5, 188 56, 184 60 C 180 61, 178 59, 176 58 Z"
                    fill={isDark ? "#10B981" : "#16A34A"}
                  />
                  <path
                    d="M 183 58 C 189 55.5, 193 58, 190 61 C 186 62, 183 60, 183 58 Z"
                    fill={isDark ? "#34D399" : "#22C55E"}
                  />
                </g>

                {/* 4. The Central Owl (Scaled to 2/3 of original size, static on hover) */}
                <g transform="translate(100, 58) scale(0.67) translate(-100, -58)">
                  {/* Owl Body & Horn Tufts */}
                  <path
                    d="M 87 16 Q 100 21 113 16 Q 115.5 24 116 33 Q 117 44 114 54 Q 107 60 100 60 Q 93 60 86 54 Q 83 44 84 33 Q 84.5 24 87 16 Z"
                    fill={isDark ? "url(#owlBodyDark)" : "url(#owlBodyLight)"}
                    stroke={isDark ? "#475569" : "#64748B"}
                    strokeWidth="0.9"
                  />

                  {/* Wings */}
                  <path
                    d="M 85 35 Q 90 46 92 55"
                    fill="none"
                    stroke={isDark ? "#475569" : "#64748B"}
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                  <path
                    d="M 115 35 Q 110 46 108 55"
                    fill="none"
                    stroke={isDark ? "#475569" : "#64748B"}
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />

                  {/* Chest Plate */}
                  <path
                    d="M 91 36 Q 100 38 109 36 Q 111 47 107 55 Q 100 58.5 93 55 Q 89 47 91 36 Z"
                    fill={isDark ? "#0F172A" : "#F1F5F9"}
                    stroke={isDark ? "#1E293B" : "#CBD5E1"}
                    strokeWidth="0.6"
                  />

                  {/* Chest Feather Markings */}
                  <path
                    d="M 96 44 Q 100 46 104 44"
                    fill="none"
                    stroke={isDark ? "#334155" : "#94A3B8"}
                    strokeWidth="1"
                    strokeLinecap="round"
                  />
                  <path
                    d="M 97 49 Q 100 51 103 49"
                    fill="none"
                    stroke={isDark ? "#334155" : "#94A3B8"}
                    strokeWidth="1"
                    strokeLinecap="round"
                  />
                  <path
                    d="M 98 53.5 Q 100 55 102 53.5"
                    fill="none"
                    stroke={isDark ? "#334155" : "#94A3B8"}
                    strokeWidth="0.8"
                    strokeLinecap="round"
                  />

                  {/* Facial Disc Ridge */}
                  <path
                    d="M 88 23 Q 100 25.5 112 23"
                    fill="none"
                    stroke={isDark ? "#64748B" : "#94A3B8"}
                    strokeWidth="0.8"
                  />

                  {/* EYES: Watchful Open (Dark) vs Resting Closed (Light) */}
                  {isDark ? (
                    <g className="transition-opacity duration-300">
                      {/* Left Eye */}
                      <circle cx="93.5" cy="28.5" r="4.2" fill="#0F172A" stroke="#334155" strokeWidth="0.6" />
                      <circle cx="93.5" cy="28.5" r="3.4" fill="url(#amberIrisGlow)" />
                      <circle cx="93.5" cy="28.5" r="1.8" fill="#090E17" />
                      <circle cx="94.6" cy="27.4" r="0.75" fill="#FFFFFF" />

                      {/* Right Eye */}
                      <circle cx="106.5" cy="28.5" r="4.2" fill="#0F172A" stroke="#334155" strokeWidth="0.6" />
                      <circle cx="106.5" cy="28.5" r="3.4" fill="url(#amberIrisGlow)" />
                      <circle cx="106.5" cy="28.5" r="1.8" fill="#090E17" />
                      <circle cx="107.6" cy="27.4" r="0.75" fill="#FFFFFF" />
                    </g>
                  ) : (
                    <g className="transition-opacity duration-300">
                      {/* Left Eye Closed (Resting) */}
                      <path
                        d="M 90.5 28.5 Q 93.5 32 96.5 28.5"
                        fill="none"
                        stroke="#1E293B"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                      />
                      {/* Right Eye Closed (Resting) */}
                      <path
                        d="M 103.5 28.5 Q 106.5 32 109.5 28.5"
                        fill="none"
                        stroke="#1E293B"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                      />
                    </g>
                  )}

                  {/* Beak */}
                  <polygon points="98.7,31 101.3,31 100,34.5" fill="#D97706" />

                  {/* Claws */}
                  <path
                    d="M 92 57 Q 92.5 60 93.5 58.5 M 94 57 Q 94.5 60.5 95.5 58.5"
                    fill="none"
                    stroke="#D97706"
                    strokeWidth="1.4"
                    strokeLinecap="round"
                  />
                  <path
                    d="M 104.5 58.5 Q 105.5 60.5 106 57 M 106.5 58.5 Q 107.5 60 108 57"
                    fill="none"
                    stroke="#D97706"
                    strokeWidth="1.4"
                    strokeLinecap="round"
                  />
                </g>
              </svg>
            </div>

            {/* Micro-bar below scene with theme status */}
            <div className="px-2.5 py-1.5 flex items-center justify-between border-t border-slate-200/70 dark:border-slate-800/70 bg-slate-50/90 dark:bg-slate-950/70 text-[10px]">
              <span className="font-mono font-medium text-slate-700 dark:text-slate-300 flex items-center gap-1.5 truncate">
                <span
                  className={cn(
                    "w-1.5 h-1.5 rounded-full shrink-0",
                    isDark ? "bg-amber-400 shadow-[0_0_6px_rgba(251,191,36,0.8)]" : "bg-sky-500"
                  )}
                />
                {isDark ? "Watchful Surveillance" : "Day Audit Mode"}
              </span>
              <span className="text-[9px] font-mono uppercase tracking-wider text-slate-500 dark:text-slate-400 shrink-0 font-semibold">
                {isDark ? "Dark" : "Light"}
              </span>
            </div>
          </div>
        )}
      </button>
    </div>
  );
};
