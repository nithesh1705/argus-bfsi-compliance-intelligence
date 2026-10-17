// frontend/src/pages/Login/index.tsx
import React, { useState, useRef, useCallback, useEffect, useId } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { useTheme } from "../../context/ThemeContext";
import {
  Lock,
  User,
  Eye,
  EyeOff,
  AlertCircle,
  Loader2,
  KeyRound,
  Sun,
  Moon,
} from "lucide-react";
import { AudioWaveCanvas } from "./components/AudioWaveCanvas";
import { FindingCard, FINDING_CARDS } from "./components/FindingCard";
import { FindingConnectors } from "./components/FindingConnectors";

// Cycle through speech phrases below the wave
const WAVE_CAPTIONS = [
  "\"…18% guaranteed return with zero risk…\"",
  "\"…don't worry about the disclaimers…\"",
  "\"…our desk guarantees the payout…\"",
  "\"…fully safe, no SEBI concerns here…\"",
];

const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

export const Login: React.FC = () => {
  const { login, isAuthenticated } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();

  // ─── Form state ──────────────────────────────────────────────────────────────
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // ─── Animation state ─────────────────────────────────────────────────────────
  const [amplitudeBoost, setAmplitudeBoost] = useState(0);
  const [errorAnim, setErrorAnim] = useState(false);
  const [submitPulse, setSubmitPulse] = useState(false);
  const [captionIdx, setCaptionIdx] = useState(0);

  // ─── Stage & Card Refs for SVG Connectors ────────────────────────────────────
  const stageRef = useRef<HTMLDivElement>(null);
  const loginCardRef = useRef<HTMLDivElement>(null);
  const finding0Ref = useRef<HTMLDivElement>(null);
  const finding1Ref = useRef<HTMLDivElement>(null);
  const finding2Ref = useRef<HTMLDivElement>(null);
  const findingRefs = useRef([finding0Ref, finding1Ref, finding2Ref]).current;

  const boostTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const errorTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ─── Reduced motion ──────────────────────────────────────────────────────────
  const [prefersReduced, setPrefersReduced] = useState(
    () => window.matchMedia(REDUCED_MOTION_QUERY).matches
  );
  useEffect(() => {
    const mq = window.matchMedia(REDUCED_MOTION_QUERY);
    const handler = (e: MediaQueryListEvent) => setPrefersReduced(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  // ─── Redirect if already authenticated ───────────────────────────────────────
  useEffect(() => {
    if (isAuthenticated) {
      const origin = (location.state as any)?.from?.pathname || "/";
      navigate(origin, { replace: true });
    }
  }, [isAuthenticated, navigate, location]);

  // ─── Wave boost on typing ────────────────────────────────────────────────────
  const triggerBoost = useCallback(() => {
    if (prefersReduced) return;
    setAmplitudeBoost(1);
    if (boostTimerRef.current) clearTimeout(boostTimerRef.current);
    boostTimerRef.current = setTimeout(() => {
      setAmplitudeBoost(0);
    }, 1200);
  }, [prefersReduced]);

  // ─── Caption cycle ────────────────────────────────────────────────────────────
  useEffect(() => {
    if (prefersReduced) return;
    const t = setInterval(() => {
      setCaptionIdx((i) => (i + 1) % WAVE_CAPTIONS.length);
    }, 4500);
    return () => clearInterval(t);
  }, [prefersReduced]);

  // ─── Submission ───────────────────────────────────────────────────────────────
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError("Please enter both username/email and password.");
      return;
    }

    setError(null);
    setIsSubmitting(true);
    if (!prefersReduced) setSubmitPulse(true);

    try {
      await login({ username: username.trim(), password });
      setTimeout(() => {
        const origin = (location.state as any)?.from?.pathname || "/";
        navigate(origin, { replace: true });
      }, 600);
    } catch (err: any) {
      const message =
        err?.data?.message ||
        err?.message ||
        "Invalid username or password. Please verify your credentials.";
      setError(message);
      setSubmitPulse(false);

      if (!prefersReduced) {
        setErrorAnim(true);
        if (errorTimerRef.current) clearTimeout(errorTimerRef.current);
        errorTimerRef.current = setTimeout(() => setErrorAnim(false), 1100);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // ─── IDs for accessibility ────────────────────────────────────────────────────
  const usernameId = useId();
  const passwordId = useId();
  const errorId = useId();

  const shakeClass = errorAnim && !prefersReduced ? "login-card-shake" : "";

  return (
    <div
      className="h-screen w-screen overflow-hidden relative flex flex-col justify-center select-none"
      style={{
        background: isDark
          ? "radial-gradient(ellipse 90% 70% at 50% 50%, #0b1120 0%, #06080f 100%)"
          : "radial-gradient(ellipse 90% 70% at 50% 50%, #f0f4ff 0%, #e8edf5 100%)",
      }}
    >
      {/* Background dotted grid with smooth radial falloff (no edge line artifacts) */}
      <div
        aria-hidden="true"
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: isDark
            ? "radial-gradient(#334155 1.2px, transparent 1.2px)"
            : "radial-gradient(#94a3b8 1.2px, transparent 1.2px)",
          backgroundSize: "32px 32px",
          opacity: isDark ? 0.35 : 0.25,
          maskImage: "radial-gradient(ellipse 70% 60% at 50% 50%, #000 35%, transparent 100%)",
          WebkitMaskImage: "radial-gradient(ellipse 70% 60% at 50% 50%, #000 35%, transparent 100%)",
        }}
      />

      {/* Subtle brand glow behind card */}
      <div
        aria-hidden="true"
        className="absolute pointer-events-none"
        style={{
          width: "560px",
          height: "560px",
          background: isDark
            ? "radial-gradient(circle, rgba(220,38,38,0.14) 0%, transparent 70%)"
            : "radial-gradient(circle, rgba(220,38,38,0.08) 0%, transparent 70%)",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
        }}
      />

      {/* ─── Theme toggle ──────────────────────────────────────────────────────── */}
      <button
        onClick={toggleTheme}
        type="button"
        aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
        className="absolute top-5 right-6 z-30 p-2.5 rounded-full bg-white/80 dark:bg-slate-800/80 border border-slate-200/60 dark:border-slate-700/60 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-all shadow-md backdrop-blur-md cursor-pointer hover:scale-105 active:scale-95"
      >
        {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-600" />}
      </button>

      {/* ═══════════════════════════════════════════════════════════════════════ */}
      {/* THREE-COLUMN STAGE: left (wave) | login card | right (finding cards)  */}
      {/* ═══════════════════════════════════════════════════════════════════════ */}
      <div
        ref={stageRef}
        className="relative z-10 w-full h-full flex items-center justify-between overflow-hidden"
      >
        {/* ─── COLUMN 1: LEFT (Waveform area) ─────────────────────────────────── */}
        <div className="relative h-full flex-1 min-w-[140px] flex flex-col justify-between overflow-visible pointer-events-none">
          {/* Pill: sits top-left above wave area, with subtle backdrop & z-index above canvas */}
          <div className="relative z-20 pt-6 pl-6 sm:pt-8 sm:pl-8 pointer-events-auto">
            <div
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-[10.5px] sm:text-[11px] font-mono tracking-wide shadow-sm whitespace-nowrap"
              style={{
                background: isDark ? "rgba(15,23,42,0.88)" : "rgba(255,255,255,0.94)",
                border: isDark ? "1px solid rgba(51,65,85,0.7)" : "1px solid rgba(203,213,225,0.9)",
                color: isDark ? "#cbd5e1" : "#334155",
                backdropFilter: "blur(12px)",
                boxShadow: isDark ? "0 2px 10px rgba(0,0,0,0.3)" : "0 2px 10px rgba(0,0,0,0.06)",
              }}
            >
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
              RM ↔ Customer Call · Streaming
            </div>
          </div>

          {/* Audio Waveform Canvas: fills column, ends EXACTLY at card left edge */}
          <div className="absolute inset-0 z-10 pointer-events-none overflow-hidden">
            <AudioWaveCanvas
              isDark={isDark}
              amplitudeBoost={amplitudeBoost}
              errorState={errorAnim}
              submitPulse={submitPulse}
            />
          </div>

          {/* Caption: sits in reserved space BELOW the wave (~78% of viewport height) */}
          <div className="relative z-20 pb-6 pl-6 sm:pb-8 sm:pl-8 pointer-events-auto">
            <div
              className="inline-block px-3 py-1.5 rounded-lg text-[10.5px] sm:text-xs font-mono italic max-w-[260px] xl:max-w-[340px] leading-relaxed transition-opacity duration-500"
              style={{
                background: isDark ? "rgba(15,23,42,0.8)" : "rgba(255,255,255,0.88)",
                border: isDark ? "1px solid rgba(51,65,85,0.5)" : "1px solid rgba(203,213,225,0.7)",
                color: isDark ? "#94a3b8" : "#475569",
                backdropFilter: "blur(10px)",
                boxShadow: isDark ? "0 2px 8px rgba(0,0,0,0.2)" : "0 2px 8px rgba(0,0,0,0.04)",
              }}
            >
              {WAVE_CAPTIONS[captionIdx]}
            </div>
          </div>
        </div>

        {/* ─── COLUMN 2: CENTRE (Login Card) ─────────────────────────────────── */}
        <div className="relative shrink-0 z-20" style={{ zIndex: 20 }}>
          {/* Wave input node at card left-edge middle */}
          <div
            className="absolute -left-2 top-1/2 -translate-y-1/2 z-30 pointer-events-none flex items-center justify-center"
            title="Acoustic Ingestion Node"
          >
            <div
              className="w-4 h-4 rounded-full flex items-center justify-center"
              style={{
                background: isDark ? "#0f172a" : "#ffffff",
                border: isDark ? "1.5px solid #38bdf8" : "1.5px solid #ef4444",
                boxShadow: isDark ? "0 0 10px rgba(56,189,248,0.5)" : "0 0 10px rgba(239,68,68,0.4)",
              }}
            >
              <div
                className="w-2 h-2 rounded-full animate-pulse"
                style={{ background: isDark ? "#38bdf8" : "#ef4444" }}
              />
            </div>
          </div>

          <div
            ref={loginCardRef}
            className={`w-[390px] lg:w-[440px] xl:w-[490px] rounded-2xl relative ${shakeClass}`}
            style={{
              background: isDark
                ? "rgba(12, 18, 35, 0.94)"
                : "rgba(255, 255, 255, 0.96)",
              border: isDark
                ? "1px solid rgba(51, 65, 85, 0.85)"
                : "1px solid rgba(203, 213, 225, 0.9)",
              boxShadow: isDark
                ? "0 0 0 1px rgba(220,38,38,0.1), 0 4px 6px -1px rgba(0,0,0,0.5), 0 25px 50px -12px rgba(0,0,0,0.7), inset 0 0 60px rgba(220,38,38,0.02)"
                : "0 0 0 1px rgba(220,38,38,0.06), 0 4px 6px -1px rgba(0,0,0,0.06), 0 25px 50px -12px rgba(0,0,0,0.12)",
              backdropFilter: "blur(24px)",
              WebkitBackdropFilter: "blur(24px)",
            }}
          >
            <div className="p-7 xl:p-8">
              {/* Brand Header */}
              <div className="flex flex-col items-center text-center mb-6 xl:mb-7">
                <div className="relative mb-3">
                  <img
                    src="/icon.png"
                    alt="ARGUS"
                    className="w-14 h-14 xl:w-16 xl:h-16 rounded-2xl shadow-xl object-contain"
                    style={{ boxShadow: "0 0 24px rgba(59,130,246,0.25)" }}
                  />
                  <span className="absolute -bottom-1 -right-1 flex h-4 w-4">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
                    <span className="relative inline-flex rounded-full h-4 w-4 bg-emerald-500 border-2 border-slate-900" />
                  </span>
                </div>
                <h1 className="text-xl xl:text-2xl font-bold tracking-widest text-slate-900 dark:text-slate-100 font-sans">
                  ARGUS
                </h1>
                <p className="text-[11px] xl:text-xs mt-1 font-medium text-slate-500 dark:text-slate-400">
                  Autonomous Compliance Intelligence Platform
                </p>
              </div>

              {/* Error Alert */}
              {error && (
                <div
                  id={errorId}
                  role="alert"
                  aria-live="assertive"
                  className="mb-4 p-3 rounded-xl flex items-start gap-2.5 text-xs"
                  style={{
                    background: "rgba(239,68,68,0.08)",
                    border: "1px solid rgba(239,68,68,0.25)",
                    color: isDark ? "rgba(252,165,165,0.95)" : "rgba(185,28,28,0.95)",
                  }}
                >
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-red-500" />
                  <div className="flex-1 leading-relaxed">{error}</div>
                </div>
              )}

              {/* Form */}
              <form onSubmit={handleSubmit} noValidate className="space-y-3.5 xl:space-y-4" aria-describedby={error ? errorId : undefined}>
                {/* Username */}
                <div className="space-y-1">
                  <label htmlFor={usernameId} className="block text-xs font-medium text-slate-700 dark:text-slate-300">
                    Username or Email
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                      <User className="w-4 h-4" />
                    </div>
                    <input
                      id={usernameId}
                      type="text"
                      value={username}
                      onChange={(e) => { setUsername(e.target.value); triggerBoost(); }}
                      placeholder="admin or audit_officer"
                      autoComplete="username"
                      required
                      aria-required="true"
                      className="w-full pl-10 pr-3.5 py-2.5 rounded-lg text-sm font-mono transition-all focus:outline-none"
                      style={{
                        background: isDark ? "rgba(15,23,42,0.7)" : "rgba(248,250,252,0.9)",
                        border: isDark ? "1px solid rgba(51,65,85,0.8)" : "1px solid rgba(203,213,225,0.9)",
                        color: isDark ? "#e2e8f0" : "#0f172a",
                      }}
                      onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(239,68,68,0.5)"; e.currentTarget.style.boxShadow = "0 0 0 2px rgba(239,68,68,0.15)"; }}
                      onBlur={(e) => { e.currentTarget.style.borderColor = isDark ? "rgba(51,65,85,0.8)" : "rgba(203,213,225,0.9)"; e.currentTarget.style.boxShadow = "none"; }}
                    />
                  </div>
                </div>

                {/* Password */}
                <div className="space-y-1">
                  <label htmlFor={passwordId} className="block text-xs font-medium text-slate-700 dark:text-slate-300">
                    Password
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                      <Lock className="w-4 h-4" />
                    </div>
                    <input
                      id={passwordId}
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => { setPassword(e.target.value); triggerBoost(); }}
                      placeholder="••••••••••••"
                      autoComplete="current-password"
                      required
                      aria-required="true"
                      className="w-full pl-10 pr-10 py-2.5 rounded-lg text-sm font-mono transition-all focus:outline-none"
                      style={{
                        background: isDark ? "rgba(15,23,42,0.7)" : "rgba(248,250,252,0.9)",
                        border: isDark ? "1px solid rgba(51,65,85,0.8)" : "1px solid rgba(203,213,225,0.9)",
                        color: isDark ? "#e2e8f0" : "#0f172a",
                      }}
                      onFocus={(e) => { e.currentTarget.style.borderColor = "rgba(239,68,68,0.5)"; e.currentTarget.style.boxShadow = "0 0 0 2px rgba(239,68,68,0.15)"; }}
                      onBlur={(e) => { e.currentTarget.style.borderColor = isDark ? "rgba(51,65,85,0.8)" : "rgba(203,213,225,0.9)"; e.currentTarget.style.boxShadow = "none"; }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      className="absolute inset-y-0 right-0 pr-3.5 flex items-center transition-colors cursor-pointer text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Remember me & token duration */}
                <div className="flex items-center justify-between pt-0.5">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      className="w-3.5 h-3.5 rounded cursor-pointer accent-red-600"
                    />
                    <span className="text-xs text-slate-500 dark:text-slate-400">
                      Remember session
                    </span>
                  </label>
                  <span className="text-[11px] font-mono text-slate-400 dark:text-slate-500">
                    Audit Token: 24h
                  </span>
                </div>

                {/* Submit button */}
                <button
                  type="submit"
                  disabled={isSubmitting}
                  aria-busy={isSubmitting}
                  className="w-full mt-1 py-2.5 px-4 rounded-lg text-sm font-semibold tracking-wide transition-all flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed group cursor-pointer"
                  style={{
                    background: isSubmitting
                      ? "rgba(185,28,28,0.8)"
                      : "rgb(220,38,38)",
                    color: "#fff",
                    boxShadow: "0 4px 14px rgba(220,38,38,0.35)",
                  }}
                  onMouseEnter={(e) => { if (!isSubmitting) e.currentTarget.style.background = "rgb(239,68,68)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = isSubmitting ? "rgba(185,28,28,0.8)" : "rgb(220,38,38)"; }}
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                      <span>Authenticating…</span>
                    </>
                  ) : (
                    <>
                      <KeyRound className="w-4 h-4 transition-transform group-hover:rotate-12" aria-hidden="true" />
                      <span>Sign In to Surveillance Console</span>
                    </>
                  )}
                </button>
              </form>

              {/* LISTEN • DETECT • COMPLY */}
              <div
                className="mt-6 pt-3.5 xl:mt-7 xl:pt-4 border-t flex items-center justify-center gap-3 text-[11px] font-mono font-semibold tracking-widest uppercase"
                style={{ borderColor: isDark ? "rgba(30,41,59,0.8)" : "rgba(203,213,225,0.7)" }}
              >
                <span className="flex items-center gap-1.5 text-blue-500 dark:text-blue-400">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                  Listen
                </span>
                <span className="text-slate-300 dark:text-slate-700">•</span>
                <span className="flex items-center gap-1.5 text-purple-500 dark:text-purple-400">
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-500" />
                  Detect
                </span>
                <span className="text-slate-300 dark:text-slate-700">•</span>
                <span className="flex items-center gap-1.5 text-emerald-500 dark:text-emerald-400">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  Comply
                </span>
              </div>
            </div>
          </div>

          {/* Footer note */}
          <p className="text-[10.5px] xl:text-[11px] font-mono text-center mt-3 text-slate-400 dark:text-slate-600">
            ARGUS AI Compliance Surveillance Engine · Secure Enterprise Session
          </p>
        </div>

        {/* ─── CLEAR SPACE FOR CONNECTORS (at least 120px) ────────────────────── */}
        <div className="w-[120px] lg:w-[130px] xl:w-[140px] shrink-0 pointer-events-none" />

        {/* ─── COLUMN 3: RIGHT (Finding Cards) ─────────────────────────────────── */}
        <div
          className="flex flex-col gap-6 xl:gap-8 shrink-0 relative mr-12 lg:mr-14"
          style={{
            width: "300px",
            maxWidth: "360px",
            zIndex: 10,
          }}
        >
          {FINDING_CARDS.map((card, i) => (
            <FindingCard
              key={card.id}
              data={card}
              cardRef={findingRefs[i]}
              isDark={isDark}
              isConnectorHovered={false}
              submitPulse={submitPulse}
            />
          ))}
          {/* Footnote */}
          {/* <p className="text-[10px] font-mono text-center text-slate-400 dark:text-slate-600 -mt-2">
            Illustrative preview
          </p> */}
        </div>

        {/* ─── CONNECTORS SVG OVERLAY (sized to stage with ResizeObserver) ─────── */}
        <FindingConnectors
          stageRef={stageRef}
          cardRef={loginCardRef}
          findingRefs={findingRefs}
          isDark={isDark}
          submitPulse={submitPulse}
          prefersReducedMotion={prefersReduced}
        />
      </div>

      {/* Shake keyframe */}
      <style>{`
        @keyframes loginCardShake {
          0%, 100% { transform: translateX(0); }
          15%  { transform: translateX(-6px); }
          30%  { transform: translateX(5px); }
          45%  { transform: translateX(-4px); }
          60%  { transform: translateX(3px); }
          75%  { transform: translateX(-2px); }
          90%  { transform: translateX(1px); }
        }
        .login-card-shake {
          animation: loginCardShake 0.55s cubic-bezier(0.36, 0.07, 0.19, 0.97) both;
        }
        @media (prefers-reduced-motion: reduce) {
          .login-card-shake { animation: none; }
        }
      `}</style>
    </div>
  );
};
